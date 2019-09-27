# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from scrapy import signals
import random
import logging
import pymysql
import time
from hongdun.settings import *
from scrapy.http import HtmlResponse

"""配置scrapy信号，记录爬取成功的url和不成功的url"""
class HongdunSpiderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, dict or Item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Response, dict
        # or Item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)

"""循环更换 User Agent"""
class UserAgentDownloaderMiddleware(object):

    def __init__(self, user_agent=USER_AGENT, headers=DEFAULT_REQUEST_HEADERS):
        self.headers = headers
        self.USER_AGENT = user_agent

    def process_request(self, request, spider):
        request.headers.setdefault(b"User-Agent", random.choice(self.USER_AGENT))

"""使用代理IP池"""
class HttpProxyDownloaderMiddleware(object):

    # 一些异常情况汇总
    EXCEPTIONS_TO_CHANGE = (TimeoutError, ConnectionRefusedError)

    def __init__(self, host=DB_HOST, db=DB, port=DB_PORT, user=DB_USER, pwd=DB_PASSWORD):
        # 链接数据库 decode_responses设置取出的编码为str
        self.conn = pymysql.connect(
            host=host,
            db=db,
            port=port,
            user=user,
            password=pwd,
            charset='utf8',
            use_unicode=True
        )
        self.cursor = self.conn.cursor()
        self.logger = logging.getLogger('web')

    def random_proxy(self):
        """
        随机获取有效代理，首先尝试获取最高分数代理，如果不存在，按照排名获取，否则异常
        :return: 随机代理
        """
        self.cursor.execute("""SELECT proxy FROM {} a WHERE score = (SELECT MAX(b.score) FROM {} b);""".format(IP_TABLE, IP_TABLE))
        result = self.cursor.fetchall()
        if len(result):
            proxy = random.choice(result)[0]
            full_proxy = "http://" + proxy
            self.logger.warning("#############" + str(full_proxy) + "试用中##############")
            return proxy, full_proxy
        else:
            raise PoolEmptyError

    def assign_max_score(self, proxy):
        """
        将代理设置为MAX_SCORE
        :param proxy: 代理
        :return: 设置结果
        """
        print('代理', proxy, '可用，设置为', MAX_SCORE)
        self.cursor.execute("""UPDATE %s SET score = %d WHERE proxy = '%s';""" % (IP_TABLE, MAX_SCORE, proxy))
        self.conn.commit()

    def decrease_score(self, proxy):
        """
        代理值从最高分100开始减25分，小于最小值则删除
        :param proxy: 代理
        :return: 修改后的代理分数
        """
        self.cursor.execute("""SELECT score FROM %s WHERE proxy = '%s';""" % (IP_TABLE, proxy))
        result = self.cursor.fetchone()
        score = result[0]
        if score and score > MIN_SCORE:
            print('代理', proxy, '当前分数', score, '减 25')
            self.cursor.execute("""UPDATE %s SET score = %d WHERE proxy = '%s';""" % (IP_TABLE, score - 25, proxy))
            self.conn.commit()
        else:
            print('代理', proxy, '当前分数', score, '移除')
            self.cursor.execute("""DELETE FROM %s WHERE proxy = '%s';""" % (IP_TABLE, proxy))
            self.conn.commit()
            logging.warning("#################" + proxy + "不可用，已经删除########################")

    def process_request(self, request, spider):
        # 随机选取一个分数最高的 IP
        proxy, full_proxy = self.random_proxy()
        request.meta["proxy"] = full_proxy
        request.meta["raw_proxy"] = proxy

    def process_response(self, request, response, spider):
        http_status = response.status
        # 根据response的状态判断 ，200的话ip设置为MAX_SCORE重新写入数据库，返回response到下一环节
        if http_status == 200:
            proxy = request.meta["raw_proxy"]
            self.assign_max_score(proxy)
            return response
        # 403有可能是因为user-agent不可用引起，和代理ip无关，返回请求即可
        elif http_status == 403:
            self.logger.warning("#########################403重新请求中############################")
            return request.replace(dont_filter=True)
        # 其他情况姑且被判定ip不可用，score 扣一分，score为0的删掉
        else:
            proxy = request.meta["raw_proxy"]
            self.decrease_score(proxy)
            return request.replace(dont_filter=True)

    def process_exception(self, request, exception, spider):
        # 其他一些timeout之类异常判断后的处理，ip不可用删除即可
        if isinstance(exception, self.EXCEPTIONS_TO_CHANGE) and request.meta.get('proxy', False):
            proxy = request.meta["raw_proxy"]
            self.decrease_score(proxy)
            self.logger.debug("Proxy {}链接出错{}.".format(request.meta['proxy'], exception))
            return request.replace(dont_filter=True)

"""随机时间缓冲"""
class RandomDelayDownloaderMiddleware(object):
    def __init__(self):
        self.delay = RANDOM_DELAY

    def process_request(self, request, spider):
        delay = random.randint(0, self.delay)
        logging.debug("### random delay: %s s ###" % delay)
        time.sleep(delay)

"""302重定向问题"""
class DealingRedirectDownloaderMiddleware(object):
    def process_response(self, request, response, spider):
        if response.status == 302:
            cookies = spider.get_cookies()
            cookies_dict = {}
            for cookie in cookies:
                cookies_dict[cookie["name"]] = cookie["value"]

            headers = {
                'set-cookie': cookies_dict
            }
            return HtmlResponse(url=spider.browser.current_url, body=spider.browser.page_source,
                                encoding='utf8', request=request, headers=headers)
        return response
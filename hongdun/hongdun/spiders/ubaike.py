# -*- coding: utf-8 -*-
import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from hongdun.items import HongdunItem
import re


class UbaikeSpider(CrawlSpider):
    name = 'ubaike'
    allowed_domains = ['ubaike.cn']
    start_urls = ['https://www.ubaike.cn']
    # start_urls = ['https://www.ubaike.cn/topic/']
    http_handlestatus_list = [301, 302, 500]
    meta = {'dont_redirect': True, "http_handlestatus_list": [302]}

    rules = (
        Rule(LinkExtractor(allow=r'.+class_3\d{1}.html'), follow=True),
        # Rule(LinkExtractor(allow=r'/topic/default/\d+.html'), callback='parse_item', follow=True),
        Rule(LinkExtractor(allow=r'.+class_\d+/\d+.html'), callback='parse_item', follow=True),
    )

    def start_requests(self):
        return [scrapy.Request(self.start_urls[0], meta=self.meta)]


    def parse_item(self, response):
        corp_name = response.xpath(""".//div[@class='content']/a/text()""").extract()
        ic_code_list = response.xpath(""".//div[@class='content']//span[contains(text(),"代码")]/../span[1]/text()""").extract()
        ic_code = [re.split('：| :', i)[1] for i in ic_code_list]
        legal_person_list = response.xpath(""".//div[@class='content']//span[contains(text(),"代码")]/../span[2]/text()""").extract()
        legal_person = [re.split('：| :', p)[1] for p in legal_person_list]
        addr_list = response.xpath(""".//div[@class='content']//p[2]//span/text()""").extract()
        addr = [re.split('：| :', a)[1] for a in addr_list]

        for i in range(len(corp_name)):
            item = HongdunItem()

            item['corp_name'] = corp_name[i]
            item['ic_code'] = ic_code[i]
            item['legal_person'] = legal_person[i]
            item['addr'] = addr[i]

            yield item

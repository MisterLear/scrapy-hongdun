# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from hongdun.items import HongdunItem
from hongdun.settings import *
import pymysql.cursors

class HongdunPipeline(object):
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

        self.cursor.execute("""Create TABLE IF NOT EXISTS hongdun (
        corp_name VARCHAR(100),
        ic_code VARCHAR(30) KEY,
        legal_person VARCHAR(10),
        addr VARCHAR(2000)
        );""")
        self.conn.commit()

        # 设置数据库可以储存中文
        self.cursor.execute("""ALTER TABLE %s CHANGE corp_name corp_name VARCHAR(100) character SET utf8 collate utf8_unicode_ci default '';"""%ITEM_TABLE)
        self.conn.commit()
        self.cursor.execute("""ALTER TABLE %s CHANGE legal_person legal_person VARCHAR(40) character SET utf8 collate utf8_unicode_ci default '';"""%ITEM_TABLE)
        self.conn.commit()
        self.cursor.execute("""ALTER TABLE %s CHANGE addr addr VARCHAR(2000) character SET utf8 collate utf8_unicode_ci default '';""" % ITEM_TABLE)
        self.conn.commit()

    def process_item(self, item, spider):

        self.cursor.execute("""INSERT IGNORE INTO %s (corp_name, ic_code, legal_person, addr) VALUES ('%s', '%s', '%s', '%s');""" % (ITEM_TABLE,
            item['corp_name'], item['ic_code'], item['legal_person'], item['addr']))
        try:
            self.conn.commit()
        except:
            self.conn.rollback()
            print(str(item['corp_name']) + "导入失败")

        return item

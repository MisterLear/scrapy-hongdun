# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class HongdunItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    corp_name = scrapy.Field()
    ic_code = scrapy.Field()
    legal_person = scrapy.Field()
    addr = scrapy.Field()

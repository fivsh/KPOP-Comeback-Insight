import scrapy

class PostItem(scrapy.Item):
    platform = scrapy.Field()
    title = scrapy.Field()
    author = scrapy.Field()
    view_count = scrapy.Field()
    likes = scrapy.Field()
    phase = scrapy.Field()
    publish_time = scrapy.Field()
import sqlite3

class DemoPipeline:
    def open_spider(self, spider):
        self.conn = sqlite3.connect(r'D:\KPOPproject\kpop_demo.db')
        self.cursor = self.conn.cursor()
        # 关键：清空旧数据，只保留当前关键词的
        self.cursor.execute("DELETE FROM posts")
        self.conn.commit()
        spider.logger.info("已清空旧数据，准备写入新关键词数据")

    def close_spider(self, spider):
        self.conn.close()
        spider.logger.info("爬虫结束，数据已入库")

    def process_item(self, item, spider):
        sql = """INSERT INTO posts (platform,title,author,view_count,likes,phase,publish_time) 
                 VALUES (?,?,?,?,?,?,?)"""
        self.cursor.execute(sql, (
            item['platform'], item['title'], item['author'],
            item['view_count'], item['likes'], item['phase'], item['publish_time']
        ))
        self.conn.commit()
        return item
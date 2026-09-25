import scrapy
import json
import urllib.parse
from kpop_demo.items import PostItem


class BilibiliSpider(scrapy.Spider):
    name = 'bilibili'

    def __init__(self, keyword=None, **kwargs):
        super().__init__(**kwargs)
        self.keyword = keyword or 'Kpop'
        self.logger.info(f"本次采集关键词：{self.keyword}")

    def start_requests(self):
        url = f'https://api.bilibili.com/x/web-interface/search/type?keyword={urllib.parse.quote(self.keyword)}&search_type=video&page=1'
        yield scrapy.Request(url, callback=self.parse_api, headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://search.bilibili.com/'
        })

    def errback_api(self, failure):
        self.logger.error(f"API请求失败：{failure.value}")
        # 降级到网页搜索
        search_url = f'https://search.bilibili.com/all?keyword={urllib.parse.quote(self.keyword)}'
        yield scrapy.Request(
            search_url,
            callback=self.parse_html,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://search.bilibili.com/',
            }
        )

    def parse_api(self, response):
        try:
            data = json.loads(response.text)
            if data.get('code') == 0:
                videos = data.get('data', {}).get('result', [])
                if videos:
                    self.logger.info(f"✅ API搜索成功，获取 {len(videos)} 条")
                    for v in videos:
                        item = PostItem()
                        item['platform'] = 'bilibili'
                        item['title'] = v.get('title', '').replace('<em class="keyword">', '').replace('</em>', '')
                        item['author'] = v.get('author', '')
                        item['view_count'] = v.get('play', 0)
                        item['likes'] = v.get('like', 0)
                        item['phase'] = self.detect_phase(item['title'])
                        item['publish_time'] = str(v.get('pubdate', ''))
                        yield item
                        self.logger.info(f"📥 入库：{item['title'][:30]}...")
                    return
            self.logger.warning(f"⚠️ API返回异常 code={data.get('code')}，降级网页搜索")
        except Exception as e:
            self.logger.error(f"⚠️ API解析失败：{e}")

        # 降级
        search_url = f'https://search.bilibili.com/all?keyword={urllib.parse.quote(self.keyword)}'
        yield scrapy.Request(search_url, callback=self.parse_html)

    def parse_html(self, response):
        """网页解析备用方案"""
        self.logger.info("🌐 使用网页解析模式")
        videos = response.css('.video-list-item, .video-card, .bili-video-card, [class*="video-list-item"]')
        self.logger.info(f"网页解析获取 {len(videos)} 个卡片")

        for v in videos:
            title = ''.join(
                v.css('.title ::text, h3 ::text, .bili-video-card__title ::text, a[title] ::text').getall()).strip()
            author = v.css('.up-name ::text, .author ::text, .up-name__1IPt ::text').get('')
            play_text = v.css('.play-text ::text, .view ::text, .bili-video-card__stats--item ::text').get('0')

            if not title:
                continue

            item = PostItem()
            item['platform'] = 'bilibili'
            item['title'] = title
            item['author'] = author.strip() if author else '未知UP'
            item['view_count'] = self._parse_play(play_text)
            item['likes'] = 0
            item['phase'] = self.detect_phase(item['title'])
            item['publish_time'] = ''
            yield item
            self.logger.info(f"📥 入库：{item['title'][:30]}...")

    def _parse_play(self, text):
        text = str(text).replace(',', '').strip()
        if '万' in text:
            try:
                return int(float(text.replace('万', '')) * 10000)
            except:
                return 0
        try:
            return int(text)
        except:
            return 0

    def detect_phase(self, text):
        text = text.lower()
        if any(k in text for k in ['teaser', '预告', 'preview']): return 'P3'
        if any(k in text for k in ['mv', 'music video']): return 'P5'
        if any(k in text for k in ['album', '专辑', 'release', 'comeback', '回归']): return 'P4'
        if any(k in text for k in ['concept', '概念', 'photo']): return 'P1'
        if any(k in text for k in ['track', '歌单', '曲目']): return 'P2'
        if any(k in text for k in ['打歌', '舞台', 'win', '一位']): return 'P6'
        return 'P0'
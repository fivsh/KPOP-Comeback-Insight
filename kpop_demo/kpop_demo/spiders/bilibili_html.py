import scrapy
import urllib.parse
import json
import re
from kpop_demo.items import PostItem


class BilibiliSpider(scrapy.Spider):
    name = 'bilibili'

    def __init__(self, keyword=None, **kwargs):
        super().__init__(**kwargs)
        self.keyword = keyword or 'Kpop'
        self.logger.info(f"本次采集关键词：{self.keyword}")

    def start_requests(self):
        url = f'https://search.bilibili.com/all?keyword={urllib.parse.quote(self.keyword)}'
        self.logger.info(f"开始请求：{url}")
        yield scrapy.Request(
            url=url,
            callback=self.parse_search,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://search.bilibili.com/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
        )

    def parse_search(self, response):
        self.logger.info(f"收到响应，状态码：{response.status}")
        html = response.text

        # 核心：从 B 站页面初始状态提取 JSON（比 CSS 选择器稳定）
        videos = []
        match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});</script>', html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                # 尝试多种可能的字段路径
                videos = (
                        data.get('flow', {}).get('list', [])
                        or data.get('videoData', {}).get('list', [])
                        or data.get('result', {}).get('video', [])
                )
                self.logger.info(f"✅ 从页面JSON解析到 {len(videos)} 个视频")
            except Exception as e:
                self.logger.error(f"JSON解析失败：{e}")

        # 兜底：CSS 选择器
        if not videos:
            cards = response.css('li.video-list-item, div.video-list-item, div.bili-video-card')
            self.logger.info(f"🔄 CSS选择器匹配到 {len(cards)} 个卡片")
            for card in cards:
                title = ''.join(card.css('a[title]::attr(title), a::text, h3::text').getall()).strip()
                if title:
                    videos.append({
                        'title': title,
                        'author': card.css('.up-name::text, .author::text').get(''),
                        'play': card.css('.play-text::text, .view::text').get('0'),
                    })

        if not videos:
            self.logger.warning("⚠️ 未获取到视频，保存 debug_bili.html 供检查")
            with open('debug_bili.html', 'w', encoding='utf-8') as f:
                f.write(html[:10000])
            return

        for v in videos:
            if not isinstance(v, dict):
                continue
            title = v.get('title', '')
            author = v.get('author', '') or v.get('up_name', '') or v.get('name', '')
            play = v.get('play', 0) or v.get('view', 0) or v.get('stat', {}).get('view', 0)

            if not title:
                continue

            item = PostItem()
            item['platform'] = 'bilibili'
            item['title'] = str(title).replace('<em class="keyword">', '').replace('</em>', '')
            item['author'] = str(author).strip() if author else '未知UP'
            item['view_count'] = self._parse_play(str(play))
            item['likes'] = 0
            item['phase'] = self.detect_phase(item['title'])
            item['publish_time'] = ''
            yield item
            self.logger.info(f"📥 入库：{item['title'][:40]}")

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
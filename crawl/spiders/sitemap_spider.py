import re
from urllib.parse import urlsplit
from xml.etree import ElementTree

import scrapy

from crawl.spiders.base_spider import BaseSpider


class SitemapSpider(BaseSpider):
    name = "sitemap_spider"

    _NS = {
        "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sitemap_urls = self.config.get("sitemap_urls", [])
        if not self.sitemap_urls and self.start_urls:
            split = urlsplit(self.start_urls[0])
            base = f"{split.scheme}://{split.netloc}"
            self.sitemap_urls = [f"{base}/sitemap.xml"]

    def start_requests(self):
        for url in self.sitemap_urls:
            yield scrapy.Request(
                url=url,
                callback=self._parse_sitemap,
                errback=self._sitemap_errback,
                priority=10,
                dont_filter=True,
                meta={"sitemap_depth": 0},
            )
        for request in super().start_requests():
            yield request

    def _parse_sitemap(self, response):
        depth = response.meta.get("sitemap_depth", 0)
        if depth > 3:
            return

        content_type = response.headers.get("Content-Type", b"").decode("latin-1", errors="replace").lower()
        body = response.text

        # Try parsing as XML sitemap
        try:
            root = ElementTree.fromstring(body.encode("utf-8"))
        except ElementTree.ParseError:
            self.logger.warning("Failed to parse sitemap XML: %s", response.url)
            return

        tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

        if tag == "sitemapindex":
            for sitemap in root.findall("sm:sitemap/sm:loc", self._NS):
                loc = (sitemap.text or "").strip()
                if loc:
                    self.increment_stat("crawl/sitemap_refs")
                    yield scrapy.Request(
                        url=loc,
                        callback=self._parse_sitemap,
                        errback=self._sitemap_errback,
                        priority=9,
                        meta={"sitemap_depth": depth + 1},
                    )
        elif tag == "urlset":
            for url_el in root.findall("sm:url/sm:loc", self._NS):
                loc = (url_el.text or "").strip()
                if not loc:
                    continue
                if not self.is_allowed_url(loc):
                    continue
                if not self.should_follow(loc, parent_url=response.url):
                    continue
                self.increment_stat("crawl/sitemap_urls_found")
                yield self.build_request(
                    url=loc,
                    callback=self.parse,
                    source_url=response.url,
                    page_type_hint=self.classify_url(loc),
                )

    async def _sitemap_errback(self, failure):
        self.logger.info("Sitemap unavailable: %s", failure.request.url)

    def classify_url(self, url):
        return super().classify_url(url)

    def classify_response(self, response, hinted=None):
        return super().classify_response(response, hinted=hinted)

    def needs_browser(self, url, page_type=None):
        return super().needs_browser(url, page_type)

    def extract_item(self, response, page_type, source_url=None):
        return super().extract_item(response, page_type, source_url)

    def extract_follow_links(self, response, page_type=None):
        return super().extract_follow_links(response, page_type)

    def should_follow(self, url, parent_url, page_type=None):
        return super().should_follow(url, parent_url, page_type=page_type)

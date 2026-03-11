from crawl.spiders.base_spider import BaseSpider


class SitemapSpider(BaseSpider):
    name = "sitemap_spider"

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

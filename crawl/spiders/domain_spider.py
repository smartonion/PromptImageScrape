import re
from urllib.parse import urlsplit

from crawl.extractors.article import ArticleExtractor
from crawl.extractors.generic import GenericExtractor
from crawl.extractors.product import ProductExtractor
from crawl.spiders.base_spider import BaseSpider
from scrapy_playwright.page import PageMethod


class DomainSpider(BaseSpider):
    name = "domain_spider"
    config_key = "domain"
    allowed_domains = ["example.com"]
    start_urls = ["https://example.com/"]
    sitemap_urls = ["https://example.com/sitemap.xml"]

    page_types = {
        "article",
        "product",
        "category",
        "search",
        "gallery",
        "profile",
        "pdf_landing",
        "generic",
    }

    blocked_prefixes = (
        "/account",
        "/cart",
        "/checkout",
        "/login",
        "/logout",
        "/register",
        "/password",
        "/admin",
        "/api/",
    )

    blocked_suffixes = (
        "/feed",
        "/rss",
        "/atom",
        "/print",
    )

    pagination_markers = ("page=", "/page/")
    faceted_markers = ("filter=", "facet=", "sort=", "min_price=", "max_price=")
    skip_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg",
        ".ico",
        ".css",
        ".js",
        ".xml",
        ".zip",
        ".rar",
        ".mp4",
        ".webm",
        ".mp3",
    }

    extractor_map = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        domain_config = self.config.get(self.config_key, {})
        self.allowed_domains = domain_config.get("allowed_domains", self.allowed_domains)
        self.start_urls = domain_config.get("start_urls", self.start_urls)
        self.sitemap_urls = domain_config.get("sitemap_urls", self.sitemap_urls)
        self.extractor_map = {
            "article": ArticleExtractor(spider=self),
            "product": ProductExtractor(spider=self),
            "gallery": GenericExtractor(spider=self),
            "generic": GenericExtractor(spider=self),
            "category": GenericExtractor(spider=self),
            "search": GenericExtractor(spider=self),
            "profile": GenericExtractor(spider=self),
            "pdf_landing": GenericExtractor(spider=self),
        }

    def classify_url(self, url):
        normalized = self.normalize_url(url)
        split = urlsplit(normalized)
        lowered = normalized.lower()
        path = split.path.lower()

        if path in {"", "/"}:
            return "category"

        if lowered.endswith(".pdf") or "/pdf/" in lowered:
            return "pdf_landing"
        if "/gallery/" in lowered:
            return "gallery"
        if "/product/" in lowered:
            return "product"
        if "/category/" in lowered:
            return "category"
        if "/search" in lowered:
            return "search"
        if "/profile/" in lowered:
            return "profile"
        if "/article/" in lowered or "/news/" in lowered:
            return "article"
        return "generic"

    def classify_response(self, response, hinted=None):
        content_type = response.headers.get("Content-Type", b"").decode("latin-1").lower()
        if "application/pdf" in content_type:
            return "pdf_landing"

        return hinted or self.classify_url(response.url)

    def needs_browser(self, url, page_type=None):
        lowered = url.lower()
        if "/interactive/" in lowered or "/dynamic/" in lowered:
            return True
        return False

    def extract_item(self, response, page_type, source_url=None):
        return super().extract_item(response, page_type, source_url)

    def extract_follow_links(self, response, page_type=None):
        urls = super().extract_follow_links(response, page_type)

        for href in response.css("[data-url]::attr(data-url), [data-href]::attr(data-href)").getall():
            if href and href.strip():
                absolute = response.urljoin(href.strip())
                normalized = self.normalize_url(absolute)
                if self.is_allowed_url(normalized):
                    urls.append(normalized)

        for onclick in response.css("[onclick]::attr(onclick)").getall():
            for match in re.findall(r"['\"](/[^'\"\s]+)['\"]", onclick or ""):
                absolute = response.urljoin(match)
                normalized = self.normalize_url(absolute)
                if self.is_allowed_url(normalized):
                    urls.append(normalized)

        return urls

    def should_follow(self, url, parent_url, page_type=None):
        if not super().should_follow(url, parent_url, page_type=page_type):
            return False

        normalized = self.normalize_url(url)
        split = urlsplit(normalized)
        path = split.path.lower() or "/"
        lowered = normalized.lower()

        if any(path.endswith(ext) for ext in self.skip_extensions):
            return False
        if any(marker in lowered for marker in self.faceted_markers):
            return False
        if any(path.startswith(prefix) for prefix in self.blocked_prefixes):
            return False
        if any(path.endswith(suffix) for suffix in self.blocked_suffixes):
            return False

        return True

    def get_extractor(self, page_type):
        return self.extractor_map.get(page_type, self.extractor_map.get("generic"))

    def build_request(
        self,
        url,
        callback=None,
        errback=None,
        priority=0,
        cb_kwargs=None,
        meta=None,
        page_type_hint=None,
        source_url=None,
        use_playwright=None,
        playwright_include_page=False,
        playwright_page_methods=None,
        dont_filter=False,
    ):
        page_type = page_type_hint or self.classify_url(url)
        headers = {"Accept-Language": "en-US,en;q=0.9"}
        merged_meta = {"download_timeout": 30, **(meta or {})}

        if page_type in {"category", "search", "gallery"}:
            playwright_page_methods = playwright_page_methods or self.playwright_page_methods_for(page_type, url)

        return super().build_request(
            url=url,
            callback=callback,
            errback=errback,
            priority=priority,
            cb_kwargs=cb_kwargs,
            meta=merged_meta,
            page_type_hint=page_type,
            source_url=source_url,
            use_playwright=use_playwright,
            playwright_include_page=playwright_include_page,
            playwright_page_methods=playwright_page_methods,
            dont_filter=dont_filter,
        ).replace(headers=headers)

    def playwright_page_methods_for(self, page_type, url):
        if page_type in {"category", "search"}:
            return [PageMethod("wait_for_timeout", 1200)]
        if page_type == "gallery":
            return [PageMethod("wait_for_timeout", 1600)]
        return []

    def parse_api_json(self, response, source_url=None, page_type_hint=None):
        page_type = page_type_hint or "generic"
        item = {
            "url": response.url,
            "source_url": source_url,
            "page_type": page_type,
            "content_type": "application/json",
            "body": response.text,
        }
        yield item

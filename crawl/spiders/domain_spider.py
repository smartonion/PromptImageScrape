import re
from urllib.parse import urlsplit

from crawl.extractors.article import ArticleExtractor
from crawl.extractors.generic import GenericExtractor
from crawl.extractors.pdf import PdfExtractor
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
    faceted_markers = (
        "filter=", "facet=", "sort=", "min_price=", "max_price=",
        "share=", "replytocom=", "like_comment=", "actionSign=",
        "__cft__", "action=share",
    )

    _junk_query_keys = {
        "share", "nb", "replytocom", "like_comment", "actionsign",
        "__cft__", "__tn__", "ref_src", "ref_url",
    }
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
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
    }

    _JS_FRAMEWORK_INDICATORS = (
        "react", "angular", "vue", "svelte", "ember",
        "__NEXT_DATA__", "__NUXT__", "window.__INITIAL_STATE__",
    )

    extractor_map = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        domain_config = self.config.get(self.config_key, {})
        self.allowed_domains = domain_config.get("allowed_domains", self.allowed_domains)
        self.start_urls = domain_config.get("start_urls", self.start_urls)
        self.sitemap_urls = domain_config.get("sitemap_urls", self.sitemap_urls)

        self._custom_allow_patterns = [
            re.compile(p) for p in domain_config.get("allow_patterns", [])
        ]
        self._custom_block_patterns = [
            re.compile(p) for p in domain_config.get("block_patterns", [])
        ]
        self._browser_patterns = [
            re.compile(p) for p in domain_config.get("browser_patterns", [])
        ]

        self.extractor_map = {
            "article": ArticleExtractor(spider=self),
            "product": ProductExtractor(spider=self),
            "gallery": GenericExtractor(spider=self),
            "generic": GenericExtractor(spider=self),
            "category": GenericExtractor(spider=self),
            "search": GenericExtractor(spider=self),
            "profile": GenericExtractor(spider=self),
            "pdf_landing": PdfExtractor(spider=self),
        }

        self._js_detected_domains: set[str] = set()

    def classify_url(self, url):
        normalized = self.normalize_url(url)
        split = urlsplit(normalized)
        lowered = normalized.lower()
        path = split.path.lower()

        if path in {"", "/"}:
            return "category"

        if lowered.endswith(".pdf") or "/pdf/" in lowered:
            return "pdf_landing"
        if "/gallery/" in lowered or "/photos/" in lowered or "/images/" in lowered:
            return "gallery"
        if "/product/" in lowered or "/item/" in lowered or "/shop/" in lowered:
            return "product"
        if any(seg in lowered for seg in ("/category/", "/categories/", "/tag/", "/tags/", "/topic/")):
            return "category"
        if "/search" in lowered:
            return "search"
        if "/profile/" in lowered or "/user/" in lowered or "/author/" in lowered:
            return "profile"
        if any(seg in lowered for seg in ("/article/", "/news/", "/blog/", "/post/", "/story/")):
            return "article"
        return "generic"

    def classify_response(self, response, hinted=None):
        content_type = response.headers.get("Content-Type", b"").decode("latin-1").lower()
        if "application/pdf" in content_type:
            return "pdf_landing"
        if "application/json" in content_type:
            return "api_json"

        return hinted or self.classify_url(response.url)

    def needs_browser(self, url, page_type=None):
        lowered = url.lower()

        if "/interactive/" in lowered or "/dynamic/" in lowered:
            return True
        if "#/" in lowered or "#!" in lowered:
            return True
        for pattern in self._browser_patterns:
            if pattern.search(lowered):
                return True
        host = (urlsplit(url).hostname or "").lower()
        if host in self._js_detected_domains:
            return True

        return False

    def _detect_js_framework(self, response):
        body = response.text or ""
        if len(body) < 2000:
            text_content = response.css("body *::text").getall()
            visible = " ".join(t.strip() for t in text_content if t.strip())
            if len(visible) < 50:
                return True

        # Framework indicators in <script> tags only
        for script in response.css("script::text").getall():
            script_lower = script.lower()
            for indicator in self._JS_FRAMEWORK_INDICATORS:
                if indicator.lower() in script_lower:
                    return True

        # Empty app container
        for sel in ("#app", "#root", "#__next", "#__nuxt"):
            el = response.css(sel)
            if el:
                text = " ".join(el.css("*::text").getall()).strip()
                if len(text) < 30:
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

        for rel in ("canonical", "alternate"):
            for href in response.css(f'link[rel="{rel}"]::attr(href)').getall():
                if href and href.strip():
                    absolute = response.urljoin(href.strip())
                    normalized = self.normalize_url(absolute)
                    if self.is_allowed_url(normalized):
                        urls.append(normalized)

        from scrapy import Selector
        for noscript in response.css("noscript").getall():
            sel = Selector(text=noscript)
            for href in sel.css("a::attr(href)").getall():
                if href and href.strip():
                    absolute = response.urljoin(href.strip())
                    normalized = self.normalize_url(absolute)
                    if self.is_allowed_url(normalized):
                        urls.append(normalized)

        return list(dict.fromkeys(urls))

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

        if split.query:
            from urllib.parse import parse_qs
            query_keys = {k.lower() for k in parse_qs(split.query).keys()}
            if query_keys & self._junk_query_keys:
                return False

        for pattern in self._custom_block_patterns:
            if pattern.search(normalized):
                return False

        if self._custom_allow_patterns:
            if not any(p.search(normalized) for p in self._custom_allow_patterns):
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

    def parse_page(self, response, source_url=None, page_type_hint=None):
        content_type = response.headers.get("Content-Type", b"").decode("latin-1", errors="replace").lower()

        if "application/json" in content_type:
            yield from self.parse_api_json(response, source_url=source_url, page_type_hint=page_type_hint)
            return

        if "application/pdf" in content_type or response.url.lower().endswith(".pdf"):
            extractor = self.get_extractor("pdf_landing")
            item = extractor.extract(response, page_type="pdf_landing", source_url=source_url)
            if item:
                yield item
                self.increment_stat("items/pdf")
            return

        if self._detect_js_framework(response):
            host = (urlsplit(response.url).hostname or "").lower()
            if host not in self._js_detected_domains:
                self._js_detected_domains.add(host)
                self.logger.info("JS framework detected on %s, enabling browser for domain", host)

        yield from super().parse_page(response, source_url=source_url, page_type_hint=page_type_hint)

    def parse_api_json(self, response, source_url=None, page_type_hint=None):
        import json
        try:
            data = json.loads(response.text)
        except (json.JSONDecodeError, TypeError):
            return

        urls_found = set()
        self._extract_urls_from_json(data, urls_found)
        for url in urls_found:
            if self.is_allowed_url(url) and self.should_follow(url, parent_url=response.url):
                self.increment_stat("crawl/json_urls_found")
                yield self.build_request(
                    url=url,
                    callback=self.parse,
                    source_url=response.url,
                )

    def _extract_urls_from_json(self, obj, urls: set, depth: int = 0):
        if depth > 10:
            return
        if isinstance(obj, str):
            if obj.startswith(("http://", "https://")) and " " not in obj:
                urls.add(obj)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                self._extract_urls_from_json(value, urls, depth + 1)
        elif isinstance(obj, list):
            for item in obj:
                self._extract_urls_from_json(item, urls, depth + 1)

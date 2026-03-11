from copy import deepcopy
from dataclasses import is_dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import scrapy
from crawl.items import ImageAssetItem
from scrapy.linkextractors import LinkExtractor


class BaseSpider(scrapy.Spider):
    name = "base_spider"
    allowed_domains = []
    start_urls = []
    config = None
    config_path = None
    link_extractor_cls = LinkExtractor

    TRACKING_PARAMS = {
        "fbclid",
        "gclid",
        "mc_cid",
        "mc_eid",
        "ref",
        "spm",
    }

    def __init__(self, config=None, config_path=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = self._load_config(config=config, config_path=config_path)
        self.allowed_domains = self.config.get("allowed_domains", self.allowed_domains)
        self.start_urls = self.config.get("start_urls", self.start_urls)
        self.link_extractor = self.link_extractor_cls()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider.crawler = crawler
        return spider

    def _load_config(self, config=None, config_path=None):
        if isinstance(config, dict):
            return deepcopy(config)

        path = config_path or self.config_path
        if not path:
            return {}

        raw = Path(path).read_text(encoding="utf-8")
        suffix = Path(path).suffix.lower()
        if suffix in {".yaml", ".yml"}:
            try:
                import yaml
            except ImportError as exc:
                raise RuntimeError("PyYAML is required for YAML spider config") from exc

            data = yaml.safe_load(raw) or {}
            if not isinstance(data, dict):
                raise ValueError("Spider YAML config must deserialize to a dict")
            return data

        raise ValueError(f"Unsupported config format: {suffix}")

    def get_shared_settings(self):
        return self.config.get("shared_settings", {})

    def log_debug(self, event, **payload):
        self.logger.debug("%s | %s", event, payload)

    def increment_stat(self, key, amount=1):
        if hasattr(self, "crawler") and self.crawler.stats:
            self.crawler.stats.inc_value(key, amount)

    def start_requests(self):
        for url in self.start_urls:
            yield self.build_request(url=url, callback=self.parse)

    async def start(self):
        for request in self.start_requests():
            yield request

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
        page_type_hint = page_type_hint or self.classify_url(url)
        use_playwright = self.needs_browser(url, page_type_hint) if use_playwright is None else use_playwright

        callback = callback or self.parse
        errback = errback or self.errback_close_page

        safe_cb_kwargs = {
            "source_url": source_url,
            "page_type_hint": page_type_hint,
            **(cb_kwargs or {}),
        }
        safe_cb_kwargs = {k: v for k, v in safe_cb_kwargs.items() if v is not None}

        safe_meta = dict(meta or {})
        if use_playwright:
            safe_meta.update(
                self.make_playwright_meta(
                    url=url,
                    page_type=page_type_hint,
                    include_page=playwright_include_page,
                    page_methods=playwright_page_methods,
                )
            )

        return scrapy.Request(
            url=self.normalize_url(url),
            callback=callback,
            errback=errback,
            priority=priority,
            cb_kwargs=safe_cb_kwargs,
            meta=safe_meta,
            dont_filter=dont_filter,
        )

    def normalize_url(self, url):
        return self.canonicalize_url(url)

    def strip_tracking_params(self, url):
        split = urlsplit(url)
        query_pairs = parse_qsl(split.query, keep_blank_values=True)
        filtered = []
        for key, value in query_pairs:
            lowered = key.lower()
            if lowered.startswith("utm_"):
                continue
            if lowered in self.TRACKING_PARAMS:
                continue
            filtered.append((key, value))

        new_query = urlencode(filtered, doseq=True)
        return urlunsplit((split.scheme, split.netloc, split.path, new_query, ""))

    def canonicalize_url(self, url):
        stripped = self.strip_tracking_params(url)
        split = urlsplit(stripped)
        scheme = split.scheme.lower() or "https"
        host = split.hostname.lower() if split.hostname else ""
        port = split.port
        if port and ((scheme == "http" and port != 80) or (scheme == "https" and port != 443)):
            netloc = f"{host}:{port}"
        else:
            netloc = host

        path = split.path or "/"
        return urlunsplit((scheme, netloc, path, split.query, ""))

    def same_domain(self, url):
        host = (urlsplit(url).hostname or "").lower()
        if not host:
            return False
        if not self.allowed_domains:
            return True

        return any(host == domain or host.endswith(f".{domain}") for domain in self.allowed_domains)

    def is_allowed_url(self, url):
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        return self.same_domain(url)

    def classify_url(self, url):
        return "page"

    def classify_response(self, response, hinted=None):
        return hinted or self.classify_url(response.url)

    def should_extract(self, response, page_type):
        return True

    def needs_browser(self, url, page_type=None):
        return False

    def get_extractor(self, page_type):
        return None

    def extract_item(self, response, page_type, source_url=None):
        extractor = self.get_extractor(page_type)
        if extractor is None:
            return None
        if hasattr(extractor, "extract"):
            return extractor.extract(response=response, page_type=page_type, source_url=source_url)
        if callable(extractor):
            return extractor(response=response, page_type=page_type, source_url=source_url)
        return None

    def iter_extracted_items(self, extracted):
        if extracted is None:
            return []
        if isinstance(extracted, list):
            return extracted
        if isinstance(extracted, tuple):
            return list(extracted)
        if isinstance(extracted, set):
            return list(extracted)
        return [extracted]

    def should_emit_image_assets(self, page_type):
        return True

    def _extract_image_urls_from_item(self, item):
        if isinstance(item, ImageAssetItem):
            return []
        if isinstance(item, dict):
            return item.get("images", []) or []
        if is_dataclass(item) and hasattr(item, "images"):
            return getattr(item, "images") or []
        if hasattr(item, "images"):
            return getattr(item, "images") or []
        return []

    def build_image_asset_items(self, item, page_type, source_url, parent_url):
        image_urls = self._extract_image_urls_from_item(item)
        seen = set()
        for image_url in image_urls:
            normalized = self.normalize_url(image_url)
            if normalized in seen:
                continue
            seen.add(normalized)
            yield ImageAssetItem(
                url=image_url,
                normalized_url=normalized,
                page_type=page_type,
                metadata={"asset_type": "image", "parent_url": parent_url},
                source_url=source_url,
            )

    def extract_follow_links(self, response, page_type=None):
        urls = []
        for link in self.link_extractor.extract_links(response):
            normalized = self.normalize_url(link.url)
            if not self.is_allowed_url(normalized):
                self.log_skip_url(normalized, reason="not_allowed")
                continue
            urls.append(normalized)

        for iframe_src in response.css("iframe::attr(src)").getall():
            if iframe_src and iframe_src.strip():
                absolute = response.urljoin(iframe_src.strip())
                urls.append(self.normalize_url(absolute))

        return urls

    def should_follow(self, url, parent_url, page_type=None):
        if not self.is_allowed_url(url):
            return False
        return True

    def make_playwright_meta(self, url, page_type=None, include_page=False, page_methods=None):
        meta = {
            "playwright": True,
            "playwright_context": self.playwright_context_name(page_type=page_type, url=url),
            "playwright_page_methods": page_methods or self.playwright_page_methods_for(page_type, url),
        }
        if include_page:
            meta["playwright_include_page"] = True
        return meta

    def playwright_page_methods_for(self, page_type, url):
        return []

    def playwright_context_name(self, page_type=None, url=None):
        return "default"

    async def async_cleanup_page_from_response(self, response):
        page = response.meta.get("playwright_page")
        if page is not None:
            await page.close()

    async def errback_close_page(self, failure):
        page = failure.request.meta.get("playwright_page")
        if page is not None:
            await page.close()
        return failure

    def log_page_type(self, url, page_type, hinted=None):
        self.log_debug("page_type", url=url, page_type=page_type, hinted=hinted)

    def log_skip_url(self, url, reason):
        self.increment_stat(f"crawl/skip/{reason}")
        self.log_debug("skip_url", url=url, reason=reason)

    def parse_page(self, response, source_url=None, page_type_hint=None):
        content_type = response.headers.get("Content-Type", b"").decode("latin-1", errors="replace").lower()
        if "application/json" in content_type:
            return

        page_type = self.classify_response(response, hinted=page_type_hint)
        self.log_page_type(response.url, page_type, hinted=page_type_hint)

        if self.should_extract(response, page_type):
            extracted = self.extract_item(response, page_type, source_url=source_url)
            for item in self.iter_extracted_items(extracted):
                self.increment_stat("crawl/items_extracted")
                yield item
                if self.should_emit_image_assets(page_type):
                    for image_item in self.build_image_asset_items(
                        item=item,
                        page_type=page_type,
                        source_url=source_url,
                        parent_url=response.url,
                    ):
                        self.increment_stat("crawl/image_assets_emitted")
                        yield image_item

        for url in self.extract_follow_links(response, page_type=page_type):
            if not self.should_follow(url, parent_url=response.url, page_type=page_type):
                self.log_skip_url(url, reason="policy")
                continue
            self.increment_stat("crawl/links_followed")
            yield self.build_request(
                url=url,
                callback=self.parse,
                source_url=response.url,
                page_type_hint=self.classify_url(url),
            )

    def parse(self, response, source_url=None, page_type_hint=None):
        request_kwargs = {}
        if response.request is not None:
            request_kwargs = getattr(response.request, "cb_kwargs", {}) or {}

        source_url = source_url or request_kwargs.get("source_url", response.url)
        page_type_hint = page_type_hint or request_kwargs.get("page_type_hint")
        yield from self.parse_page(
            response=response,
            source_url=source_url,
            page_type_hint=page_type_hint,
        )

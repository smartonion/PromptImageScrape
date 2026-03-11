import re
from typing import Any

from crawl.items import DocumentItem

_BG_IMAGE_RE = re.compile(r"url\([\s'\"]*([^)\s'\"]+)[\s'\"]*\)")


class BaseExtractor:
    def __init__(self, spider=None):
        self.spider = spider

    def normalize_url(self, url: str) -> str:
        if self.spider and hasattr(self.spider, "normalize_url"):
            return self.spider.normalize_url(url)
        return url

    def extract_title(self, response) -> str | None:
        title = response.css("title::text").get()
        return title.strip() if title else None

    def extract_text(self, response) -> str | None:
        chunks = response.css("body *::text").getall()
        clean_chunks = [chunk.strip() for chunk in chunks if chunk and chunk.strip()]
        if not clean_chunks:
            return None
        return " ".join(clean_chunks)

    def extract_html(self, response) -> str:
        return response.text

    def extract_images(self, response) -> list[str]:
        raw_urls: list[str] = []

        for src in response.css("img::attr(src)").getall():
            if src and src.strip():
                raw_urls.append(src.strip())

        for attr in ("data-src", "data-lazy-src", "data-original"):
            for src in response.css(f"img::attr({attr})").getall():
                if src and src.strip():
                    raw_urls.append(src.strip())

        for srcset in response.css("img::attr(srcset)").getall():
            raw_urls.extend(self._parse_srcset(srcset))

        for srcset in response.css("picture source::attr(srcset)").getall():
            raw_urls.extend(self._parse_srcset(srcset))

        og_image = response.css('meta[property="og:image"]::attr(content)').get()
        if og_image and og_image.strip():
            raw_urls.append(og_image.strip())

        tw_image = response.css('meta[name="twitter:image"]::attr(content)').get()
        if tw_image and tw_image.strip():
            raw_urls.append(tw_image.strip())

        for poster in response.css("video::attr(poster)").getall():
            if poster and poster.strip():
                raw_urls.append(poster.strip())

        for img_input in response.css('input[type="image"]::attr(src)').getall():
            if img_input and img_input.strip():
                raw_urls.append(img_input.strip())

        for href in response.css('link[rel~="icon"]::attr(href)').getall():
            if href and href.strip():
                raw_urls.append(href.strip())

        for style_val in response.css("[style]::attr(style)").getall():
            raw_urls.extend(self._extract_bg_images(style_val))

        for style_block in response.css("style::text").getall():
            raw_urls.extend(self._extract_bg_images(style_block))

        image_urls: list[str] = []
        for raw in raw_urls:
            if raw.startswith("data:"):
                continue
            absolute = response.urljoin(raw)
            image_urls.append(self.normalize_url(absolute))
        return list(dict.fromkeys(image_urls))

    @staticmethod
    def _parse_srcset(srcset: str) -> list[str]:
        urls: list[str] = []
        for candidate in srcset.split(","):
            parts = candidate.strip().split()
            if parts and parts[0]:
                urls.append(parts[0])
        return urls

    @staticmethod
    def _extract_bg_images(css_text: str) -> list[str]:
        return [m.group(1) for m in _BG_IMAGE_RE.finditer(css_text or "")]

    def extract_metadata(self, response, page_type: str) -> dict[str, Any]:
        return {
            "status": response.status,
            "content_type": response.headers.get("Content-Type", b"").decode("latin-1"),
            "page_type": page_type,
        }

    def build_document_item(self, response, page_type: str, source_url: str | None = None, metadata: dict[str, Any] | None = None) -> DocumentItem:
        base_metadata = self.extract_metadata(response, page_type)
        if metadata:
            base_metadata.update(metadata)

        return DocumentItem(
            url=response.url,
            normalized_url=self.normalize_url(response.url),
            page_type=page_type,
            title=self.extract_title(response),
            text=self.extract_text(response),
            html=self.extract_html(response),
            images=self.extract_images(response),
            metadata=base_metadata,
            source_url=source_url,
        )

    def extract(self, response, page_type: str, source_url: str | None = None):
        raise NotImplementedError

import re
from typing import Any

from scrapy import Selector

from crawl.items import DocumentItem

_BG_IMAGE_RE = re.compile(r"url\([\s'\"]*([^)\s'\"]+)[\s'\"]*\)")

_BOILERPLATE_SELECTORS = (
    "nav", "footer", "header", "aside",
    "[role='navigation']", "[role='banner']", "[role='contentinfo']",
    ".cookie-banner", ".cookie-notice", "#cookie-consent",
    ".site-footer", ".site-header", ".site-nav",
    ".breadcrumb", ".breadcrumbs", ".pagination",
    ".sidebar", "#sidebar",
    ".advertisement", ".ad-container",
    ".social-share", ".share-buttons",
    ".skip-link", ".screen-reader-text",
)

_BLOCK_TAGS = {
    "p", "div", "section", "article", "main",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "li", "blockquote", "pre", "figcaption",
    "td", "th", "dt", "dd", "address",
}

_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


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

    def _clean_selector(self, response) -> Selector:
        sel = Selector(text=response.text)
        for tag in ("script", "style", "noscript", "svg", "template"):
            for node in sel.css(tag):
                node.root.getparent().remove(node.root)
        for css in _BOILERPLATE_SELECTORS:
            for node in sel.css(css):
                try:
                    node.root.getparent().remove(node.root)
                except (AttributeError, ValueError):
                    continue
        return sel

    def extract_text(self, response) -> str | None:
        sel = self._clean_selector(response)
        body = sel.css("body")
        if not body:
            return None

        blocks: list[str] = []
        current_heading: str | None = None

        for el in body.css("body *"):
            tag = el.root.tag if hasattr(el.root, "tag") else ""
            if not isinstance(tag, str):
                continue

            tag_lower = tag.lower()
            texts = el.css("::text").getall()
            line = " ".join(t.strip() for t in texts if t and t.strip())
            if not line:
                continue

            if tag_lower in _HEADING_TAGS:
                current_heading = line
                blocks.append(f"\n\n## {line}\n")
            elif tag_lower in _BLOCK_TAGS:
                blocks.append(line)
            else:
                if blocks and not blocks[-1].endswith("\n"):
                    blocks.append(line)

        if not blocks:
            all_text = body.css("*::text").getall()
            clean = [t.strip() for t in all_text if t and t.strip()]
            if not clean:
                return None
            return " ".join(clean)

        result_parts: list[str] = []
        for block in blocks:
            stripped = block.strip()
            if not stripped:
                continue
            result_parts.append(stripped)

        return "\n\n".join(result_parts) if result_parts else None

    def extract_html(self, response) -> str:
        return response.text

    def extract_images(self, response) -> list[dict]:
        records: list[dict] = []

        for img in response.css("img"):
            src = img.attrib.get("src", "").strip()
            lazy = (
                img.attrib.get("data-src", "").strip()
                or img.attrib.get("data-lazy-src", "").strip()
                or img.attrib.get("data-original", "").strip()
            )
            url = lazy or src
            if not url:
                continue
            records.append({
                "url": url,
                "alt_text": img.attrib.get("alt", "").strip() or None,
                "title": img.attrib.get("title", "").strip() or None,
                "width": img.attrib.get("width", "").strip() or None,
                "height": img.attrib.get("height", "").strip() or None,
            })
            for srcset_attr in ("srcset", "data-srcset"):
                srcset_val = img.attrib.get(srcset_attr, "")
                if srcset_val:
                    for srcset_url in self._parse_srcset(srcset_val):
                        records.append({
                            "url": srcset_url,
                            "alt_text": img.attrib.get("alt", "").strip() or None,
                            "title": None, "width": None, "height": None,
                        })

        for source in response.css("picture source"):
            for srcset_attr in ("srcset", "data-srcset"):
                srcset_val = source.attrib.get(srcset_attr, "")
                if srcset_val:
                    for url in self._parse_srcset(srcset_val):
                        records.append({
                            "url": url,
                            "alt_text": None, "title": None,
                            "width": None, "height": None,
                        })

        for noscript in response.css("noscript"):
            inner = Selector(text=noscript.get())
            for img in inner.css("img"):
                src = img.attrib.get("src", "").strip()
                if src:
                    records.append({
                        "url": src,
                        "alt_text": img.attrib.get("alt", "").strip() or None,
                        "title": img.attrib.get("title", "").strip() or None,
                        "width": None, "height": None,
                    })

        og_image = response.css('meta[property="og:image"]::attr(content)').get()
        if og_image and og_image.strip():
            records.append({
                "url": og_image.strip(),
                "alt_text": response.css('meta[property="og:image:alt"]::attr(content)').get(),
                "title": None, "width": None, "height": None,
            })

        tw_image = response.css('meta[name="twitter:image"]::attr(content)').get()
        if tw_image and tw_image.strip():
            records.append({
                "url": tw_image.strip(),
                "alt_text": None, "title": None, "width": None, "height": None,
            })

        for poster in response.css("video::attr(poster)").getall():
            if poster and poster.strip():
                records.append({
                    "url": poster.strip(),
                    "alt_text": None, "title": None, "width": None, "height": None,
                })

        for img_input in response.css('input[type="image"]'):
            src = img_input.attrib.get("src", "").strip()
            if src:
                records.append({
                    "url": src,
                    "alt_text": img_input.attrib.get("alt", "").strip() or None,
                    "title": None, "width": None, "height": None,
                })

        for link in response.css('link[rel~="icon"]'):
            href = link.attrib.get("href", "").strip()
            if href:
                records.append({
                    "url": href,
                    "alt_text": None, "title": None, "width": None, "height": None,
                })

        for style_val in response.css("[style]::attr(style)").getall():
            for bg_url in self._extract_bg_images(style_val):
                records.append({
                    "url": bg_url,
                    "alt_text": None, "title": None, "width": None, "height": None,
                })

        for style_block in response.css("style::text").getall():
            for bg_url in self._extract_bg_images(style_block):
                records.append({
                    "url": bg_url,
                    "alt_text": None, "title": None, "width": None, "height": None,
                })

        seen: set[str] = set()
        result: list[dict] = []
        for rec in records:
            raw_url = rec["url"]
            if not raw_url or raw_url.startswith("data:"):
                continue
            absolute = response.urljoin(raw_url)
            normalized = self.normalize_url(absolute)
            if normalized in seen:
                continue
            seen.add(normalized)
            rec["url"] = normalized
            result.append(rec)

        return result

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
        lang = response.css("html::attr(lang)").get()
        return {
            "status": response.status,
            "content_type": response.headers.get("Content-Type", b"").decode("latin-1"),
            "page_type": page_type,
            "language": lang.strip() if lang else None,
        }

    def build_document_item(self, response, page_type: str, source_url: str | None = None, metadata: dict[str, Any] | None = None) -> DocumentItem:
        base_metadata = self.extract_metadata(response, page_type)
        if metadata:
            base_metadata.update(metadata)

        image_records = self.extract_images(response)
        base_metadata["image_records"] = image_records
        image_urls = [rec["url"] for rec in image_records]

        return DocumentItem(
            url=response.url,
            normalized_url=self.normalize_url(response.url),
            page_type=page_type,
            title=self.extract_title(response),
            text=self.extract_text(response),
            html=self.extract_html(response),
            images=image_urls,
            metadata=base_metadata,
            source_url=source_url,
        )

    def extract(self, response, page_type: str, source_url: str | None = None):
        raise NotImplementedError

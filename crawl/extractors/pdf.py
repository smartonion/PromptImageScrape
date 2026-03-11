import io
from typing import Any

from crawl.items import DocumentItem


class PdfExtractor:

    def __init__(self, spider=None):
        self.spider = spider

    def normalize_url(self, url: str) -> str:
        if self.spider and hasattr(self.spider, "normalize_url"):
            return self.spider.normalize_url(url)
        return url

    def extract(self, response, page_type: str, source_url: str | None = None):
        text = self._extract_pdf_text(response.body)
        if not text:
            return None

        metadata: dict[str, Any] = {
            "status": response.status,
            "content_type": "application/pdf",
            "page_type": page_type,
        }

        image_urls: list[str] = []

        return DocumentItem(
            url=response.url,
            normalized_url=self.normalize_url(response.url),
            page_type=page_type,
            title=self._guess_title(text, response.url),
            text=text,
            html=None,
            images=image_urls,
            metadata=metadata,
            source_url=source_url,
        )

    def _extract_pdf_text(self, body: bytes) -> str | None:
        try:
            import pdfplumber
        except ImportError:
            # pdfplumber unavailable, try PyPDF2
            return self._extract_with_pypdf2(body)

        try:
            with pdfplumber.open(io.BytesIO(body)) as pdf:
                pages = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text.strip())
                return "\n\n".join(pages) if pages else None
        except Exception:
            return None

    def _extract_with_pypdf2(self, body: bytes) -> str | None:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            return None

        try:
            reader = PdfReader(io.BytesIO(body))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text.strip())
            return "\n\n".join(pages) if pages else None
        except Exception:
            return None

    def _guess_title(self, text: str, url: str) -> str:
        """First non-empty line, or filename from URL."""
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped and len(stripped) > 3:
                return stripped[:200]
        return url.rsplit("/", 1)[-1]

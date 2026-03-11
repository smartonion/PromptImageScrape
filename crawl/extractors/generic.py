from crawl.extractors.base import BaseExtractor


class GenericExtractor(BaseExtractor):
    def extract(self, response, page_type: str, source_url: str | None = None):
        return self.build_document_item(response, page_type=page_type, source_url=source_url)

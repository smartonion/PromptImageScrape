from crawl.extractors.generic import GenericExtractor
from crawl.extractors.jsonld import first_jsonld_of_type, parse_jsonld_blocks


class ArticleExtractor(GenericExtractor):
    def extract(self, response, page_type: str, source_url: str | None = None):
        blocks = parse_jsonld_blocks(response)
        article_ld = first_jsonld_of_type(blocks, "article") or {}

        metadata = {
            "author": article_ld.get("author"),
            "published_at": article_ld.get("datePublished"),
            "modified_at": article_ld.get("dateModified"),
            "jsonld_blocks": len(blocks),
        }
        title = article_ld.get("headline")

        item = self.build_document_item(response, page_type=page_type, source_url=source_url, metadata=metadata)
        if title and not item.title:
            item.title = str(title).strip()
        return item

from crawl.extractors.generic import GenericExtractor
from crawl.extractors.jsonld import first_jsonld_of_type, parse_jsonld_blocks


class ProductExtractor(GenericExtractor):
    def extract(self, response, page_type: str, source_url: str | None = None):
        blocks = parse_jsonld_blocks(response)
        product_ld = first_jsonld_of_type(blocks, "product") or {}

        offers = product_ld.get("offers") if isinstance(product_ld, dict) else None
        if isinstance(offers, list):
            offer = offers[0] if offers else {}
        elif isinstance(offers, dict):
            offer = offers
        else:
            offer = {}

        metadata = {
            "sku": product_ld.get("sku"),
            "brand": product_ld.get("brand"),
            "price": offer.get("price"),
            "currency": offer.get("priceCurrency"),
            "availability": offer.get("availability"),
            "jsonld_blocks": len(blocks),
        }
        title = product_ld.get("name")

        item = self.build_document_item(response, page_type=page_type, source_url=source_url, metadata=metadata)
        if title and not item.title:
            item.title = str(title).strip()
        return item

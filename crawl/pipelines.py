from dataclasses import asdict, is_dataclass

from crawl.items import DocumentItem, ImageAssetItem, RawPageItem
from storage.asset_store import AssetStore
from storage.document_store import DocumentStore
from storage.raw_store import RawStore


class RawPagePipeline:
    def __init__(self, raw_store: RawStore):
        self.raw_store = raw_store

    @classmethod
    def from_crawler(cls, crawler):
        base_dir = crawler.settings.get("RAW_STORE_DIR", "data/raw")
        return cls(raw_store=RawStore(base_dir=base_dir))

    def process_item(self, item, spider=None):
        if isinstance(item, RawPageItem):
            metadata = dict(item.metadata)
            metadata["page_type"] = item.page_type
            metadata["source_url"] = item.source_url

            if item.html:
                self.raw_store.save_html(url=item.normalized_url or item.url, html=item.html, metadata=metadata)
            elif item.text:
                self.raw_store.save_json(
                    url=item.normalized_url or item.url,
                    payload={"text": item.text},
                    metadata=metadata,
                )
        return item


class DocumentPipeline:
    def __init__(self, document_store: DocumentStore):
        self.document_store = document_store
        self._seen_urls: set[str] = set()

    @classmethod
    def from_crawler(cls, crawler):
        output_path = crawler.settings.get("DOCUMENT_STORE_PATH", "data/documents/documents.jsonl")
        return cls(document_store=DocumentStore(output_path=output_path))

    def process_item(self, item, spider=None):
        if isinstance(item, DocumentItem):
            key = item.normalized_url or item.url
            if key in self._seen_urls:
                return item
            self._seen_urls.add(key)
            self.document_store.save(item)
        return item


class ImageAssetPipeline:
    def __init__(self, asset_store: AssetStore, manifest_store: DocumentStore):
        self.asset_store = asset_store
        self.manifest_store = manifest_store
        self._seen_urls: set[str] = set()

    @classmethod
    def from_crawler(cls, crawler):
        base_dir = crawler.settings.get("ASSET_STORE_DIR", "data/assets")
        manifest_path = crawler.settings.get("ASSET_MANIFEST_PATH", "data/assets/assets.jsonl")
        return cls(
            asset_store=AssetStore(base_dir=base_dir),
            manifest_store=DocumentStore(output_path=manifest_path),
        )

    def process_item(self, item, spider=None):
        if not isinstance(item, ImageAssetItem):
            return item

        key = item.normalized_url or item.url
        if key in self._seen_urls:
            return item
        self._seen_urls.add(key)

        record = asdict(item) if is_dataclass(item) else dict(item)
        self.asset_store.save_reference(asset_url=item.normalized_url or item.url, payload=record)
        self.manifest_store.save(record)
        return item

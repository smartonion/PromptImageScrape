BOT_NAME = "crawl"

SPIDER_MODULES = ["crawl.spiders"]
NEWSPIDER_MODULE = "crawl.spiders"

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

ROBOTSTXT_OBEY = True

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": True}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30_000
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 8
PLAYWRIGHT_MAX_CONTEXTS = 4

ITEM_PIPELINES = {
    "crawl.pipelines.RawPagePipeline": 100,
    "crawl.pipelines.DocumentPipeline": 200,
    "crawl.pipelines.ImageAssetPipeline": 300,
}

RAW_STORE_DIR = "data/raw"
DOCUMENT_STORE_PATH = "data/documents/documents.jsonl"
ASSET_STORE_DIR = "data/assets"
ASSET_MANIFEST_PATH = "data/assets/assets.jsonl"

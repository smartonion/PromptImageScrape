BOT_NAME = "crawl"

SPIDER_MODULES = ["crawl.spiders"]
NEWSPIDER_MODULE = "crawl.spiders"

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

ROBOTSTXT_OBEY = True

USER_AGENT = "PromptImageScrape/1.0 (+https://github.com/smartonion/PromptImageScrape)"

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {"headless": True}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30_000
PLAYWRIGHT_MAX_PAGES_PER_CONTEXT = 8
PLAYWRIGHT_MAX_CONTEXTS = 4

CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8
DOWNLOAD_DELAY = 0.25
DOWNLOAD_TIMEOUT = 30
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 4.0

HTTPCACHE_ENABLED = False
HTTPCACHE_DIR = "data/.httpcache"
HTTPCACHE_EXPIRATION_SECS = 86400
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504]

ITEM_PIPELINES = {
    "crawl.pipelines.RawPagePipeline": 100,
    "crawl.pipelines.DocumentPipeline": 200,
    "crawl.pipelines.ImageAssetPipeline": 300,
}

RAW_STORE_DIR = "data/raw"
DOCUMENT_STORE_PATH = "data/documents/documents.jsonl"
ASSET_STORE_DIR = "data/assets"
ASSET_MANIFEST_PATH = "data/assets/assets.jsonl"

# PromptImageScrape

Scrape all images from a domain, embed them with **jina-clip-v2**, and search by text prompt.

## Setup

```powershell
python -m venv .venv312          # Python 3.12 recommended
. .\.venv312\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

For CUDA support install the CUDA PyTorch wheels:

```powershell
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

## Quick start — full pipeline

```powershell
python cli.py run --domain books.toscrape.com --start-url https://books.toscrape.com/
```

This runs **crawl → index → interactive query** in one shot.  
Type a prompt (e.g. `a colourful book cover`) and the top-10 images are saved to `results/`.

## Individual steps

### 1. Crawl

```powershell
python cli.py crawl --domain books.toscrape.com --start-url https://books.toscrape.com/ --max-pages 50 --max-depth 3 --clean
```

Outputs:
- `data/documents/documents.jsonl` — normalised page documents
- `data/assets/assets.jsonl` — image asset manifest
- `data/raw/<domain>/` — raw HTML + sidecar metadata

### 2. Index

```powershell
python cli.py index
```

### 3. Interactive query

```powershell
python cli.py query --k 10
```

Each query saves the matched images at their original resolution plus a
`results.json` manifest into `results/<query>_<timestamp>/images/`.

## CLI reference

| Command | Description |
|---------|-------------|
| `python cli.py run`   | Full pipeline (crawl → index → query) |
| `python cli.py crawl` | Crawl a domain |
| `python cli.py index` | Build / rebuild LanceDB indexes |
| `python cli.py query` | Interactive prompt-based image search |

Use `python cli.py <command> --help` for all flags.
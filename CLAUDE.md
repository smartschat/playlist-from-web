# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLM-assisted CLI that scrapes public webpages, extracts track listings using OpenAI, and creates Spotify playlists. Requires Python 3.12+ and uv for dependency management.

## Commands

```bash
# Setup
uv venv && uv sync

# Development (no Spotify writes)
uv run python -m app dev <url>

# Full import (creates playlists)
uv run python -m app import <url>
uv run python -m app import <url> --search-only   # search/map without creating playlists

# Crawl index page (extract links, process all discovered playlists)
uv run python -m app crawl <index-url> --dev      # dry-run mode
uv run python -m app crawl <index-url>            # full import
uv run python -m app crawl <index-url> --max-links 5  # limit to first N links

# Replay from existing parsed artifact
uv run python -m app replay <data/parsed/foo.json>

# Web UI (view and manage playlists)
uv run python -m app serve              # start server on port 8000
uv run python -m app serve --reload     # with hot reload for development
# Frontend dev server: cd src/app/web/frontend && npm run dev

# Testing & linting
uv run python -m pytest              # run all tests
uv run python -m pytest -k test_name # run single test
uv run ruff check && uv run ruff format
uv run mypy
cd src/app/web/frontend && npm run check  # frontend type check
```

CI runs lint (Python + frontend) and tests on every push/PR to `main`.

## Architecture

```
src/app/
├── cli.py          # Typer CLI entrypoint (dev, import, replay, crawl, serve commands)
├── config.py       # Pydantic settings from .env (OpenAI, Spotify creds)
├── pipeline.py     # Main orchestration: fetch → parse → map → create playlists
├── llm.py          # OpenAI integration for extracting track blocks and links
├── pdf.py          # PDF text extraction using PyMuPDF
├── spotify_client.py # Spotify Web API client (auth, search, playlist creation)
├── models.py       # Pydantic models: Track, TrackBlock, ParsedPage, ExtractedLink, CrawlResult
├── utils.py        # Helpers: slugify URLs, file I/O
└── web/            # Web UI (FastAPI backend + Svelte frontend)
    ├── api/        # FastAPI routes and services
    │   └── routes/ # REST endpoints (playlists, spotify)
    └── frontend/   # Svelte 5 + Vite app
        ├── src/lib/        # API client, types
        ├── src/routes/     # Page components (Dashboard, PlaylistDetail)
        └── src/components/ # Reusable components (BlockCard, TrackRow, SpotifyPanel, etc.)
```

**Data flow:**
1. Fetch HTML/PDF → save to `data/raw/<slug>.html` or `data/raw/<slug>.pdf`
2. Clean HTML (strip scripts/nav) or extract PDF text → send to OpenAI for structured extraction
3. LLM returns JSON with track blocks → merge blocks by title → deduplicate → save to `data/parsed/<slug>.json`
4. Search Spotify for each track → create playlists → save results to `data/spotify/<slug>.json`

**Crawl flow:**
1. Fetch index page → extract links in markdown format `[text](url)`
2. LLM identifies playlist/tracklist links → return list of URLs
3. Process each URL through standard flow → save crawl summary to `data/crawl/<slug>.json`

## Configuration

Copy `.env.example` to `.env` with:
- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`, `SPOTIFY_USER_ID`, `SPOTIFY_REDIRECT_URI`
- `MASTER_PLAYLIST_ENABLED` (default: false)

## Code Style

- Python 3.12+, type hints throughout
- snake_case for functions/variables, PascalCase for classes, kebab-case for filenames
- Ruff for linting (E, F, W, I rules), line length 100
- Keep functions small; add comments only when intent is non-obvious

## Testing

- Tests in `tests/` directory, pytest with `pythonpath = ["src"]`
- Mock external APIs (Spotify, OpenAI) in tests; never hit live APIs in CI
- **Before pushing, always run:** `uv run ruff check && uv run ruff format --check && uv run python -m pytest`

## Commits

- Use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, etc.
- Keep PRs focused; split large changes into reviewable chunks

## Screenshots

Use Playwright to capture screenshots of the web UI:

```bash
# Ensure server is running
uv run python -m app serve

# Capture screenshot
uv run python -c "
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1200, 'height': 700})
    page.goto('http://localhost:8000')
    page.wait_for_load_state('networkidle')
    page.screenshot(path='screenshot.png')
    browser.close()
"
```

Add sample data to `data/parsed/` if needed (JSON files with playlist metadata).

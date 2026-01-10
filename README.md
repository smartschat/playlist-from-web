# playlist-from-web

![Python](https://img.shields.io/badge/python-3.12+-blue)
![Svelte](https://img.shields.io/badge/svelte-5-orange)
[![Tests](https://github.com/smartschat/playlist-from-web/actions/workflows/test.yml/badge.svg)](https://github.com/smartschat/playlist-from-web/actions/workflows/test.yml)
[![Lint](https://github.com/smartschat/playlist-from-web/actions/workflows/lint.yml/badge.svg)](https://github.com/smartschat/playlist-from-web/actions/workflows/lint.yml)

A CLI tool that turns any webpage with music track listings into Spotify playlists. Point it at a radio station's playlist page, a blog post listing songs, or any public webpage with artist/track info — it uses an LLM to extract the tracks and creates playlists in your Spotify account.

## Table of Contents

- [Quick Start](#quick-start)
- [How it works](#how-it-works)
- [Setup](#setup)
- [Commands](#commands)
  - [dev](#dev--test-parsing-without-spotify-writes)
  - [import](#import--parse-and-create-spotify-playlists)
  - [crawl](#crawl--process-multiple-pages-from-an-index)
  - [replay](#replay--re-run-from-saved-data)
- [Web UI](#web-ui)
- [Output Artifacts](#output-artifacts)
- [Development](#development)

## Quick Start

```bash
# Install
git clone https://github.com/smartschat/playlist-from-web.git
cd playlist-from-web
uv venv && uv sync

# Build frontend (required for web UI)
cd src/app/web/frontend && npm install && npm run build && cd -

# Configure (see Setup section for details)
cp .env.example .env
# Add your OPENAI_API_KEY and Spotify credentials to .env

# Authenticate with Spotify (one-time)
uv run python -m app auth

# Try it out (dry-run, no Spotify writes)
uv run python -m app dev "https://example.com/playlist-page"

# Create playlists for real
uv run python -m app import "https://example.com/playlist-page"
```

## How it works

1. **Fetch** — Downloads the webpage (HTML or PDF) and saves it locally
2. **Parse** — Sends cleaned text to OpenAI, which extracts structured track blocks (artist, title, album). For multi-page PDFs, blocks with the same title are merged automatically.
3. **Match** — Searches Spotify for each track using fuzzy matching with diacritic normalization. Tries multiple query strategies (artist+track, combined, title-only) to maximize matches.
4. **Create** — Builds one playlist per track block, named `<source> – <block title> – <date>`

## Setup

### Requirements

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- Node.js 18+ (for web UI)
- OpenAI API key
- Spotify Developer app (free to create)

### Configuration

Create a `.env` file with your API keys:

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5-nano  # or gpt-4o-mini, gpt-4o, etc.

# Spotify (from https://developer.spotify.com/dashboard)
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback  # must match your Spotify app settings

# Optional
MASTER_PLAYLIST_ENABLED=false  # create one combined playlist in addition to individual ones
LOG_LEVEL=INFO
```

Then authenticate with Spotify:

```bash
uv run python -m app auth
```

This opens your browser, asks you to log in, and saves your refresh token and user ID to `.env`. You only need to do this once.

For headless servers (no browser), use `--headless` to print the auth URL and paste the callback URL manually:

```bash
uv run python -m app auth --headless
```

## Commands

### `dev` — Test parsing without Spotify writes

```bash
uv run python -m app dev <url>
uv run python -m app dev <url> --force  # re-fetch even if cached
```

Fetches the page, runs LLM extraction, and saves artifacts to `data/raw/` and `data/parsed/`. Useful for checking what tracks were found before creating playlists.

### `import` — Parse and create Spotify playlists

```bash
uv run python -m app import <url>
uv run python -m app import <url> --search-only      # search Spotify but don't create playlists
uv run python -m app import <url> --force            # re-fetch and re-parse
uv run python -m app import <url> --master-playlist  # also create one combined playlist
```

### `crawl` — Process multiple pages from an index

If you have an index page linking to multiple playlist pages:

```bash
uv run python -m app crawl <index-url> --dev         # dry-run all discovered pages
uv run python -m app crawl <index-url>               # full import for all pages
uv run python -m app crawl <index-url> --max-links 5 # limit to first N links
uv run python -m app crawl <index-url> --search-only # search without creating playlists
```

The crawl command fetches the index, uses LLM to identify playlist links (including PDFs), and processes each through the standard pipeline. Results are saved to `data/crawl/<slug>.json`.

### `replay` — Re-run from saved data

Skip fetching and LLM calls by replaying from a previously parsed artifact:

```bash
uv run python -m app replay data/parsed/<slug>.json
```

## Web UI

View and manage extracted playlists through a web interface:

- Browse all parsed playlists and track blocks
- Edit tracks, blocks, and metadata inline
- View Spotify mapping status (matches and misses)
- Manually search and assign Spotify URIs for unmatched tracks
- Rename or delete Spotify playlists
- Import new URLs directly from the browser (preview before importing)
- Create Spotify playlists directly from parsed data (no CLI needed)
- View crawl results and retry failed URLs
- Track LLM costs per playlist and crawl

![Web UI Dashboard](dashboard.png)

**Note:** Requires the frontend to be built first (see Quick Start).

```bash
uv run python -m app serve
# Open http://localhost:8000
```

For development with hot reload:

```bash
# Terminal 1: Backend
uv run python -m app serve --reload

# Terminal 2: Frontend dev server
cd src/app/web/frontend
npm install  # first time only
npm run dev
# Open http://localhost:5173
```

## Output Artifacts

All data is saved locally for inspection and replay:

| Location | Contents |
|----------|----------|
| `data/raw/<slug>.html` | Original HTML from the source page |
| `data/raw/<slug>.pdf` | Original PDF (for PDF sources) |
| `data/parsed/<slug>.json` | Extracted track blocks from LLM |
| `data/spotify/<slug>.json` | Spotify search results and playlist URLs |
| `data/crawl/<slug>.json` | Crawl summary with discovered links and processing status |

## Development

```bash
# Run tests
uv run python -m pytest

# Lint and format
uv run ruff check && uv run ruff format

# Type check
uv run mypy
cd src/app/web/frontend && npm run check  # frontend
```

CI runs lint (Python + frontend) and tests on every push/PR to `main`.

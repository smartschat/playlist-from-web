# playlist-from-web

A CLI tool that turns any webpage with music track listings into Spotify playlists. Point it at a radio station's playlist page, a blog post listing songs, or any public webpage with artist/track info — it uses an LLM to extract the tracks and creates playlists in your Spotify account.

## How it works

1. **Fetch** — Downloads the webpage and saves the raw HTML
2. **Parse** — Sends cleaned text to OpenAI, which extracts structured track blocks (artist, title, album)
3. **Match** — Searches Spotify for each track using fuzzy matching with fallback queries
4. **Create** — Builds one playlist per track block, named after the source and date

## Setup

### Requirements

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- OpenAI API key
- Spotify Developer app (free to create)

### Installation

```bash
git clone https://github.com/youruser/playlist-from-web.git
cd playlist-from-web
uv venv && uv sync
```

### Configuration

**1. Create a `.env` file** with your API keys:

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini  # or gpt-4o, gpt-5-nano, etc.

# Spotify app credentials (from https://developer.spotify.com/dashboard)
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...

# Optional
MASTER_PLAYLIST_ENABLED=false  # set to true to also create one combined playlist
LOG_LEVEL=INFO
```

**2. Authenticate with Spotify** by running:

```bash
uv run python -m app auth
```

This opens your browser, asks you to log in to Spotify, and automatically saves your refresh token and user ID to `.env`. You only need to do this once.

> **Note**: Make sure `http://localhost:8888/callback` is listed as a redirect URI in your [Spotify app settings](https://developer.spotify.com/dashboard).

## Usage

### Development mode (no Spotify writes)

Test the parsing without creating any playlists:

```bash
uv run python -m app dev https://example.com/playlist-page
```

This fetches the page, runs LLM extraction, and saves artifacts to `data/raw/` and `data/parsed/` — useful for checking what tracks were found before committing to Spotify.

### Full import

Parse the page and create Spotify playlists:

```bash
uv run python -m app import https://example.com/playlist-page
```

Add `--search-only` to run Spotify search/matching without actually creating playlists (useful for checking match quality):

```bash
uv run python -m app import https://example.com/playlist-page --search-only
```

### Crawl an index page

If you have an index page that links to multiple playlist pages (including PDFs), use `crawl` to process them all:

```bash
# Dry-run: extract links and parse all discovered pages without creating playlists
uv run python -m app crawl https://example.com/playlists/index.html --dev

# Full import: parse and create Spotify playlists for all discovered pages
uv run python -m app crawl https://example.com/playlists/index.html

# Limit to first 5 discovered links
uv run python -m app crawl https://example.com/playlists/index.html --max-links 5
```

The crawl command:
1. Fetches the index page and extracts all links
2. Uses LLM to identify which links point to playlist/tracklist pages (including PDFs)
3. Processes each discovered URL through the standard pipeline
4. Saves a summary to `data/crawl/<slug>.json`

### Replay from saved data

Re-run Spotify mapping using a previously parsed artifact (skips fetch and LLM calls):

```bash
uv run python -m app replay data/parsed/example-com-playlist-page.json
```

### Web UI

View and manage your extracted playlists through a web interface:

```bash
# Start the server
uv run python -m app serve

# Open http://localhost:8000 in your browser
```

For development with hot reload:

```bash
# Terminal 1: Backend with reload
uv run python -m app serve --reload

# Terminal 2: Frontend dev server
cd src/app/web/frontend
npm install  # first time only
npm run dev

# Open http://localhost:5173
```

### Options

- `--force` — Re-fetch and re-parse even if artifacts already exist
- `--master-playlist` / `--no-master-playlist` — Override the default master playlist setting
- `--search-only` — Search Spotify but don't create playlists (import command only)

## Output artifacts

All data is saved locally for inspection and replay:

| Location | Contents |
|----------|----------|
| `data/raw/<slug>.html` | Original HTML from the source page |
| `data/raw/<slug>.pdf` | Original PDF (for PDF sources) |
| `data/parsed/<slug>.json` | Extracted track blocks from LLM |
| `data/spotify/<slug>.json` | Spotify search results, playlist URLs, and any tracks that couldn't be matched |
| `data/crawl/<slug>.json` | Crawl summary: discovered links, processing status for each |

## Example

```bash
# Parse an hr2 radio playlist page
uv run python -m app dev "https://www.hr2.de/programm/hoerbar/hoerbar---musik-grenzenlos,epg-hoerbar-4290.html"

# Check the parsed output
cat data/parsed/www-hr2-de-programm-hoerbar-*.json | jq '.blocks[0].tracks[:3]'

# Create the playlists
uv run python -m app import "https://www.hr2.de/programm/hoerbar/hoerbar---musik-grenzenlos,epg-hoerbar-4290.html"
```

## Development

```bash
# Run tests
uv run python -m pytest

# Lint and format
uv run ruff check
uv run ruff format

# Type check (optional)
uv run mypy
```

## Notes

- **PDF support**: Automatically detects and extracts text from PDF tracklists using PyMuPDF
- **Block merging**: When a multi-page PDF produces multiple blocks with the same title, they're merged into one
- **Playlist naming**: Playlists are named `<source> – <block title> – <date>`, e.g., "hr2 – Hörbar Musik Grenzenlos – 2024-01-15"
- **Track matching**: Uses fuzzy matching with diacritic normalization. Tries multiple query strategies (artist+track, combined, title-only) to minimize misses
- **Rate limits**: Automatically retries on Spotify rate limits (429) with exponential backoff
- **Caching**: Search results are cached within a session to avoid duplicate API calls for the same track

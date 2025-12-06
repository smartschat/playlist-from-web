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
- Spotify Developer credentials with a refresh token

### Installation

```bash
git clone https://github.com/youruser/playlist-from-web.git
cd playlist-from-web
uv venv && uv sync
```

### Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini  # or gpt-4o, gpt-5-nano, etc.

# Spotify (requires Authorization Code flow with refresh token)
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REFRESH_TOKEN=...
SPOTIFY_USER_ID=...
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback

# Optional
MASTER_PLAYLIST_ENABLED=false  # set to true to also create one combined playlist
LOG_LEVEL=INFO
```

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

### Replay from saved data

Re-run Spotify mapping using a previously parsed artifact (skips fetch and LLM calls):

```bash
uv run python -m app replay data/parsed/example-com-playlist-page.json
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
| `data/parsed/<slug>.json` | Extracted track blocks from LLM |
| `data/spotify/<slug>.json` | Spotify search results, playlist URLs, and any tracks that couldn't be matched |

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

- **Playlist naming**: Playlists are named `<source> – <block title> – <date>`, e.g., "hr2 – Hörbar Musik Grenzenlos – 2024-01-15"
- **Track matching**: Uses fuzzy matching with diacritic normalization. Tries multiple query strategies (artist+track, combined, title-only) to minimize misses
- **Rate limits**: Automatically retries on Spotify rate limits (429) with exponential backoff
- **Caching**: Search results are cached within a session to avoid duplicate API calls for the same track

# playlist-from-web

LLM-assisted CLI that scrapes public webpages, extracts track listings, and creates Spotify playlists under your account. Uses OpenAI for structured parsing and the Spotify Web API for playlist creation.

## Setup
- Python 3.12+, [uv](https://github.com/astral-sh/uv) installed.
- Copy `.env.example` to `.env` and fill:
- OpenAI: `OPENAI_API_KEY`, `OPENAI_MODEL` (e.g., `gpt-5-nano` or your preferred model).
  - Spotify: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`, `SPOTIFY_USER_ID`, `SPOTIFY_REDIRECT_URI`.
  - Optional: `MASTER_PLAYLIST_ENABLED=false` to keep per-block only.
- Install deps: `uv venv && uv sync`.

## Commands
- `uv run python -m app dev <url>` — fetch, LLM-parse, write artifacts (`data/raw/`, `data/parsed/`), no Spotify writes.
- `uv run python -m app import <url>` — full run: parse + Spotify search + playlist creation; add `--no-write` to collect matches/misses without creating playlists.
- `uv run python -m app replay <data/parsed/foo.json>` — re-run Spotify mapping from an existing parsed artifact.

Artifacts:
- Raw HTML: `data/raw/<slug>.html`
- Parsed blocks JSON: `data/parsed/<slug>.json`
- Spotify results: `data/spotify/<slug>.json` (includes playlist URLs and misses)

## Testing & Linting
- `uv run pytest` (set `UV_CACHE_DIR=.uv-cache` if needed for cache permissions)
- `uv run ruff check` / `uv run ruff format`
- `uv run mypy` (optional type check)

## Behavior Notes
- Playlist names: `<source> – <block title or context> – <date>`. Master playlist creation is disabled by default.
- Spotify search: fuzzy matching with diacritic-insensitive normalization and multi-query fallback to reduce misses.
- LLM parsing: truncates long pages, strips scripts/nav from HTML, and enforces a strict JSON schema for blocks/tracks.

## Secrets & Safety
- Keep `.env` out of git. Rotate Spotify/OpenAI keys if exposed.
- Use `--no-write` to validate mapping without touching your Spotify account.

## Example Run
```
# Dry run: parse hr2 page without Spotify writes
uv run python -m app dev https://www.hr2.de/programm/hoerbar/hoerbar---musik-grenzenlos,epg-hoerbar-4290.html

# Full import: create playlists
uv run python -m app import https://www.hr2.de/programm/hoerbar/hoerbar---musik-grenzenlos,epg-hoerbar-4290.html
# Output includes playlist URL and misses; artifacts in data/parsed/ and data/spotify/
```

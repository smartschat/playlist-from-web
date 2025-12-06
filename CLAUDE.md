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

# Replay from existing parsed artifact
uv run python -m app replay <data/parsed/foo.json>

# Testing & linting
uv run pytest                    # run all tests
uv run pytest -k test_name       # run single test
uv run ruff check && uv run ruff format
uv run mypy
```

## Architecture

```
src/app/
├── cli.py          # Typer CLI entrypoint (dev, import, replay commands)
├── config.py       # Pydantic settings from .env (OpenAI, Spotify creds)
├── pipeline.py     # Main orchestration: fetch → parse → map → create playlists
├── llm.py          # OpenAI integration for extracting track blocks
├── spotify_client.py # Spotify Web API client (auth, search, playlist creation)
├── models.py       # Pydantic models: Track, TrackBlock, ParsedPage
└── utils.py        # Helpers: slugify URLs, file I/O
```

**Data flow:**
1. Fetch HTML → save to `data/raw/<slug>.html`
2. Clean HTML (strip scripts/nav) → send to OpenAI for structured extraction
3. LLM returns JSON with track blocks → validate with Pydantic → save to `data/parsed/<slug>.json`
4. Search Spotify for each track → create playlists → save results to `data/spotify/<slug>.json`

## Configuration

Copy `.env.example` to `.env` with:
- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`, `SPOTIFY_USER_ID`, `SPOTIFY_REDIRECT_URI`
- `MASTER_PLAYLIST_ENABLED` (default: false)

## Code Style

- Python 3.12+, type hints throughout
- snake_case for functions/variables, PascalCase for classes
- Ruff for linting (E, F, W, I rules), line length 100
- Tests in `tests/` directory, pytest with `pythonpath = ["src"]`

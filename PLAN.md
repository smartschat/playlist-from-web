# Implementation Plan

## Goal
Build a Python tool that, given a public webpage, uses OpenAI to extract coherent blocks of music track listings, stores each block, maps tracks to Spotify, and creates one playlist per block under the user’s account (with a master playlist optional).

## Assumptions
- Stack: Python 3.12+, uv for env/deps; OpenAI GPT-4o/4o-mini via `OPENAI_API_KEY`.
- Spotify: Authorization Code with refresh token; require `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`, `SPOTIFY_USER_ID`, `SPOTIFY_REDIRECT_URI`.
- Pages are public HTML (e.g., hr2 Hörbar) without login walls or heavy anti-bot measures.

## Architecture & Data Flow
1) Fetch + sanitize HTML (httpx + selectolax/BeautifulSoup); save raw snapshot to `data/raw/<slug>.html`.
2) Segment candidate blocks: detect repeated sections/lists and extract text per block.
3) LLM extraction: send per-block text to OpenAI with strict JSON schema (title/context, ordered tracks with artist/title/optional album/source line). Use low temperature and JSON mode/`response_format`.
4) Validation: pydantic models + heuristics (require artist & title; drop lines <3 tokens; normalize dashes/whitespace; dedupe by slugified artist+title).
5) Spotify mapping: search per track via Spotify Web API; prefer exact artist+title match, then popularity. Log misses for retries.
6) Playlist creation: name format `SourceName – BlockTitle – YYYY-MM-DD` (fallback: timestamp); optional master playlist aggregating all tracks. Persist `data/parsed/<slug>.json` and `data/spotify/<slug>.json`.
7) Re-runability: skip already processed URLs unless `--force`; `--dry-run` avoids Spotify writes.

## Commands (planned)
- `uv venv && uv sync` — create/populate venv.
- `uv run python -m app dev <url>` — fetch + LLM parse + write artifacts (dry run; no Spotify writes).
- `uv run python -m app import <url>` — full run including Spotify playlist creation.
- `uv run python -m app replay <parsed.json>` — re-run Spotify mapping without new LLM calls.
- `uv run pytest` — tests; `uv run ruff check/format`; `uv run mypy` if enabled.

## Implementation Milestones
1) Scaffold: `pyproject.toml` (uv), ruff config, pytest config, `src/` + `data/` dirs, env loading (`python-dotenv`).
2) HTML ingest & block segmentation utilities with fixtures from the hr2 example.
3) OpenAI client + prompts + pydantic validation; retries/backoff; logging of raw LLM responses.
4) Track normalization + dedupe; handle edge cases (missing artist, timecodes, commentary lines).
5) Spotify client (auth refresh), search + best-match selection, playlist creation, rate-limit handling.
6) CLI wiring (typer/click) with flags `--force`, `--dry-run`, `--master-playlist`.
7) Tests: parsing fixtures, prompt-contract tests, Spotify search mapper with mocked API, CLI smoke tests.

## Security & Ops
- Never commit secrets; require `.env` with sample `.env.example`.
- Respect robots.txt where applicable; throttle requests to avoid hammering source sites.
- Log to stdout + files under `logs/` for mapping failures and playlist URLs.

## Next Steps
- Initialize the Python project with uv scaffolding.
- Obtain Spotify refresh token for the target account.

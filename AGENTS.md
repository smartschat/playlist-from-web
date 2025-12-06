# Repository Guidelines

## Project Structure & Module Organization
- Keep application code under `src/` (ingestion, LLM parsing, Spotify client, CLI entrypoints).
- Mirror tests in `tests/` using the same folder names for quick lookup; fixtures under `tests/fixtures/`.
- Put one-off tooling in `scripts/` (data pulls, lint hooks); persist raw/parsed artifacts in `data/raw/` and `data/parsed/`.
- Document decisions in `docs/`; keep `.env.example` updated as secrets/config evolve.

## Build, Test, and Development Commands
- `uv venv && uv sync` — create and populate the virtualenv from `pyproject.toml`/`uv.lock`.
- `uv run python -m app dev <url>` — fetch, LLM parse, write artifacts (no Spotify writes).
- `uv run python -m app import <url>` — full run including Spotify playlist creation; add `--no-write` to search/map without creating playlists (collect misses).
- `uv run python -m app replay <parsed.json>` — re-run Spotify mapping without new LLM calls (e.g., from `data/parsed/...json`).
- `uv run pytest` — execute tests; add `-k`/`-q` for focused runs.
- `uv run ruff check` / `uv run ruff format` — lint and format; keep clean before opening PRs.
- `uv run mypy` — optional static type check if enabled in the project.

## Coding Style & Naming Conventions
- Target Python 3.12+ with 4-space indentation; prefer type hints everywhere.
- Use snake_case for functions/variables, PascalCase for classes, kebab-case for filenames, and UPPER_SNAKE_CASE for environment variables.
- Centralize HTTP/Spotify calls in shared helpers for auth, headers, and error mapping; avoid duplicating request logic.
- Keep functions small and pure when possible; add brief comments only when intent is non-obvious.

## Testing Guidelines
- Use pytest with files named `test_*.py`; colocate tests near code or under `tests/`.
- Mock Spotify HTTP calls and LLM responses; never hit live APIs in CI.
- Cover parsing/normalization, auth flows, and playlist/track mapping; add regression cases for any bug found.
- Run `uv run pytest` before pushing; include malformed input and negative cases.

## Commit & Pull Request Guidelines
- Use conventional commits (`feat:`, `fix:`, `chore:`, etc.) with imperative, scoped messages.
- PRs should state intent, user impact, tests run, and link issues/tickets; attach screenshots/CLI output for user-facing changes.
- Keep diffs focused; split large changes into reviewable chunks when needed.

## Security & Configuration Tips
- Keep secrets out of git; load Spotify and OpenAI credentials from `.env` and commit only a sanitized `.env.example`.
- Rotate client secrets if leaked; store environment-specific config separately (e.g., `config/` or per-env `.env` files).

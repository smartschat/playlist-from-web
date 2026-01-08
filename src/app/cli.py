import re
from pathlib import Path
from typing import Optional

import typer

from . import pipeline
from .config import get_settings
from .logging_setup import setup_logging

app = typer.Typer(
    add_completion=False,
    help="LLM-powered importer: parse web track listings and create Spotify playlists.",
)


@app.command()
def auth(
    client_id: Optional[str] = typer.Option(
        None,
        "--client-id",
        envvar="SPOTIFY_CLIENT_ID",
        help="Spotify client ID (or set SPOTIFY_CLIENT_ID env var).",
    ),
    client_secret: Optional[str] = typer.Option(
        None,
        "--client-secret",
        envvar="SPOTIFY_CLIENT_SECRET",
        help="Spotify client secret (or set SPOTIFY_CLIENT_SECRET env var).",
    ),
    redirect_uri: str = typer.Option(
        "http://localhost:8888/callback",
        "--redirect-uri",
        envvar="SPOTIFY_REDIRECT_URI",
        help="OAuth redirect URI (must match your Spotify app settings).",
    ),
    save_to_env: bool = typer.Option(
        True,
        "--save/--no-save",
        help="Save tokens to .env file.",
    ),
) -> None:
    """
    Authenticate with Spotify and obtain a refresh token.

    Opens your browser to log in to Spotify, then saves the refresh token
    to your .env file. You only need to run this once.
    """
    from .spotify_auth import get_user_id, run_oauth_flow

    if not client_id or not client_secret:
        typer.echo("Error: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are required.")
        typer.echo("Set them as environment variables or pass --client-id and --client-secret.")
        raise typer.Exit(code=1)

    typer.echo("Opening browser for Spotify authorization...")
    typer.echo(f"Redirect URI: {redirect_uri}")
    typer.echo("(Make sure this URI is registered in your Spotify app settings)\n")

    try:
        tokens = run_oauth_flow(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
    except TimeoutError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1) from e
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1) from e

    refresh_token = tokens["refresh_token"]
    access_token = tokens["access_token"]

    # Fetch user ID
    try:
        user_id = get_user_id(access_token)
    except Exception as e:
        typer.echo(f"Warning: Could not fetch user ID: {e}")
        user_id = None

    typer.echo("\nAuthorization successful!\n")
    typer.echo(f"Refresh Token: {refresh_token}")
    if user_id:
        typer.echo(f"User ID: {user_id}")

    if save_to_env:
        env_path = Path(".env")
        _update_env_file(env_path, "SPOTIFY_REFRESH_TOKEN", refresh_token)
        if user_id:
            _update_env_file(env_path, "SPOTIFY_USER_ID", user_id)
        typer.echo(f"\nSaved to {env_path}")
    else:
        typer.echo("\nAdd these to your .env file:")
        typer.echo(f"SPOTIFY_REFRESH_TOKEN={refresh_token}")
        if user_id:
            typer.echo(f"SPOTIFY_USER_ID={user_id}")


def _update_env_file(env_path: Path, key: str, value: str) -> None:
    """Update or add a key in the .env file."""
    if env_path.exists():
        content = env_path.read_text()
    else:
        content = ""

    # Check if key already exists
    pattern = rf"^{re.escape(key)}=.*$"
    if re.search(pattern, content, re.MULTILINE):
        # Replace existing value
        content = re.sub(pattern, f"{key}={value}", content, flags=re.MULTILINE)
    else:
        # Append new key
        if content and not content.endswith("\n"):
            content += "\n"
        content += f"{key}={value}\n"

    env_path.write_text(content)


@app.command()
def dev(
    url: str = typer.Argument(..., help="URL of the page to parse (no Spotify writes)."),
    force: bool = typer.Option(
        False, "--force", help="Re-fetch and overwrite existing artifacts for the URL."
    ),
) -> None:
    """
    Dry-run: fetch, parse with LLM, and emit artifacts without writing to Spotify.
    """
    settings = get_settings()
    setup_logging(settings.log_level)
    master_playlist = settings.master_playlist_enabled
    typer.echo(f"[dry-run] Processing {url} | master playlist: {master_playlist} | force: {force}.")
    try:
        pipeline.run_dev(url=url, force=force, settings=settings)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1) from exc


@app.command("import")
def import_cmd(
    url: str = typer.Argument(..., help="URL of the page to import."),
    force: bool = typer.Option(
        False, "--force", help="Re-fetch and overwrite existing artifacts for the URL."
    ),
    master_playlist: Optional[bool] = typer.Option(
        None,
        "--master-playlist/--no-master-playlist",
        help="Override default master playlist creation.",
    ),
    search_only: bool = typer.Option(
        False,
        "--search-only",
        help="Run Spotify search/mapping but do not create playlists (collect misses only).",
    ),
) -> None:
    """
    Full run: fetch, parse with LLM, map to Spotify, and create playlists.
    """
    settings = get_settings()
    setup_logging(settings.log_level)
    master_enabled = (
        settings.master_playlist_enabled if master_playlist is None else master_playlist
    )
    typer.echo(
        f"[import] Processing {url} | master playlist: {master_enabled} | "
        f"force: {force} | search_only: {search_only}."
    )
    try:
        pipeline.run_import(
            url=url,
            force=force,
            master_playlist=master_enabled,
            settings=settings,
            write_playlists=not search_only,
        )
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def replay(
    parsed: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        dir_okay=False,
        help="Path to a parsed JSON artifact to re-run Spotify mapping without new LLM calls.",
    ),
) -> None:
    """
    Re-run Spotify mapping using an existing parsed artifact; skip fetch/LLM.
    """
    settings = get_settings()
    setup_logging(settings.log_level)
    master_playlist = settings.master_playlist_enabled
    typer.echo(f"[replay] Using {parsed} | master playlist: {master_playlist}.")
    try:
        pipeline.run_replay(parsed=parsed, master_playlist=master_playlist, settings=settings)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1) from exc


@app.command()
def crawl(
    index_url: str = typer.Argument(..., help="URL of the index page to crawl for playlist links."),
    dev_mode: bool = typer.Option(
        False, "--dev", help="Run in dev mode (dry-run, no Spotify writes)."
    ),
    force: bool = typer.Option(False, "--force", help="Re-fetch pages even if cached."),
    master_playlist: Optional[bool] = typer.Option(
        None,
        "--master-playlist/--no-master-playlist",
        help="Override default master playlist creation.",
    ),
    search_only: bool = typer.Option(
        False,
        "--search-only",
        help="Run Spotify search/mapping but do not create playlists.",
    ),
    max_links: Optional[int] = typer.Option(
        None,
        "--max-links",
        help="Maximum number of discovered links to process.",
    ),
) -> None:
    """
    Crawl an index page, extract playlist links with LLM, and process all discovered URLs.

    Uses OpenAI to identify links to pages containing playlists or track listings,
    then processes each link through the normal import or dev pipeline.
    Supports both HTML pages and PDF files.

    Examples:
        uv run python -m app crawl https://example.com/playlists --dev
        uv run python -m app crawl https://example.com/archive --max-links 5
    """
    settings = get_settings()
    setup_logging(settings.log_level)

    master_enabled = (
        settings.master_playlist_enabled if master_playlist is None else master_playlist
    )

    mode_str = "dev" if dev_mode else "import"
    typer.echo(
        f"[crawl] Processing index {index_url} | mode: {mode_str} | "
        f"master playlist: {master_enabled} | force: {force}"
    )

    if not dev_mode:
        settings.require_spotify_auth()

    try:
        from .utils import slugify_url

        result = pipeline.run_crawl(
            index_url=index_url,
            dev_mode=dev_mode,
            force=force,
            master_playlist=master_enabled,
            settings=settings,
            write_playlists=not search_only,
            max_links=max_links,
        )

        # Summary
        success_count = sum(1 for p in result.processed if p["status"] == "success")
        skipped_count = sum(1 for p in result.processed if p["status"] == "skipped")
        fail_count = sum(1 for p in result.processed if p["status"] == "failed")

        typer.echo(f"\n[crawl] Complete. Discovered {len(result.discovered_links)} links.")
        typer.echo(
            f"  Processed: {success_count} new, {skipped_count} skipped, {fail_count} failed."
        )

        index_slug = slugify_url(index_url)
        typer.echo(f"  Summary artifact: data/crawl/{index_slug}.json")

        if fail_count > 0 and success_count == 0:
            raise typer.Exit(code=1)

    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1) from exc

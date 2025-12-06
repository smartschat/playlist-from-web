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
    no_write: bool = typer.Option(
        False,
        "--no-write",
        help="Search and map tracks but do not create playlists (collect misses only).",
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
        f"[import] Processing {url} | master playlist: {master_enabled} | force: {force} | no_write: {no_write}."
    )
    try:
        pipeline.run_import(
            url=url,
            force=force,
            master_playlist=master_enabled,
            settings=settings,
            write_playlists=not no_write,
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
    )
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

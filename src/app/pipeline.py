import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import Settings
from .llm import parse_with_llm
from .models import ParsedPage, Track, TrackBlock
from .spotify_client import (
    SpotifyClient,
    select_description,
    select_playlist_name,
)
from .utils import ensure_parent, read_text, slugify_url, write_json

logger = logging.getLogger(__name__)


def _clean_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, httpx.HTTPStatusError)),
    reraise=True,
)
def _fetch_html(url: str) -> str:
    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def _load_or_fetch_html(url: str, slug: str, force: bool) -> Tuple[str, Path]:
    raw_path = Path("data/raw") / f"{slug}.html"
    if raw_path.exists() and not force:
        return read_text(raw_path), raw_path
    html = _fetch_html(url)
    ensure_parent(raw_path)
    raw_path.write_text(html, encoding="utf-8")
    return html, raw_path


def _serialize_parsed(parsed: ParsedPage) -> Dict:
    return {
        "source_url": str(parsed.source_url),
        "source_name": parsed.source_name,
        "fetched_at": parsed.fetched_at.isoformat(),
        "blocks": [
            {
                "title": block.title,
                "context": block.context,
                "tracks": [
                    {
                        "artist": t.artist,
                        "title": t.title,
                        "album": t.album,
                        "source_line": t.source_line,
                    }
                    for t in block.tracks
                ],
            }
            for block in parsed.blocks
        ],
    }


def _dedupe_tracks(tracks: List[Track], seen: set | None = None) -> Tuple[List[Track], set]:
    """Deduplicate tracks, optionally using a shared seen set for global deduplication."""
    if seen is None:
        seen = set()
    deduped = []
    for t in tracks:
        key = (t.artist.lower().strip(), t.title.lower().strip())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(t)
    return deduped, seen


def _dedupe_blocks_globally(blocks: List[TrackBlock]) -> List[TrackBlock]:
    """Deduplicate tracks across all blocks globally."""
    seen: set = set()
    result = []
    for block in blocks:
        deduped_tracks, seen = _dedupe_tracks(block.tracks, seen)
        if deduped_tracks:
            result.append(
                TrackBlock(
                    title=block.title,
                    context=block.context,
                    tracks=deduped_tracks,
                )
            )
    return result


def _process_url(url: str, force: bool, settings: Settings) -> Tuple[ParsedPage, Path]:
    slug = slugify_url(url)
    html, raw_path = _load_or_fetch_html(url, slug, force)
    cleaned = _clean_text_from_html(html)
    parsed = parse_with_llm(
        url=url, content=cleaned, model=settings.openai_model, api_key=settings.openai_api_key
    )
    # Global deduplication across all blocks
    deduped_blocks = _dedupe_blocks_globally(parsed.blocks)
    parsed = ParsedPage(
        source_url=parsed.source_url,
        source_name=parsed.source_name,
        fetched_at=parsed.fetched_at,
        blocks=deduped_blocks,
    )
    parsed_path = Path("data/parsed") / f"{slug}.json"
    write_json(parsed_path, _serialize_parsed(parsed))
    return parsed, parsed_path


def _map_tracks_to_spotify(
    client: SpotifyClient, parsed: ParsedPage
) -> Tuple[List[Dict], List[Dict]]:
    mapped_blocks: List[Dict] = []
    misses: List[Dict] = []
    for block in parsed.blocks:
        mapped_tracks: List[Dict] = []
        for track in block.tracks:
            result = client.search_track(artist=track.artist, title=track.title)
            if not result:
                misses.append({"block": block.title, "artist": track.artist, "title": track.title})
                continue
            mapped_tracks.append(
                {
                    "artist": track.artist,
                    "title": track.title,
                    "album": track.album,
                    "source_line": track.source_line,
                    "spotify_uri": result["uri"],
                    "spotify_url": result["external_urls"]["spotify"],
                }
            )
        mapped_blocks.append(
            {
                "title": block.title,
                "context": block.context,
                "tracks": mapped_tracks,
            }
        )
    return mapped_blocks, misses


def run_dev(url: str, force: bool, settings: Settings) -> None:
    parsed, parsed_path = _process_url(url, force, settings)
    logger.info("Parsed %d blocks from %s. Saved to %s", len(parsed.blocks), url, parsed_path)
    typer_msg = f"Parsed {len(parsed.blocks)} blocks. Artifact: {parsed_path}"
    print(typer_msg)


def _create_playlists(
    client: SpotifyClient,
    parsed: ParsedPage,
    mapped_blocks: List[Dict],
    master_playlist: bool,
) -> Dict:
    results: Dict = {"playlists": [], "master_playlist": None, "failed_tracks": []}
    fetched_date = parsed.fetched_at.date().isoformat()
    master_tracks: List[str] = []
    for block in mapped_blocks:
        uris = [t["spotify_uri"] for t in block["tracks"] if t.get("spotify_uri")]
        if not uris:
            continue
        name = select_playlist_name(
            parsed.source_name, block.get("title", ""), fetched_date, block.get("context")
        )
        description = select_description(parsed.source_url, block.get("context"))
        playlist = client.create_playlist(name=name, description=description, public=False)
        added, failed = client.add_tracks(playlist_id=playlist["id"], uris=uris)
        if failed:
            results["failed_tracks"].extend(failed)
            logger.warning("Failed to add %d tracks to playlist %s", len(failed), name)
        results["playlists"].append(
            {
                "id": playlist["id"],
                "name": playlist["name"],
                "url": playlist["external_urls"]["spotify"],
                "tracks": uris,
                "tracks_added": added,
            }
        )
        master_tracks.extend(uris)

    if master_playlist and master_tracks:
        name = f"{parsed.source_name or 'Imported'} – All – {fetched_date}"
        description = select_description(parsed.source_url, "All blocks combined")
        playlist = client.create_playlist(name=name, description=description, public=False)
        added, failed = client.add_tracks(playlist_id=playlist["id"], uris=master_tracks)
        if failed:
            results["failed_tracks"].extend(failed)
        results["master_playlist"] = {
            "id": playlist["id"],
            "name": playlist["name"],
            "url": playlist["external_urls"]["spotify"],
            "tracks": master_tracks,
            "tracks_added": added,
        }
    return results


def run_import(
    url: str,
    force: bool,
    master_playlist: bool,
    settings: Settings,
    write_playlists: bool = True,
) -> None:
    settings.require_spotify_auth()
    parsed, parsed_path = _process_url(url, force, settings)
    with SpotifyClient(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
        refresh_token=settings.spotify_refresh_token,
        user_id=settings.spotify_user_id,
    ) as client:
        mapped_blocks, misses = _map_tracks_to_spotify(client, parsed)
        creation = (
            _create_playlists(client, parsed, mapped_blocks, master_playlist)
            if write_playlists
            else {"playlists": [], "master_playlist": None, "failed_tracks": []}
        )
    slug = slugify_url(url)
    spotify_path = Path("data/spotify") / f"{slug}.json"
    write_json(
        spotify_path,
        {
            "source_url": url,
            "parsed_artifact": str(parsed_path),
            "blocks": mapped_blocks,
            "playlists": creation["playlists"],
            "master_playlist": creation.get("master_playlist"),
            "misses": misses,
            "failed_tracks": creation.get("failed_tracks", []),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "write_playlists": write_playlists,
        },
    )
    action = "Mapped (no write)" if not write_playlists else "Created"
    n_playlists = len(creation["playlists"])
    print(f"{action} {n_playlists} playlists. Misses: {len(misses)}. Artifact: {spotify_path}")


def run_replay(parsed: Path, master_playlist: bool, settings: Settings) -> None:
    settings.require_spotify_auth()
    data = json.loads(parsed.read_text(encoding="utf-8"))
    parsed_page = ParsedPage(
        source_url=data["source_url"],
        source_name=data.get("source_name"),
        fetched_at=datetime.fromisoformat(data["fetched_at"]),
        blocks=[
            TrackBlock(
                title=b["title"],
                context=b.get("context"),
                tracks=[
                    Track(
                        artist=t["artist"],
                        title=t["title"],
                        album=t.get("album"),
                        source_line=t.get("source_line"),
                    )
                    for t in b.get("tracks", [])
                ],
            )
            for b in data.get("blocks", [])
        ],
    )
    with SpotifyClient(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
        refresh_token=settings.spotify_refresh_token,
        user_id=settings.spotify_user_id,
    ) as client:
        mapped_blocks, misses = _map_tracks_to_spotify(client, parsed_page)
        creation = _create_playlists(client, parsed_page, mapped_blocks, master_playlist)
    slug = parsed.stem
    spotify_path = Path("data/spotify") / f"{slug}.json"
    write_json(
        spotify_path,
        {
            "source_url": str(parsed_page.source_url),
            "parsed_artifact": str(parsed),
            "blocks": mapped_blocks,
            "playlists": creation["playlists"],
            "master_playlist": creation.get("master_playlist"),
            "misses": misses,
            "failed_tracks": creation.get("failed_tracks", []),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    n_playlists = len(creation["playlists"])
    n_misses = len(misses)
    print(f"[replay] Created {n_playlists} playlists. Misses: {n_misses}. Artifact: {spotify_path}")

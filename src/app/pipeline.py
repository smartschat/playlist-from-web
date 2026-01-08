import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import Settings
from .llm import extract_links_with_llm, parse_with_llm
from .models import CrawlResult, ExtractedLink, ParsedPage, Track, TrackBlock
from .pdf import extract_text_from_pdf
from .spotify_client import (
    SpotifyClient,
    select_description,
    select_playlist_name,
)
from .utils import ensure_parent, read_text, slugify_url, write_json

logger = logging.getLogger(__name__)


def _get_artifact_path(url: str, artifact_type: str) -> Path:
    """Get the artifact path for a URL. artifact_type is 'parsed' or 'spotify'."""
    slug = slugify_url(url)
    return Path(f"data/{artifact_type}") / f"{slug}.json"


def is_already_imported(url: str) -> bool:
    """Check if a URL has already been imported (has a spotify artifact)."""
    return _get_artifact_path(url, "spotify").exists()


def is_already_parsed(url: str) -> bool:
    """Check if a URL has already been parsed (has a parsed artifact)."""
    return _get_artifact_path(url, "parsed").exists()


def _clean_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _extract_links_from_html(html: str) -> str:
    """
    Extract links from HTML, preserving URL information for the LLM.

    Returns a formatted string with each link on its own line:
    [link text](url)
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True) or "(no text)"
        # Skip anchors and javascript
        if href.startswith("#") or href.startswith("javascript:"):
            continue
        links.append(f"[{text}]({href})")

    return "\n".join(links)


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


def _is_pdf_url(url: str) -> bool:
    """Check if URL likely points to a PDF based on extension."""
    return url.lower().rstrip("/").endswith(".pdf")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, httpx.HTTPStatusError)),
    reraise=True,
)
def _fetch_pdf(url: str) -> bytes:
    """Fetch PDF content as bytes."""
    resp = httpx.get(url, timeout=60)
    resp.raise_for_status()
    return resp.content


def _load_or_fetch_pdf(url: str, slug: str, force: bool) -> Tuple[str, Path]:
    """Load PDF from cache or fetch, returning extracted text content."""
    raw_path = Path("data/raw") / f"{slug}.pdf"
    if raw_path.exists() and not force:
        pdf_bytes = raw_path.read_bytes()
    else:
        pdf_bytes = _fetch_pdf(url)
        ensure_parent(raw_path)
        raw_path.write_bytes(pdf_bytes)
    text = extract_text_from_pdf(pdf_bytes)
    return text, raw_path


def _load_or_fetch_content(url: str, slug: str, force: bool) -> Tuple[str, Path, bool]:
    """
    Unified content fetcher for HTML and PDF.

    Returns:
        Tuple of (text_content, raw_path, is_pdf)
    """
    if _is_pdf_url(url):
        text, raw_path = _load_or_fetch_pdf(url, slug, force)
        return text, raw_path, True
    else:
        html, raw_path = _load_or_fetch_html(url, slug, force)
        text = _clean_text_from_html(html)
        return text, raw_path, False


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


def _merge_blocks_by_title(blocks: List[TrackBlock]) -> List[TrackBlock]:
    """Merge blocks with matching title and context into single blocks."""
    merged: Dict[Tuple[str, Optional[str]], TrackBlock] = {}

    for block in blocks:
        key = (block.title.strip().lower(), (block.context or "").strip().lower() or None)
        if key in merged:
            # Append tracks to existing block
            existing = merged[key]
            merged[key] = TrackBlock(
                title=existing.title,
                context=existing.context,
                tracks=existing.tracks + block.tracks,
            )
        else:
            merged[key] = block

    return list(merged.values())


def _process_url(url: str, force: bool, settings: Settings) -> Tuple[ParsedPage, Path]:
    slug = slugify_url(url)
    content, raw_path, is_pdf = _load_or_fetch_content(url, slug, force)
    parsed = parse_with_llm(
        url=url, content=content, model=settings.openai_model, api_key=settings.openai_api_key
    )
    # Merge blocks with same title/context, then deduplicate tracks globally
    merged_blocks = _merge_blocks_by_title(parsed.blocks)
    deduped_blocks = _dedupe_blocks_globally(merged_blocks)
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


def run_dev(url: str, force: bool, settings: Settings) -> bool:
    """
    Run dev mode (parse only, no Spotify).

    Returns:
        True if the URL was processed, False if skipped (already parsed).
    """
    if not force and is_already_parsed(url):
        logger.info("Skipping %s – already parsed (use --force to re-parse)", url)
        print(f"Skipped (already parsed): {url}")
        return False

    parsed, parsed_path = _process_url(url, force, settings)
    logger.info("Parsed %d blocks from %s. Saved to %s", len(parsed.blocks), url, parsed_path)
    typer_msg = f"Parsed {len(parsed.blocks)} blocks. Artifact: {parsed_path}"
    print(typer_msg)
    return True


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
) -> bool:
    """
    Import a URL to Spotify.

    Returns:
        True if the URL was processed, False if skipped (already imported).
    """
    if not force and is_already_imported(url):
        logger.info("Skipping %s – already imported (use --force to re-import)", url)
        print(f"Skipped (already imported): {url}")
        return False

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
    return True


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


def _extract_links_from_index(url: str, force: bool, settings: Settings) -> List[ExtractedLink]:
    """Fetch index page and extract playlist-related links using LLM."""
    slug = slugify_url(url)
    html, raw_path = _load_or_fetch_html(url, slug, force)
    # Use link-preserving extraction for crawling
    links_content = _extract_links_from_html(html)

    links = extract_links_with_llm(
        url=url,
        content=links_content,
        model=settings.openai_model,
        api_key=settings.openai_api_key,
    )

    logger.info("Extracted %d links from index %s", len(links), url)
    return links


def run_crawl(
    index_url: str,
    dev_mode: bool,
    force: bool,
    master_playlist: bool,
    settings: Settings,
    write_playlists: bool = True,
    max_links: Optional[int] = None,
) -> CrawlResult:
    """
    Crawl an index page and process all discovered playlist URLs.

    Args:
        index_url: URL of the index page.
        dev_mode: If True, run in dev mode (no Spotify writes).
        force: Re-fetch pages even if cached.
        master_playlist: Whether to create master playlists.
        settings: Application settings.
        write_playlists: Whether to write playlists (only relevant if not dev_mode).
        max_links: Maximum number of links to process (None for unlimited).

    Returns:
        CrawlResult with summary of all processed URLs.
    """
    # Extract links from index page
    links = _extract_links_from_index(index_url, force, settings)

    if max_links is not None:
        links = links[:max_links]

    processed: List[Dict] = []

    for i, link in enumerate(links, 1):
        result: Dict = {"url": link.url, "description": link.description}
        logger.info("Processing link %d/%d: %s", i, len(links), link.url)
        try:
            if dev_mode:
                was_processed = run_dev(url=link.url, force=force, settings=settings)
                result["status"] = "success" if was_processed else "skipped"
                result["mode"] = "dev"
            else:
                was_processed = run_import(
                    url=link.url,
                    force=force,
                    master_playlist=master_playlist,
                    settings=settings,
                    write_playlists=write_playlists,
                )
                result["status"] = "success" if was_processed else "skipped"
                result["mode"] = "import"

            # Add artifact path
            slug = slugify_url(link.url)
            if dev_mode:
                result["artifact"] = f"data/parsed/{slug}.json"
            else:
                result["artifact"] = f"data/spotify/{slug}.json"

        except Exception as exc:
            logger.error("Failed to process %s: %s", link.url, exc)
            result["status"] = "failed"
            result["error"] = str(exc)

        processed.append(result)

    # Save crawl summary
    crawl_result = CrawlResult(
        index_url=index_url,
        discovered_links=links,
        processed=processed,
        crawled_at=datetime.now(timezone.utc),
    )

    index_slug = slugify_url(index_url)
    crawl_path = Path("data/crawl") / f"{index_slug}.json"
    write_json(
        crawl_path,
        {
            "index_url": str(crawl_result.index_url),
            "discovered_links": [
                {"url": link.url, "description": link.description}
                for link in crawl_result.discovered_links
            ],
            "processed": crawl_result.processed,
            "crawled_at": crawl_result.crawled_at.isoformat(),
        },
    )

    return crawl_result

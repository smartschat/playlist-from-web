from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.models import ParsedPage, Track, TrackBlock
from app.pipeline import _create_playlists, _map_tracks_to_spotify
from app.spotify_client import SpotifyClient

from ..services.data_service import data_service

router = APIRouter(prefix="/api/spotify", tags=["spotify"])


class SearchRequest(BaseModel):
    artist: str
    title: str


class SearchResult(BaseModel):
    uri: str
    name: str
    artists: list[str]
    album: str
    url: str


class AssignRequest(BaseModel):
    uri: str
    url: str | None = None


class PlaylistUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


def _get_spotify_client() -> SpotifyClient:
    """Create a SpotifyClient from settings."""
    settings = get_settings()
    settings.require_spotify_auth()
    return SpotifyClient(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
        refresh_token=settings.spotify_refresh_token,
        user_id=settings.spotify_user_id,
    )


@router.post("/search", response_model=list[SearchResult])
def search_spotify(req: SearchRequest) -> list[dict[str, Any]]:
    """Search Spotify for a track."""
    with _get_spotify_client() as client:
        # Use the internal _search method to get multiple results
        queries = [
            f"artist:{req.artist} track:{req.title}",
            f"{req.artist} {req.title}",
        ]
        results: list[dict[str, Any]] = []
        seen_uris: set[str] = set()

        for query in queries:
            items = client._search(query, limit=10)
            for item in items:
                uri = item.get("uri", "")
                if uri and uri not in seen_uris:
                    seen_uris.add(uri)
                    results.append(
                        {
                            "uri": uri,
                            "name": item.get("name", ""),
                            "artists": [a.get("name", "") for a in item.get("artists", [])],
                            "album": item.get("album", {}).get("name", ""),
                            "url": item.get("external_urls", {}).get("spotify", ""),
                        }
                    )
            if len(results) >= 10:
                break

        return results[:10]


@router.get("/{slug}")
def get_spotify_artifact(slug: str) -> dict[str, Any]:
    """Get Spotify artifact for a playlist."""
    artifact = data_service.get_spotify_artifact(slug)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Spotify artifact not found: {slug}")
    return artifact


@router.post("/{slug}/remap")
def remap_playlist(slug: str) -> dict[str, Any]:
    """Re-run Spotify mapping for all tracks in a playlist."""
    parsed = data_service.get_parsed_playlist(slug)
    if parsed is None:
        raise HTTPException(status_code=404, detail=f"Playlist not found: {slug}")

    # Convert dict to ParsedPage model to reuse pipeline function
    parsed_page = _dict_to_parsed_page(parsed)

    with _get_spotify_client() as client:
        # Use keep_unmatched=True to preserve all tracks for remapping
        mapped_blocks, misses = _map_tracks_to_spotify(client, parsed_page, keep_unmatched=True)

    # Get existing artifact to preserve playlists
    existing = data_service.get_spotify_artifact(slug)
    artifact = {
        "source_url": str(parsed_page.source_url),
        "parsed_artifact": f"data/parsed/{slug}.json",
        "blocks": mapped_blocks,
        "playlists": existing.get("playlists", []) if existing else [],
        "master_playlist": existing.get("master_playlist") if existing else None,
        "misses": misses,
        "failed_tracks": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    data_service.save_spotify_artifact(slug, artifact)
    return artifact


class CreatePlaylistsRequest(BaseModel):
    master_playlist: bool = False


def _dict_to_parsed_page(data: dict[str, Any]) -> ParsedPage:
    """Convert a parsed playlist dict to a ParsedPage model."""
    fetched_at_str = data.get("fetched_at", "")
    if fetched_at_str:
        fetched_at = datetime.fromisoformat(fetched_at_str)
    else:
        fetched_at = datetime.now(timezone.utc)

    return ParsedPage(
        source_url=data.get("source_url", ""),
        source_name=data.get("source_name"),
        fetched_at=fetched_at,
        blocks=[
            TrackBlock(
                title=b.get("title", ""),
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


@router.post("/{slug}/create")
def create_spotify_playlists(
    slug: str, req: CreatePlaylistsRequest | None = None
) -> dict[str, Any]:
    """Create Spotify playlists from a parsed playlist.

    This endpoint maps all tracks to Spotify and creates the actual playlists.
    Use this after editing a parsed playlist to push it to Spotify.
    """
    parsed = data_service.get_parsed_playlist(slug)
    if parsed is None:
        raise HTTPException(status_code=404, detail=f"Playlist not found: {slug}")

    # Check if Spotify artifact already exists with playlists
    existing = data_service.get_spotify_artifact(slug)
    if existing and existing.get("playlists"):
        raise HTTPException(
            status_code=400,
            detail="Spotify playlists already exist. Use sync to update or delete them first.",
        )

    master_playlist = req.master_playlist if req else get_settings().master_playlist_enabled

    # Convert dict to ParsedPage model to reuse pipeline functions
    parsed_page = _dict_to_parsed_page(parsed)

    with _get_spotify_client() as client:
        # Reuse pipeline functions for mapping and playlist creation
        mapped_blocks, misses = _map_tracks_to_spotify(client, parsed_page)
        creation = _create_playlists(client, parsed_page, mapped_blocks, master_playlist)

    # Build and save artifact
    artifact = {
        "source_url": str(parsed_page.source_url),
        "parsed_artifact": f"data/parsed/{slug}.json",
        "blocks": mapped_blocks,
        "playlists": creation["playlists"],
        "master_playlist": creation.get("master_playlist"),
        "misses": misses,
        "failed_tracks": creation.get("failed_tracks", []),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    data_service.save_spotify_artifact(slug, artifact)
    return artifact


@router.post("/{slug}/tracks/{block_idx}/{track_idx}/assign")
def assign_track_uri(
    slug: str, block_idx: int, track_idx: int, req: AssignRequest
) -> dict[str, Any]:
    """Assign a Spotify URI to a specific track."""
    artifact = data_service.get_spotify_artifact(slug)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Spotify artifact not found: {slug}")

    blocks = artifact.get("blocks", [])
    if block_idx < 0 or block_idx >= len(blocks):
        raise HTTPException(status_code=400, detail=f"Invalid block index: {block_idx}")

    tracks = blocks[block_idx].get("tracks", [])
    if track_idx < 0 or track_idx >= len(tracks):
        raise HTTPException(status_code=400, detail=f"Invalid track index: {track_idx}")

    # Update the track with the assigned URI
    track = tracks[track_idx]
    track["spotify_uri"] = req.uri
    if req.url:
        track["spotify_url"] = req.url

    # Remove from misses if present
    artist = track.get("artist", "")
    title = track.get("title", "")
    block_title = blocks[block_idx].get("title", "")
    artifact["misses"] = [
        m
        for m in artifact.get("misses", [])
        if not (m["artist"] == artist and m["title"] == title and m["block"] == block_title)
    ]

    data_service.save_spotify_artifact(slug, artifact)
    return artifact


@router.put("/playlists/{playlist_id}")
def update_spotify_playlist(
    playlist_id: str, req: PlaylistUpdateRequest, slug: str | None = None
) -> dict[str, str]:
    """Update a Spotify playlist's name and/or description."""
    if req.name is None and req.description is None:
        raise HTTPException(status_code=400, detail="Must provide name or description to update")

    with _get_spotify_client() as client:
        try:
            client.update_playlist_details(
                playlist_id=playlist_id, name=req.name, description=req.description
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update playlist: {e}")

    # Persist changes to local artifact
    if slug:
        artifact = data_service.get_spotify_artifact(slug)
        if artifact:
            # Update in playlists list
            for p in artifact.get("playlists", []):
                if p.get("id") == playlist_id:
                    if req.name is not None:
                        p["name"] = req.name
                    if req.description is not None:
                        p["description"] = req.description
                    break
            # Check master playlist
            master = artifact.get("master_playlist")
            if master and master.get("id") == playlist_id:
                if req.name is not None:
                    master["name"] = req.name
                if req.description is not None:
                    master["description"] = req.description
            data_service.save_spotify_artifact(slug, artifact)

    return {"status": "updated", "playlist_id": playlist_id}


@router.post("/playlists/{playlist_id}/sync")
def sync_spotify_playlist(playlist_id: str, slug: str) -> dict[str, Any]:
    """Sync local tracks to a Spotify playlist."""
    artifact = data_service.get_spotify_artifact(slug)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"Spotify artifact not found: {slug}")

    # Find the playlist in the artifact and determine if it's the master
    playlist_info = None
    is_master = False
    playlist_index = -1

    master = artifact.get("master_playlist")
    if master and master.get("id") == playlist_id:
        playlist_info = master
        is_master = True
    else:
        for idx, p in enumerate(artifact.get("playlists", [])):
            if p.get("id") == playlist_id:
                playlist_info = p
                playlist_index = idx
                break

    if playlist_info is None:
        raise HTTPException(
            status_code=404, detail=f"Playlist not found in artifact: {playlist_id}"
        )

    # Collect URIs based on playlist type
    uris: list[str] = []
    blocks = artifact.get("blocks", [])

    if is_master:
        # Master playlist: sync all tracks from all blocks
        for block in blocks:
            for track in block.get("tracks", []):
                uri = track.get("spotify_uri")
                if uri:
                    uris.append(uri)
    else:
        # Block-specific playlist: find the matching block
        # Try to match by block title in playlist name
        playlist_name = playlist_info.get("name", "")
        matching_block = None

        for block in blocks:
            block_title = block.get("title", "")
            if block_title and block_title in playlist_name:
                matching_block = block
                break

        # If no match by name, use playlist index if valid
        if matching_block is None and 0 <= playlist_index < len(blocks):
            matching_block = blocks[playlist_index]

        if matching_block:
            for track in matching_block.get("tracks", []):
                uri = track.get("spotify_uri")
                if uri:
                    uris.append(uri)
        else:
            # Fallback: use the playlist's stored tracks
            uris = list(playlist_info.get("tracks", []))

    with _get_spotify_client() as client:
        try:
            client.replace_playlist_tracks(playlist_id, uris)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to sync playlist: {e}")

    # Update track count in artifact
    playlist_info["tracks"] = uris
    playlist_info["tracks_added"] = len(uris)
    data_service.save_spotify_artifact(slug, artifact)

    return {"status": "synced", "playlist_id": playlist_id, "tracks_synced": len(uris)}


@router.delete("/playlists/{playlist_id}")
def delete_spotify_playlist(playlist_id: str, slug: str | None = None) -> dict[str, str]:
    """Unfollow (delete) a Spotify playlist."""
    with _get_spotify_client() as client:
        try:
            client.unfollow_playlist(playlist_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete playlist: {e}")

    # If slug provided, remove playlist from artifact
    if slug:
        artifact = data_service.get_spotify_artifact(slug)
        if artifact:
            # Remove from playlists list
            artifact["playlists"] = [
                p for p in artifact.get("playlists", []) if p.get("id") != playlist_id
            ]
            # Check if it's the master playlist
            master = artifact.get("master_playlist")
            if master and master.get("id") == playlist_id:
                artifact["master_playlist"] = None
            data_service.save_spotify_artifact(slug, artifact)

    return {"status": "deleted", "playlist_id": playlist_id}

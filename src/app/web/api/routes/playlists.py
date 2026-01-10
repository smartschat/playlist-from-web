from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.data_service import data_service

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


class PlaylistSummary(BaseModel):
    slug: str
    source_url: str | None
    source_name: str | None
    fetched_at: str | None
    block_count: int
    track_count: int
    has_spotify: bool
    miss_count: int | None = None
    playlist_count: int | None = None
    llm_cost_usd: float | None = None


class PlaylistUpdate(BaseModel):
    """Request body for updating a playlist."""

    blocks: list[dict[str, Any]]
    source_name: str | None = None


@router.get("", response_model=list[PlaylistSummary])
def list_playlists() -> list[dict[str, Any]]:
    """List all parsed playlists with metadata."""
    return data_service.list_parsed_playlists()


@router.get("/{slug}")
def get_playlist(slug: str) -> dict[str, Any]:
    """Get a parsed playlist by slug."""
    playlist = data_service.get_parsed_playlist(slug)
    if playlist is None:
        raise HTTPException(status_code=404, detail=f"Playlist not found: {slug}")
    return playlist


@router.put("/{slug}")
def update_playlist(slug: str, update: PlaylistUpdate) -> dict[str, Any]:
    """Update a parsed playlist."""
    playlist = data_service.get_parsed_playlist(slug)
    if playlist is None:
        raise HTTPException(status_code=404, detail=f"Playlist not found: {slug}")

    # Update fields
    playlist["blocks"] = update.blocks
    if update.source_name is not None:
        playlist["source_name"] = update.source_name

    data_service.save_parsed_playlist(slug, playlist)
    return playlist


@router.delete("/{slug}")
def delete_playlist(slug: str, also_spotify: bool = False) -> dict[str, str]:
    """Delete a parsed playlist and optionally its Spotify artifact."""
    deleted = data_service.delete_parsed_playlist(slug, also_spotify=also_spotify)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Playlist not found: {slug}")
    return {"status": "deleted", "slug": slug}

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.pipeline import run_dev, run_import
from app.utils import slugify_url

from ..services.data_service import data_service

router = APIRouter(prefix="/api/import", tags=["import"])


class ImportRequest(BaseModel):
    """Request body for importing a URL."""

    url: str
    force: bool = False


class ImportPreviewResponse(BaseModel):
    """Response for preview (dev mode) import."""

    slug: str
    source_url: str
    source_name: str | None
    block_count: int
    track_count: int
    blocks: list[dict[str, Any]]
    llm_cost_usd: float | None = None


class ImportExecuteResponse(BaseModel):
    """Response for full import."""

    slug: str
    source_url: str
    playlist_count: int
    miss_count: int
    has_master: bool
    llm_cost_usd: float | None = None


@router.post("/preview", response_model=ImportPreviewResponse)
def preview_import(req: ImportRequest) -> dict[str, Any]:
    """
    Preview import by running dev mode (parse only, no Spotify).

    Returns the parsed data without creating Spotify playlists.
    """
    settings = get_settings()
    slug = slugify_url(req.url)

    try:
        run_dev(url=req.url, force=req.force, settings=settings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse URL: {e}")

    # Load the parsed result
    parsed = data_service.get_parsed_playlist(slug)
    if parsed is None:
        raise HTTPException(status_code=500, detail="Parsing succeeded but artifact not found")

    blocks = parsed.get("blocks", [])
    track_count = sum(len(b.get("tracks", [])) for b in blocks)
    llm_usage = parsed.get("llm_usage")
    llm_cost_usd = llm_usage.get("cost_usd") if llm_usage else None

    return {
        "slug": slug,
        "source_url": req.url,
        "source_name": parsed.get("source_name"),
        "block_count": len(blocks),
        "track_count": track_count,
        "blocks": blocks,
        "llm_cost_usd": llm_cost_usd,
    }


@router.post("/execute", response_model=ImportExecuteResponse)
def execute_import(req: ImportRequest) -> dict[str, Any]:
    """
    Execute full import: parse, map to Spotify, and create playlists.
    """
    settings = get_settings()
    slug = slugify_url(req.url)

    try:
        run_import(
            url=req.url,
            force=req.force,
            master_playlist=settings.master_playlist_enabled,
            settings=settings,
            write_playlists=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import URL: {e}")

    # Load the spotify result
    artifact = data_service.get_spotify_artifact(slug)
    if artifact is None:
        raise HTTPException(status_code=500, detail="Import succeeded but artifact not found")

    llm_usage = artifact.get("llm_usage")
    llm_cost_usd = llm_usage.get("cost_usd") if llm_usage else None

    return {
        "slug": slug,
        "source_url": req.url,
        "playlist_count": len(artifact.get("playlists", [])),
        "miss_count": len(artifact.get("misses", [])),
        "has_master": artifact.get("master_playlist") is not None,
        "llm_cost_usd": llm_cost_usd,
    }

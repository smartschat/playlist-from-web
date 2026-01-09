from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.pipeline import run_dev, run_import
from app.utils import slugify_url

from ..services.data_service import data_service

router = APIRouter(prefix="/api/crawls", tags=["crawls"])


class CrawlSummary(BaseModel):
    """Summary of a crawl result for list view."""

    slug: str
    index_url: str | None
    crawled_at: str | None
    link_count: int
    success_count: int
    skipped_count: int
    failed_count: int


class ReprocessRequest(BaseModel):
    """Request body for reprocessing a URL."""

    dev_mode: bool = False
    force: bool = False


@router.get("", response_model=list[CrawlSummary])
def list_crawls() -> list[dict[str, Any]]:
    """List all crawl results with summary metadata."""
    return data_service.list_crawls()


@router.get("/{slug}")
def get_crawl(slug: str) -> dict[str, Any]:
    """Get a crawl result by slug."""
    crawl = data_service.get_crawl(slug)
    if crawl is None:
        raise HTTPException(status_code=404, detail=f"Crawl not found: {slug}")
    return crawl


@router.post("/{slug}/reprocess/{idx}")
def reprocess_url(slug: str, idx: int, req: ReprocessRequest) -> dict[str, Any]:
    """
    Reprocess a single URL from a crawl result.

    Args:
        slug: Crawl result slug
        idx: Index of the processed URL in the crawl result
        req: Reprocess options (dev_mode, force)

    Returns:
        Updated status for the reprocessed URL
    """
    crawl = data_service.get_crawl(slug)
    if crawl is None:
        raise HTTPException(status_code=404, detail=f"Crawl not found: {slug}")

    processed = crawl.get("processed", [])
    if idx < 0 or idx >= len(processed):
        raise HTTPException(status_code=400, detail=f"Invalid index: {idx}")

    entry = processed[idx]
    url = entry.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="No URL found at index")

    settings = get_settings()
    result: dict[str, Any] = {"url": url}

    try:
        if req.dev_mode:
            was_processed = run_dev(url=url, force=req.force, settings=settings)
            result["status"] = "success" if was_processed else "skipped"
            result["mode"] = "dev"
        else:
            was_processed = run_import(
                url=url,
                force=req.force,
                master_playlist=settings.master_playlist_enabled,
                settings=settings,
                write_playlists=True,
            )
            result["status"] = "success" if was_processed else "skipped"
            result["mode"] = "import"

        # Add artifact path
        url_slug = slugify_url(url)
        if req.dev_mode:
            result["artifact"] = f"data/parsed/{url_slug}.json"
        else:
            result["artifact"] = f"data/spotify/{url_slug}.json"

    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)

    # Update the crawl result, clearing stale error on success
    updated_entry = {**entry, **result}
    if result["status"] != "failed":
        updated_entry.pop("error", None)
    processed[idx] = updated_entry
    crawl["processed"] = processed

    # Save updated crawl
    from pathlib import Path

    from app.utils import write_json

    crawl_path = Path("data/crawl") / f"{slug}.json"
    write_json(crawl_path, crawl)

    return result

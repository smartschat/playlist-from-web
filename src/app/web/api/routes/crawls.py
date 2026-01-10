import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.pipeline import run_dev, run_import
from app.utils import slugify_url, write_json

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
    llm_cost_usd: float | None = None


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

        # Add artifact path and read LLM cost
        url_slug = slugify_url(url)
        if req.dev_mode:
            artifact_path = Path(f"data/parsed/{url_slug}.json")
        else:
            artifact_path = Path(f"data/spotify/{url_slug}.json")
        result["artifact"] = str(artifact_path)

        # Read LLM cost from artifact
        if artifact_path.exists():
            try:
                artifact_data = json.loads(artifact_path.read_text(encoding="utf-8"))
                if "llm_usage" in artifact_data:
                    result["llm_cost_usd"] = artifact_data["llm_usage"].get("cost_usd")
            except Exception:
                pass  # Ignore errors reading cost

    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)

    # Update the crawl result, clearing stale error on success
    updated_entry = {**entry, **result}
    if result["status"] != "failed":
        updated_entry.pop("error", None)
    processed[idx] = updated_entry
    crawl["processed"] = processed

    # Recalculate total LLM usage from all entries
    _recalculate_crawl_llm_usage(crawl)

    # Save updated crawl
    crawl_path = Path("data/crawl") / f"{slug}.json"
    write_json(crawl_path, crawl)

    return result


def _recalculate_crawl_llm_usage(crawl: dict[str, Any]) -> None:
    """Recalculate total LLM usage from all processed entries and link extraction.

    Sums cost_usd directly from each source to handle mixed-model crawls correctly.
    """
    total_prompt = 0
    total_completion = 0
    total_cost = 0.0

    # Include link extraction cost if stored separately
    link_extraction = crawl.get("link_extraction_llm_usage")
    if link_extraction:
        total_prompt += link_extraction.get("prompt_tokens", 0)
        total_completion += link_extraction.get("completion_tokens", 0)
        total_cost += link_extraction.get("cost_usd", 0.0)

    # Sum costs from successfully processed entries only
    for entry in crawl.get("processed", []):
        if entry.get("status") != "success":
            continue
        artifact_path = entry.get("artifact")
        if artifact_path and Path(artifact_path).exists():
            try:
                artifact_data = json.loads(Path(artifact_path).read_text(encoding="utf-8"))
                if "llm_usage" in artifact_data:
                    usage = artifact_data["llm_usage"]
                    total_prompt += usage.get("prompt_tokens", 0)
                    total_completion += usage.get("completion_tokens", 0)
                    total_cost += usage.get("cost_usd", 0.0)
            except Exception:
                pass

    # Update crawl's total llm_usage
    if total_prompt > 0 or total_completion > 0 or total_cost > 0:
        crawl["llm_usage"] = {
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "cost_usd": total_cost,
        }

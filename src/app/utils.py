import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def slugify_url(url: str) -> str:
    """
    Produce a filesystem-friendly slug from a URL.
    """
    parsed = urlparse(url)
    base = f"{parsed.netloc}{parsed.path}"
    base = base if base else "page"
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower() or "page"
    if parsed.query:
        qhash = hashlib.sha1(parsed.query.encode("utf-8")).hexdigest()[:8]
        slug = f"{slug}-q{qhash}"
    return slug


def ensure_parent(path: Path) -> None:
    """Create parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    """Write JSON with a stable, readable format."""
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as f:
        return f.read()

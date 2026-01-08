import json
from pathlib import Path
from typing import Any, Optional

from app.utils import write_json

DATA_DIR = Path("data")


class DataService:
    """Service for reading/writing playlist data files."""

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir
        self.parsed_dir = data_dir / "parsed"
        self.spotify_dir = data_dir / "spotify"
        self.crawl_dir = data_dir / "crawl"

    def list_parsed_playlists(self) -> list[dict[str, Any]]:
        """List all parsed playlists with metadata."""
        if not self.parsed_dir.exists():
            return []

        playlists = []
        for path in sorted(
            self.parsed_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            slug = path.stem
            spotify_path = self.spotify_dir / f"{slug}.json"

            # Calculate counts
            blocks = data.get("blocks", [])
            track_count = sum(len(b.get("tracks", [])) for b in blocks)

            summary: dict[str, Any] = {
                "slug": slug,
                "source_url": data.get("source_url"),
                "source_name": data.get("source_name"),
                "fetched_at": data.get("fetched_at"),
                "block_count": len(blocks),
                "track_count": track_count,
                "has_spotify": spotify_path.exists(),
            }

            if spotify_path.exists():
                try:
                    spotify_data = json.loads(spotify_path.read_text(encoding="utf-8"))
                    summary["miss_count"] = len(spotify_data.get("misses", []))
                    summary["playlist_count"] = len(spotify_data.get("playlists", []))
                except (json.JSONDecodeError, OSError):
                    pass

            playlists.append(summary)

        return playlists

    def get_parsed_playlist(self, slug: str) -> Optional[dict[str, Any]]:
        """Load a parsed playlist by slug."""
        path = self.parsed_dir / f"{slug}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def save_parsed_playlist(self, slug: str, data: dict[str, Any]) -> None:
        """Save changes to a parsed playlist."""
        path = self.parsed_dir / f"{slug}.json"
        write_json(path, data)

    def delete_parsed_playlist(self, slug: str, also_spotify: bool = False) -> bool:
        """Delete a parsed playlist and optionally its Spotify artifact.

        Returns True if at least one file was deleted.
        """
        deleted = False
        parsed_path = self.parsed_dir / f"{slug}.json"
        if parsed_path.exists():
            parsed_path.unlink()
            deleted = True

        if also_spotify:
            spotify_path = self.spotify_dir / f"{slug}.json"
            if spotify_path.exists():
                spotify_path.unlink()
                deleted = True

        return deleted

    def get_spotify_artifact(self, slug: str) -> Optional[dict[str, Any]]:
        """Load Spotify artifact by slug."""
        path = self.spotify_dir / f"{slug}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def save_spotify_artifact(self, slug: str, data: dict[str, Any]) -> None:
        """Save changes to a Spotify artifact."""
        path = self.spotify_dir / f"{slug}.json"
        write_json(path, data)

    def list_crawls(self) -> list[dict[str, Any]]:
        """List all crawl results with metadata."""
        if not self.crawl_dir.exists():
            return []

        crawls = []
        for path in sorted(
            self.crawl_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            slug = path.stem
            processed = data.get("processed", [])

            crawls.append({
                "slug": slug,
                "index_url": data.get("index_url"),
                "crawled_at": data.get("crawled_at"),
                "link_count": len(data.get("discovered_links", [])),
                "success_count": sum(1 for p in processed if p.get("status") == "success"),
                "skipped_count": sum(1 for p in processed if p.get("status") == "skipped"),
                "failed_count": sum(1 for p in processed if p.get("status") == "failed"),
            })

        return crawls

    def get_crawl(self, slug: str) -> Optional[dict[str, Any]]:
        """Load a crawl result by slug."""
        path = self.crawl_dir / f"{slug}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None


# Singleton instance
data_service = DataService()

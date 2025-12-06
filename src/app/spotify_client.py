import base64
import logging
import re
import threading
import time
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    """Retry on rate limits (429) and server errors (5xx)."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return isinstance(exc, (httpx.ConnectError, httpx.ReadTimeout))


class SpotifyClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        user_id: str,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.user_id = user_id
        self._access_token: Optional[str] = None
        self._expires_at: float = 0.0
        self._token_lock = threading.Lock()
        self._http = httpx.Client(timeout=20)
        self._search_cache: Dict[str, Optional[Dict]] = {}

    def close(self) -> None:
        """Close the HTTP client."""
        self._http.close()

    def __enter__(self) -> "SpotifyClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _auth_header(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._get_access_token()}"}

    def _get_access_token(self) -> str:
        with self._token_lock:
            if self._access_token and time.time() < self._expires_at - 30:
                return self._access_token
            token_url = "https://accounts.spotify.com/api/token"
            basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            }
            headers = {"Authorization": f"Basic {basic}"}
            resp = self._http.post(token_url, data=data, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
            self._access_token = payload["access_token"]
            self._expires_at = time.time() + float(payload.get("expires_in", 3600))
            return self._access_token

    @staticmethod
    @lru_cache(maxsize=1024)
    def _normalize(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        normalized = "".join(c for c in normalized if not unicodedata.combining(c))
        normalized = normalized.lower().strip()
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def _best_match(
        self, items: List[Dict], target_artist: str, target_title: str
    ) -> Optional[Dict]:
        if not items:
            return None
        best = None
        best_score = 0.0
        for item in items:
            cand_title = self._normalize(item.get("name", ""))
            cand_artists = [self._normalize(a.get("name", "")) for a in item.get("artists", [])]
            if target_title == cand_title and target_artist in cand_artists:
                return item
            score_title = SequenceMatcher(None, target_title, cand_title).ratio()
            score_artist = max(
                (SequenceMatcher(None, target_artist, ca).ratio() for ca in cand_artists),
                default=0.0,
            )
            score = 0.6 * score_title + 0.4 * score_artist
            if score > best_score:
                best_score = score
                best = item
        if best_score < 0.5:
            return None
        return best

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    def _search(self, query: str, limit: int = 20) -> List[Dict]:
        resp = self._http.get(
            "https://api.spotify.com/v1/search",
            params={"q": query, "type": "track", "limit": limit},
            headers=self._auth_header(),
        )
        resp.raise_for_status()
        return resp.json().get("tracks", {}).get("items", [])

    def search_track(self, artist: str, title: str) -> Optional[Dict]:
        # Check cache first
        cache_key = f"{artist.lower().strip()}|{title.lower().strip()}"
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]

        # Pre-normalize targets once
        target_artist = self._normalize(artist)
        target_title = self._normalize(title)

        queries = [
            f"artist:{artist} track:{title}",
            f"{artist} {title}",
            title,
        ]
        for q in queries:
            items = self._search(q)
            best = self._best_match(items, target_artist=target_artist, target_title=target_title)
            if best:
                self._search_cache[cache_key] = best
                return best

        self._search_cache[cache_key] = None
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    def create_playlist(self, name: str, description: str, public: bool = False) -> Dict:
        resp = self._http.post(
            f"https://api.spotify.com/v1/users/{self.user_id}/playlists",
            headers=self._auth_header(),
            json={"name": name, "description": description, "public": public},
        )
        resp.raise_for_status()
        return resp.json()

    def add_tracks(self, playlist_id: str, uris: List[str]) -> Tuple[int, List[str]]:
        """Add tracks to playlist with partial failure recovery.

        Returns:
            Tuple of (tracks_added, failed_uris)
        """
        added = 0
        failed: List[str] = []
        # Spotify allows up to 100 URIs per request.
        for i in range(0, len(uris), 100):
            chunk = uris[i : i + 100]
            try:
                self._add_tracks_chunk(playlist_id, chunk)
                added += len(chunk)
            except Exception as exc:
                logger.warning("Failed to add chunk %d-%d: %s", i, i + len(chunk), exc)
                failed.extend(chunk)
        return added, failed

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    def _add_tracks_chunk(self, playlist_id: str, uris: List[str]) -> None:
        resp = self._http.post(
            f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
            headers=self._auth_header(),
            json={"uris": uris},
        )
        resp.raise_for_status()


def select_playlist_name(
    source_name: Optional[str], block_title: str, fetched_at: str, context: Optional[str]
) -> str:
    prefix = source_name or "Imported"
    label = (block_title or "").strip()
    if not label or label.lower() in {"playlist", "block"}:
        label = (context or "Playlist").strip()
    return f"{prefix} – {label} – {fetched_at}"


def select_description(source_url: str, context: Optional[str]) -> str:
    desc = f"Imported from {source_url}"
    if context:
        desc = f"{desc} | {context}"
    return desc

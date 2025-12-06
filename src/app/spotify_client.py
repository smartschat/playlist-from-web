import base64
import re
import time
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, List, Optional

import httpx


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

    def _auth_header(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._get_access_token()}"}

    def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._expires_at - 30:
            return self._access_token
        token_url = "https://accounts.spotify.com/api/token"
        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }
        headers = {"Authorization": f"Basic {basic}"}
        resp = httpx.post(token_url, data=data, headers=headers, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
        self._access_token = payload["access_token"]
        self._expires_at = time.time() + float(payload.get("expires_in", 3600))
        return self._access_token

    def _normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        normalized = "".join(c for c in normalized if not unicodedata.combining(c))
        normalized = normalized.lower().strip()
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def _best_match(self, items: List[Dict], artist: str, title: str) -> Optional[Dict]:
        if not items:
            return None
        target_artist = self._normalize(artist)
        target_title = self._normalize(title)
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

    def _search(self, query: str, limit: int = 20) -> List[Dict]:
        resp = httpx.get(
            "https://api.spotify.com/v1/search",
            params={"q": query, "type": "track", "limit": limit},
            headers=self._auth_header(),
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json().get("tracks", {}).get("items", [])

    def search_track(self, artist: str, title: str) -> Optional[Dict]:
        queries = [
            f"artist:{artist} track:{title}",
            f"{artist} {title}",
            title,
        ]
        for q in queries:
            items = self._search(q)
            best = self._best_match(items, artist=artist, title=title)
            if best:
                return best
        return None

    def create_playlist(self, name: str, description: str, public: bool = False) -> Dict:
        resp = httpx.post(
            f"https://api.spotify.com/v1/users/{self.user_id}/playlists",
            headers=self._auth_header(),
            json={"name": name, "description": description, "public": public},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    def add_tracks(self, playlist_id: str, uris: List[str]) -> None:
        # Spotify allows up to 100 URIs per request.
        for i in range(0, len(uris), 100):
            chunk = uris[i : i + 100]
            resp = httpx.post(
                f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
                headers=self._auth_header(),
                json={"uris": chunk},
                timeout=20,
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

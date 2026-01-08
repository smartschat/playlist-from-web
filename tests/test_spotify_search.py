from app.spotify_client import SpotifyClient


def make_client() -> SpotifyClient:
    return SpotifyClient(
        client_id="id",
        client_secret="secret",
        refresh_token="refresh",
        user_id="user",
    )


def test_search_track_exact_and_fuzzy(monkeypatch) -> None:
    client = make_client()
    items = [
        {
            "name": "Velho vagabundo",
            "artists": [{"name": "Rivière Noire"}],
            "uri": "spotify:track:exact",
            "external_urls": {"spotify": "https://spotify.com/track/exact"},
        },
        {
            "name": "Other song",
            "artists": [{"name": "Other"}],
            "uri": "spotify:track:other",
            "external_urls": {"spotify": "https://spotify.com/track/other"},
        },
    ]
    calls = []

    def fake_search(query: str, limit: int = 20):
        calls.append(query)
        return items

    monkeypatch.setattr(client, "_search", fake_search)

    result = client.search_track(artist="Riviere Noire", title="Velho   vagabundo")
    assert result is not None
    assert result["uri"] == "spotify:track:exact"
    assert calls[0].startswith("artist:")


def test_search_track_fallback_queries(monkeypatch) -> None:
    client = make_client()
    items = [
        {
            "name": "Skokiaan",
            "artists": [{"name": "Hugh Masekela"}],
            "uri": "spotify:track:skokiaan",
            "external_urls": {"spotify": "https://spotify.com/track/skokiaan"},
        }
    ]
    calls = []
    responses = [[], items]

    def fake_search(query: str, limit: int = 20):
        calls.append(query)
        return responses.pop(0)

    monkeypatch.setattr(client, "_search", fake_search)

    result = client.search_track(artist="Hugh Masekela", title="Skokiaan")
    assert result is not None
    assert result["uri"] == "spotify:track:skokiaan"
    # first query empty, second query succeeds
    assert len(calls) == 2


def test_search_track_returns_none_when_similarity_low(monkeypatch) -> None:
    client = make_client()

    def fake_search(query: str, limit: int = 20):
        return [
            {
                "name": "Unrelated Song",
                "artists": [{"name": "Random Artist"}],
                "uri": "spotify:track:bad",
                "external_urls": {"spotify": "https://spotify.com/track/bad"},
            }
        ]

    monkeypatch.setattr(client, "_search", fake_search)

    result = client.search_track(artist="Totally Different", title="Nothing Alike")
    assert result is None

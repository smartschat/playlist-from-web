"""Tests for the web API endpoints."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.web.api.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the API."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def sample_playlist_data() -> dict:
    """Sample parsed playlist data."""
    return {
        "source_url": "https://example.com/playlist",
        "source_name": "Test Playlist",
        "fetched_at": "2025-01-01T12:00:00+00:00",
        "blocks": [
            {
                "title": "Block 1",
                "context": "January 2025",
                "tracks": [
                    {"artist": "Artist 1", "title": "Song 1", "album": None},
                    {"artist": "Artist 2", "title": "Song 2", "album": "Album 2"},
                ],
            }
        ],
    }


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint returns ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_playlists_empty(client: TestClient, monkeypatch, tmp_path: Path) -> None:
    """Test listing playlists when none exist."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "parsed").mkdir(parents=True)

    response = client.get("/api/playlists")
    assert response.status_code == 200
    assert response.json() == []


def test_list_playlists(
    client: TestClient, monkeypatch, tmp_path: Path, sample_playlist_data: dict
) -> None:
    """Test listing playlists returns playlist summaries."""
    monkeypatch.chdir(tmp_path)
    parsed_dir = tmp_path / "data" / "parsed"
    parsed_dir.mkdir(parents=True)

    # Create a sample playlist file
    playlist_file = parsed_dir / "test-playlist.json"
    playlist_file.write_text(json.dumps(sample_playlist_data))

    response = client.get("/api/playlists")
    assert response.status_code == 200

    playlists = response.json()
    assert len(playlists) == 1
    assert playlists[0]["slug"] == "test-playlist"
    assert playlists[0]["source_name"] == "Test Playlist"
    assert playlists[0]["block_count"] == 1
    assert playlists[0]["track_count"] == 2
    assert playlists[0]["has_spotify"] is False


def test_list_playlists_includes_llm_cost(
    client: TestClient, monkeypatch, tmp_path: Path, sample_playlist_data: dict
) -> None:
    """Test that playlist list includes LLM cost when available."""
    monkeypatch.chdir(tmp_path)
    parsed_dir = tmp_path / "data" / "parsed"
    parsed_dir.mkdir(parents=True)

    # Add LLM usage to the sample data
    playlist_with_cost = {
        **sample_playlist_data,
        "llm_usage": {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "model": "gpt-4",
            "cost_usd": 0.0234,
        },
    }
    playlist_file = parsed_dir / "test-playlist.json"
    playlist_file.write_text(json.dumps(playlist_with_cost))

    response = client.get("/api/playlists")
    assert response.status_code == 200

    playlists = response.json()
    assert len(playlists) == 1
    assert playlists[0]["llm_cost_usd"] == 0.0234


def test_get_playlist(
    client: TestClient, monkeypatch, tmp_path: Path, sample_playlist_data: dict
) -> None:
    """Test getting a single playlist by slug."""
    monkeypatch.chdir(tmp_path)
    parsed_dir = tmp_path / "data" / "parsed"
    parsed_dir.mkdir(parents=True)

    playlist_file = parsed_dir / "test-playlist.json"
    playlist_file.write_text(json.dumps(sample_playlist_data))

    response = client.get("/api/playlists/test-playlist")
    assert response.status_code == 200

    playlist = response.json()
    assert playlist["source_name"] == "Test Playlist"
    assert len(playlist["blocks"]) == 1
    assert len(playlist["blocks"][0]["tracks"]) == 2


def test_get_playlist_includes_llm_usage(
    client: TestClient, monkeypatch, tmp_path: Path, sample_playlist_data: dict
) -> None:
    """Test that getting a playlist includes LLM usage details."""
    monkeypatch.chdir(tmp_path)
    parsed_dir = tmp_path / "data" / "parsed"
    parsed_dir.mkdir(parents=True)

    playlist_with_usage = {
        **sample_playlist_data,
        "llm_usage": {
            "prompt_tokens": 1500,
            "completion_tokens": 750,
            "model": "gpt-4",
            "cost_usd": 0.0345,
        },
    }
    playlist_file = parsed_dir / "test-playlist.json"
    playlist_file.write_text(json.dumps(playlist_with_usage))

    response = client.get("/api/playlists/test-playlist")
    assert response.status_code == 200

    playlist = response.json()
    assert "llm_usage" in playlist
    assert playlist["llm_usage"]["cost_usd"] == 0.0345
    assert playlist["llm_usage"]["model"] == "gpt-4"


def test_get_playlist_not_found(client: TestClient, monkeypatch, tmp_path: Path) -> None:
    """Test getting a non-existent playlist returns 404."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "parsed").mkdir(parents=True)

    response = client.get("/api/playlists/non-existent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_playlist(
    client: TestClient, monkeypatch, tmp_path: Path, sample_playlist_data: dict
) -> None:
    """Test updating a playlist."""
    monkeypatch.chdir(tmp_path)
    parsed_dir = tmp_path / "data" / "parsed"
    parsed_dir.mkdir(parents=True)

    playlist_file = parsed_dir / "test-playlist.json"
    playlist_file.write_text(json.dumps(sample_playlist_data))

    # Update with new blocks
    updated_blocks = [
        {
            "title": "Updated Block",
            "context": None,
            "tracks": [{"artist": "New Artist", "title": "New Song", "album": None}],
        }
    ]

    response = client.put(
        "/api/playlists/test-playlist",
        json={"blocks": updated_blocks, "source_name": "Updated Name"},
    )
    assert response.status_code == 200

    # Verify the update
    result = response.json()
    assert result["source_name"] == "Updated Name"
    assert len(result["blocks"]) == 1
    assert result["blocks"][0]["title"] == "Updated Block"

    # Verify file was updated
    saved_data = json.loads(playlist_file.read_text())
    assert saved_data["source_name"] == "Updated Name"


def test_update_playlist_not_found(client: TestClient, monkeypatch, tmp_path: Path) -> None:
    """Test updating a non-existent playlist returns 404."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "parsed").mkdir(parents=True)

    response = client.put(
        "/api/playlists/non-existent",
        json={"blocks": []},
    )
    assert response.status_code == 404


def test_delete_playlist(
    client: TestClient, monkeypatch, tmp_path: Path, sample_playlist_data: dict
) -> None:
    """Test deleting a playlist."""
    monkeypatch.chdir(tmp_path)
    parsed_dir = tmp_path / "data" / "parsed"
    parsed_dir.mkdir(parents=True)

    playlist_file = parsed_dir / "test-playlist.json"
    playlist_file.write_text(json.dumps(sample_playlist_data))

    response = client.delete("/api/playlists/test-playlist")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    # Verify file was deleted
    assert not playlist_file.exists()


def test_delete_playlist_not_found(client: TestClient, monkeypatch, tmp_path: Path) -> None:
    """Test deleting a non-existent playlist returns 404."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "parsed").mkdir(parents=True)

    response = client.delete("/api/playlists/non-existent")
    assert response.status_code == 404


def test_delete_playlist_with_spotify(
    client: TestClient, monkeypatch, tmp_path: Path, sample_playlist_data: dict
) -> None:
    """Test deleting a playlist also deletes Spotify artifact when requested."""
    monkeypatch.chdir(tmp_path)
    parsed_dir = tmp_path / "data" / "parsed"
    spotify_dir = tmp_path / "data" / "spotify"
    parsed_dir.mkdir(parents=True)
    spotify_dir.mkdir(parents=True)

    # Create both parsed and spotify files
    parsed_file = parsed_dir / "test-playlist.json"
    spotify_file = spotify_dir / "test-playlist.json"
    parsed_file.write_text(json.dumps(sample_playlist_data))
    spotify_file.write_text(json.dumps({"playlists": []}))

    response = client.delete("/api/playlists/test-playlist?also_spotify=true")
    assert response.status_code == 200

    # Both files should be deleted
    assert not parsed_file.exists()
    assert not spotify_file.exists()


# --- Spotify API tests ---


@pytest.fixture
def sample_spotify_artifact() -> dict:
    """Sample Spotify artifact data."""
    return {
        "source_url": "https://example.com/playlist",
        "parsed_artifact": "data/parsed/test-playlist.json",
        "blocks": [
            {
                "title": "Block 1",
                "context": "January 2025",
                "tracks": [
                    {
                        "artist": "Artist 1",
                        "title": "Song 1",
                        "album": None,
                        "spotify_uri": "spotify:track:123",
                        "spotify_url": "https://open.spotify.com/track/123",
                    },
                    {"artist": "Artist 2", "title": "Song 2", "album": "Album 2"},
                ],
            }
        ],
        "playlists": [
            {
                "id": "playlist123",
                "name": "Test Playlist - Block 1",
                "url": "https://open.spotify.com/playlist/123",
                "tracks": ["spotify:track:123"],
                "tracks_added": 1,
            }
        ],
        "master_playlist": None,
        "misses": [{"block": "Block 1", "artist": "Artist 2", "title": "Song 2"}],
        "failed_tracks": [],
        "generated_at": "2025-01-01T12:00:00+00:00",
    }


def test_get_spotify_artifact(
    client: TestClient, monkeypatch, tmp_path: Path, sample_spotify_artifact: dict
) -> None:
    """Test getting a Spotify artifact by slug."""
    monkeypatch.chdir(tmp_path)
    spotify_dir = tmp_path / "data" / "spotify"
    spotify_dir.mkdir(parents=True)

    spotify_file = spotify_dir / "test-playlist.json"
    spotify_file.write_text(json.dumps(sample_spotify_artifact))

    response = client.get("/api/spotify/test-playlist")
    assert response.status_code == 200

    artifact = response.json()
    assert artifact["source_url"] == "https://example.com/playlist"
    assert len(artifact["blocks"]) == 1
    assert len(artifact["playlists"]) == 1
    assert len(artifact["misses"]) == 1


def test_get_spotify_artifact_not_found(client: TestClient, monkeypatch, tmp_path: Path) -> None:
    """Test getting a non-existent Spotify artifact returns 404."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "spotify").mkdir(parents=True)

    response = client.get("/api/spotify/non-existent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_assign_track_uri(
    client: TestClient,
    monkeypatch,
    tmp_path: Path,
    sample_spotify_artifact: dict,
) -> None:
    """Test assigning a Spotify URI to a track."""
    monkeypatch.chdir(tmp_path)
    spotify_dir = tmp_path / "data" / "spotify"
    spotify_dir.mkdir(parents=True)

    spotify_file = spotify_dir / "test-playlist.json"
    spotify_file.write_text(json.dumps(sample_spotify_artifact))

    # Assign URI to the second track (index 1) in block 0
    response = client.post(
        "/api/spotify/test-playlist/tracks/0/1/assign",
        json={"uri": "spotify:track:456", "url": "https://open.spotify.com/track/456"},
    )
    assert response.status_code == 200

    result = response.json()
    # Track should have the new URI
    assert result["blocks"][0]["tracks"][1]["spotify_uri"] == "spotify:track:456"
    # Miss should be removed
    assert len(result["misses"]) == 0


def test_assign_track_uri_invalid_index(
    client: TestClient,
    monkeypatch,
    tmp_path: Path,
    sample_spotify_artifact: dict,
) -> None:
    """Test assigning URI with invalid indices returns error."""
    monkeypatch.chdir(tmp_path)
    spotify_dir = tmp_path / "data" / "spotify"
    spotify_dir.mkdir(parents=True)

    spotify_file = spotify_dir / "test-playlist.json"
    spotify_file.write_text(json.dumps(sample_spotify_artifact))

    # Invalid block index
    response = client.post(
        "/api/spotify/test-playlist/tracks/99/0/assign",
        json={"uri": "spotify:track:456"},
    )
    assert response.status_code == 400
    assert "invalid block index" in response.json()["detail"].lower()

    # Invalid track index
    response = client.post(
        "/api/spotify/test-playlist/tracks/0/99/assign",
        json={"uri": "spotify:track:456"},
    )
    assert response.status_code == 400
    assert "invalid track index" in response.json()["detail"].lower()


def test_search_spotify(client: TestClient, monkeypatch) -> None:
    """Test searching Spotify (mocked)."""
    from unittest.mock import MagicMock

    # Mock the SpotifyClient
    mock_client = MagicMock()
    mock_client._search.return_value = [
        {
            "uri": "spotify:track:abc",
            "name": "Test Song",
            "artists": [{"name": "Test Artist"}],
            "album": {"name": "Test Album"},
            "external_urls": {"spotify": "https://open.spotify.com/track/abc"},
        }
    ]
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    def mock_get_client():
        return mock_client

    monkeypatch.setattr("app.web.api.routes.spotify._get_spotify_client", mock_get_client)

    response = client.post(
        "/api/spotify/search",
        json={"artist": "Test Artist", "title": "Test Song"},
    )
    assert response.status_code == 200

    results = response.json()
    assert len(results) >= 1
    assert results[0]["uri"] == "spotify:track:abc"
    assert results[0]["name"] == "Test Song"
    assert "Test Artist" in results[0]["artists"]


def test_remap_playlist(
    client: TestClient,
    monkeypatch,
    tmp_path: Path,
    sample_playlist_data: dict,
    sample_spotify_artifact: dict,
) -> None:
    """Test remapping a playlist (mocked SpotifyClient)."""
    from unittest.mock import MagicMock

    monkeypatch.chdir(tmp_path)
    parsed_dir = tmp_path / "data" / "parsed"
    spotify_dir = tmp_path / "data" / "spotify"
    parsed_dir.mkdir(parents=True)
    spotify_dir.mkdir(parents=True)

    # Create parsed and spotify files
    parsed_file = parsed_dir / "test-playlist.json"
    parsed_file.write_text(json.dumps(sample_playlist_data))
    spotify_file = spotify_dir / "test-playlist.json"
    spotify_file.write_text(json.dumps(sample_spotify_artifact))

    # Mock the SpotifyClient
    mock_client = MagicMock()
    mock_client.search_track.side_effect = [
        # First track matches
        {
            "uri": "spotify:track:new1",
            "external_urls": {"spotify": "https://open.spotify.com/track/new1"},
        },
        # Second track doesn't match
        None,
    ]
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    def mock_get_client():
        return mock_client

    monkeypatch.setattr("app.web.api.routes.spotify._get_spotify_client", mock_get_client)

    response = client.post("/api/spotify/test-playlist/remap")
    assert response.status_code == 200

    result = response.json()
    # First track should have URI
    assert result["blocks"][0]["tracks"][0]["spotify_uri"] == "spotify:track:new1"
    # Second track should be in misses
    assert len(result["misses"]) == 1
    assert result["misses"][0]["artist"] == "Artist 2"
    # Remap keeps unmatched tracks in blocks (without URI) - key behavior
    assert len(result["blocks"][0]["tracks"]) == 2
    assert result["blocks"][0]["tracks"][1]["artist"] == "Artist 2"
    assert "spotify_uri" not in result["blocks"][0]["tracks"][1]


def test_create_spotify_playlists(
    client: TestClient,
    monkeypatch,
    tmp_path: Path,
    sample_playlist_data: dict,
) -> None:
    """Test creating Spotify playlists from a parsed playlist."""
    from unittest.mock import MagicMock

    monkeypatch.chdir(tmp_path)
    parsed_dir = tmp_path / "data" / "parsed"
    spotify_dir = tmp_path / "data" / "spotify"
    parsed_dir.mkdir(parents=True)
    spotify_dir.mkdir(parents=True)

    # Create only parsed file (no spotify artifact yet)
    parsed_file = parsed_dir / "test-playlist.json"
    parsed_file.write_text(json.dumps(sample_playlist_data))

    # Mock the SpotifyClient
    mock_client = MagicMock()
    mock_client.search_track.side_effect = [
        # First track matches
        {
            "uri": "spotify:track:123",
            "external_urls": {"spotify": "https://open.spotify.com/track/123"},
        },
        # Second track doesn't match
        None,
    ]
    mock_client.create_playlist.return_value = {
        "id": "new_playlist_id",
        "name": "Test Playlist - Block 1 - 2025-01-01",
        "external_urls": {"spotify": "https://open.spotify.com/playlist/new_playlist_id"},
    }
    mock_client.add_tracks.return_value = (1, [])  # 1 added, 0 failed
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    def mock_get_client():
        return mock_client

    monkeypatch.setattr("app.web.api.routes.spotify._get_spotify_client", mock_get_client)

    response = client.post("/api/spotify/test-playlist/create")
    assert response.status_code == 200

    result = response.json()
    # Should have created one playlist
    assert len(result["playlists"]) == 1
    assert result["playlists"][0]["id"] == "new_playlist_id"
    # Should have one miss (second track)
    assert len(result["misses"]) == 1
    assert result["misses"][0]["artist"] == "Artist 2"
    # First track should have spotify_uri
    assert result["blocks"][0]["tracks"][0]["spotify_uri"] == "spotify:track:123"

    # Verify Spotify artifact was saved
    spotify_file = spotify_dir / "test-playlist.json"
    assert spotify_file.exists()


def test_create_spotify_playlists_not_found(
    client: TestClient, monkeypatch, tmp_path: Path
) -> None:
    """Test creating playlists for non-existent parsed playlist returns 404."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "parsed").mkdir(parents=True)
    (tmp_path / "data" / "spotify").mkdir(parents=True)

    response = client.post("/api/spotify/non-existent/create")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_spotify_playlists_already_exists(
    client: TestClient,
    monkeypatch,
    tmp_path: Path,
    sample_playlist_data: dict,
    sample_spotify_artifact: dict,
) -> None:
    """Test creating playlists when they already exist returns 400."""
    monkeypatch.chdir(tmp_path)
    parsed_dir = tmp_path / "data" / "parsed"
    spotify_dir = tmp_path / "data" / "spotify"
    parsed_dir.mkdir(parents=True)
    spotify_dir.mkdir(parents=True)

    # Create both parsed and spotify files (playlists already exist)
    parsed_file = parsed_dir / "test-playlist.json"
    parsed_file.write_text(json.dumps(sample_playlist_data))
    spotify_file = spotify_dir / "test-playlist.json"
    spotify_file.write_text(json.dumps(sample_spotify_artifact))

    response = client.post("/api/spotify/test-playlist/create")
    assert response.status_code == 400
    assert "already exist" in response.json()["detail"].lower()


def test_create_spotify_playlists_with_master(
    client: TestClient,
    monkeypatch,
    tmp_path: Path,
    sample_playlist_data: dict,
) -> None:
    """Test creating Spotify playlists with master playlist option."""
    from unittest.mock import MagicMock

    monkeypatch.chdir(tmp_path)
    parsed_dir = tmp_path / "data" / "parsed"
    spotify_dir = tmp_path / "data" / "spotify"
    parsed_dir.mkdir(parents=True)
    spotify_dir.mkdir(parents=True)

    parsed_file = parsed_dir / "test-playlist.json"
    parsed_file.write_text(json.dumps(sample_playlist_data))

    mock_client = MagicMock()
    mock_client.search_track.return_value = {
        "uri": "spotify:track:123",
        "external_urls": {"spotify": "https://open.spotify.com/track/123"},
    }
    # Two create_playlist calls: one for block, one for master
    mock_client.create_playlist.side_effect = [
        {
            "id": "block_playlist_id",
            "name": "Test - Block 1",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/block"},
        },
        {
            "id": "master_playlist_id",
            "name": "Test - All",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/master"},
        },
    ]
    mock_client.add_tracks.return_value = (2, [])
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    def mock_get_client():
        return mock_client

    monkeypatch.setattr("app.web.api.routes.spotify._get_spotify_client", mock_get_client)

    response = client.post(
        "/api/spotify/test-playlist/create",
        json={"master_playlist": True},
    )
    assert response.status_code == 200

    result = response.json()
    assert len(result["playlists"]) == 1
    assert result["master_playlist"] is not None
    assert result["master_playlist"]["id"] == "master_playlist_id"


def test_update_spotify_playlist_name(client: TestClient, monkeypatch) -> None:
    """Test updating a Spotify playlist name (mocked, no artifact)."""
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    def mock_get_client():
        return mock_client

    monkeypatch.setattr("app.web.api.routes.spotify._get_spotify_client", mock_get_client)

    response = client.put(
        "/api/spotify/playlists/playlist123",
        json={"name": "New Playlist Name"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "updated"

    # Verify client method was called
    mock_client.update_playlist_details.assert_called_once_with(
        playlist_id="playlist123", name="New Playlist Name", description=None
    )


def test_update_spotify_playlist_name_persists(
    client: TestClient, monkeypatch, tmp_path: Path, sample_spotify_artifact: dict
) -> None:
    """Test updating a Spotify playlist name persists to local artifact."""
    from unittest.mock import MagicMock

    monkeypatch.chdir(tmp_path)
    spotify_dir = tmp_path / "data" / "spotify"
    spotify_dir.mkdir(parents=True)

    spotify_file = spotify_dir / "test-playlist.json"
    spotify_file.write_text(json.dumps(sample_spotify_artifact))

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    def mock_get_client():
        return mock_client

    monkeypatch.setattr("app.web.api.routes.spotify._get_spotify_client", mock_get_client)

    # Update with slug to persist locally
    response = client.put(
        "/api/spotify/playlists/playlist123?slug=test-playlist",
        json={"name": "Renamed Playlist"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "updated"

    # Verify the artifact was updated
    updated_artifact = json.loads(spotify_file.read_text())
    assert updated_artifact["playlists"][0]["name"] == "Renamed Playlist"


def test_delete_spotify_playlist(
    client: TestClient, monkeypatch, tmp_path: Path, sample_spotify_artifact: dict
) -> None:
    """Test deleting a Spotify playlist (mocked)."""
    from unittest.mock import MagicMock

    monkeypatch.chdir(tmp_path)
    spotify_dir = tmp_path / "data" / "spotify"
    spotify_dir.mkdir(parents=True)

    spotify_file = spotify_dir / "test-playlist.json"
    spotify_file.write_text(json.dumps(sample_spotify_artifact))

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    def mock_get_client():
        return mock_client

    monkeypatch.setattr("app.web.api.routes.spotify._get_spotify_client", mock_get_client)

    response = client.delete("/api/spotify/playlists/playlist123?slug=test-playlist")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    # Verify the playlist was removed from artifact
    saved_artifact = json.loads(spotify_file.read_text())
    assert len(saved_artifact["playlists"]) == 0


def test_sync_spotify_playlist_block_specific(
    client: TestClient, monkeypatch, tmp_path: Path
) -> None:
    """Test syncing a block-specific playlist only syncs that block's tracks."""
    from unittest.mock import MagicMock

    monkeypatch.chdir(tmp_path)
    spotify_dir = tmp_path / "data" / "spotify"
    spotify_dir.mkdir(parents=True)

    # Create artifact with multiple blocks and playlists
    multi_block_artifact = {
        "source_url": "https://example.com/playlist",
        "blocks": [
            {
                "title": "Block A",
                "tracks": [
                    {"artist": "Artist A1", "title": "Song A1", "spotify_uri": "spotify:track:a1"},
                    {"artist": "Artist A2", "title": "Song A2", "spotify_uri": "spotify:track:a2"},
                ],
            },
            {
                "title": "Block B",
                "tracks": [
                    {"artist": "Artist B1", "title": "Song B1", "spotify_uri": "spotify:track:b1"},
                ],
            },
        ],
        "playlists": [
            {
                "id": "playlist_a",
                "name": "Test - Block A - 2025-01-01",
                "tracks": ["spotify:track:a1", "spotify:track:a2"],
                "tracks_added": 2,
            },
            {
                "id": "playlist_b",
                "name": "Test - Block B - 2025-01-01",
                "tracks": ["spotify:track:b1"],
                "tracks_added": 1,
            },
        ],
        "master_playlist": None,
        "misses": [],
    }

    spotify_file = spotify_dir / "test-playlist.json"
    spotify_file.write_text(json.dumps(multi_block_artifact))

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    def mock_get_client():
        return mock_client

    monkeypatch.setattr("app.web.api.routes.spotify._get_spotify_client", mock_get_client)

    # Sync playlist_a (Block A)
    response = client.post("/api/spotify/playlists/playlist_a/sync?slug=test-playlist")
    assert response.status_code == 200
    assert response.json()["tracks_synced"] == 2

    # Verify only Block A tracks were synced (not all 3 tracks)
    mock_client.replace_playlist_tracks.assert_called_with(
        "playlist_a", ["spotify:track:a1", "spotify:track:a2"]
    )


def test_sync_spotify_master_playlist(client: TestClient, monkeypatch, tmp_path: Path) -> None:
    """Test syncing master playlist syncs all tracks from all blocks."""
    from unittest.mock import MagicMock

    monkeypatch.chdir(tmp_path)
    spotify_dir = tmp_path / "data" / "spotify"
    spotify_dir.mkdir(parents=True)

    # Create artifact with multiple blocks and a master playlist
    multi_block_artifact = {
        "source_url": "https://example.com/playlist",
        "blocks": [
            {
                "title": "Block A",
                "tracks": [
                    {"artist": "Artist A1", "title": "Song A1", "spotify_uri": "spotify:track:a1"},
                ],
            },
            {
                "title": "Block B",
                "tracks": [
                    {"artist": "Artist B1", "title": "Song B1", "spotify_uri": "spotify:track:b1"},
                ],
            },
        ],
        "playlists": [],
        "master_playlist": {
            "id": "master_playlist",
            "name": "Test - All - 2025-01-01",
            "tracks": ["spotify:track:a1", "spotify:track:b1"],
            "tracks_added": 2,
        },
        "misses": [],
    }

    spotify_file = spotify_dir / "test-playlist.json"
    spotify_file.write_text(json.dumps(multi_block_artifact))

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    def mock_get_client():
        return mock_client

    monkeypatch.setattr("app.web.api.routes.spotify._get_spotify_client", mock_get_client)

    # Sync master playlist
    response = client.post("/api/spotify/playlists/master_playlist/sync?slug=test-playlist")
    assert response.status_code == 200
    assert response.json()["tracks_synced"] == 2

    # Verify all tracks from all blocks were synced
    mock_client.replace_playlist_tracks.assert_called_with(
        "master_playlist", ["spotify:track:a1", "spotify:track:b1"]
    )


# --- Crawl API tests ---


@pytest.fixture
def sample_crawl_data() -> dict:
    """Sample crawl result data."""
    return {
        "index_url": "https://example.com/index",
        "discovered_links": [
            {"url": "https://example.com/playlist1", "description": "Playlist 1"},
            {"url": "https://example.com/playlist2", "description": "Playlist 2"},
        ],
        "processed": [
            {
                "url": "https://example.com/playlist1",
                "description": "Playlist 1",
                "status": "success",
                "mode": "import",
                "artifact": "data/spotify/example-com-playlist1.json",
            },
            {
                "url": "https://example.com/playlist2",
                "description": "Playlist 2",
                "status": "failed",
                "error": "Connection timeout",
            },
        ],
        "crawled_at": "2025-01-01T12:00:00+00:00",
    }


def test_list_crawls_empty(client: TestClient, monkeypatch, tmp_path: Path) -> None:
    """Test listing crawls when none exist."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "crawl").mkdir(parents=True)

    response = client.get("/api/crawls")
    assert response.status_code == 200
    assert response.json() == []


def test_list_crawls(
    client: TestClient, monkeypatch, tmp_path: Path, sample_crawl_data: dict
) -> None:
    """Test listing crawls returns crawl summaries."""
    monkeypatch.chdir(tmp_path)
    crawl_dir = tmp_path / "data" / "crawl"
    crawl_dir.mkdir(parents=True)

    crawl_file = crawl_dir / "example-com-index.json"
    crawl_file.write_text(json.dumps(sample_crawl_data))

    response = client.get("/api/crawls")
    assert response.status_code == 200

    crawls = response.json()
    assert len(crawls) == 1
    assert crawls[0]["slug"] == "example-com-index"
    assert crawls[0]["index_url"] == "https://example.com/index"
    assert crawls[0]["link_count"] == 2
    assert crawls[0]["success_count"] == 1
    assert crawls[0]["failed_count"] == 1


def test_list_crawls_includes_llm_cost(
    client: TestClient, monkeypatch, tmp_path: Path, sample_crawl_data: dict
) -> None:
    """Test that crawl list includes LLM cost when available."""
    monkeypatch.chdir(tmp_path)
    crawl_dir = tmp_path / "data" / "crawl"
    crawl_dir.mkdir(parents=True)

    # Add LLM usage to the sample crawl data
    crawl_with_cost = {
        **sample_crawl_data,
        "llm_usage": {
            "prompt_tokens": 2000,
            "completion_tokens": 1000,
            "model": "gpt-4",
            "cost_usd": 0.0567,
        },
    }
    crawl_file = crawl_dir / "example-com-index.json"
    crawl_file.write_text(json.dumps(crawl_with_cost))

    response = client.get("/api/crawls")
    assert response.status_code == 200

    crawls = response.json()
    assert len(crawls) == 1
    assert crawls[0]["llm_cost_usd"] == 0.0567


def test_get_crawl(
    client: TestClient, monkeypatch, tmp_path: Path, sample_crawl_data: dict
) -> None:
    """Test getting a single crawl by slug."""
    monkeypatch.chdir(tmp_path)
    crawl_dir = tmp_path / "data" / "crawl"
    crawl_dir.mkdir(parents=True)

    crawl_file = crawl_dir / "example-com-index.json"
    crawl_file.write_text(json.dumps(sample_crawl_data))

    response = client.get("/api/crawls/example-com-index")
    assert response.status_code == 200

    crawl = response.json()
    assert crawl["index_url"] == "https://example.com/index"
    assert len(crawl["discovered_links"]) == 2
    assert len(crawl["processed"]) == 2


def test_get_crawl_not_found(client: TestClient, monkeypatch, tmp_path: Path) -> None:
    """Test getting a non-existent crawl returns 404."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "crawl").mkdir(parents=True)

    response = client.get("/api/crawls/non-existent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_reprocess_crawl_url(
    client: TestClient, monkeypatch, tmp_path: Path, sample_crawl_data: dict
) -> None:
    """Test reprocessing a failed URL from a crawl."""
    from unittest.mock import MagicMock

    monkeypatch.chdir(tmp_path)
    crawl_dir = tmp_path / "data" / "crawl"
    parsed_dir = tmp_path / "data" / "parsed"
    crawl_dir.mkdir(parents=True)
    parsed_dir.mkdir(parents=True)

    crawl_file = crawl_dir / "example-com-index.json"
    crawl_file.write_text(json.dumps(sample_crawl_data))

    # Mock run_dev to succeed
    mock_run_dev = MagicMock(return_value=True)
    monkeypatch.setattr("app.web.api.routes.crawls.run_dev", mock_run_dev)

    # Reprocess the failed URL (index 1) in dev mode
    response = client.post(
        "/api/crawls/example-com-index/reprocess/1",
        json={"dev_mode": True, "force": True},
    )
    assert response.status_code == 200

    result = response.json()
    assert result["status"] == "success"
    assert result["mode"] == "dev"

    # Verify the crawl file was updated
    updated_crawl = json.loads(crawl_file.read_text())
    assert updated_crawl["processed"][1]["status"] == "success"
    assert updated_crawl["processed"][1].get("artifact") is not None
    # Verify stale error was cleared
    assert "error" not in updated_crawl["processed"][1]


def test_reprocess_crawl_url_invalid_index(
    client: TestClient, monkeypatch, tmp_path: Path, sample_crawl_data: dict
) -> None:
    """Test reprocessing with invalid index returns error."""
    monkeypatch.chdir(tmp_path)
    crawl_dir = tmp_path / "data" / "crawl"
    crawl_dir.mkdir(parents=True)

    crawl_file = crawl_dir / "example-com-index.json"
    crawl_file.write_text(json.dumps(sample_crawl_data))

    response = client.post(
        "/api/crawls/example-com-index/reprocess/99",
        json={"dev_mode": True},
    )
    assert response.status_code == 400
    assert "invalid index" in response.json()["detail"].lower()


# --- Import API tests ---


def test_preview_import(
    client: TestClient, monkeypatch, tmp_path: Path, sample_playlist_data: dict
) -> None:
    """Test previewing an import (dev mode)."""
    monkeypatch.chdir(tmp_path)
    parsed_dir = tmp_path / "data" / "parsed"
    parsed_dir.mkdir(parents=True)

    # Mock run_dev to create a parsed file
    def mock_run_dev(url, force, settings):
        parsed_file = parsed_dir / "example-com-playlist.json"
        parsed_file.write_text(json.dumps(sample_playlist_data))
        return True

    monkeypatch.setattr("app.web.api.routes.imports.run_dev", mock_run_dev)

    # Mock slugify_url
    monkeypatch.setattr(
        "app.web.api.routes.imports.slugify_url", lambda url: "example-com-playlist"
    )

    response = client.post(
        "/api/import/preview",
        json={"url": "https://example.com/playlist", "force": False},
    )
    assert response.status_code == 200

    result = response.json()
    assert result["slug"] == "example-com-playlist"
    assert result["source_name"] == "Test Playlist"
    assert result["block_count"] == 1
    assert result["track_count"] == 2


def test_execute_import(
    client: TestClient, monkeypatch, tmp_path: Path, sample_spotify_artifact: dict
) -> None:
    """Test executing a full import."""
    monkeypatch.chdir(tmp_path)
    spotify_dir = tmp_path / "data" / "spotify"
    spotify_dir.mkdir(parents=True)

    # Mock run_import to create a spotify file
    def mock_run_import(url, force, master_playlist, settings, write_playlists):
        spotify_file = spotify_dir / "example-com-playlist.json"
        spotify_file.write_text(json.dumps(sample_spotify_artifact))
        return True

    monkeypatch.setattr("app.web.api.routes.imports.run_import", mock_run_import)

    # Mock slugify_url
    monkeypatch.setattr(
        "app.web.api.routes.imports.slugify_url", lambda url: "example-com-playlist"
    )

    response = client.post(
        "/api/import/execute",
        json={"url": "https://example.com/playlist", "force": False},
    )
    assert response.status_code == 200

    result = response.json()
    assert result["slug"] == "example-com-playlist"
    assert result["playlist_count"] == 1
    assert result["miss_count"] == 1


def test_preview_import_failure(client: TestClient, monkeypatch, tmp_path: Path) -> None:
    """Test preview import handles errors gracefully."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "parsed").mkdir(parents=True)

    # Mock run_dev to raise an exception
    def mock_run_dev(url, force, settings):
        raise RuntimeError("Connection failed")

    monkeypatch.setattr("app.web.api.routes.imports.run_dev", mock_run_dev)

    response = client.post(
        "/api/import/preview",
        json={"url": "https://example.com/playlist"},
    )
    assert response.status_code == 500
    assert "failed to parse" in response.json()["detail"].lower()

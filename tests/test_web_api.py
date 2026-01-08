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


def test_get_spotify_artifact_not_found(
    client: TestClient, monkeypatch, tmp_path: Path
) -> None:
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

    monkeypatch.setattr(
        "app.web.api.routes.spotify._get_spotify_client", mock_get_client
    )

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
        {"uri": "spotify:track:new1", "external_urls": {"spotify": "https://open.spotify.com/track/new1"}},
        # Second track doesn't match
        None,
    ]
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    def mock_get_client():
        return mock_client

    monkeypatch.setattr(
        "app.web.api.routes.spotify._get_spotify_client", mock_get_client
    )

    response = client.post("/api/spotify/test-playlist/remap")
    assert response.status_code == 200

    result = response.json()
    # First track should have URI
    assert result["blocks"][0]["tracks"][0]["spotify_uri"] == "spotify:track:new1"
    # Second track should be in misses
    assert len(result["misses"]) == 1
    assert result["misses"][0]["artist"] == "Artist 2"


def test_update_spotify_playlist_name(client: TestClient, monkeypatch) -> None:
    """Test updating a Spotify playlist name (mocked, no artifact)."""
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    def mock_get_client():
        return mock_client

    monkeypatch.setattr(
        "app.web.api.routes.spotify._get_spotify_client", mock_get_client
    )

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

    monkeypatch.setattr(
        "app.web.api.routes.spotify._get_spotify_client", mock_get_client
    )

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

    monkeypatch.setattr(
        "app.web.api.routes.spotify._get_spotify_client", mock_get_client
    )

    response = client.delete("/api/spotify/playlists/playlist123?slug=test-playlist")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"

    # Verify the playlist was removed from artifact
    saved_artifact = json.loads(spotify_file.read_text())
    assert len(saved_artifact["playlists"]) == 0

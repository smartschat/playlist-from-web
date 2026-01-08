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

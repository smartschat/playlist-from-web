"""Tests for the crawl command and link extraction."""

from pathlib import Path

import pytest

from app import pipeline
from app.config import Settings
from app.models import ExtractedLink, LLMUsage, Track, TrackBlock


def _mock_llm_usage() -> LLMUsage:
    """Create a mock LLMUsage for tests."""
    return LLMUsage(prompt_tokens=100, completion_tokens=50, model="gpt-5-nano", cost_usd=0.0001)


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        openai_api_key="test-key",
        openai_model="gpt-5-nano",
        spotify_client_id="test-id",
        spotify_client_secret="test-secret",
        spotify_refresh_token="test-refresh",
        spotify_user_id="test-user",
        spotify_redirect_uri="http://localhost/callback",
        master_playlist_enabled=False,
        log_level="INFO",
    )


def test_is_pdf_url() -> None:
    """Test PDF URL detection."""
    assert pipeline._is_pdf_url("https://example.com/file.pdf")
    assert pipeline._is_pdf_url("https://example.com/file.PDF")
    assert pipeline._is_pdf_url("https://example.com/path/to/file.pdf")
    assert not pipeline._is_pdf_url("https://example.com/page.html")
    assert not pipeline._is_pdf_url("https://example.com/page")
    assert not pipeline._is_pdf_url("https://example.com/pdf-info")


def test_extract_links_from_index(monkeypatch, tmp_path: Path, settings: Settings) -> None:
    """Test that link extraction from index page works."""
    monkeypatch.chdir(tmp_path)

    # Create data directories
    (tmp_path / "data" / "raw").mkdir(parents=True)

    # Mock the HTML fetch
    index_html = """
    <html>
    <body>
        <a href="/playlist/2024-01-01.pdf">January Playlist</a>
        <a href="/playlist/2024-02-01.pdf">February Playlist</a>
    </body>
    </html>
    """

    def fake_fetch_html(url: str) -> str:
        return index_html

    monkeypatch.setattr(pipeline, "_fetch_html", fake_fetch_html)

    # Mock LLM extraction
    def fake_extract_links(url, content, model, api_key):
        links = [
            ExtractedLink(url="https://example.com/playlist/2024-01-01.pdf", description="January"),
            ExtractedLink(
                url="https://example.com/playlist/2024-02-01.pdf", description="February"
            ),
        ]
        return links, _mock_llm_usage()

    monkeypatch.setattr(pipeline, "extract_links_with_llm", fake_extract_links)

    links, llm_usage = pipeline._extract_links_from_index(
        "https://example.com/index", force=True, settings=settings
    )

    assert len(links) == 2
    assert links[0].url == "https://example.com/playlist/2024-01-01.pdf"
    assert links[1].url == "https://example.com/playlist/2024-02-01.pdf"
    assert llm_usage is not None


def test_run_crawl_dev_mode(monkeypatch, tmp_path: Path, settings: Settings) -> None:
    """Test crawl in dev mode processes all links."""
    monkeypatch.chdir(tmp_path)

    # Create data directories
    (tmp_path / "data" / "crawl").mkdir(parents=True)

    # Mock link extraction
    def fake_extract(url, force, settings):
        links = [
            ExtractedLink(url="https://example.com/page1", description="Page 1"),
            ExtractedLink(url="https://example.com/page2", description="Page 2"),
        ]
        return links, _mock_llm_usage()

    monkeypatch.setattr(pipeline, "_extract_links_from_index", fake_extract)

    # Track run_dev calls
    dev_calls = []

    def fake_run_dev(url, force, settings):
        dev_calls.append(url)
        return True  # Indicate processing occurred

    monkeypatch.setattr(pipeline, "run_dev", fake_run_dev)

    result = pipeline.run_crawl(
        index_url="https://example.com/index",
        dev_mode=True,
        force=False,
        master_playlist=False,
        settings=settings,
    )

    assert len(dev_calls) == 2
    assert "https://example.com/page1" in dev_calls
    assert "https://example.com/page2" in dev_calls
    assert len(result.processed) == 2
    assert all(p["status"] == "success" for p in result.processed)


def test_run_crawl_max_links(monkeypatch, tmp_path: Path, settings: Settings) -> None:
    """Test that max_links limits processing."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "crawl").mkdir(parents=True)

    def fake_extract(url, force, settings):
        links = [
            ExtractedLink(url="https://example.com/page1", description="Page 1"),
            ExtractedLink(url="https://example.com/page2", description="Page 2"),
            ExtractedLink(url="https://example.com/page3", description="Page 3"),
        ]
        return links, _mock_llm_usage()

    monkeypatch.setattr(pipeline, "_extract_links_from_index", fake_extract)

    dev_calls = []

    def fake_run_dev(url, force, settings):
        dev_calls.append(url)
        return True  # Indicate processing occurred

    monkeypatch.setattr(pipeline, "run_dev", fake_run_dev)

    result = pipeline.run_crawl(
        index_url="https://example.com/index",
        dev_mode=True,
        force=False,
        master_playlist=False,
        settings=settings,
        max_links=2,
    )

    assert len(dev_calls) == 2
    assert len(result.processed) == 2


def test_run_crawl_continues_on_error(monkeypatch, tmp_path: Path, settings: Settings) -> None:
    """Test that crawl continues processing when one URL fails."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "crawl").mkdir(parents=True)

    def fake_extract(url, force, settings):
        links = [
            ExtractedLink(url="https://example.com/fail", description="Will fail"),
            ExtractedLink(url="https://example.com/success", description="Will succeed"),
        ]
        return links, _mock_llm_usage()

    monkeypatch.setattr(pipeline, "_extract_links_from_index", fake_extract)

    call_count = [0]

    def fake_run_dev(url, force, settings):
        call_count[0] += 1
        if "fail" in url:
            raise ValueError("Simulated failure")
        return True  # Indicate processing occurred

    monkeypatch.setattr(pipeline, "run_dev", fake_run_dev)

    result = pipeline.run_crawl(
        index_url="https://example.com/index",
        dev_mode=True,
        force=False,
        master_playlist=False,
        settings=settings,
    )

    assert call_count[0] == 2  # Both URLs were attempted
    assert result.processed[0]["status"] == "failed"
    assert "error" in result.processed[0]
    assert result.processed[1]["status"] == "success"


def test_crawl_result_saved(monkeypatch, tmp_path: Path, settings: Settings) -> None:
    """Test that crawl result is saved to artifact file."""
    monkeypatch.chdir(tmp_path)
    crawl_dir = tmp_path / "data" / "crawl"
    crawl_dir.mkdir(parents=True)

    def fake_extract(url, force, settings):
        links = [ExtractedLink(url="https://example.com/page1", description="Page 1")]
        return links, _mock_llm_usage()

    monkeypatch.setattr(pipeline, "_extract_links_from_index", fake_extract)
    monkeypatch.setattr(pipeline, "run_dev", lambda *args, **kwargs: True)

    pipeline.run_crawl(
        index_url="https://example.com/index",
        dev_mode=True,
        force=False,
        master_playlist=False,
        settings=settings,
    )

    # Check that artifact was saved
    artifacts = list(crawl_dir.glob("*.json"))
    assert len(artifacts) == 1


def test_merge_blocks_by_title() -> None:
    """Test that blocks with same title/context are merged."""
    blocks = [
        TrackBlock(
            title="Playlist A",
            context="January 2025",
            tracks=[
                Track(artist="Artist 1", title="Song 1"),
                Track(artist="Artist 2", title="Song 2"),
            ],
        ),
        TrackBlock(
            title="Playlist A",
            context="January 2025",
            tracks=[
                Track(artist="Artist 3", title="Song 3"),
            ],
        ),
        TrackBlock(
            title="Playlist B",
            context=None,
            tracks=[
                Track(artist="Artist 4", title="Song 4"),
            ],
        ),
    ]

    merged = pipeline._merge_blocks_by_title(blocks)

    assert len(merged) == 2

    # Find merged block A
    block_a = next(b for b in merged if b.title == "Playlist A")
    assert len(block_a.tracks) == 3
    assert block_a.tracks[0].artist == "Artist 1"
    assert block_a.tracks[2].artist == "Artist 3"

    # Block B should be unchanged
    block_b = next(b for b in merged if b.title == "Playlist B")
    assert len(block_b.tracks) == 1


def test_merge_blocks_case_insensitive() -> None:
    """Test that block merging is case-insensitive."""
    blocks = [
        TrackBlock(
            title="Playlist A",
            context=None,
            tracks=[Track(artist="Artist 1", title="Song 1")],
        ),
        TrackBlock(
            title="PLAYLIST A",
            context=None,
            tracks=[Track(artist="Artist 2", title="Song 2")],
        ),
    ]

    merged = pipeline._merge_blocks_by_title(blocks)

    assert len(merged) == 1
    assert len(merged[0].tracks) == 2

from datetime import datetime, timezone
from pathlib import Path
from shutil import copyfile

from app import pipeline
from app.config import Settings
from app.models import ParsedPage, Track, TrackBlock
from app.utils import slugify_url


def test_process_url_uses_stubbed_llm_and_dedupes(monkeypatch, tmp_path: Path) -> None:
    url = "https://www.hr2.de/programm/hoerbar/hoerbar---musik-grenzenlos,epg-hoerbar-4290.html"
    slug = slugify_url(url)

    # prepare working dir with fixture raw HTML
    monkeypatch.chdir(tmp_path)
    raw_src = Path(__file__).parent / "fixtures" / "hr2_sample.html"
    raw_dst = Path("data/raw") / f"{slug}.html"
    raw_dst.parent.mkdir(parents=True, exist_ok=True)
    copyfile(raw_src, raw_dst)

    captured = {}

    def fake_parse_with_llm(url: str, content: str, model: str, api_key: str) -> ParsedPage:
        captured["content"] = content
        return ParsedPage(
            source_url=url,
            source_name="hr2",
            fetched_at=datetime.now(timezone.utc),
            blocks=[
                TrackBlock(
                    title="Fixture Block",
                    context="context line",
                    tracks=[
                        Track(artist="Minru", title="Thin places"),
                        Track(artist="Minru", title="Thin places"),  # duplicate for dedupe test
                        Track(artist="Hugh Masekela", title="Skokiaan"),
                    ],
                )
            ],
        )

    monkeypatch.setattr(pipeline, "parse_with_llm", fake_parse_with_llm)

    settings = Settings(
        openai_api_key="test",
        openai_model="gpt-5-nano",
        spotify_client_id="id",
        spotify_client_secret="secret",
        spotify_refresh_token="refresh",
        spotify_user_id="user",
        spotify_redirect_uri="http://localhost/callback",
        master_playlist_enabled=False,
        log_level="INFO",
    )

    parsed, parsed_path = pipeline._process_url(url, force=False, settings=settings)  # type: ignore[attr-defined]

    # ensure LLM saw the cleaned content
    assert "Hörbar" in captured["content"] or "Horbar" in captured["content"]

    # dedupe should drop the duplicate Minru track
    assert len(parsed.blocks[0].tracks) == 2

    # artifact is written in the temporary workspace
    assert parsed_path.exists()
    data = parsed_path.read_text(encoding="utf-8")
    assert '"Fixture Block"' in data

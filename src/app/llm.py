import json
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from openai import OpenAI

from .models import ParsedPage, Track, TrackBlock


SYSTEM_PROMPT = """You are a meticulous parser that extracts music track listings from webpages.
- Identify coherent blocks of track listings (e.g., playlists, program segments).
- For each block, preserve order, and keep artist and track title as written.
- Include album only if stated; otherwise leave null.
- Include a short context/label for the block (e.g., program title/date) when available.
- If unsure a line is a valid track, skip it rather than guessing.
Return strict JSON following the schema."""

USER_PROMPT_TEMPLATE = """Source URL: {url}
Task: Extract track listing blocks from the page text below.
Return JSON with fields: source_name (string, short name for the source), blocks (array). Each block has: title (string), context (string|null), tracks (array). Each track has: artist (string), title (string), album (string|null), source_line (string|null).
Page text:
\"\"\"
{content}
\"\"\""""


def truncate_content(content: str, max_chars: int = 12000) -> Tuple[str, int]:
    if len(content) <= max_chars:
        return content, len(content)
    return content[:max_chars], len(content)


def parse_with_llm(url: str, content: str, model: str, api_key: str) -> ParsedPage:
    client = OpenAI(api_key=api_key)
    truncated_content, _ = truncate_content(content)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_PROMPT_TEMPLATE.format(url=url, content=truncated_content),
        },
    ]
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
    )
    raw = completion.choices[0].message.content
    if raw is None:
        raise ValueError("LLM returned empty content")

    try:
        data: Dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM returned invalid JSON") from exc

    source_name = data.get("source_name") or ""
    blocks_data: List[Dict] = data.get("blocks") or []

    blocks: List[TrackBlock] = []
    for block in blocks_data:
        tracks_data = block.get("tracks") or []
        tracks: List[Track] = []
        for track in tracks_data:
            try:
                tracks.append(
                    Track(
                        artist=track.get("artist", "").strip(),
                        title=track.get("title", "").strip(),
                        album=(track.get("album") or None),
                        source_line=(track.get("source_line") or None),
                    )
                )
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"Invalid track entry from LLM: {track}") from exc
        if not tracks:
            continue
        blocks.append(
            TrackBlock(
                title=block.get("title", "").strip() or "Untitled Block",
                context=(block.get("context") or None),
                tracks=tracks,
            )
        )

    if not blocks:
        raise ValueError("No track blocks returned by LLM")

    return ParsedPage(
        source_url=url,
        source_name=source_name or None,
        fetched_at=datetime.now(timezone.utc),
        blocks=blocks,
    )

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, HttpUrl


class Track(BaseModel):
    artist: str
    title: str
    album: Optional[str] = None
    source_line: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class TrackBlock(BaseModel):
    title: str
    context: Optional[str] = None
    tracks: List[Track]

    model_config = ConfigDict(extra="ignore")


class ParsedPage(BaseModel):
    source_url: HttpUrl
    source_name: Optional[str] = None
    fetched_at: datetime
    blocks: List[TrackBlock]

    model_config = ConfigDict(extra="ignore", frozen=True)

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, HttpUrl

# Model pricing per 1M tokens (USD)
MODEL_PRICING = {
    "gpt-5-nano": {"input": 0.05, "output": 0.40},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
}


class LLMUsage(BaseModel):
    """Track token usage and cost for LLM API calls."""

    prompt_tokens: int
    completion_tokens: int
    model: str
    cost_usd: float

    model_config = ConfigDict(extra="ignore")

    @classmethod
    def from_completion(cls, usage, model: str) -> "LLMUsage":
        """Create from OpenAI completion usage object."""
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens

        # Calculate cost
        pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
        cost_usd = (prompt_tokens * pricing["input"] / 1_000_000) + (
            completion_tokens * pricing["output"] / 1_000_000
        )

        return cls(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
            cost_usd=cost_usd,
        )

    def __add__(self, other: "LLMUsage") -> "LLMUsage":
        """Combine two usage records."""
        return LLMUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            model=self.model,  # Keep first model
            cost_usd=self.cost_usd + other.cost_usd,
        )


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
    llm_usage: Optional[LLMUsage] = None

    model_config = ConfigDict(extra="ignore", frozen=True)


class ExtractedLink(BaseModel):
    """A link extracted from an index page that may contain playlist/track data."""

    url: str
    description: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class CrawlResult(BaseModel):
    """Summary of a crawl operation over an index page."""

    index_url: HttpUrl
    discovered_links: List[ExtractedLink]
    processed: List[dict]  # List of {url, status, error?, artifact_path?}
    crawled_at: datetime
    llm_usage: Optional[LLMUsage] = None  # Aggregated usage for entire crawl

    model_config = ConfigDict(extra="ignore")

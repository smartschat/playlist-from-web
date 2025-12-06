from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()


class Settings(BaseSettings):
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5-nano", alias="OPENAI_MODEL")

    spotify_client_id: str = Field(..., alias="SPOTIFY_CLIENT_ID")
    spotify_client_secret: str = Field(..., alias="SPOTIFY_CLIENT_SECRET")
    spotify_refresh_token: str = Field(..., alias="SPOTIFY_REFRESH_TOKEN")
    spotify_user_id: str = Field(..., alias="SPOTIFY_USER_ID")
    spotify_redirect_uri: str = Field(..., alias="SPOTIFY_REDIRECT_URI")

    master_playlist_enabled: bool = Field(
        default=False, alias="MASTER_PLAYLIST_ENABLED"
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache settings from environment and .env."""
    return Settings()

"""
backend/config.py
-----------------
Loads and validates all environment variables using pydantic-settings.
Import `settings` anywhere in the backend to access config values.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from .env file."""

    # Google Gemini
    gemini_api_key: str

    # GitHub
    github_token: str
    github_webhook_secret: str

    # Behaviour
    max_retry_attempts: int = 3
    sandbox_timeout_seconds: int = 60

    # CORS / WebSocket
    frontend_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once at startup)."""
    return Settings()


# Convenience singleton
settings = get_settings()

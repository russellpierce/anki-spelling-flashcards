"""
Configuration management using pydantic-settings.

This module provides type-safe configuration loading from environment variables
and .env files. All settings are validated at startup.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.

    Environment variables take precedence over .env file values.

    Attributes:
        mw_elementary_api_key: Merriam-Webster Elementary Dictionary API key (required)
        cache_dir: Directory for caching HTTP responses and audio files (default: .cache/)
    """

    mw_elementary_api_key: str = Field(
        ...,
        description="Merriam-Webster Elementary Dictionary API key",
    )

    cache_dir: str = Field(
        default=".cache/",
        description="Directory for caching HTTP responses and audio files",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("mw_elementary_api_key")
    @classmethod
    def validate_api_key_not_empty(cls, v: str) -> str:
        """Validate that API key is not empty after stripping whitespace."""
        stripped = v.strip()
        if not stripped:
            msg = "API key cannot be empty or whitespace only"
            raise ValueError(msg)
        return stripped


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get application settings singleton.

    This function caches the Settings instance to ensure consistent configuration
    throughout the application lifetime. The settings are loaded once and reused.

    Returns:
        Settings: The application settings instance

    Raises:
        ValidationError: If required settings are missing or invalid

    Example:
        >>> settings = get_settings()
        >>> api_key = settings.mw_elementary_api_key
    """
    return Settings()

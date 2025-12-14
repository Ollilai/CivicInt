"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "sqlite:///./data/watchdog.db"

    # Storage
    storage_backend: Literal["local", "s3"] = "local"
    storage_path: str = "./data/files"

    # OpenAI
    openai_api_key: str = ""

    # Security
    secret_key: str = "change-this-in-production"

    # Email
    mail_server: str = ""
    mail_port: int = 587
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = ""
    mail_use_tls: bool = True

    # App settings
    app_name: str = "Watchdog"
    app_url: str = "http://localhost:8000"
    debug: bool = False

    # Rate limiting
    connector_rate_limit: float = 1.0  # requests per second
    connector_user_agent: str = "CivicWatchdog/1.0 (contact@example.com)"

    # LLM budget
    llm_monthly_budget: float = 10.0  # euros

    # Token limits
    triage_max_tokens: int = 4000
    case_builder_max_tokens: int = 8000


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

"""Application configuration using Pydantic Settings."""

import os
import secrets
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


# SECURITY: Insecure default key that must be changed in production
_INSECURE_DEFAULT_KEY = "change-this-in-production"


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
    secret_key: str = _INSECURE_DEFAULT_KEY
    admin_token: str = ""  # Required for admin access

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

    # LLM settings
    llm_monthly_budget: float = 10.0  # euros
    triage_model: str = "gpt-4o-mini"
    case_builder_model: str = "gpt-4o"

    # Token limits
    triage_max_tokens: int = 4000
    case_builder_max_tokens: int = 8000

    # Rate limiting for authentication
    auth_rate_limit_attempts: int = 5  # Max failed attempts
    auth_rate_limit_window: int = 300  # Window in seconds (5 minutes)


def validate_security_settings(settings: Settings) -> None:
    """
    Validate security-critical settings.

    SECURITY: Raises RuntimeError if insecure defaults are used in production.
    """
    if not settings.debug and settings.secret_key == _INSECURE_DEFAULT_KEY:
        raise RuntimeError(
            "SECURITY ERROR: SECRET_KEY must be changed from default in production. "
            "Generate a secure key with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    validate_security_settings(settings)
    return settings

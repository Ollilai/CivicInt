from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "postgresql://civicint:civicint@localhost:5432/civicint"
    storage_path: str = "./data/files"

    openai_api_key: str = ""
    secret_key: str = "change-in-production"
    admin_token: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    app_name: str = "CivicInt"
    app_url: str = "http://localhost:8000"
    debug: bool = False

    connector_rate_limit: float = 1.0
    connector_user_agent: str = "CivicInt/2.0 (+https://civicint.fi; contact@civicint.fi)"

    llm_monthly_budget: float = 10.0
    triage_max_chars: int = 12000
    case_builder_max_chars: int = 24000

    nextauth_secret: str = ""
    nextauth_url: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()

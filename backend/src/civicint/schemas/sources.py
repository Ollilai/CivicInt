from datetime import datetime

from pydantic import BaseModel


class SourceHealth(BaseModel):
    id: int
    municipality: str
    region: str | None
    platform: str
    base_url: str
    enabled: bool
    last_success_at: datetime | None
    last_error: str | None
    consecutive_failures: int

    model_config = {"from_attributes": True}


class SourceCreate(BaseModel):
    municipality: str
    region: str | None = None
    platform: str
    base_url: str
    scrape_interval_minutes: int = 120
    extra_config: dict | None = None


class MunicipalityItem(BaseModel):
    name: str
    region: str | None
    source_count: int
    case_count: int

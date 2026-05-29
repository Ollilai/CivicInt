from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SourceHealth(BaseModel):
    id: int
    municipality: str
    region: Optional[str]
    platform: str
    base_url: str
    enabled: bool
    last_success_at: Optional[datetime]
    last_error: Optional[str]
    consecutive_failures: int

    model_config = {"from_attributes": True}


class SourceCreate(BaseModel):
    municipality: str
    region: Optional[str] = None
    platform: str
    base_url: str
    scrape_interval_minutes: int = 120
    extra_config: Optional[dict] = None


class MunicipalityItem(BaseModel):
    name: str
    region: Optional[str]
    source_count: int
    case_count: int

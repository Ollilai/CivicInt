from datetime import datetime

from pydantic import BaseModel

from civicint.models.enums import CaseStatus, Confidence


class CaseListItem(BaseModel):
    id: int
    slug: str
    headline: str
    primary_category: str
    status: CaseStatus
    confidence: Confidence
    municipalities: list[str]
    first_seen_at: datetime
    updated_at: datetime
    is_bookmarked: bool = False

    model_config = {"from_attributes": True}


class EvidenceItem(BaseModel):
    id: int
    page: int | None
    snippet: str
    source_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseEventItem(BaseModel):
    id: int
    event_type: str
    event_time: datetime | None
    payload: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseDetail(CaseListItem):
    summary_md: str
    confidence_reason: str | None
    permit_number: str | None
    entities: dict | None = None
    locations: dict | None = None
    evidence: list[EvidenceItem] = []
    events: list[CaseEventItem] = []


class BookmarkCreate(BaseModel):
    note: str | None = None

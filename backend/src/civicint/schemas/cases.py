from datetime import datetime
from typing import Optional

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
    page: Optional[int]
    snippet: str
    source_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseEventItem(BaseModel):
    id: int
    event_type: str
    event_time: Optional[datetime]
    payload: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseDetail(CaseListItem):
    summary_md: str
    confidence_reason: Optional[str]
    permit_number: Optional[str]
    entities: Optional[dict] = None
    locations: Optional[dict] = None
    evidence: list[EvidenceItem] = []
    events: list[CaseEventItem] = []


class BookmarkCreate(BaseModel):
    note: Optional[str] = None

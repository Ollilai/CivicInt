from datetime import date, datetime

from pydantic import BaseModel

from civicint.models.enums import CaseStatus


class CaseListItem(BaseModel):
    id: int
    slug: str
    headline: str
    primary_category: str
    status: CaseStatus
    municipalities: list[str]
    meeting_date: date | None
    action_deadline: date | None
    first_seen_at: datetime
    updated_at: datetime

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
    permit_number: str | None
    entities: dict | None = None
    locations: dict | None = None
    evidence: list[EvidenceItem] = []
    events: list[CaseEventItem] = []


class BookmarkCreate(BaseModel):
    note: str | None = None

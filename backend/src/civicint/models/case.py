from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from civicint.models.base import Base, TimestampMixin
from civicint.models.enums import CaseStatus, Confidence


class Case(TimestampMixin, Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    primary_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    headline: Mapped[str] = mapped_column(String(300), nullable=False)
    summary_md: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CaseStatus] = mapped_column(default=CaseStatus.VIREILLA)
    confidence: Mapped[Confidence] = mapped_column(default=Confidence.MEDIUM)
    confidence_reason: Mapped[str | None] = mapped_column(Text)

    meeting_date: Mapped[date | None] = mapped_column(Date)
    action_deadline: Mapped[date | None] = mapped_column(Date)

    permit_number: Mapped[str | None] = mapped_column(String(100), index=True)
    municipalities_json: Mapped[list | None] = mapped_column(JSONB)
    entities_json: Mapped[dict | None] = mapped_column(JSONB)
    locations_json: Mapped[dict | None] = mapped_column(JSONB)

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    events: Mapped[list["CaseEvent"]] = relationship(back_populates="case")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="case")
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="case")


class CaseEvent(Base):
    __tablename__ = "case_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    case: Mapped["Case"] = relationship(back_populates="events")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False)
    file_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("files.id"))
    document_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("documents.id"))
    page: Mapped[int | None] = mapped_column(Integer)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    case: Mapped["Case"] = relationship(back_populates="evidence")
    file: Mapped[Optional["File"]] = relationship(back_populates="evidence")
    document: Mapped[Optional["Document"]] = relationship(back_populates="evidence")

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from civicint.models.base import Base, TimestampMixin
from civicint.models.enums import DocumentStatus


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("source_id", "external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False)

    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(String(200))
    meeting_date: Mapped[Optional[date]] = mapped_column(Date)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)

    status: Mapped[DocumentStatus] = mapped_column(default=DocumentStatus.NEW)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))
    items_json: Mapped[Optional[dict]] = mapped_column(JSONB)

    triage_score: Mapped[Optional[float]] = mapped_column(Float)
    triage_categories: Mapped[Optional[list]] = mapped_column(JSONB)
    triage_reason: Mapped[Optional[str]] = mapped_column(Text)

    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source: Mapped["Source"] = relationship(back_populates="documents")
    files: Mapped[list["File"]] = relationship(back_populates="document")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="document")

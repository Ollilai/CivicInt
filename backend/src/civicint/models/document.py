from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
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
    body: Mapped[str | None] = mapped_column(String(200))
    meeting_date: Mapped[date | None] = mapped_column(Date)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)

    status: Mapped[DocumentStatus] = mapped_column(default=DocumentStatus.NEW)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    items_json: Mapped[dict | None] = mapped_column(JSONB)

    triage_score: Mapped[float | None] = mapped_column(Float)
    triage_categories: Mapped[list | None] = mapped_column(JSONB)
    triage_reason: Mapped[str | None] = mapped_column(Text)

    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source: Mapped["Source"] = relationship(back_populates="documents")
    files: Mapped[list["File"]] = relationship(back_populates="document")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="document")

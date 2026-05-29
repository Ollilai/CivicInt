from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from civicint.models.base import Base, TimestampMixin


class Source(TimestampMixin, Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    municipality: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    region: Mapped[str | None] = mapped_column(String(100))
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    scrape_interval_minutes: Mapped[int] = mapped_column(Integer, default=120)
    extra_config: Mapped[dict | None] = mapped_column(JSONB)

    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    last_scrape_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)

    documents: Mapped[list["Document"]] = relationship(back_populates="source")

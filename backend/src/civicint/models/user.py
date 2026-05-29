from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from civicint.models.base import Base, TimestampMixin
from civicint.models.enums import Confidence, UserRole


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    watch_profiles: Mapped[list["WatchProfile"]] = relationship(back_populates="organization")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(200))
    image: Mapped[str | None] = mapped_column(String(500))
    role: Mapped[UserRole] = mapped_column(default=UserRole.MEMBER)
    org_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("organizations.id"))

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization: Mapped[Optional["Organization"]] = relationship(back_populates="users")
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="user")


class WatchProfile(TimestampMixin, Base):
    __tablename__ = "watch_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), default="Default")
    scope_json: Mapped[list | None] = mapped_column(JSONB)
    topics_json: Mapped[list | None] = mapped_column(JSONB)
    min_confidence: Mapped[Confidence] = mapped_column(default=Confidence.LOW)

    organization: Mapped["Organization"] = relationship(back_populates="watch_profiles")


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "case_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="bookmarks")
    case: Mapped["Case"] = relationship(back_populates="bookmarks")

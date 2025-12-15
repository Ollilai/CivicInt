"""SQLAlchemy database models for Watchdog MVP."""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from watchdog.config import get_settings


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# Enums as proper Python Enums with string values for SQLite compatibility
class DocumentStatus(str, PyEnum):
    """Document processing status."""
    NEW = "new"
    FETCHED = "fetched"
    PROCESSED = "processed"
    ERROR = "error"


class TextStatus(str, PyEnum):
    """Text extraction status."""
    PENDING = "pending"
    EXTRACTED = "extracted"
    OCR_QUEUED = "ocr_queued"
    OCR_DONE = "ocr_done"
    FAILED = "failed"


class CaseStatus(str, PyEnum):
    """Case decision status."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    UNKNOWN = "unknown"


class Confidence(str, PyEnum):
    """Confidence level for case classification."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UserRole(str, PyEnum):
    """User role in the system."""
    ADMIN = "admin"
    MEMBER = "member"


class UserAction(str, PyEnum):
    """User action on a case."""
    DISMISSED = "dismissed"
    STARRED = "starred"
    NOTED = "noted"


# ============================================================================
# SOURCES
# ============================================================================

class Source(Base):
    """Municipality data source configuration."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    municipality: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    config_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    # Health tracking
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="source")


# ============================================================================
# DOCUMENTS & FILES
# ============================================================================

class Document(Base):
    """A municipal document (meeting minutes, agenda, decision)."""

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_source_external", "source_id", "external_id"),
        Index("ix_documents_status_score", "status", "triage_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(Integer, ForeignKey("sources.id"), nullable=False, index=True)

    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)  # minutes, agenda, decision
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # Committee/board name
    meeting_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Processing state
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.NEW, index=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Triage results
    triage_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    triage_categories: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    triage_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="documents")
    files: Mapped[list["File"]] = relationship("File", back_populates="document")
    evidence: Mapped[list["Evidence"]] = relationship("Evidence", back_populates="document")


class File(Base):
    """A file (PDF, attachment) belonging to a document."""

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id"), nullable=False, index=True)

    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # pdf, attachment
    mime: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Storage
    storage_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Text extraction
    text_status: Mapped[str] = mapped_column(String(20), default=TextStatus.PENDING, index=True)
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="files")
    evidence: Mapped[list["Evidence"]] = relationship("Evidence", back_populates="file")


# ============================================================================
# CASES
# ============================================================================

class Case(Base):
    """An environmental case surfaced from documents."""

    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    primary_category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    headline: Mapped[str] = mapped_column(String(300), nullable=False)
    summary_md: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown debrief
    status: Mapped[str] = mapped_column(String(20), default=CaseStatus.UNKNOWN, index=True)

    # Confidence
    confidence: Mapped[str] = mapped_column(String(10), default=Confidence.MEDIUM, index=True)
    confidence_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Extracted entities (JSON arrays)
    municipalities_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    entities_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    locations_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, index=True)

    # Relationships
    events: Mapped[list["CaseEvent"]] = relationship("CaseEvent", back_populates="case")
    evidence: Mapped[list["Evidence"]] = relationship("Evidence", back_populates="case")
    user_actions: Mapped[list["UserCaseAction"]] = relationship("UserCaseAction", back_populates="case")


class CaseEvent(Base):
    """A timeline event for a case."""

    __tablename__ = "case_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False, index=True)

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    event_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    payload_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationships
    case: Mapped["Case"] = relationship("Case", back_populates="events")


class Evidence(Base):
    """A piece of evidence linking a case to source material."""

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    file_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("files.id"), nullable=True, index=True)
    document_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("documents.id"), nullable=True, index=True)

    page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationships
    case: Mapped["Case"] = relationship("Case", back_populates="evidence")
    file: Mapped[Optional["File"]] = relationship("File", back_populates="evidence")
    document: Mapped[Optional["Document"]] = relationship("Document", back_populates="evidence")


# ============================================================================
# USERS & AUTH
# ============================================================================

class User(Base):
    """A user account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    org: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.MEMBER)

    # Magic link auth
    magic_token: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    watch_profiles: Mapped[list["WatchProfile"]] = relationship("WatchProfile", back_populates="user")
    case_actions: Mapped[list["UserCaseAction"]] = relationship("UserCaseAction", back_populates="user")
    deliveries: Mapped[list["Delivery"]] = relationship("Delivery", back_populates="user")


class WatchProfile(Base):
    """User's watch preferences for filtering cases."""

    __tablename__ = "watch_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(100), default="Default")
    scope_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # Municipalities
    topics_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # Categories
    entities_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # Specific keywords
    min_confidence: Mapped[str] = mapped_column(String(10), default=Confidence.LOW)
    delivery_prefs_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="watch_profiles")


class UserCaseAction(Base):
    """User actions on cases (star, dismiss, note)."""

    __tablename__ = "user_case_actions"
    __table_args__ = (
        Index("ix_user_case_actions_user_case", "user_id", "case_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    case_id: Mapped[int] = mapped_column(Integer, ForeignKey("cases.id"), nullable=False, index=True)

    action: Mapped[str] = mapped_column(String(20), nullable=False)  # dismissed, starred, noted
    note_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="case_actions")
    case: Mapped["Case"] = relationship("Case", back_populates="user_actions")


class Delivery(Base):
    """Record of email digest deliveries."""

    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    delivered_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    channel: Mapped[str] = mapped_column(String(20), default="email")
    payload_json: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="deliveries")


# ============================================================================
# LLM USAGE TRACKING
# ============================================================================

class LLMUsage(Base):
    """Track LLM API usage for budget control."""

    __tablename__ = "llm_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    document_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    stage: Mapped[str] = mapped_column(String(20), nullable=False)  # triage, case_builder

    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_eur: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)


# ============================================================================
# DATABASE SESSION
# ============================================================================

def get_engine():
    """Create database engine."""
    settings = get_settings()
    return create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    )


def get_session_factory():
    """Create session factory."""
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

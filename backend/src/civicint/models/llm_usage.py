from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from civicint.models.base import Base


class LLMUsage(Base):
    __tablename__ = "llm_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("documents.id"))
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    stage: Mapped[str] = mapped_column(String(20), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_eur: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

"""LLM budget checking helper."""

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from civicint.config import get_settings
from civicint.models import LLMUsage


def check_budget(session: Session) -> tuple[bool, float, float]:
    """Check if LLM budget allows more spending.

    Returns:
        A tuple of (within_budget, spent_this_month, monthly_limit).
    """
    settings = get_settings()
    now = datetime.now(UTC)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    spent = (
        session.query(func.coalesce(func.sum(LLMUsage.estimated_cost_eur), 0.0))
        .filter(LLMUsage.created_at >= start_of_month)
        .scalar()
    )

    return float(spent) < settings.llm_monthly_budget, float(spent), settings.llm_monthly_budget

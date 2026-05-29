from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from civicint.config import get_settings
from civicint.models import Case, Document, File, LLMUsage, Source


def get_pipeline_stats(db: Session) -> dict:
    status_counts = (
        db.query(Document.status, func.count(Document.id))
        .group_by(Document.status)
        .all()
    )
    return {
        "total_sources": db.query(Source).count(),
        "enabled_sources": db.query(Source).filter(Source.enabled.is_(True)).count(),
        "total_documents": db.query(Document).count(),
        "documents_by_status": {
            s.value if hasattr(s, "value") else str(s): c for s, c in status_counts
        },
        "total_cases": db.query(Case).count(),
        "total_files": db.query(File).count(),
    }


def get_llm_spend(db: Session) -> dict:
    settings = get_settings()
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    records = db.query(LLMUsage).filter(LLMUsage.created_at >= month_start).all()

    triage_cost = sum(r.estimated_cost_eur for r in records if r.stage == "triage")
    builder_cost = sum(r.estimated_cost_eur for r in records if r.stage == "case_builder")

    return {
        "month": now.strftime("%Y-%m"),
        "total_cost_eur": triage_cost + builder_cost,
        "budget_eur": settings.llm_monthly_budget,
        "triage_cost": triage_cost,
        "case_builder_cost": builder_cost,
        "documents_triaged": sum(1 for r in records if r.stage == "triage"),
        "cases_built": sum(1 for r in records if r.stage == "case_builder"),
    }

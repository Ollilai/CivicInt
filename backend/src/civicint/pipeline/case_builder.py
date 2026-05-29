"""Case builder pipeline stage -- create Cases from triaged documents."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from openai import OpenAI
from slugify import slugify
from sqlalchemy.orm import Session

from civicint.config import get_settings
from civicint.models import (
    Case,
    CaseEvent,
    CaseStatus,
    Confidence,
    Document,
    DocumentStatus,
    Evidence,
    LLMUsage,
    TextStatus,
)
from civicint.pipeline.budget import check_budget
from civicint.pipeline.prompts import CASE_BUILDER_PROMPT, estimate_cost, truncate_text

logger = logging.getLogger(__name__)


def _find_existing_case(
    entities: dict, session: Session
) -> Case | None:
    """Try to match an existing case by permit number."""
    permit_number = entities.get("permit_number", "")
    if not permit_number:
        return None

    return (
        session.query(Case)
        .filter(Case.permit_number == permit_number)
        .first()
    )


def _unique_slug(base_slug: str, session: Session) -> str:
    """Return *base_slug*, appending a counter suffix if it already exists."""
    slug = base_slug
    counter = 1
    while session.query(Case).filter_by(slug=slug).first() is not None:
        counter += 1
        slug = f"{base_slug}-{counter}"
    return slug


def run_case_builder(document_id: int, session: Session) -> int | None:
    """Build or update a case from a triaged document.

    The document must be in TRIAGED status with triage_score >= 0.6.

    Args:
        document_id: Database ID of the :class:`Document`.
        session: An open SQLAlchemy session.

    Returns:
        The case ID (new or updated), or ``None`` if skipped.
    """
    settings = get_settings()

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    doc = session.get(Document, document_id)
    if doc is None:
        raise ValueError(f"Document {document_id} not found")

    if doc.status != DocumentStatus.TRIAGED:
        logger.warning("Document %d not in TRIAGED status, skipping case builder", document_id)
        return None

    if (doc.triage_score or 0.0) < 0.6:
        logger.info(
            "Document %d triage score %.2f below threshold, skipping", document_id, doc.triage_score
        )
        return None

    # Collect text
    texts: list[str] = []
    for file in doc.files:
        if file.text_status in (TextStatus.EXTRACTED, TextStatus.OCR_DONE) and file.text:
            texts.append(file.text.content)

    if not texts:
        logger.warning("Document %d has no extracted text", document_id)
        return None

    combined_text = "\n\n---\n\n".join(texts)

    # Check budget
    within_budget, spent, limit = check_budget(session)
    if not within_budget:
        logger.warning(
            "LLM budget exhausted (%.2f / %.2f EUR). Pausing document %d.",
            spent,
            limit,
            document_id,
        )
        doc.status = DocumentStatus.BUDGET_PAUSED
        session.commit()
        return None

    # Build user message
    categories = doc.triage_categories or []
    metadata = (
        f"Municipality: {doc.source.municipality}\n"
        f"Body: {doc.body or 'Unknown'}\n"
        f"Title: {doc.title}\n"
        f"Date: {doc.meeting_date}\n"
        f"Categories: {', '.join(categories)}\n"
        f"---\n"
    )
    truncated = truncate_text(combined_text, settings.case_builder_max_chars)

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": CASE_BUILDER_PROMPT},
            {"role": "user", "content": metadata + truncated},
        ],
        response_format={"type": "json_object"},
        max_tokens=1500,
    )

    # Record usage
    usage = LLMUsage(
        document_id=doc.id,
        model="gpt-4o",
        stage="case_builder",
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        estimated_cost_eur=estimate_cost(
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            "gpt-4o",
        ),
    )
    session.add(usage)

    result = json.loads(response.choices[0].message.content)
    entities = result.get("entities", {})

    # Try to find an existing case by permit number
    existing_case = _find_existing_case(entities, session)

    if existing_case:
        existing_case.updated_at = datetime.now(UTC)

        for ev in result.get("evidence", []):
            evidence = Evidence(
                case_id=existing_case.id,
                document_id=doc.id,
                page=ev.get("page"),
                snippet=ev.get("snippet", ""),
                source_url=doc.source_url,
            )
            session.add(evidence)

        event = CaseEvent(
            case_id=existing_case.id,
            event_type="evidence_added",
            event_time=datetime.now(UTC),
            payload_json={"document_id": doc.id},
        )
        session.add(event)

        doc.status = DocumentStatus.BUILT
        session.commit()
        logger.info("Updated existing case %d for document %d", existing_case.id, document_id)
        return existing_case.id

    # Create new case
    confidence_str = result.get("confidence", "medium")
    if confidence_str not in ("high", "medium", "low"):
        confidence_str = "medium"

    status_str = result.get("status", "unknown")
    if status_str not in ("proposed", "approved", "unknown"):
        status_str = "unknown"

    headline = result.get("headline", doc.title)[:300]
    base_slug = slugify(headline, max_length=190)
    slug = _unique_slug(base_slug, session)

    case = Case(
        slug=slug,
        primary_category=categories[0] if categories else "unknown",
        headline=headline,
        summary_md="\n".join(f"- {point}" for point in result.get("debrief", [])),
        status=CaseStatus(status_str),
        confidence=Confidence(confidence_str),
        confidence_reason=result.get("confidence_reason"),
        permit_number=entities.get("permit_number"),
        municipalities_json=[doc.source.municipality],
        entities_json=entities,
        locations_json={"location": entities.get("location", "")},
    )
    session.add(case)
    session.flush()  # Obtain ID

    # Add evidence
    for ev in result.get("evidence", []):
        evidence = Evidence(
            case_id=case.id,
            document_id=doc.id,
            page=ev.get("page"),
            snippet=ev.get("snippet", ""),
            source_url=doc.source_url,
        )
        session.add(evidence)

    # Add timeline events
    for item in result.get("timeline", []):
        try:
            event_date = datetime.fromisoformat(item.get("date", ""))
        except (ValueError, TypeError):
            event_date = None

        event = CaseEvent(
            case_id=case.id,
            event_type="timeline",
            event_time=event_date,
            payload_json={"description": item.get("event", "")},
        )
        session.add(event)

    doc.status = DocumentStatus.BUILT
    session.commit()
    logger.info("Created case %d (%s) for document %d", case.id, slug, document_id)
    return case.id

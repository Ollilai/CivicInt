"""Triage pipeline stage -- classify documents using LLM."""

from __future__ import annotations

import json
import logging

from openai import OpenAI
from sqlalchemy.orm import Session

from civicint.config import get_settings
from civicint.models import Document, DocumentStatus, LLMUsage, TextStatus
from civicint.pipeline.budget import check_budget
from civicint.pipeline.prompts import TRIAGE_PROMPT, estimate_cost, truncate_text

logger = logging.getLogger(__name__)


def run_triage(document_id: int, session: Session) -> None:
    """Run LLM triage on a document to classify environmental relevance.

    The document must have status EXTRACTED and at least one FileText record.
    Updates triage_score, triage_categories, triage_reason and advances status.

    Args:
        document_id: Database ID of the :class:`Document`.
        session: An open SQLAlchemy session.
    """
    settings = get_settings()

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")

    doc = session.get(Document, document_id)
    if doc is None:
        raise ValueError(f"Document {document_id} not found")

    if doc.status != DocumentStatus.EXTRACTED:
        logger.warning("Document %d not in EXTRACTED status, skipping triage", document_id)
        return

    # Collect text from FileText records
    texts: list[str] = []
    for file in doc.files:
        if file.text_status in (TextStatus.EXTRACTED, TextStatus.OCR_DONE) and file.text:
            texts.append(file.text.content)

    if not texts:
        logger.warning("Document %d has no extracted text, skipping triage", document_id)
        return

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
        return

    # Build user message with metadata
    metadata = (
        f"Municipality: {doc.source.municipality}\n"
        f"Body: {doc.body or 'Unknown'}\n"
        f"Title: {doc.title}\n"
        f"Date: {doc.meeting_date}\n"
        f"---\n"
    )
    truncated = truncate_text(combined_text, settings.triage_max_chars)

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": TRIAGE_PROMPT},
            {"role": "user", "content": metadata + truncated},
        ],
        response_format={"type": "json_object"},
        max_tokens=500,
    )

    # Record usage
    usage = LLMUsage(
        document_id=doc.id,
        model="gpt-4o-mini",
        stage="triage",
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        estimated_cost_eur=estimate_cost(
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            "gpt-4o-mini",
        ),
    )
    session.add(usage)

    result = json.loads(response.choices[0].message.content)

    doc.triage_categories = result.get("categories", [])
    doc.triage_score = result.get("relevance_score", 0.0)
    doc.triage_reason = result.get("candidate_reason", "")
    doc.status = DocumentStatus.TRIAGED

    session.commit()

    is_env = result.get("is_environmental", False)
    score = doc.triage_score or 0.0
    if is_env and score >= 0.6:
        logger.info("Document %d triaged as environmental (score=%.2f)", document_id, score)
    else:
        logger.info("Document %d triaged as non-environmental (score=%.2f)", document_id, score)

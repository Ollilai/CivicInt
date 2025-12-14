"""Triage pipeline stage - classify documents using LLM."""

import json
from datetime import datetime

from openai import OpenAI

from watchdog.config import get_settings
from watchdog.db.models import (
    Document, 
    File, 
    DocumentStatus, 
    TextStatus, 
    LLMUsage,
    get_session_factory,
)


TRIAGE_SYSTEM_PROMPT = """You are analyzing Finnish municipal environmental documents.

Classify each document into environmental categories and assess relevance.

Categories:
1. zoning - Zoning & land-use (kaava, yleiskaava, osayleiskaava, asemakaava, poikkeaminen)
2. permits - Permits & extraction (maa-aines, ympäristölupa, meluilmoitus, vesitalous)
3. water - Water & wetlands (ojitus, kuivatus, rantarakentaminen, vesistö)
4. industry - Industry & infrastructure (wind, mining, peat, major road projects)

Return a JSON object with:
{
  "categories": ["zoning"],  // array of matching categories
  "relevance_score": 0.85,   // 0.0 to 1.0
  "candidate_reason": "Contains asemakaava proposal for industrial zone",
  "is_environmental": true   // whether this is environment-related
}

Be strict: only mark as environmental if it clearly relates to land, permits, water, or industry.
"""


def truncate_text(text: str, max_chars: int = 8000) -> str:
    """Truncate text to max characters."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... truncated ...]"


def estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    """Estimate cost in EUR (approximate rates)."""
    # gpt-4o-mini rates (per 1M tokens, converted to EUR ~0.92 rate)
    rates = {
        "gpt-4o-mini": {"prompt": 0.15 * 0.92 / 1_000_000, "completion": 0.60 * 0.92 / 1_000_000},
        "gpt-4o": {"prompt": 2.50 * 0.92 / 1_000_000, "completion": 10.00 * 0.92 / 1_000_000},
    }
    rate = rates.get(model, rates["gpt-4o-mini"])
    return prompt_tokens * rate["prompt"] + completion_tokens * rate["completion"]


def triage_document(doc: Document, text: str, client: OpenAI, session) -> dict:
    """Run triage LLM on a document."""
    settings = get_settings()
    
    # Build prompt with metadata
    metadata = f"""Municipality: {doc.source.municipality}
Body: {doc.body or 'Unknown'}
Title: {doc.title}
Date: {doc.meeting_date}
---
"""
    
    # Truncate text to stay within budget
    truncated = truncate_text(text, settings.triage_max_tokens * 3)  # ~3 chars per token
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": metadata + truncated},
        ],
        response_format={"type": "json_object"},
        max_tokens=500,
    )
    
    # Track usage
    usage = LLMUsage(
        document_id=doc.id,
        model="gpt-4o-mini",
        stage="triage",
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        estimated_cost_eur=estimate_cost(
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            "gpt-4o-mini"
        ),
    )
    session.add(usage)
    
    result = json.loads(response.choices[0].message.content)
    return result


def run():
    """Run triage on all extracted documents."""
    settings = get_settings()
    
    if not settings.openai_api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    client = OpenAI(api_key=settings.openai_api_key)
    SessionLocal = get_session_factory()
    
    with SessionLocal() as session:
        # Get documents with extracted text but not yet processed
        docs = session.query(Document).filter(
            Document.status == DocumentStatus.FETCHED,
        ).all()
        
        # Filter to those with extracted text
        docs_with_text = []
        for doc in docs:
            text_files = [f for f in doc.files if f.text_status in (TextStatus.EXTRACTED, TextStatus.OCR_DONE)]
            if text_files:
                # Combine text from all files
                combined_text = "\n\n---\n\n".join(f.text_content for f in text_files if f.text_content)
                if combined_text:
                    docs_with_text.append((doc, combined_text))
        
        if not docs_with_text:
            print("No documents ready for triage.")
            return
        
        print(f"Triaging {len(docs_with_text)} documents...")
        
        candidates = []
        for doc, text in docs_with_text:
            try:
                result = triage_document(doc, text, client, session)
                
                is_env = result.get("is_environmental", False)
                score = result.get("relevance_score", 0)
                categories = result.get("categories", [])
                
                # Store triage result in document metadata (could add a column for this)
                doc.status = DocumentStatus.PROCESSED
                
                if is_env and score >= 0.5:
                    candidates.append({
                        "doc": doc,
                        "text": text,
                        "categories": categories,
                        "score": score,
                        "reason": result.get("candidate_reason", ""),
                    })
                    print(f"  ✓ Candidate: {doc.title[:50]}... ({score:.2f})")
                else:
                    print(f"  - Skip: {doc.title[:50]}... ({score:.2f})")
                
            except Exception as e:
                print(f"  ✗ Error: {doc.title[:50]}... - {e}")
                doc.status = DocumentStatus.ERROR
        
        session.commit()
        
        print(f"\nFound {len(candidates)} candidates for case building.")
        
        # Store candidates for case_builder (could use a queue table)
        return candidates

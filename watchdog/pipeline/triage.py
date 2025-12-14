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


TRIAGE_SYSTEM_PROMPT = """You are a nature conservation watchdog analyzing Finnish municipal documents.

Your job: Flag ONLY decisions that a Green Party environmental activist would act on.

== FLAG THESE (high relevance) ==

EXTRACTION & PERMITS:
- Maa-ainesluvat (gravel, sand, rock extraction permits)
- Ympäristöluvat (environmental permits)
- Poikkeusluvat in sensitive areas (variances near nature)
- Mining applications or expansions (kaivostoiminta)
- Peat extraction (turvetuotanto)

LAND USE & ZONING:
- Kaava changes near: waterways, forests, wetlands, Natura 2000, nature reserves
- Rantakaava (shoreline zoning) - especially new construction
- Industrial zoning in previously undeveloped areas
- Rezoning forest/agricultural land for development

ENERGY & INFRASTRUCTURE:
- Wind farm permits and assessments (tuulivoima)
- Solar farm applications (aurinkovoima)
- Major road/rail projects through natural areas
- Power line routes

FORESTRY & WATER:
- Forestry decisions on municipal land (kunnan metsät)
- Ojitus (ditching/drainage) affecting wetlands
- Vesistö modifications, dam permits
- Anything mentioning ELY-keskus environmental statements (ELY-lausunto)

== IGNORE THESE (score 0) ==

- Committee reorganizations, mergers, appointments
- School policies, library fees, daycare
- Elderly care, social services, healthcare
- HR decisions, salary matters, personnel
- Generic budget approvals (unless environment-specific line items)
- Building permits for ordinary residential (unless shoreline/sensitive area)
- Internal governance, meeting schedules
- Culture, sports, youth services

== OUTPUT FORMAT ==

Return JSON:
{
  "dominated": true/false,    // Is this document DOMINATED by environmental content?
  "categories": ["extraction", "zoning", "energy", "forestry", "water"],
  "relevance_score": 0.0-1.0, // 0.8+ = definitely actionable, 0.5-0.8 = maybe worth watching
  "signal_reason": "Specific environmental decision found: ...",
  "noise_indicators": ["Also contains unrelated items like..."]
}

CRITICAL: Be aggressive about filtering. A document mentioning "ympäristö" in passing
about committee structure is NOT environmental. Look for actual permits, actual land
decisions, actual extraction applications. When in doubt, score LOW.
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

                is_dominated = result.get("dominated", False)
                score = result.get("relevance_score", 0)
                categories = result.get("categories", [])

                # Store triage result in document metadata (could add a column for this)
                doc.status = DocumentStatus.PROCESSED

                # Higher threshold: must be dominated by env content AND score >= 0.6
                if is_dominated and score >= 0.6:
                    candidates.append({
                        "doc": doc,
                        "text": text,
                        "categories": categories,
                        "score": score,
                        "reason": result.get("signal_reason", ""),
                    })
                    print(f"  ✓ SIGNAL: {doc.title[:50]}... ({score:.2f})")
                elif score >= 0.4:
                    print(f"  ~ Maybe: {doc.title[:50]}... ({score:.2f}) - {result.get('signal_reason', '')[:60]}")
                else:
                    print(f"  - Noise: {doc.title[:50]}... ({score:.2f})")
                
            except Exception as e:
                print(f"  ✗ Error: {doc.title[:50]}... - {e}")
                doc.status = DocumentStatus.ERROR
        
        session.commit()
        
        print(f"\nFound {len(candidates)} candidates for case building.")
        
        # Store candidates for case_builder (could use a queue table)
        return candidates

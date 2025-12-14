"""Case builder pipeline stage - create Cases from triaged documents."""

import json
from datetime import datetime
from typing import Optional

from openai import OpenAI

from watchdog.config import get_settings
from watchdog.db.models import (
    Document,
    File,
    Case,
    CaseEvent,
    Evidence,
    LLMUsage,
    CaseStatus,
    Confidence,
    TextStatus,
    DocumentStatus,
    get_session_factory,
)
from watchdog.pipeline.triage import estimate_cost, truncate_text


CASE_BUILDER_SYSTEM_PROMPT = """You are creating actionable environmental intelligence for Green Party activists in Finland.

Your output will be used by people who:
- File appeals against harmful permits
- Attend public hearings
- Write opinion pieces
- Coordinate with ELY-keskus
- Alert national environmental orgs

== WHAT MAKES A CASE ACTIONABLE ==

1. DEADLINES: Appeal windows, comment periods, hearing dates
2. LOCATION: Exact area, proximity to Natura 2000, waterways, protected areas
3. SCALE: Hectares, cubic meters, number of turbines, extraction volume
4. DECISION STAGE: Proposal vs approved vs under appeal
5. KEY ACTORS: Applicant company, responsible official, ELY contact

== OUTPUT FORMAT ==

Return JSON:
{
  "headline": "Gravel extraction permit (50,000m³) proposed near Ounasjoki - comment period ends 15.2",
  "debrief": [
    "DEADLINE: Public comment period closes 15.2.2025",
    "LOCATION: 2km from Ounasjoki river, borders municipal forest",
    "SCALE: 50,000 cubic meters over 10 years, 15 hectare site",
    "APPLICANT: Lapin Sora Oy",
    "ELY-lausunto requested but not yet received"
  ],
  "action_type": "comment_period",  // comment_period, appeal_window, hearing, monitoring, info_only
  "deadline": "2025-02-15",  // ISO date of next action deadline, null if none
  "status": "proposed",  // proposed, approved, rejected, appealed, unknown
  "timeline": [
    {"date": "2025-01-10", "event": "Application submitted"},
    {"date": "2025-02-15", "event": "Comment period ends"}
  ],
  "evidence": [
    {"page": 3, "snippet": "Exact Finnish quote...", "key_point": "What this proves"}
  ],
  "entities": {
    "applicant": "Lapin Sora Oy",
    "permit_number": "MAL-2025-42",
    "location": "Kittilä, Ounasjoen itäpuoli",
    "area_hectares": 15,
    "volume_m3": 50000,
    "nearest_protected": "Ounasjoki (2km), Natura FI123456 (5km)"
  },
  "confidence": "high",
  "confidence_reason": "Clear permit application with explicit deadline"
}

== RULES ==

1. HEADLINE: Include the key number (hectares, m³, MW) and any deadline
2. DEBRIEF: Start with deadline/action item, then location, then scale
3. Always look for: valitusaika, muistutusaika, nähtävilläolo, kuulutus
4. Extract exact dates in Finnish format (15.2.2025) and convert to ISO
5. If no actionable deadline exists, action_type = "monitoring" or "info_only"
6. Evidence snippets must be EXACT quotes, not paraphrased
"""


def find_matching_case(doc: Document, entities: dict, session) -> Optional[Case]:
    """Try to find an existing case that matches this document."""
    # Simple matching: same municipality + similar project name/permit
    project_name = entities.get("project_name", "")
    permit_number = entities.get("permit_number", "")
    
    if permit_number:
        # Try exact permit match
        existing = session.query(Case).filter(
            Case.entities_json.contains(permit_number)
        ).first()
        if existing:
            return existing
    
    # Could add more sophisticated matching here
    return None


def build_case(doc: Document, text: str, categories: list[str], client: OpenAI, session) -> Case:
    """Build a case from a document using LLM."""
    settings = get_settings()
    
    # Truncate text
    truncated = truncate_text(text, settings.case_builder_max_tokens * 3)
    
    metadata = f"""Municipality: {doc.source.municipality}
Body: {doc.body or 'Unknown'}
Title: {doc.title}
Date: {doc.meeting_date}
Categories: {', '.join(categories)}
---
"""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": CASE_BUILDER_SYSTEM_PROMPT},
            {"role": "user", "content": metadata + truncated},
        ],
        response_format={"type": "json_object"},
        max_tokens=1500,
    )
    
    # Track usage
    usage = LLMUsage(
        document_id=doc.id,
        model="gpt-4o",
        stage="case_builder",
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        estimated_cost_eur=estimate_cost(
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            "gpt-4o"
        ),
    )
    session.add(usage)
    
    result = json.loads(response.choices[0].message.content)
    
    # Check for existing case
    entities = result.get("entities", {})
    existing_case = find_matching_case(doc, entities, session)
    
    if existing_case:
        # Update existing case
        existing_case.updated_at = datetime.utcnow()
        
        # Add new evidence
        for ev in result.get("evidence", []):
            evidence = Evidence(
                case_id=existing_case.id,
                document_id=doc.id,
                page=ev.get("page"),
                snippet=ev.get("snippet", ""),
                source_url=doc.source_url,
            )
            session.add(evidence)
        
        # Add update event
        event = CaseEvent(
            case_id=existing_case.id,
            event_type="evidence_added",
            event_time=datetime.utcnow(),
            payload_json=json.dumps({"document_id": doc.id}),
        )
        session.add(event)
        
        return existing_case
    
    # Create new case
    confidence = result.get("confidence", "medium")
    if confidence not in ("high", "medium", "low"):
        confidence = "medium"
    
    status = result.get("status", "unknown")
    if status not in ("proposed", "approved", "unknown"):
        status = "unknown"
    
    case = Case(
        primary_category=categories[0] if categories else "unknown",
        headline=result.get("headline", doc.title)[:300],
        summary_md="\n".join(f"- {point}" for point in result.get("debrief", [])),
        status=status,
        confidence=confidence,
        confidence_reason=result.get("confidence_reason"),
        municipalities_json=json.dumps([doc.source.municipality]),
        entities_json=json.dumps(entities),
        locations_json=json.dumps({"location": entities.get("location", "")}),
    )
    session.add(case)
    session.flush()  # Get ID
    
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
        except:
            event_date = None
        
        event = CaseEvent(
            case_id=case.id,
            event_type="timeline",
            event_time=event_date,
            payload_json=json.dumps({"description": item.get("event", "")}),
        )
        session.add(event)
    
    return case


def run():
    """Build cases from processed documents."""
    settings = get_settings()
    
    if not settings.openai_api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    client = OpenAI(api_key=settings.openai_api_key)
    SessionLocal = get_session_factory()
    
    with SessionLocal() as session:
        # Get processed documents that don't have evidence yet
        # (Simple heuristic - could track more explicitly)
        processed_docs = session.query(Document).filter(
            Document.status == DocumentStatus.PROCESSED,
        ).all()
        
        # Filter to those with text and not yet linked to cases
        candidates = []
        for doc in processed_docs:
            # Check if already has evidence
            existing_evidence = session.query(Evidence).filter_by(document_id=doc.id).first()
            if existing_evidence:
                continue
            
            # Get text
            text_files = [f for f in doc.files if f.text_status in (TextStatus.EXTRACTED, TextStatus.OCR_DONE)]
            if text_files:
                combined_text = "\n\n---\n\n".join(f.text_content for f in text_files if f.text_content)
                if combined_text:
                    # Default categories for now (should come from triage)
                    candidates.append((doc, combined_text, ["unknown"]))
        
        if not candidates:
            print("No documents ready for case building.")
            return
        
        print(f"Building cases from {len(candidates)} documents...")
        
        for doc, text, categories in candidates:
            try:
                case = build_case(doc, text, categories, client, session)
                if case.id:  # New case
                    print(f"  ✓ New case: {case.headline[:50]}...")
                else:
                    print(f"  ↻ Updated case: {case.headline[:50]}...")
                
            except Exception as e:
                print(f"  ✗ Error: {doc.title[:50]}... - {e}")
        
        session.commit()
        print("Case building complete.")

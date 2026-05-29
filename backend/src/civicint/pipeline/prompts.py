"""LLM prompts, cost estimation, and text helpers for the pipeline."""

TRIAGE_PROMPT = """You are analyzing Finnish municipal environmental documents.

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

CASE_BUILDER_PROMPT = """\
You are creating environmental case summaries for Finnish advocacy professionals.

Create actionable intelligence from municipal documents. Return JSON:

{
  "headline": "Wind farm permit approved in Muonio",
  "debrief": [
    "Permit granted for 15 wind turbines in northern area",
    "Environmental impact assessment completed",
    "30-day appeal window opened",
    "Construction estimated to begin Q2 2025"
  ],
  "status": "approved",  // proposed, approved, or unknown
  "timeline": [
    {"date": "2025-01-15", "event": "Permit application submitted"},
    {"date": "2025-03-01", "event": "Public notice period ended"}
  ],
  "evidence": [
    {"page": 3, "snippet": "Ympäristölupa myönnetään ehdoin...",
     "key_point": "Permit granted with conditions"}
  ],
  "entities": {
    "project_name": "Tuulivoimapuisto Pohjoinen",
    "permit_number": "YL-2025-123",
    "location": "Muonion pohjoinen alue",
    "area_hectares": 150
  },
  "confidence": "high",  // high, medium, or low
  "confidence_reason": "Explicit permit approval with clear timeline"
}

Rules:
- Headline should be clear and actionable (max 100 chars)
- Debrief: 3-6 key points, most important first
- Only include timeline events explicitly mentioned in text
- Evidence snippets should be exact quotes from source
- Be accurate about status - use "unknown" if unclear
"""


def estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    """Estimate cost in EUR (approximate rates with USD/EUR conversion)."""
    rates = {
        "gpt-4o-mini": {
            "prompt": 0.15 * 0.92 / 1_000_000,
            "completion": 0.60 * 0.92 / 1_000_000,
        },
        "gpt-4o": {
            "prompt": 2.50 * 0.92 / 1_000_000,
            "completion": 10.00 * 0.92 / 1_000_000,
        },
    }
    rate = rates.get(model, rates["gpt-4o-mini"])
    return prompt_tokens * rate["prompt"] + completion_tokens * rate["completion"]


def truncate_text(text: str, max_chars: int) -> str:
    """Truncate text to *max_chars*, appending a marker when trimmed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... truncated ...]"

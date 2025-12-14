# Watchdog MVP Spec (Environmental, Finland)

## 0) Goal

Build a Watchdog application that helps **Finnish environmental professionals** (The Greens, WWF, Suomen luonnonsuojeluliitto, etc.) close local information asymmetry by continuously surfacing **high-signal, evidence-backed "Cases"** from **municipal decision documents** (minutes, agendas, official decisions, attachments).

The user experience is not "read documents" — it's **receive a curated Case** you can immediately act on, then drill down into original sources.

> [!NOTE]
> **MVP Scope:** News/web presence and social media monitoring are out of scope for v1. Focus is exclusively on municipal decision documents.

---

## 1) MVP Scope

### 1.1 Initial geographic scope (Lapland CSV)

Start with **21 Lapland municipalities**, grouped by publishing platform:

| Platform | Municipalities |
|----------|----------------|
| **Dynasty (9)** | Inari, Kemi, Kemijärvi, Kittilä, Pelkosenniemi, Ranua, Savukoski, Simo, Tornio |
| **TWeb/KTweb/Triplancloud (7)** | Keminmaa, Kolari, Pello, Posio, Sodankylä, Tervola, Ylitornio |
| **CloudNC (3)** | Enontekiö, Muonio, Rovaniemi |
| **Plain PDFs (2)** | Salla, Utsjoki |

### 1.2 Content scope (environmental case types)

MVP supports 4 Case buckets:

1. **Zoning & land-use**: kaava, yleiskaava, osayleiskaava, asemakaava, poikkeaminen
2. **Permits & extraction**: maa-aines, ympäristölupa, meluilmoitus, vesitalous
3. **Water & wetlands**: ojitus/kuivatus, rantarakentaminen, river works, stormwater
4. **Industry & infrastructure**: wind, mining, peat, major road projects *when tied to land-use/permits*

### 1.3 Bodies to monitor (default)

Prioritize bodies most likely to contain environmental decisions:

- ympäristölautakunta (and equivalents)
- tekninen lautakunta / kaavoitus / rakennusvalvonta-related bodies
- kaupunginhallitus + valtuusto (only when triage marks as environment-related)

---

## 2) Tech Stack

```
Backend:      Python 3.11+ / FastAPI / SQLite (Postgres-ready)
Frontend:     FastAPI + Jinja2 templates (server-rendered for MVP speed)
Scheduling:   APScheduler (in-process) for MVP
PDF:          pdfplumber (text extraction) + Tesseract (OCR fallback, Finnish)
LLM:          OpenAI API (see §6 for models and budget)
Storage:      Local filesystem (./data/files/)
```

**Deployment:** Local-first development. Cloud deployment (AWS/GCP) planned for later.

---

## 3) Scalable Architecture (309 municipalities-ready)

Key scaling principle: **implement connectors per platform type**, not per municipality.

### 3.1 Layers

1. **Discovery & ingestion** (connectors)
2. **Storage** (SQLite now; Postgres-ready schema)
3. **Processing** (text extraction → triage → Case creation/updates)
4. **Presentation** (UI feed + dossier)
5. **Delivery** (optional daily digest)

### 3.2 Connector interface (single standard)

Each connector returns a list of `DocumentRef` records:

```json
{
  "municipality": "Rovaniemi",
  "platform": "cloudnc",
  "body": "Kaupunginvaltuusto",
  "meeting_date": "2025-12-01",
  "published_at": "2025-12-02T09:15:00Z",
  "doc_type": "minutes",
  "title": "Kokous 1.12.2025",
  "source_url": "https://.../Kokous_1122025",
  "file_urls": ["https://.../download/.../1031890"],
  "external_id": "1031890"
}
```

**Scaling to 309** = add rows to a `sources` table with `(municipality, platform, base_url, connector_config)`.

### 3.3 MVP connectors to implement

- **CloudNC connector**: uses `meetingrss` where available; parses meeting pages for PDF links.
- **Dynasty connector**: uses RSS endpoints when available; otherwise parses listing HTML.
- **TWeb connector**: supports `fileshow?doctype=...&docid=...` and discovery via listing pages.

### 3.4 Rate limiting & politeness policy

> [!IMPORTANT]
> All connectors MUST respect municipal servers.

- **Rate limit:** 1 request/second per domain (default)
- **User-Agent:** `CivicWatchdog/1.0 (contact@example.com)` — identify the service
- **robots.txt:** Log warning if disallowed; proceed only with explicit override
- **Backoff:** Exponential backoff on 429/503 errors (max 3 retries)

---

## 4) Storage (SQLite, designed for Postgres)

Use **SQLite** for MVP. Keep schema Postgres-friendly:
- Avoid SQLite-only features
- Use migrations (Alembic-style) for future Postgres switch

### 4.1 Core tables

**sources**
- `id`, `municipality`, `platform`, `base_url`, `enabled`, `config_json`
- `last_success_at`, `last_error`, `consecutive_failures`

**documents**
- `id`, `source_id`, `external_id`, `doc_type`, `title`, `body`, `meeting_date`, `published_at`
- `source_url`, `discovered_at`, `status` (new/fetched/processed/error)
- `content_hash` (for change detection)

**files**
- `id`, `document_id`, `url`, `file_type` (pdf/attachment), `mime`, `bytes`, `fetched_at`
- `storage_path` (relative: `{source_id}/{file_id}.pdf`)
- `text_status` (pending/extracted/ocr_queued/ocr_done/failed)
- `text_content`

**cases**
- `id`, `primary_category`, `headline`, `summary_md`, `status`, `confidence`, `confidence_reason`
- `municipalities_json`, `entities_json`, `locations_json`
- `first_seen_at`, `updated_at`

**case_events**
- `id`, `case_id`, `event_type`, `event_time`, `payload_json`
  - Examples: `approved`, `published_notice`, `complaint_window`, `next_handling`, `evidence_added`

**evidence**
- `id`, `case_id`, `file_id`, `document_id`, `page`, `snippet`, `source_url`

**users**
- `id`, `org`, `email`, `role`, `magic_token`, `token_expires_at`

**watch_profiles**
- `id`, `user_id`, `scope_json`, `topics_json`, `entities_json`, `min_confidence`, `delivery_prefs_json`

**user_case_actions**
- `id`, `user_id`, `case_id`, `action` (dismissed/starred/noted), `note_text`, `created_at`

**deliveries**
- `id`, `user_id`, `delivered_at`, `channel`, `payload_json`

### 4.2 File storage

MVP uses local filesystem:
```
./data/files/{source_id}/{file_id}.pdf
```

Environment variable `STORAGE_BACKEND` (default: `local`) for future S3 switch.

### 4.3 Deduplication strategy

- **Same `external_id` + different `content_hash`:** Update — store new version, add `case_event`
- **Cross-platform dedup:** Use `meeting_date` + `body` + fuzzy title matching as heuristic

### 4.4 Case merging logic

When new evidence arrives, attempt to match to existing Cases:
- Identical project name / permit number (extracted entities)
- Same municipality + overlapping locations + matching category

If match confidence > 0.8, update existing Case; otherwise create new.

---

## 5) Processing Pipeline

All jobs must be **idempotent and retryable**.

1. **Discover** — run connectors per source; write new `documents` (dedupe by `external_id` + `content_hash`)
2. **Fetch** — download PDFs + attachments → `files`; store in `./data/files/`
3. **Extract** — extract text from PDFs with pdfplumber
4. **OCR fallback** — if extracted text < 100 chars from multi-page PDF, queue for Tesseract OCR (Finnish)
5. **Triage** — classify into 4 buckets; compute relevance score; mark candidates
6. **Case build/update** — create or update Case with headline, debrief, timeline, evidence
7. **Publish** — Cases appear in UI feed; optionally queue for digest

---

## 6) Agent Behavior (LLM)

### 6.1 Deterministic extraction first

Before any LLM calls, extract:
- Municipality, body, meeting date
- List of § items/headings
- Keywords: kaava, lupa, Natura, vesistö, maa-aines, etc.

### 6.2 Two LLM passes

**Pass 1: Triage (cheap/fast)**
- Model: `gpt-4o-mini`
- Input: metadata + headings + first 2000 chars
- Output (JSON):
  - `categories[]`
  - `relevance_score` (0–1)
  - `candidate_reason`

**Pass 2: Case Builder (stronger)**
- Model: `gpt-4o`
- Input: watch profile + relevant text chunks
- Output (strict JSON schema):
  - `headline`
  - `debrief` (3–6 bullets)
  - `status` (proposed/approved/unknown)
  - `timeline[]` — only if supported by text
  - `evidence[]` — page + snippet + source link
  - `confidence` + `confidence_reason`

### 6.3 Cost guardrails

> [!CAUTION]
> **Monthly LLM budget: €10**

- **Token limits:** Max 4K input tokens per triage, 8K per Case build
- **Document cap:** If a document exceeds limits, truncate with `[...]` and note in processing log
- **Fallback:** If LLM API fails, mark document as `llm_error`; surface in admin view
- **Tracking:** Log tokens used per document; admin dashboard shows monthly spend

---

## 7) Error Handling & Observability

### 7.1 Retry policy

- **Connector errors:** Retry 3× with exponential backoff (1s, 4s, 16s)
- **LLM errors:** Retry 2× with 5s delay
- **Permanent failures:** Mark as `error` status; increment `consecutive_failures` on source

### 7.2 Logging

- **Format:** Structured JSON logs
- **Levels:** INFO for normal ops, WARNING for retries, ERROR for failures
- **Fields:** `timestamp`, `source_id`, `document_id`, `stage`, `message`, `error`

### 7.3 Health monitoring

- **CLI command:** `python -m watchdog.cli health` — show connector status, last success, error counts
- **Alert threshold:** If a source has no successful run in 72 hours, flag in admin UI
- **Admin dashboard:** Simple page showing pipeline stats, LLM spend, error queue

---

## 8) Authentication & Access Control

### 8.1 Magic link authentication

MVP uses **passwordless magic link** auth:

1. User enters email on login page
2. System sends email with time-limited link (valid 15 min)
3. Clicking link sets session cookie (valid 7 days)
4. No passwords to manage

### 8.2 Multi-tenancy model

- **Org-based:** Users belong to an organization
- **Shared Cases:** All users in an org see all Cases (no per-user filtering in MVP)
- **Roles:** `admin` (can manage sources, view errors) / `member` (read-only feed)

### 8.3 Session handling

- Session stored in secure HTTP-only cookie
- CSRF protection via double-submit cookie pattern
- Logout invalidates session

---

## 9) UX/UI MVP

### 9.1 The feed is Cases (not raw documents)

**Case card fields:**
- Headline
- Category badge
- Status (proposed/approved/unknown)
- Time signal ("published 3 days ago")
- Confidence (High/Med/Low) + tooltip showing `confidence_reason`
- "Why it matters" (1–2 lines)
- Source badges (municipality + body)
- Actions: Star, Dismiss, Open dossier

### 9.2 Dossier (detail view)

- **Executive debrief** (structured bullets)
- **Timeline** (events with timestamps when available)
- **Evidence pack** (snippets with page numbers + links)
- **Original sources** (meeting page + PDFs + attachments)
- **User notes** (if any)

### 9.3 Filters

- Municipality / region
- Category (4 buckets)
- Status
- Confidence ("High only" toggle)
- Search (headline + entities)
- Show: All / Starred / Dismissed

### 9.4 Admin pages

- **Sources:** List of all sources with health status
- **Errors:** Queue of documents with errors (LLM, fetch, parse)
- **Spend:** Monthly LLM token usage and estimated cost

---

## 10) Delivery

- **Primary:** In-app feed
- **Optional:** Daily email digest (top N cases per user/org)

No real-time push in MVP.

---

## 11) Implementation Notes

- **Adding a municipality = configuration, not code:** Add a `sources` row with platform + base_url + config
- **Connectors:** Keep small and testable; unit tests against saved HTML/RSS fixtures
- **Case JSON schema:** Keep strict; avoid free-form LLM outputs feeding UI directly
- **Raw storage:** Store raw files + extracted text for future re-processing with better models
- **Environment variables:**
  - `DATABASE_URL` — SQLite path (default: `./data/watchdog.db`)
  - `STORAGE_BACKEND` — `local` or `s3`
  - `OPENAI_API_KEY` — required
  - `MAIL_*` — SMTP config for magic links
  - `SECRET_KEY` — for session signing

---

## Appendix: Project Structure

```
watchdog/
├── app/
│   ├── main.py              # FastAPI app
│   ├── api/                  # API routes
│   ├── templates/            # Jinja2 templates
│   ├── static/               # CSS, JS
│   └── auth/                 # Magic link auth
├── connectors/
│   ├── base.py               # Connector interface
│   ├── cloudnc.py
│   ├── dynasty.py
│   └── tweb.py
├── pipeline/
│   ├── discover.py
│   ├── fetch.py
│   ├── extract.py
│   ├── triage.py
│   └── case_builder.py
├── db/
│   ├── models.py             # SQLAlchemy models
│   └── migrations/
├── cli.py                    # Admin CLI
├── scheduler.py              # APScheduler config
├── data/                     # Local storage
│   ├── watchdog.db
│   └── files/
└── tests/
    └── fixtures/             # Saved HTML/RSS for testing
```

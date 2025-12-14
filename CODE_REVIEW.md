# Code Review: CivicInt/Watchdog MVP

**Review Date:** 2025-12-14
**Reviewer:** Claude Code
**Repository:** CivicInt

## Overview

This is an environmental document watchdog system for monitoring Finnish municipal decisions. The codebase is well-structured with clear separation of concerns between connectors, pipeline stages, and the web application. Overall code quality is good, but there are several security and quality issues to address.

---

## 🔴 Critical Security Issues

### 1. SSRF Vulnerability in Fetch Pipeline

**Location:** `watchdog/pipeline/fetch.py:14-32`

The `download_file` function bypasses SSRF protection:

```python
async def download_file(url: str, storage_path: Path, user_agent: str) -> tuple[int, str]:
    async with httpx.AsyncClient(headers={"User-Agent": user_agent}) as client:
        response = await client.get(url, follow_redirects=True, timeout=60.0)  # No SSRF check!
```

The base connector has `is_safe_url()` validation, but `download_file` doesn't use it. An attacker who controls a document source could inject internal URLs (e.g., `http://169.254.169.254/` for cloud metadata).

**Recommendation:** Import and use `is_safe_url()` in `download_file()` before making requests.

---

### 2. DNS Rebinding Vulnerability

**Location:** `watchdog/connectors/base.py:65-75`

```python
try:
    ip_str = socket.gethostbyname(parsed.hostname)  # DNS lookup at validation time
    ip = ipaddress.ip_address(ip_str)
```

The IP check happens during validation, but a malicious DNS server could return a safe IP initially, then resolve to an internal IP during the actual HTTP request (DNS rebinding attack).

**Recommendation:** Pin the resolved IP for the request using `httpx` transport customization, or validate the IP in the response.

---

### 3. LLM Prompt Injection Risk

**Location:** `watchdog/pipeline/triage.py:101-106`, `watchdog/pipeline/case_builder.py:118-124`

Document content is directly interpolated into LLM prompts:

```python
metadata = f"""Municipality: {doc.source.municipality}
Body: {doc.body or 'Unknown'}
Title: {doc.title}
---
"""
# truncated document text appended directly
```

Malicious content in municipal documents could manipulate LLM behavior (e.g., "Ignore all previous instructions...").

**Recommendation:** Consider structured prompting with clear delimiters, input sanitization, or use system/user message separation more defensively.

---

## 🟠 Medium Security Issues

### 4. No Rate Limiting on Authentication

**Location:** `watchdog/app/main.py:65-90`

The `verify_admin_token` function has no rate limiting on failed attempts:

```python
if not secrets.compare_digest(token, settings.admin_token):
    raise HTTPException(status_code=403, detail="Invalid admin token.")
```

While timing-attack resistant, this is vulnerable to brute-force attacks.

**Recommendation:** Add rate limiting middleware or track failed attempts per IP.

---

### 5. Missing Content-Type Validation

**Location:** `watchdog/pipeline/fetch.py:18-31`

Downloaded files are saved without verifying they're actually PDFs:

```python
content = response.content
storage_path.write_bytes(content)  # Could be any content type
```

**Recommendation:** Check `Content-Type` header and/or validate file magic bytes before saving.

---

## 🟡 Code Quality Issues

### 6. Deprecated `datetime.utcnow()`

**Location:** Multiple files including `watchdog/db/models.py:88-89`, `watchdog/pipeline/*.py`

```python
created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

`datetime.utcnow()` is deprecated in Python 3.12+.

**Recommendation:** Use `datetime.now(timezone.utc)` instead.

---

### 7. Enums as Plain Classes

**Location:** `watchdog/db/models.py:29-65`

```python
class DocumentStatus:
    NEW = "new"
    FETCHED = "fetched"
    # ...
```

These should be Python `Enum` types for type safety:

```python
from enum import Enum

class DocumentStatus(str, Enum):
    NEW = "new"
    FETCHED = "fetched"
    # ...
```

---

### 8. Inefficient Async Pattern

**Location:** `watchdog/pipeline/discover.py:114-118`

```python
for source in sources:
    new_count = asyncio.run(process_source(source, session))  # Sequential!
```

Each source is processed sequentially with a new event loop. This loses the async benefits.

**Recommendation:** Use `asyncio.gather()` to process sources concurrently:

```python
async def run_async():
    tasks = [process_source(source, session) for source in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

---

### 9. Bare Exception Handling

**Location:** Multiple files including `watchdog/pipeline/case_builder.py:219-222`

```python
try:
    event_date = datetime.fromisoformat(item.get("date", ""))
except:  # Bare except catches everything including KeyboardInterrupt
    event_date = None
```

**Recommendation:** Use specific exception types:

```python
except (ValueError, TypeError):
    event_date = None
```

---

### 10. Global Mutable State

**Location:** `watchdog/scheduler.py:107-115`

```python
_scheduler = None  # Global mutable state

def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = create_scheduler()
    return _scheduler
```

This pattern is problematic for testing and multi-process deployments.

**Recommendation:** Use dependency injection or a proper singleton pattern.

---

## 🔵 Architectural Suggestions

### 11. Missing Database Indexes

**Location:** `watchdog/db/models.py`

Frequently queried columns lack indexes:

```python
status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.NEW)
# Should add: index=True
```

**Recommendation:** Add indexes on `Document.status`, `Document.source_id`, `File.text_status`, `Case.primary_category`.

---

### 12. No Database Migrations

The codebase uses `Base.metadata.create_all()` without Alembic. Schema changes in production will be problematic.

**Recommendation:** Integrate Alembic for database migrations.

---

### 13. Triage Results Not Persisted

**Location:** `watchdog/pipeline/triage.py:212-213`

```python
# Store candidates for case_builder (could use a queue table)
return candidates
```

The comment acknowledges the issue - candidates are returned but not persisted between stages. If case_builder isn't run immediately, work is lost.

**Recommendation:** Use the existing database to queue candidates, or add a dedicated queue table.

---

### 14. Hardcoded Model Names

**Location:** `watchdog/pipeline/triage.py:112`, `watchdog/pipeline/case_builder.py:127`

```python
model="gpt-4o-mini",
model="gpt-4o",
```

**Recommendation:** Move to configuration:

```python
# config.py
triage_model: str = "gpt-4o-mini"
case_builder_model: str = "gpt-4o"
```

---

## ✅ Good Practices Observed

1. **Constant-time token comparison** (`app/main.py:87`) - prevents timing attacks
2. **Path traversal protection** (`pipeline/extract.py:9-32`) - `safe_path_join()` is well-implemented
3. **SSRF protection in base connector** (`connectors/base.py:32-80`) - good IP range blocking
4. **Production security validation** (`config.py:63-73`) - prevents insecure defaults
5. **Rate limiting per domain** (`connectors/base.py:105-124`) - polite scraping
6. **LLM budget tracking** (`db/models.py:324-339`) - cost awareness
7. **Clean separation of concerns** - connectors, pipeline, app layers are well-organized

---

## Summary

| Severity | Count | Key Issues |
|----------|-------|------------|
| 🔴 Critical | 3 | SSRF bypass, DNS rebinding, prompt injection |
| 🟠 Medium | 2 | No rate limiting, missing content validation |
| 🟡 Quality | 5 | Deprecated APIs, bare exceptions, inefficient async |
| 🔵 Architecture | 4 | Missing indexes, no migrations, hardcoded values |

The codebase demonstrates good security awareness but has gaps in consistent application of those principles. The critical issues should be addressed before production deployment.

---

## Next Steps (Priority Order)

1. Fix SSRF bypass in `fetch.py` by adding URL validation
2. Address DNS rebinding in base connector
3. Add rate limiting to admin authentication
4. Migrate from `datetime.utcnow()` to timezone-aware datetimes
5. Convert status classes to proper Enums
6. Add database indexes for performance
7. Integrate Alembic for migrations

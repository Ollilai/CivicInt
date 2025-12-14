# Lapland Data Collection Plan: Adding Missing Municipalities

## Executive Summary

CivicInt currently collects data from **19 of 21** Lapland municipalities. Two municipalities remain disabled:

| Municipality | Platform | Status | Issue |
|-------------|----------|--------|-------|
| **Salla** | pdf | Disabled | No connector implementation |
| **Utsjoki** | pdf | Disabled | No connector implementation |

These municipalities don't use standard decision platforms (Dynasty, CloudNC, TWeb). Instead, they publish PDFs directly on their WordPress-based municipal websites.

---

## Problem Analysis

### Current Architecture

The discovery pipeline (`watchdog/pipeline/discover.py:20-24`) has a connector map:

```python
connector_map = {
    "cloudnc": CloudNCConnector,
    "dynasty": DynastyConnector,
    "tweb": TWebConnector,
    # "pdf" IS MISSING - causes ValueError if enabled
}
```

When a source has `platform="pdf"`, the system crashes with:
```
ValueError: Unknown platform: pdf
```

### Target Sites

**Salla:**
- Decision page: `https://www.salla.fi/hallinto-ja-paatoksenteko/esityslistat-ja-poytakirjat/`
- Officer decisions: `https://www.salla.fi/hallinto-ja-paatoksenteko/viranhaltijapaatokset/`
- Site type: WordPress

**Utsjoki:**
- Decision page: `https://www.utsjoki.fi/hallinto/esityslistat-ja-poytakirjat/`
- Officer decisions: `https://www.utsjoki.fi/hallinto/viranhaltijapaatokset/`
- Site type: WordPress

### Challenge

Both sites return **403 Forbidden** for automated requests, meaning:
1. They likely have bot protection (Cloudflare, WordPress security plugin)
2. Standard HTTP client requests are blocked
3. May require browser-like headers or session handling

---

## Implementation Options

### Option A: WordPress/Generic HTML Connector (Recommended)

Create a new connector specifically for municipal websites that publish PDFs without a standard platform.

**Pros:**
- Reusable for any municipality with similar setup
- Clean architecture following existing patterns
- Configurable per-municipality via `config_json`

**Cons:**
- Must handle 403 blocking (may need headers/cookies)
- Site structure may vary between municipalities

**Implementation Steps:**

1. **Create `watchdog/connectors/municipal_website.py`**
   - Inherit from `BaseConnector`
   - Accept configuration for listing page paths
   - Support multiple discovery strategies
   - Handle WordPress-specific patterns

2. **Add to connector map** in `discover.py`:
   ```python
   connector_map = {
       "cloudnc": CloudNCConnector,
       "dynasty": DynastyConnector,
       "tweb": TWebConnector,
       "municipal_website": MunicipalWebsiteConnector,
   }
   ```

3. **Update database sources** for Salla and Utsjoki:
   ```sql
   UPDATE sources SET
     platform = 'municipal_website',
     enabled = TRUE,
     config_json = '{
       "listing_paths": ["/hallinto-ja-paatoksenteko/esityslistat-ja-poytakirjat/"],
       "municipality": "Salla"
     }'
   WHERE municipality = 'Salla';
   ```

### Option B: Enhanced HTTP Client with Browser Emulation

Add browser-like capabilities to bypass 403 blocks.

**Implementation:**
- Use `httpx` with realistic headers (Accept, Accept-Language, etc.)
- Add `Referer` header matching the site
- Consider rotating User-Agent strings
- Implement session handling for cookies

### Option C: Playwright/Selenium Integration

Use headless browser for JavaScript-heavy sites.

**Pros:**
- Can handle any site, including those requiring JavaScript
- Bypasses most bot detection

**Cons:**
- Heavy dependency (Chromium binary)
- Slower execution
- More resource intensive
- May be overkill for WordPress sites

### Option D: Direct PDF URL Configuration

For simplest implementation, manually configure known PDF URLs.

**Pros:**
- Fast to implement
- No complex parsing needed

**Cons:**
- Requires manual updates when new meetings occur
- Not sustainable for ongoing monitoring

---

## Recommended Approach: Option A + B

Combine the generic connector with enhanced HTTP handling.

### Implementation Plan

#### Phase 1: Create Municipal Website Connector

**File: `watchdog/connectors/municipal_website.py`**

```python
"""Generic connector for municipal websites publishing PDFs."""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from watchdog.connectors.base import BaseConnector, DocumentRef


class MunicipalWebsiteConnector(BaseConnector):
    """
    Connector for municipal websites that publish PDFs directly.

    Used by: Salla, Utsjoki (and potentially others)

    Configuration (via config_json):
    - listing_paths: List of paths to scrape for PDF links
    - municipality: Municipality name
    - pdf_pattern: Optional regex for matching PDF URLs
    - body_patterns: Dict mapping keywords to committee names
    """

    @property
    def platform_name(self) -> str:
        return "municipal_website"

    async def _get_client(self):
        """Get HTTP client with browser-like headers."""
        import httpx

        if self._client is None:
            # Enhanced headers to bypass basic bot detection
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "fi-FI,fi;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    async def discover(self) -> list[DocumentRef]:
        """Discover PDFs from municipal website."""
        documents = []
        listing_paths = self.config.get("listing_paths", ["/"])

        for path in listing_paths:
            listing_url = urljoin(self.base_url, path)
            try:
                response = await self.fetch(listing_url)
                docs = await self._parse_page(response.text, listing_url)
                documents.extend(docs)
            except Exception as e:
                print(f"Error fetching {listing_url}: {e}")
                continue

        return documents

    async def _parse_page(self, html: str, base_url: str) -> list[DocumentRef]:
        """Parse HTML page for PDF links."""
        documents = []
        soup = BeautifulSoup(html, "lxml")

        # Find all PDF links
        pdf_pattern = self.config.get("pdf_pattern", r"\.pdf")

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")

            # Check if this is a PDF link
            if not re.search(pdf_pattern, href, re.IGNORECASE):
                continue

            full_url = urljoin(base_url, href)
            link_text = link.get_text(strip=True)

            # Get surrounding context
            parent = link.find_parent(["li", "p", "div", "td"])
            context = parent.get_text(" ", strip=True) if parent else link_text

            doc = DocumentRef(
                municipality=self.config.get("municipality", "Unknown"),
                platform=self.platform_name,
                body=self._extract_body(context),
                meeting_date=self._extract_date(context),
                published_at=None,
                doc_type=self._extract_doc_type(context),
                title=link_text or context[:100],
                source_url=full_url,
                file_urls=[full_url],
            )
            documents.append(doc)

        return documents

    def _extract_body(self, text: str) -> str:
        """Extract committee/body name from text."""
        default_patterns = {
            "valtuusto": "Kunnanvaltuusto",
            "hallitus": "Kunnanhallitus",
            "ympäristö": "Ympäristölautakunta",
            "tekninen": "Tekninen lautakunta",
            "rakennus": "Rakennuslautakunta",
            "hyvinvointi": "Hyvinvointilautakunta",
            "sivistys": "Sivistyslautakunta",
            "tarkastus": "Tarkastuslautakunta",
        }

        patterns = self.config.get("body_patterns", default_patterns)
        text_lower = text.lower()

        for key, value in patterns.items():
            if key in text_lower:
                return value

        return "Tuntematon"

    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extract date from text (Finnish format)."""
        patterns = [
            r"(\d{1,2})\.(\d{1,2})\.(\d{4})",  # 13.12.2024
            r"(\d{4})-(\d{2})-(\d{2})",         # 2024-12-13
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                try:
                    if len(groups[0]) == 4:
                        return datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                    else:
                        return datetime(int(groups[2]), int(groups[1]), int(groups[0]))
                except ValueError:
                    pass

        return None

    def _extract_doc_type(self, text: str) -> str:
        """Extract document type."""
        text_lower = text.lower()

        if "esityslista" in text_lower:
            return "agenda"
        elif "pöytäkirja" in text_lower:
            return "minutes"
        elif "päätös" in text_lower:
            return "decision"

        return "minutes"
```

#### Phase 2: Update Discovery Pipeline

**File: `watchdog/pipeline/discover.py`**

Add the new connector to the map:

```python
from watchdog.connectors.municipal_website import MunicipalWebsiteConnector

connector_map = {
    "cloudnc": CloudNCConnector,
    "dynasty": DynastyConnector,
    "tweb": TWebConnector,
    "municipal_website": MunicipalWebsiteConnector,
}
```

#### Phase 3: Update CLI

**File: `watchdog/cli.py`**

Add `municipal_website` to allowed platform choices:

```python
parser_add.add_argument("--platform", "-p", required=True,
                       choices=["cloudnc", "dynasty", "tweb", "municipal_website"])
```

#### Phase 4: Database Configuration

**Add/Update Salla source:**
```bash
watchdog-cli add-source \
  --municipality "Salla" \
  --platform municipal_website \
  --base-url "https://www.salla.fi" \
  --config '{"listing_paths": ["/hallinto-ja-paatoksenteko/esityslistat-ja-poytakirjat/", "/hallinto-ja-paatoksenteko/viranhaltijapaatokset/"], "municipality": "Salla"}'
```

**Add/Update Utsjoki source:**
```bash
watchdog-cli add-source \
  --municipality "Utsjoki" \
  --platform municipal_website \
  --base-url "https://www.utsjoki.fi" \
  --config '{"listing_paths": ["/hallinto/esityslistat-ja-poytakirjat/", "/hallinto/viranhaltijapaatokset/"], "municipality": "Utsjoki"}'
```

#### Phase 5: Handle 403 Responses

If sites still return 403, additional measures:

1. **Add Referer header**: Match the site's own URL
2. **Session handling**: Fetch homepage first to get cookies
3. **Retry with delays**: Some sites rate-limit aggressively
4. **Consider proxy rotation**: For production use

---

## Testing Plan

1. **Unit tests**: Test connector with mock HTML responses
2. **Integration tests**: Test against real sites (manual verification)
3. **Monitoring**: Check admin dashboard for successful fetches

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Sites continue blocking | Medium | High | Try browser emulation, contact municipality |
| Site structure changes | Low | Medium | Configurable selectors, monitoring alerts |
| Rate limiting | Medium | Low | Already have rate limiter, add backoff |
| PDF download issues | Low | Low | Existing fetch pipeline handles this |

---

## Alternative: Contact Municipalities

If technical solutions fail, consider:

1. **Email municipality IT**: Explain the civic transparency project
2. **Request RSS feed**: Many WordPress sites can enable this
3. **Request API access**: Some may have internal APIs
4. **Ask for whitelist**: Get the bot User-Agent whitelisted

---

## Timeline Estimate

| Phase | Tasks | Dependencies |
|-------|-------|-------------|
| Phase 1 | Create connector | None |
| Phase 2 | Update discover.py | Phase 1 |
| Phase 3 | Update CLI | Phase 2 |
| Phase 4 | Configure sources | Phase 3 |
| Phase 5 | Handle 403 (if needed) | Phase 4 |
| Testing | Verify data flow | All phases |

---

## Summary

To complete Lapland coverage:

1. **Create** `municipal_website` connector (~150 lines)
2. **Register** it in the connector map
3. **Configure** Salla and Utsjoki as sources
4. **Test** and monitor for successful data collection
5. **Handle** 403 blocks if they persist

This approach follows existing architectural patterns and provides a reusable solution for any future municipalities with similar setups.

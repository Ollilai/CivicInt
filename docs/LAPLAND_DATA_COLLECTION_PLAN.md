# Lapland Data Collection Plan: Complete Coverage

## Executive Summary

Based on comprehensive manual data collection, here's the complete picture:

| Category | Current | Target | Gap |
|----------|---------|--------|-----|
| Municipalities | 19/21 | 21/21 | Salla, Utsjoki |
| Regional Organizations | 0/3 | 3/3 | Lapin Liitto, ELY-keskus, Hyvinvointialue |
| Document Types | 2 | 5 | +Viranhaltijapäätökset, Kuulutukset, Kaavat |

**Critical Discovery:** Salla actually uses **TWeb**, not PDF! The original configuration was wrong.

---

## Current vs. Actual Platform Analysis

### Salla - EASY FIX (Wrong Platform Configuration)

| Field | Current | Correct |
|-------|---------|---------|
| Platform | `pdf` | `tweb` |
| Base URL | salla.fi | `http://salla.tweb.fi` |

**Actual TWeb URLs:**
- Esityslistat: `http://salla.tweb.fi/ktwebbin/dbisa.dll/ktwebscr/epj_tek_tweb.htm`
- Pöytäkirjat: `http://salla.tweb.fi/ktwebbin/dbisa.dll/ktwebscr/pk_tek_tweb.htm`
- Viranhaltijapäätökset: `http://salla.tweb.fi/ktwebbin/dbisa.dll/ktwebscr/vparhaku_tweb.htm`
- Kuulutukset: `http://salla.tweb.fi/ktwebbin/dbisa.dll/ktwebscr/kuullist_tweb.htm`

**Fix:** Update database source configuration - no code changes needed!

### Utsjoki - Needs New Connector

Utsjoki is the **only** municipality that genuinely uses WordPress for document publishing:
- Esityslistat/Pöytäkirjat: `https://www.utsjoki.fi/kunta-ja-paatoksenteko/paatoksenteko/esityslistat-ja-poytakirjat/`
- Viranhaltijapäätökset: `https://www.utsjoki.fi/kunta-ja-paatoksenteko/paatoksenteko/viranhaltijapaatokset/`
- Kuulutukset: None available

**Fix:** Create `MunicipalWebsiteConnector` for WordPress sites.

---

## New Regional Organizations to Add

### 1. Lapin Liitto (Regional Council) - Dynasty

| Document Type | URL |
|---------------|-----|
| Esityslistat | `https://lapinliittod10.oncloudos.com/cgi/DREQUEST.PHP?page=meeting_handlers&id=` |
| Pöytäkirjat | `https://lapinliittod10.oncloudos.com/cgi/DREQUEST.PHP?page=meeting_handlers&id=` |
| Viranhaltijapäätökset | `https://lapinliittod10.oncloudos.com/cgi/DREQUEST.PHP?page=official_handlers&id=` |
| Kuulutukset | `https://www.lapinliitto.fi/arkisto/ajankohtaista/kuulutus/` (WordPress) |

**Platform:** Dynasty (existing connector works)

### 2. Lapin ELY-keskus (Regional Authority) - Special

| Document Type | URL |
|---------------|-----|
| Kuulutukset | `https://www.ely-keskus.fi/-/lap-kuulutukset` |

**Platform:** WordPress/custom (limited scope - only announcements)

### 3. Lapin Hyvinvointialue (Wellbeing Services) - TWeb

| Document Type | URL |
|---------------|-----|
| Esityslistat | `https://lapha-julkaisu.tweb.fi/ktwebscr/epj_tek_tweb.htm` |
| Pöytäkirjat | `https://lapha-julkaisu.tweb.fi/ktwebscr/pk_tek_tweb.htm` |
| Viranhaltijapäätökset | `https://lapha-julkaisu.tweb.fi/ktwebscr/vparhaku_tweb.htm` |
| Kuulutukset | `https://lapha-julkaisu.tweb.fi/ktwebscr/kuullist_tweb.htm` |

**Platform:** TWeb (existing connector works)

---

## Complete Platform Distribution

| Platform | Count | Organizations |
|----------|-------|---------------|
| **CloudNC** | 3 | Enontekiö, Muonio, Rovaniemi |
| **Dynasty** | 10 | Inari, Kemi, Kemijärvi, Kittilä, Pelkosenniemi, Ranua, Savukoski, Simo, Tornio, **Lapin Liitto** |
| **TWeb** | 10 | Keminmaa, Kolari, Pello, Posio, Sodankylä, Tervola, Ylitornio, **Salla**, **Lapin Hyvinvointialue** |
| **WordPress** | 2 | **Utsjoki**, **Lapin ELY-keskus** (limited) |

---

## Document Types Overview

| Type | Finnish | Description | Priority |
|------|---------|-------------|----------|
| Esityslistat | Agendas | Upcoming meeting items | High |
| Pöytäkirjat | Minutes | Decisions made | High |
| Viranhaltijapäätökset | Officer Decisions | Administrative decisions | High |
| Kuulutukset | Announcements | Public notices, permits | High |
| Kaavat | Zoning Plans | Land use planning | Medium |

---

## Implementation Plan

### Phase 1: Quick Wins (No Code Changes)

**1.1 Fix Salla Configuration**
```sql
UPDATE sources
SET platform = 'tweb',
    base_url = 'http://salla.tweb.fi',
    enabled = TRUE,
    config_json = '{"municipality": "Salla", "listing_paths": ["/ktwebbin/dbisa.dll/ktwebscr/pk_tek_tweb.htm"]}'
WHERE municipality = 'Salla';
```

Or via CLI:
```bash
# Delete old source and add correct one
watchdog-cli add-source \
  --municipality "Salla" \
  --platform tweb \
  --base-url "http://salla.tweb.fi"
```

**1.2 Add Lapin Hyvinvointialue (TWeb)**
```bash
watchdog-cli add-source \
  --municipality "Lapin hyvinvointialue" \
  --platform tweb \
  --base-url "https://lapha-julkaisu.tweb.fi"
```

**1.3 Add Lapin Liitto (Dynasty)**
```bash
watchdog-cli add-source \
  --municipality "Lapin Liitto" \
  --platform dynasty \
  --base-url "https://lapinliittod10.oncloudos.com"
```

### Phase 2: WordPress Connector (For Utsjoki & ELY-keskus)

Create `watchdog/connectors/municipal_website.py`:

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
    Connector for WordPress/custom municipal websites.

    Used by: Utsjoki, Lapin ELY-keskus (kuulutukset only)

    Configuration (via config_json):
    - listing_paths: List of paths to scrape for PDF links
    - municipality: Municipality name
    """

    @property
    def platform_name(self) -> str:
        return "municipal_website"

    async def _get_client(self):
        """Get HTTP client with browser-like headers to bypass bot detection."""
        import httpx

        if self._client is None:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
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

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")

            # Match PDF links
            if not re.search(r"\.pdf", href, re.IGNORECASE):
                continue

            full_url = urljoin(base_url, href)
            link_text = link.get_text(strip=True)

            # Get surrounding context for metadata extraction
            parent = link.find_parent(["li", "p", "div", "td", "article"])
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
        """Extract committee name from text."""
        patterns = {
            "valtuusto": "Kunnanvaltuusto",
            "hallitus": "Kunnanhallitus",
            "ympäristö": "Ympäristölautakunta",
            "tekninen": "Tekninen lautakunta",
            "rakennus": "Rakennuslautakunta",
            "hyvinvointi": "Hyvinvointilautakunta",
            "sivistys": "Sivistyslautakunta",
            "tarkastus": "Tarkastuslautakunta",
        }

        text_lower = text.lower()
        for key, value in patterns.items():
            if key in text_lower:
                return value
        return "Tuntematon"

    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extract Finnish date from text."""
        match = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
        if match:
            try:
                return datetime(int(match.group(3)), int(match.group(2)), int(match.group(1)))
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
        elif "kuulutus" in text_lower:
            return "announcement"
        return "minutes"
```

### Phase 3: Register Connector

**Update `watchdog/pipeline/discover.py`:**

```python
from watchdog.connectors.municipal_website import MunicipalWebsiteConnector

connector_map = {
    "cloudnc": CloudNCConnector,
    "dynasty": DynastyConnector,
    "tweb": TWebConnector,
    "municipal_website": MunicipalWebsiteConnector,  # NEW
}
```

**Update `watchdog/cli.py`:**

```python
parser_add.add_argument("--platform", "-p", required=True,
                       choices=["cloudnc", "dynasty", "tweb", "municipal_website"])
```

### Phase 4: Configure WordPress Sources

**Utsjoki:**
```bash
watchdog-cli add-source \
  --municipality "Utsjoki" \
  --platform municipal_website \
  --base-url "https://www.utsjoki.fi" \
  --config '{"listing_paths": ["/kunta-ja-paatoksenteko/paatoksenteko/esityslistat-ja-poytakirjat/", "/kunta-ja-paatoksenteko/paatoksenteko/viranhaltijapaatokset/"], "municipality": "Utsjoki"}'
```

**Lapin ELY-keskus (kuulutukset only):**
```bash
watchdog-cli add-source \
  --municipality "Lapin ELY-keskus" \
  --platform municipal_website \
  --base-url "https://www.ely-keskus.fi" \
  --config '{"listing_paths": ["/-/lap-kuulutukset"], "municipality": "Lapin ELY-keskus"}'
```

---

## Extended Data Collection (Document Types)

The current system primarily collects from meeting pages. To fully support all document types:

### Current Connector Enhancements Needed

| Connector | Current | Enhancement |
|-----------|---------|-------------|
| CloudNC | Toimielimet | Add `/Viranhaltijat`, `/Kuulutukset` paths |
| Dynasty | meeting_frames | Add `official_frames`, `announcement_search` |
| TWeb | pk_tek_tweb.htm | Add `vparhaku_tweb.htm`, `kuullist_tweb.htm` |

### Suggested Config Structure

Enhance `config_json` to support multiple document type paths:

```json
{
  "municipality": "Keminmaa",
  "paths": {
    "meetings": "/ktwebscr/pk_tek_tweb.htm",
    "agendas": "/ktwebscr/epj_tek_tweb.htm",
    "officer_decisions": "/ktwebscr/vparhaku_tweb.htm",
    "announcements": "/ktwebscr/kuullist_tweb.htm"
  }
}
```

---

## Summary: Action Items

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| 🔴 High | Fix Salla → TWeb | 5 min | +1 municipality |
| 🔴 High | Add Lapin Hyvinvointialue (TWeb) | 5 min | +1 regional org |
| 🔴 High | Add Lapin Liitto (Dynasty) | 5 min | +1 regional org |
| 🟡 Medium | Create WordPress connector | 2-3 hrs | Enables Utsjoki |
| 🟡 Medium | Add Utsjoki (WordPress) | 15 min | +1 municipality |
| 🟡 Medium | Add ELY-keskus (WordPress) | 15 min | +1 regional org |
| 🟢 Low | Enhance connectors for all doc types | 4-6 hrs | +3 document types |

---

## Final Coverage After Implementation

| Organization | Platform | Status |
|--------------|----------|--------|
| Enontekiö | CloudNC | ✅ Working |
| Inari | Dynasty | ✅ Working |
| Kemi | Dynasty | ✅ Working |
| Kemijärvi | Dynasty | ✅ Working |
| Keminmaa | TWeb | ✅ Working |
| Kittilä | Dynasty | ✅ Working |
| Kolari | TWeb | ✅ Working |
| Muonio | CloudNC | ✅ Working |
| Pello | TWeb | ✅ Working |
| Pelkosenniemi | Dynasty | ✅ Working |
| Posio | TWeb | ✅ Working |
| Ranua | Dynasty | ✅ Working |
| Rovaniemi | CloudNC | ✅ Working |
| **Salla** | **TWeb** | 🔧 Fix config |
| Savukoski | Dynasty | ✅ Working |
| Simo | Dynasty | ✅ Working |
| Sodankylä | TWeb | ✅ Working |
| Tervola | TWeb | ✅ Working |
| Tornio | Dynasty | ✅ Working |
| **Utsjoki** | **WordPress** | 🆕 New connector |
| Ylitornio | TWeb | ✅ Working |
| **Lapin Liitto** | **Dynasty** | 🆕 Add source |
| **Lapin ELY-keskus** | **WordPress** | 🆕 New connector |
| **Lapin Hyvinvointialue** | **TWeb** | 🆕 Add source |

**Total: 24 organizations, 100% Lapland coverage**

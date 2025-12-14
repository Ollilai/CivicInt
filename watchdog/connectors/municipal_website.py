"""Generic connector for municipal websites publishing PDFs directly."""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from watchdog.connectors.base import BaseConnector, DocumentRef


class MunicipalWebsiteConnector(BaseConnector):
    """
    Connector for WordPress/custom municipal websites that publish PDFs directly.

    Used by: Utsjoki, Lapin ELY-keskus

    Configuration (via config_json):
    - municipality: Municipality name
    - paths: Dict of document type -> path mappings:
        - meetings: Path to meeting minutes (pöytäkirjat)
        - agendas: Path to agendas (esityslistat)
        - officer_decisions: Path to officer decisions (viranhaltijapäätökset)
        - announcements: Path to announcements (kuulutukset)
    - pdf_pattern: Optional custom regex for matching PDF URLs (default: \.pdf)
    """

    @property
    def platform_name(self) -> str:
        return "municipal_website"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client with browser-like headers to bypass bot detection."""
        if self._client is None:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "fi-FI,fi;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
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

        # Get paths from config
        paths = self.config.get("paths", {})

        # If no structured paths, fall back to listing_paths for backwards compatibility
        if not paths:
            listing_paths = self.config.get("listing_paths", ["/"])
            paths = {"default": path for path in listing_paths}

        # Process each document type path
        for doc_type, path in paths.items():
            if not path:
                continue

            listing_url = urljoin(self.base_url, path)
            try:
                response = await self.fetch(listing_url)
                docs = await self._parse_page(response.text, listing_url, doc_type)
                documents.extend(docs)
            except Exception as e:
                print(f"Error fetching {listing_url}: {e}")
                continue

        return documents

    async def _parse_page(self, html: str, base_url: str, doc_type: str) -> list[DocumentRef]:
        """Parse HTML page for PDF links."""
        documents = []
        soup = BeautifulSoup(html, "lxml")

        # Get custom PDF pattern or use default
        pdf_pattern = self.config.get("pdf_pattern", r"\.pdf")

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")

            # Match PDF links
            if not re.search(pdf_pattern, href, re.IGNORECASE):
                continue

            full_url = urljoin(base_url, href)
            link_text = link.get_text(strip=True)

            # Get surrounding context for metadata extraction
            parent = link.find_parent(["li", "p", "div", "td", "article", "section"])
            context = parent.get_text(" ", strip=True) if parent else link_text

            # Determine document type from path or context
            determined_doc_type = self._determine_doc_type(doc_type, context)

            doc = DocumentRef(
                municipality=self.config.get("municipality", "Unknown"),
                platform=self.platform_name,
                body=self._extract_body(context),
                meeting_date=self._extract_date(context),
                published_at=None,
                doc_type=determined_doc_type,
                title=link_text or context[:100],
                source_url=full_url,
                file_urls=[full_url],
            )
            documents.append(doc)

        return documents

    def _determine_doc_type(self, path_type: str, text: str) -> str:
        """Determine document type from path type or text content."""
        # Map config path keys to document types
        type_map = {
            "meetings": "minutes",
            "agendas": "agenda",
            "officer_decisions": "decision",
            "announcements": "announcement",
        }

        if path_type in type_map:
            return type_map[path_type]

        # Fall back to text analysis
        text_lower = text.lower()
        if "esityslista" in text_lower:
            return "agenda"
        elif "pöytäkirja" in text_lower:
            return "minutes"
        elif "päätös" in text_lower or "viranhaltija" in text_lower:
            return "decision"
        elif "kuulutus" in text_lower:
            return "announcement"

        return "minutes"

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
            "keskusvaali": "Keskusvaalilautakunta",
            "lupalautakunta": "Lupalautakunta",
            "elinvoima": "Elinvoimalautakunta",
        }

        text_lower = text.lower()
        for key, value in patterns.items():
            if key in text_lower:
                return value
        return "Tuntematon"

    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extract Finnish date from text."""
        # Try Finnish format first (dd.mm.yyyy)
        match = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
        if match:
            try:
                return datetime(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            except ValueError:
                pass

        # Try ISO format (yyyy-mm-dd)
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
        if match:
            try:
                return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            except ValueError:
                pass

        return None

"""CloudNC connector for municipal document discovery."""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import feedparser
from bs4 import BeautifulSoup

from watchdog.connectors.base import BaseConnector, DocumentRef


class CloudNCConnector(BaseConnector):
    """
    Connector for CloudNC platform.

    Used by: Enontekiö, Muonio, Rovaniemi

    Configuration (via config_json):
    - municipality: Municipality name
    - paths: Dict of document type -> path mappings:
        - meetings: Path to meetings/minutes (e.g., /fi-FI/Toimielimet)
        - officer_decisions: Path to officer decisions (e.g., /fi-FI/Viranhaltijat)
        - announcements: Path to announcements (e.g., /fi-FI/Kuulutukset)
        - zoning: Path to zoning plans (e.g., /fi-FI/Kaavat)

    Discovery methods:
    1. Config paths (if provided)
    2. RSS feed at /meetingrss (if available)
    3. HTML parsing of meeting listings
    """

    @property
    def platform_name(self) -> str:
        return "cloudnc"

    async def discover(self) -> list[DocumentRef]:
        """Discover documents from CloudNC platform."""
        documents = []

        # Check for configured paths first
        paths = self.config.get("paths", {})

        if paths:
            # Use configured paths for each document type
            for doc_type, path in paths.items():
                if not path:
                    continue
                url = urljoin(self.base_url, path)
                try:
                    response = await self.fetch(url)
                    docs = await self._parse_html(response.text, url, doc_type)
                    documents.extend(docs)
                except Exception as e:
                    print(f"Error fetching {url}: {e}")
                    continue
        else:
            # Fall back to generic discovery
            # Try RSS feed first
            rss_url = urljoin(self.base_url, "/meetingrss")
            try:
                response = await self.fetch(rss_url)
                rss_docs = self._parse_rss(response.text)
                documents.extend(rss_docs)
            except Exception:
                pass

            # If RSS didn't work or returned nothing, try HTML
            if not documents:
                # Try default CloudNC paths
                default_paths = [
                    ("/fi-FI/Toimielimet", "meetings"),
                    ("/fi-FI", "meetings"),
                ]
                for path, doc_type in default_paths:
                    try:
                        url = urljoin(self.base_url, path)
                        response = await self.fetch(url)
                        html_docs = await self._parse_html(response.text, url, doc_type)
                        documents.extend(html_docs)
                        if documents:
                            break
                    except Exception:
                        continue

        return documents

    def _parse_rss(self, rss_content: str) -> list[DocumentRef]:
        """Parse RSS feed for meeting documents."""
        documents = []
        feed = feedparser.parse(rss_content)

        for entry in feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            published = entry.get("published_parsed")

            if published:
                published_dt = datetime(*published[:6])
            else:
                published_dt = None

            body = self._extract_body(title)
            meeting_date = self._extract_date(title) or published_dt

            # Get PDF links from entry
            file_urls = []
            if hasattr(entry, "enclosures"):
                for enc in entry.enclosures:
                    if enc.get("type", "").startswith("application/pdf"):
                        file_urls.append(enc.get("href", ""))

            if link:
                doc = DocumentRef(
                    municipality=self.config.get("municipality", "Unknown"),
                    platform=self.platform_name,
                    body=body,
                    meeting_date=meeting_date,
                    published_at=published_dt,
                    doc_type="minutes",
                    title=title,
                    source_url=link,
                    file_urls=file_urls,
                )
                documents.append(doc)

        return documents

    async def _parse_html(self, html_content: str, base_url: str, doc_type: str = "meetings") -> list[DocumentRef]:
        """Parse HTML listing page for meeting documents."""
        documents = []
        soup = BeautifulSoup(html_content, "lxml")

        # Map config doc_type to internal doc_type
        doc_type_map = {
            "meetings": "minutes",
            "agendas": "agenda",
            "officer_decisions": "decision",
            "announcements": "announcement",
            "zoning": "zoning",
        }
        internal_doc_type = doc_type_map.get(doc_type, "minutes")

        # CloudNC typically has meeting links in a list or table
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)

            # Look for meeting-related links
            keywords = ["kokous", "meeting", "download", "poytakirja", "esityslista",
                       "päätös", "kuulutus", "kaava", "asiakirja"]
            if any(kw in href.lower() or kw in text.lower() for kw in keywords):
                full_url = urljoin(base_url, href)

                # Skip if it's just a navigation link
                if full_url == base_url or "#" in href:
                    continue

                # Try to find PDF links on the meeting page
                file_urls = []
                try:
                    meeting_response = await self.fetch(full_url)
                    meeting_soup = BeautifulSoup(meeting_response.text, "lxml")

                    for pdf_link in meeting_soup.find_all("a", href=re.compile(r"\.pdf|download", re.I)):
                        pdf_href = pdf_link.get("href", "")
                        if pdf_href:
                            file_urls.append(urljoin(full_url, pdf_href))
                except Exception:
                    # If we can't fetch the page, check if the link itself is a PDF
                    if ".pdf" in href.lower():
                        file_urls = [full_url]

                # Only add if we found files or it looks like a document page
                if file_urls or any(kw in href.lower() for kw in ["docid", "document", "file"]):
                    doc = DocumentRef(
                        municipality=self.config.get("municipality", "Unknown"),
                        platform=self.platform_name,
                        body=self._extract_body(text),
                        meeting_date=self._extract_date(text),
                        published_at=None,
                        doc_type=internal_doc_type,
                        title=text or "Document",
                        source_url=full_url,
                        file_urls=file_urls,
                    )
                    documents.append(doc)

        return documents

    def _extract_body(self, text: str) -> str:
        """Extract committee/body name from text."""
        bodies = {
            "kaupunginvaltuusto": "Kaupunginvaltuusto",
            "kunnanvaltuusto": "Kunnanvaltuusto",
            "valtuusto": "Valtuusto",
            "kaupunginhallitus": "Kaupunginhallitus",
            "kunnanhallitus": "Kunnanhallitus",
            "hallitus": "Hallitus",
            "ympäristölautakunta": "Ympäristölautakunta",
            "ympäristö": "Ympäristölautakunta",
            "tekninen lautakunta": "Tekninen lautakunta",
            "tekninen": "Tekninen lautakunta",
            "kaavoituslautakunta": "Kaavoituslautakunta",
            "rakennuslautakunta": "Rakennuslautakunta",
            "rakennus": "Rakennuslautakunta",
            "tarkastuslautakunta": "Tarkastuslautakunta",
            "hyvinvointilautakunta": "Hyvinvointilautakunta",
        }

        text_lower = text.lower()
        for key, value in bodies.items():
            if key in text_lower:
                return value

        return "Tuntematon"

    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extract date from text."""
        patterns = [
            r"(\d{1,2})\.(\d{1,2})\.(\d{4})",  # 1.12.2025
            r"(\d{4})-(\d{2})-(\d{2})",         # 2025-12-01
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                try:
                    if len(groups[0]) == 4:  # ISO format
                        return datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                    else:  # Finnish format
                        return datetime(int(groups[2]), int(groups[1]), int(groups[0]))
                except ValueError:
                    pass

        return None

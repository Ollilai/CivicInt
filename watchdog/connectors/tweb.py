"""TWeb connector for municipal document discovery."""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from watchdog.connectors.base import BaseConnector, DocumentRef


class TWebConnector(BaseConnector):
    """
    Connector for TWeb/KTweb/Triplancloud platforms.

    Used by: Keminmaa, Kolari, Pello, Posio, Salla, Sodankylä, Tervola, Ylitornio,
             Lapin Hyvinvointialue

    Configuration (via config_json):
    - municipality: Municipality name
    - paths: Dict of document type -> path mappings:
        - meetings: Path to minutes (e.g., /ktwebscr/pk_tek_tweb.htm)
        - agendas: Path to agendas (e.g., /ktwebscr/epj_tek_tweb.htm)
        - officer_decisions: Path to officer decisions (e.g., /ktwebscr/vparhaku_tweb.htm)
        - announcements: Path to announcements (e.g., /ktwebscr/kuullist_tweb.htm)

    Discovery methods:
    1. Config paths (if provided)
    2. Direct PDF fetch via fileshow?doctype=...&docid=...
    3. HTML listing page parsing
    """

    @property
    def platform_name(self) -> str:
        return "tweb"

    async def discover(self) -> list[DocumentRef]:
        """Discover documents from TWeb platform."""
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
            # TWeb listing patterns
            listing_paths = [
                ("/ktwebscr/pk_tek_tweb.htm", "meetings"),
                ("/ktwebbin/dbisa.dll/ktwebscr/pk_tek_tweb.htm", "meetings"),
                ("/ktwebscr/epj_tek_tweb.htm", "agendas"),
                ("/ktwebbin/dbisa.dll/ktwebscr/epj_tek_tweb.htm", "agendas"),
                ("/tweb/", "meetings"),
                ("/ktwebbin/", "meetings"),
                ("/pk_tek.htm", "meetings"),
            ]

            for listing_path, doc_type in listing_paths:
                listing_url = urljoin(self.base_url, listing_path)
                try:
                    response = await self.fetch(listing_url)
                    html_docs = await self._parse_html(response.text, listing_url, doc_type)
                    documents.extend(html_docs)
                    if documents:
                        break
                except Exception:
                    continue

        return documents

    async def _parse_html(self, html_content: str, base_url: str, doc_type: str = "meetings") -> list[DocumentRef]:
        """Parse TWeb HTML listing."""
        documents = []
        soup = BeautifulSoup(html_content, "lxml")

        # Map config doc_type to internal doc_type
        doc_type_map = {
            "meetings": "minutes",
            "agendas": "agenda",
            "officer_decisions": "decision",
            "announcements": "announcement",
        }
        internal_doc_type = doc_type_map.get(doc_type, "minutes")

        # TWeb uses tables for listings
        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue

                # Look for links to meetings/documents
                for link in row.find_all("a", href=True):
                    href = link.get("href", "")
                    text = link.get_text(strip=True)

                    # TWeb patterns
                    if any(p in href.lower() for p in ["fileshow", "docid", "kokous", "meeting", "htmtxt"]):
                        full_url = urljoin(base_url, href)

                        # Get row text for context
                        row_text = row.get_text(" ", strip=True)

                        # Determine if this is a PDF link or a page link
                        file_urls = []
                        if "fileshow" in href.lower() or ".pdf" in href.lower():
                            file_urls = [full_url]
                        else:
                            # Try to get PDF from the linked page
                            file_urls = await self._get_pdf_links(full_url)

                        doc = DocumentRef(
                            municipality=self.config.get("municipality", "Unknown"),
                            platform=self.platform_name,
                            body=self._extract_body(row_text),
                            meeting_date=self._extract_date(row_text),
                            published_at=None,
                            doc_type=internal_doc_type,
                            title=text or row_text[:100],
                            source_url=full_url,
                            file_urls=file_urls,
                        )
                        documents.append(doc)

        # Also look for standalone links outside tables
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if "fileshow" in href.lower() and "docid" in href.lower():
                full_url = urljoin(base_url, href)

                # Check if already added
                if any(d.source_url == full_url for d in documents):
                    continue

                doc = DocumentRef(
                    municipality=self.config.get("municipality", "Unknown"),
                    platform=self.platform_name,
                    body=self._extract_body(text),
                    meeting_date=self._extract_date(text),
                    published_at=None,
                    doc_type=internal_doc_type,
                    title=text or "Document",
                    source_url=full_url,
                    file_urls=[full_url],
                )
                documents.append(doc)

        return documents

    async def _get_pdf_links(self, page_url: str) -> list[str]:
        """Extract PDF links from a page."""
        file_urls = []
        try:
            response = await self.fetch(page_url)
            soup = BeautifulSoup(response.text, "lxml")

            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if "fileshow" in href.lower() or ".pdf" in href.lower():
                    file_urls.append(urljoin(page_url, href))
        except Exception:
            pass

        return file_urls

    def _extract_body(self, text: str) -> str:
        """Extract committee/body name."""
        bodies = {
            "valtuusto": "Valtuusto",
            "hallitus": "Hallitus",
            "ympäristö": "Ympäristölautakunta",
            "tekninen": "Tekninen lautakunta",
            "kaavoitus": "Kaavoituslautakunta",
            "rakennus": "Rakennuslautakunta",
            "lupa": "Lupalautakunta",
            "hyvinvointi": "Hyvinvointilautakunta",
            "sivistys": "Sivistyslautakunta",
            "tarkastus": "Tarkastuslautakunta",
            "aluehallitus": "Aluehallitus",
            "aluevaltuusto": "Aluevaltuusto",
        }

        text_lower = text.lower()
        for key, value in bodies.items():
            if key in text_lower:
                return value

        return "Tuntematon"

    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extract date from text."""
        patterns = [
            r"(\d{1,2})\.(\d{1,2})\.(\d{4})",
            r"(\d{4})-(\d{2})-(\d{2})",
            r"(\d{1,2})/(\d{1,2})/(\d{4})",
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

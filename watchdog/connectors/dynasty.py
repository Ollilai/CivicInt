"""Dynasty connector for municipal document discovery."""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, parse_qs, urlparse

import feedparser
from bs4 import BeautifulSoup

from watchdog.connectors.base import BaseConnector, DocumentRef


class DynastyConnector(BaseConnector):
    """
    Connector for Dynasty (Innofactor) platform.

    Used by: Inari, Kemi, Kemijärvi, Kittilä, Pelkosenniemi, Ranua, Savukoski,
             Simo, Tornio, Lapin Liitto

    Configuration (via config_json):
    - municipality: Municipality name
    - paths: Dict of document type -> path mappings:
        - meetings: Path to meetings (e.g., /cgi/DREQUEST.PHP?page=meeting_frames)
        - agendas: Path to agendas (same as meetings for Dynasty)
        - officer_decisions: Path to officer decisions (e.g., /cgi/DREQUEST.PHP?page=official_frames)
        - announcements: Path to announcements (e.g., /cgi/DREQUEST.PHP?alo=1&page=announcement_search&tzo=-120)

    Discovery methods:
    1. Config paths (if provided)
    2. RSS feed (if available)
    3. HTML parsing of kokous/esityslista listings
    """

    @property
    def platform_name(self) -> str:
        return "dynasty"

    async def discover(self) -> list[DocumentRef]:
        """Discover documents from Dynasty platform."""
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
                    # Check if it's RSS
                    if "xml" in response.headers.get("content-type", "") or "<rss" in response.text[:500]:
                        docs = self._parse_rss(response.text, doc_type)
                    else:
                        docs = await self._parse_html(response.text, url, doc_type)
                    documents.extend(docs)
                except Exception as e:
                    print(f"Error fetching {url}: {e}")
                    continue
        else:
            # Fall back to generic discovery
            # Common Dynasty RSS feed paths
            rss_paths = [
                "/cgi/DREQUEST.PHP?page=rss/meetingrss",
                "/d10/kokous/TELIASES.HTM",
                "/rss",
            ]

            # Try RSS feeds
            for rss_path in rss_paths:
                rss_url = urljoin(self.base_url, rss_path)
                try:
                    response = await self.fetch(rss_url)
                    if "xml" in response.headers.get("content-type", "") or "<rss" in response.text[:500]:
                        rss_docs = self._parse_rss(response.text)
                        documents.extend(rss_docs)
                        if documents:
                            break
                except Exception:
                    continue

            # If no RSS success, try HTML listing
            if not documents:
                listing_paths = [
                    ("/cgi/DREQUEST.PHP?page=meeting_frames", "meetings"),
                    ("/cgi/DREQUEST.PHP?page=meeting_handlers&id=", "meetings"),
                    ("/kokous/", "meetings"),
                    ("/esityslista/", "agendas"),
                ]

                for listing_path, doc_type in listing_paths:
                    listing_url = urljoin(self.base_url, listing_path)
                    try:
                        response = await self.fetch(listing_url)
                        if "html" in response.headers.get("content-type", "").lower():
                            html_docs = await self._parse_html(response.text, listing_url, doc_type)
                            documents.extend(html_docs)
                            if documents:
                                break
                    except Exception:
                        continue

        return documents

    def _parse_rss(self, rss_content: str, doc_type: str = "meetings") -> list[DocumentRef]:
        """Parse Dynasty RSS feed."""
        documents = []
        feed = feedparser.parse(rss_content)

        # Map config doc_type to internal doc_type
        doc_type_map = {
            "meetings": "minutes",
            "agendas": "agenda",
            "officer_decisions": "decision",
            "announcements": "announcement",
        }
        internal_doc_type = doc_type_map.get(doc_type, "minutes")

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

            doc = DocumentRef(
                municipality=self.config.get("municipality", "Unknown"),
                platform=self.platform_name,
                body=body,
                meeting_date=meeting_date,
                published_at=published_dt,
                doc_type=internal_doc_type,
                title=title,
                source_url=link,
                file_urls=[],  # Will be populated during fetch
            )
            documents.append(doc)

        return documents

    async def _parse_html(self, html_content: str, base_url: str, doc_type: str = "meetings") -> list[DocumentRef]:
        """Parse Dynasty HTML listing."""
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

        # Dynasty often uses frames - try to find the content frame
        frames = soup.find_all("frame")
        for frame in frames:
            src = frame.get("src", "")
            if src and any(kw in src.lower() for kw in ["kokous", "meeting", "official", "announcement"]):
                frame_url = urljoin(base_url, src)
                try:
                    response = await self.fetch(frame_url)
                    soup = BeautifulSoup(response.text, "lxml")
                    base_url = frame_url
                except Exception:
                    continue

        # Look for meeting links
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)

            # Dynasty meeting URLs often contain specific patterns
            patterns = ["docid=", "kokession", "meeting", "official", "htmtxt", "download"]
            if any(pattern in href.lower() for pattern in patterns):
                full_url = urljoin(base_url, href)

                # Skip navigation links
                if full_url == base_url or href.startswith("#"):
                    continue

                # Try to extract PDF from the meeting page
                file_urls = await self._get_pdf_links(full_url)

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

    async def _get_pdf_links(self, meeting_url: str) -> list[str]:
        """Extract PDF links from a meeting page."""
        file_urls = []
        try:
            response = await self.fetch(meeting_url)
            soup = BeautifulSoup(response.text, "lxml")

            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if ".pdf" in href.lower() or "download" in href.lower() or "fileshow" in href.lower():
                    file_urls.append(urljoin(meeting_url, href))
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
            "maakuntahallitus": "Maakuntahallitus",
            "maakuntavaltuusto": "Maakuntavaltuusto",
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

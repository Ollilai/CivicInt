"""Dynasty connector for municipal document discovery.

Used by: Inari, Kemi, Kemijarvi, Kittila, Pelkosenniemi, Ranua, Savukoski, Simo, Tornio.

Discovery strategy:
1. Multiple RSS feed paths (preferred).
2. HTML meeting listings with frame support (fallback).
"""

import re
from datetime import datetime
from urllib.parse import urljoin

import feedparser
from bs4 import BeautifulSoup

from civicint.connectors.base import BaseConnector, DocumentRef


class DynastyConnector(BaseConnector):
    """Connector for the Dynasty municipal platform."""

    @property
    def platform_name(self) -> str:
        return "dynasty"

    async def discover(self) -> list[DocumentRef]:
        """Discover documents from Dynasty platform."""
        documents: list[DocumentRef] = []

        # Common Dynasty RSS feed paths
        rss_paths = [
            "/cgi/DREQUEST.PHP?page=rss/meetingrss",
            "/d10/kokous/TELIASES.HTM",
            "/rss",
        ]

        for rss_path in rss_paths:
            rss_url = urljoin(self.base_url, rss_path)
            try:
                response = await self.fetch(rss_url)
                content_type = response.headers.get("content-type", "")
                if "xml" in content_type or "<rss" in response.text:
                    rss_docs = self._parse_rss(response.text)
                    documents.extend(rss_docs)
                    if documents:
                        break
            except Exception:
                continue

        # If no RSS success, try HTML listing
        if not documents:
            listing_paths = [
                "/cgi/DREQUEST.PHP?page=meeting_frames",
                "/kokous/",
                "/esityslista/",
            ]

            for listing_path in listing_paths:
                listing_url = urljoin(self.base_url, listing_path)
                try:
                    response = await self.fetch(listing_url)
                    if "html" in response.headers.get("content-type", "").lower():
                        html_docs = await self._parse_html(response.text, listing_url)
                        documents.extend(html_docs)
                        if documents:
                            break
                except Exception:
                    continue

        return documents

    # ------------------------------------------------------------------
    # RSS parsing
    # ------------------------------------------------------------------

    def _parse_rss(self, rss_content: str) -> list[DocumentRef]:
        """Parse Dynasty RSS feed."""
        documents: list[DocumentRef] = []
        feed = feedparser.parse(rss_content)

        for entry in feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            published = entry.get("published_parsed")

            published_dt = datetime(*published[:6]) if published else None

            body = self._extract_body(title)
            meeting_date = self._extract_date(title) or published_dt

            doc = DocumentRef(
                municipality=self.config.get("municipality", "Unknown"),
                platform=self.platform_name,
                body=body,
                meeting_date=meeting_date,
                published_at=published_dt,
                doc_type="minutes",
                title=title,
                source_url=link,
                file_urls=[],  # Populated during fetch stage
            )
            documents.append(doc)

        return documents

    # ------------------------------------------------------------------
    # HTML parsing (fallback)
    # ------------------------------------------------------------------

    async def _parse_html(self, html_content: str, base_url: str) -> list[DocumentRef]:
        """Parse Dynasty HTML listing, following frames if present."""
        documents: list[DocumentRef] = []
        soup = BeautifulSoup(html_content, "lxml")

        # Dynasty often uses frames -- follow the content frame
        frames = soup.find_all("frame")
        for frame in frames:
            src = frame.get("src", "")
            if src and "kokous" in src.lower():
                frame_url = urljoin(base_url, src)
                try:
                    response = await self.fetch(frame_url)
                    soup = BeautifulSoup(response.text, "lxml")
                except Exception:
                    continue

        # Look for meeting links
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)

            if any(p in href.lower() for p in ["docid=", "kokession", "meeting"]):
                full_url = urljoin(base_url, href)
                file_urls = await self._get_pdf_links(full_url)

                doc = DocumentRef(
                    municipality=self.config.get("municipality", "Unknown"),
                    platform=self.platform_name,
                    body=self._extract_body(text),
                    meeting_date=self._extract_date(text),
                    published_at=None,
                    doc_type="minutes",
                    title=text or "Meeting",
                    source_url=full_url,
                    file_urls=file_urls,
                )
                documents.append(doc)

        return documents

    async def _get_pdf_links(self, meeting_url: str) -> list[str]:
        """Extract PDF download links from a meeting page."""
        file_urls: list[str] = []
        try:
            response = await self.fetch(meeting_url)
            soup = BeautifulSoup(response.text, "lxml")

            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if ".pdf" in href.lower() or "download" in href.lower():
                    file_urls.append(urljoin(meeting_url, href))
        except Exception:
            pass

        return file_urls

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_body(text: str) -> str:
        """Extract committee/body name from *text*."""
        bodies = {
            "valtuusto": "Valtuusto",
            "hallitus": "Hallitus",
            "ymparisto": "Ymparistolautakunta",
            "tekninen": "Tekninen lautakunta",
            "kaavoitus": "Kaavoituslautakunta",
            "rakennus": "Rakennuslautakunta",
            "lupa": "Lupalautakunta",
        }

        text_lower = text.lower()
        for key, value in bodies.items():
            if key in text_lower:
                return value

        return "Unknown"

    @staticmethod
    def _extract_date(text: str) -> datetime | None:
        """Extract date from *text* using common Finnish/ISO patterns."""
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
                except (ValueError, IndexError):
                    pass

        return None

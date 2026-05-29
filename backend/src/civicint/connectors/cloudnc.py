"""CloudNC connector for municipal document discovery.

Used by: Enontekio, Muonio, Rovaniemi.

Discovery strategy:
1. RSS feed at ``/meetingrss`` (preferred).
2. HTML parsing of meeting listing pages (fallback).
"""

import re
from datetime import datetime
from urllib.parse import urljoin

import feedparser
from bs4 import BeautifulSoup

from civicint.connectors.base import BaseConnector, DocumentRef


class CloudNCConnector(BaseConnector):
    """Connector for the CloudNC municipal platform."""

    @property
    def platform_name(self) -> str:
        return "cloudnc"

    async def discover(self) -> list[DocumentRef]:
        """Discover documents from CloudNC platform."""
        documents: list[DocumentRef] = []

        # Try RSS feed first
        rss_url = urljoin(self.base_url, "/meetingrss")
        try:
            response = await self.fetch(rss_url)
            rss_docs = self._parse_rss(response.text)
            documents.extend(rss_docs)
        except Exception:
            pass

        # If RSS yielded nothing, fall back to HTML parsing
        if not documents:
            try:
                response = await self.fetch(self.base_url)
                html_docs = await self._parse_html(response.text)
                documents.extend(html_docs)
            except Exception as exc:
                raise Exception(f"CloudNC discovery failed: {exc}") from exc

        return documents

    # ------------------------------------------------------------------
    # RSS parsing
    # ------------------------------------------------------------------

    def _parse_rss(self, rss_content: str) -> list[DocumentRef]:
        """Parse RSS feed for meeting documents."""
        documents: list[DocumentRef] = []
        feed = feedparser.parse(rss_content)

        for entry in feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            published = entry.get("published_parsed")

            published_dt = datetime(*published[:6]) if published else None

            body = self._extract_body(title)
            meeting_date = self._extract_date(title) or published_dt

            # Collect PDF enclosures
            file_urls: list[str] = []
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

    # ------------------------------------------------------------------
    # HTML parsing (fallback)
    # ------------------------------------------------------------------

    async def _parse_html(self, html_content: str) -> list[DocumentRef]:
        """Parse HTML listing page for meeting documents."""
        documents: list[DocumentRef] = []
        soup = BeautifulSoup(html_content, "lxml")

        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)

            # Meeting-related keywords (Finnish / English)
            if any(
                kw in href.lower()
                for kw in ["kokous", "meeting", "download", "poytakirja", "esityslista"]
            ):
                full_url = urljoin(self.base_url, href)

                # Attempt to find PDF links on the meeting page
                file_urls: list[str] = []
                try:
                    meeting_response = await self.fetch(full_url)
                    meeting_soup = BeautifulSoup(meeting_response.text, "lxml")

                    for pdf_link in meeting_soup.find_all(
                        "a", href=re.compile(r"\.pdf|download", re.I)
                    ):
                        pdf_href = pdf_link.get("href", "")
                        if pdf_href:
                            file_urls.append(urljoin(full_url, pdf_href))
                except Exception:
                    pass

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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_body(text: str) -> str:
        """Extract committee/body name from *text*."""
        bodies = [
            "kaupunginvaltuusto",
            "kunnanvaltuusto",
            "valtuusto",
            "kaupunginhallitus",
            "kunnanhallitus",
            "hallitus",
            "ymparistolautakunta",
            "tekninen lautakunta",
            "kaavoituslautakunta",
            "rakennuslautakunta",
        ]

        text_lower = text.lower()
        for body in bodies:
            if body in text_lower:
                return body.title()

        return "Unknown"

    @staticmethod
    def _extract_date(text: str) -> datetime | None:
        """Extract date from *text* using common Finnish/ISO patterns."""
        patterns = [
            r"(\d{1,2})\.(\d{1,2})\.(\d{4})",  # 1.12.2025
            r"(\d{4})-(\d{2})-(\d{2})",  # 2025-12-01
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                try:
                    if len(groups[0]) == 4:  # ISO format
                        return datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                    else:  # Finnish day.month.year
                        return datetime(int(groups[2]), int(groups[1]), int(groups[0]))
                except (ValueError, IndexError):
                    pass

        return None

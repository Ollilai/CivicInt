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
    
    Discovery methods:
    1. RSS feed at /meetingrss (if available)
    2. HTML parsing of meeting listings
    """
    
    @property
    def platform_name(self) -> str:
        return "cloudnc"
    
    async def discover(self) -> list[DocumentRef]:
        """Discover documents from CloudNC platform."""
        documents = []
        
        # Try RSS feed first
        rss_url = urljoin(self.base_url, "/meetingrss")
        try:
            response = await self.fetch(rss_url)
            rss_docs = self._parse_rss(response.text)
            documents.extend(rss_docs)
        except Exception as e:
            # RSS not available, try HTML parsing
            pass
        
        # If RSS didn't work or returned nothing, try HTML
        if not documents:
            try:
                response = await self.fetch(self.base_url)
                html_docs = await self._parse_html(response.text)
                documents.extend(html_docs)
            except Exception as e:
                raise Exception(f"CloudNC discovery failed: {e}")
        
        return documents
    
    def _parse_rss(self, rss_content: str) -> list[DocumentRef]:
        """Parse RSS feed for meeting documents."""
        documents = []
        feed = feedparser.parse(rss_content)
        
        for entry in feed.entries:
            # Extract meeting info from entry
            title = entry.get("title", "")
            link = entry.get("link", "")
            published = entry.get("published_parsed")
            
            if published:
                published_dt = datetime(*published[:6])
            else:
                published_dt = None
            
            # Try to extract body/committee name from title
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
    
    async def _parse_html(self, html_content: str) -> list[DocumentRef]:
        """Parse HTML listing page for meeting documents."""
        documents = []
        soup = BeautifulSoup(html_content, "lxml")
        
        # CloudNC typically has meeting links in a list or table
        # Look for common patterns
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)
            
            # Look for meeting-related links
            if any(kw in href.lower() for kw in ["kokous", "meeting", "download", "poytakirja", "esityslista"]):
                full_url = urljoin(self.base_url, href)
                
                # Try to find PDF links on the meeting page
                file_urls = []
                try:
                    meeting_response = await self.fetch(full_url)
                    meeting_soup = BeautifulSoup(meeting_response.text, "lxml")
                    
                    for pdf_link in meeting_soup.find_all("a", href=re.compile(r"\.pdf|download", re.I)):
                        pdf_href = pdf_link.get("href", "")
                        if pdf_href:
                            file_urls.append(urljoin(full_url, pdf_href))
                except:
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
    
    def _extract_body(self, text: str) -> str:
        """Extract committee/body name from text."""
        # Common Finnish municipal bodies
        bodies = [
            "kaupunginvaltuusto", "kunnanvaltuusto", "valtuusto",
            "kaupunginhallitus", "kunnanhallitus", "hallitus",
            "ympäristölautakunta", "tekninen lautakunta",
            "kaavoituslautakunta", "rakennuslautakunta",
        ]
        
        text_lower = text.lower()
        for body in bodies:
            if body in text_lower:
                return body.replace("ä", "a").title()
        
        return "Unknown"
    
    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extract date from text."""
        # Try common Finnish date formats
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
                except:
                    pass
        
        return None

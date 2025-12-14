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
    Connector for Dynasty platform.
    
    Used by: Inari, Kemi, Kemijärvi, Kittilä, Pelkosenniemi, Ranua, Savukoski, Simo, Tornio
    
    Discovery methods:
    1. RSS feed (if available)
    2. HTML parsing of kokous/esityslista listings
    """
    
    @property
    def platform_name(self) -> str:
        return "dynasty"
    
    async def discover(self) -> list[DocumentRef]:
        """Discover documents from Dynasty platform."""
        documents = []
        
        # Common Dynasty RSS feed paths
        rss_paths = [
            "/cgi/DREQUEST.PHP?page=rss/meetingrss",
            "/d10/kokous/TELIASES.HTM",  # Alternative listing
            "/rss",
        ]
        
        # Try RSS feeds
        for rss_path in rss_paths:
            rss_url = urljoin(self.base_url, rss_path)
            try:
                response = await self.fetch(rss_url)
                if "xml" in response.headers.get("content-type", "") or "<rss" in response.text:
                    rss_docs = self._parse_rss(response.text)
                    documents.extend(rss_docs)
                    if documents:
                        break
            except:
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
                except:
                    continue
        
        return documents
    
    def _parse_rss(self, rss_content: str) -> list[DocumentRef]:
        """Parse Dynasty RSS feed."""
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
            
            doc = DocumentRef(
                municipality=self.config.get("municipality", "Unknown"),
                platform=self.platform_name,
                body=body,
                meeting_date=meeting_date,
                published_at=published_dt,
                doc_type="minutes",
                title=title,
                source_url=link,
                file_urls=[],  # Will be populated during fetch
            )
            documents.append(doc)
        
        return documents
    
    async def _parse_html(self, html_content: str, base_url: str) -> list[DocumentRef]:
        """Parse Dynasty HTML listing."""
        documents = []
        soup = BeautifulSoup(html_content, "lxml")
        
        # Dynasty often uses frames - try to find the content frame
        frames = soup.find_all("frame")
        for frame in frames:
            src = frame.get("src", "")
            if src and "kokous" in src.lower():
                frame_url = urljoin(base_url, src)
                try:
                    response = await self.fetch(frame_url)
                    soup = BeautifulSoup(response.text, "lxml")
                except:
                    continue
        
        # Look for meeting links
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            text = link.get_text(strip=True)
            
            # Dynasty meeting URLs often contain specific patterns
            if any(pattern in href.lower() for pattern in ["docid=", "kokession", "meeting"]):
                full_url = urljoin(base_url, href)
                
                # Try to extract PDF from the meeting page
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
        """Extract PDF links from a meeting page."""
        file_urls = []
        try:
            response = await self.fetch(meeting_url)
            soup = BeautifulSoup(response.text, "lxml")
            
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if ".pdf" in href.lower() or "download" in href.lower():
                    file_urls.append(urljoin(meeting_url, href))
        except:
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
        }
        
        text_lower = text.lower()
        for key, value in bodies.items():
            if key in text_lower:
                return value
        
        return "Unknown"
    
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
                except:
                    pass
        
        return None

"""TWeb connector for municipal document discovery."""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup

from watchdog.connectors.base import BaseConnector, DocumentRef


class TWebConnector(BaseConnector):
    """
    Connector for TWeb/KTweb/Triplancloud platforms.
    
    Used by: Keminmaa, Kolari, Pello, Posio, Sodankylä, Tervola, Ylitornio
    
    Discovery methods:
    1. Direct PDF fetch via fileshow?doctype=...&docid=...
    2. HTML listing page parsing
    """
    
    @property
    def platform_name(self) -> str:
        return "tweb"
    
    async def discover(self) -> list[DocumentRef]:
        """Discover documents from TWeb platform."""
        documents = []
        
        # TWeb listing patterns
        listing_paths = [
            "/ktwebbin/dbisa.dll/ktwebscr/pk_tek_tweb.htm",
            "/tweb/",
            "/ktwebbin/",
            "/pk_tek.htm",
        ]
        
        for listing_path in listing_paths:
            listing_url = urljoin(self.base_url, listing_path)
            try:
                response = await self.fetch(listing_url)
                html_docs = await self._parse_html(response.text, listing_url)
                documents.extend(html_docs)
                if documents:
                    break
            except:
                continue
        
        return documents
    
    async def _parse_html(self, html_content: str, base_url: str) -> list[DocumentRef]:
        """Parse TWeb HTML listing."""
        documents = []
        soup = BeautifulSoup(html_content, "lxml")
        
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
                    if any(p in href.lower() for p in ["fileshow", "docid", "kokous", "meeting"]):
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
                            doc_type="minutes",
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
                    doc_type="minutes",
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
                except:
                    pass
        
        return None

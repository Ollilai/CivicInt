"""Base connector interface with rate limiting and politeness."""

import asyncio
import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import httpx

from watchdog.config import get_settings


@dataclass
class DocumentRef:
    """Reference to a discovered municipal document."""
    
    municipality: str
    platform: str
    body: str  # Committee/board name
    meeting_date: Optional[datetime]
    published_at: Optional[datetime]
    doc_type: str  # minutes, agenda, decision
    title: str
    source_url: str
    file_urls: list[str] = field(default_factory=list)
    external_id: str = ""
    
    def __post_init__(self):
        """Generate external_id if not provided."""
        if not self.external_id:
            # Create a stable ID from URL
            self.external_id = hashlib.sha256(self.source_url.encode()).hexdigest()[:16]


class RateLimiter:
    """Per-domain rate limiter."""
    
    def __init__(self, requests_per_second: float = 1.0):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self._last_request: dict[str, float] = {}
        self._lock = asyncio.Lock()
    
    async def acquire(self, domain: str) -> None:
        """Wait until we can make a request to the given domain."""
        async with self._lock:
            now = time.monotonic()
            last = self._last_request.get(domain, 0)
            wait_time = self.min_interval - (now - last)
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
            self._last_request[domain] = time.monotonic()


class BaseConnector(ABC):
    """Abstract base class for platform connectors."""
    
    def __init__(self, source_id: int, base_url: str, config: Optional[dict] = None):
        self.source_id = source_id
        self.base_url = base_url
        self.config = config or {}
        
        settings = get_settings()
        self.rate_limiter = RateLimiter(settings.connector_rate_limit)
        self.user_agent = settings.connector_user_agent
        
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def domain(self) -> str:
        """Extract domain from base URL."""
        return urlparse(self.base_url).netloc
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": self.user_agent},
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client
    
    async def fetch(self, url: str, retries: int = 3) -> httpx.Response:
        """Fetch URL with rate limiting and retries."""
        domain = urlparse(url).netloc
        await self.rate_limiter.acquire(domain)
        
        client = await self._get_client()
        
        last_error = None
        for attempt in range(retries):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 503):
                    # Rate limited or overloaded, back off exponentially
                    wait = (2 ** attempt) * 2
                    await asyncio.sleep(wait)
                    last_error = e
                else:
                    raise
            except httpx.RequestError as e:
                last_error = e
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        raise last_error or Exception("Max retries exceeded")
    
    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @abstractmethod
    async def discover(self) -> list[DocumentRef]:
        """
        Discover new documents from the source.
        
        Returns a list of DocumentRef objects representing newly discovered documents.
        """
        pass
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform identifier (e.g., 'cloudnc', 'dynasty', 'tweb')."""
        pass

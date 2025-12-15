"""Base connector interface with rate limiting and politeness."""

import asyncio
import hashlib
import ipaddress
import socket
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple
from urllib.parse import urlparse

import httpx

from watchdog.config import get_settings


# SECURITY: Private/internal IP ranges that should never be accessed
_BLOCKED_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("::1/128"),  # IPv6 localhost
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]


def _is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP address is in a blocked range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        for blocked_range in _BLOCKED_IP_RANGES:
            if ip in blocked_range:
                return True
        return False
    except ValueError:
        return True  # Invalid IP is blocked


def resolve_and_validate_url(url: str, allowed_domain: Optional[str] = None) -> Tuple[str, str, int]:
    """
    Resolve URL hostname to IP and validate against blocked ranges.

    SECURITY: Returns the resolved IP so it can be used for the actual request,
    preventing DNS rebinding attacks where a malicious DNS server returns different
    IPs on subsequent lookups.

    Args:
        url: The URL to resolve and validate.
        allowed_domain: If provided, only allow URLs from this domain.

    Returns:
        Tuple of (resolved_ip, hostname, port) for safe URLs.

    Raises:
        ValueError: If URL is unsafe or cannot be resolved.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"SECURITY: Invalid scheme '{parsed.scheme}', only http/https allowed")

    if not parsed.hostname:
        raise ValueError("SECURITY: URL must have a hostname")

    # Check domain restriction if provided
    if allowed_domain and parsed.hostname != allowed_domain:
        if not parsed.hostname.endswith(f".{allowed_domain}"):
            raise ValueError(f"SECURITY: Domain {parsed.hostname} not allowed")

    try:
        resolved_ip = socket.gethostbyname(parsed.hostname)
    except socket.gaierror as e:
        raise ValueError(f"SECURITY: DNS resolution failed for {parsed.hostname}: {e}")

    if _is_ip_blocked(resolved_ip):
        raise ValueError(f"SECURITY: Blocked IP address {resolved_ip} for hostname {parsed.hostname}")

    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    return resolved_ip, parsed.hostname, port


def is_safe_url(url: str, allowed_domain: Optional[str] = None) -> bool:
    """
    Check if a URL is safe to fetch (not targeting internal resources).

    SECURITY: Prevents SSRF by blocking:
    - Non-HTTP(S) schemes
    - Private/internal IP addresses
    - Localhost and link-local addresses

    Args:
        url: The URL to validate.
        allowed_domain: If provided, only allow URLs from this domain.

    Returns:
        True if the URL is safe to fetch, False otherwise.
    """
    try:
        resolve_and_validate_url(url, allowed_domain)
        return True
    except ValueError:
        return False


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
        """Fetch URL with rate limiting and retries.

        SECURITY: Validates URL before request and verifies final URL after redirects
        to prevent SSRF via DNS rebinding or open redirects.
        """
        # SECURITY: Validate initial URL to prevent SSRF attacks
        resolve_and_validate_url(url)  # Raises ValueError if unsafe

        domain = urlparse(url).netloc
        await self.rate_limiter.acquire(domain)

        client = await self._get_client()

        last_error = None
        for attempt in range(retries):
            try:
                response = await client.get(url)

                # SECURITY: Validate final URL after redirects to prevent
                # SSRF via open redirect vulnerabilities
                final_url = str(response.url)
                if final_url != url:
                    try:
                        resolve_and_validate_url(final_url)
                    except ValueError as e:
                        raise ValueError(
                            f"SECURITY: Redirect to unsafe URL blocked. "
                            f"Original: {url}, Final: {final_url}, Reason: {e}"
                        )

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

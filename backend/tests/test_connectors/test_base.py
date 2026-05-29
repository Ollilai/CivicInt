"""Tests for connector base module: is_safe_url, DocumentRef, RateLimiter."""

import time
from unittest.mock import patch

import pytest

from civicint.connectors.base import DocumentRef, RateLimiter, is_safe_url

# ---------------------------------------------------------------
# is_safe_url
# ---------------------------------------------------------------


class TestIsSafeUrl:
    """Validate SSRF protection logic."""

    @patch("civicint.connectors.base.socket.gethostbyname", return_value="93.184.216.34")
    def test_normal_http_url(self, mock_dns):
        assert is_safe_url("http://example.com/page") is True

    @patch("civicint.connectors.base.socket.gethostbyname", return_value="93.184.216.34")
    def test_normal_https_url(self, mock_dns):
        assert is_safe_url("https://example.com/page") is True

    @patch("civicint.connectors.base.socket.gethostbyname", return_value="10.0.0.1")
    def test_rejects_private_10(self, mock_dns):
        assert is_safe_url("http://internal.example.com") is False

    @patch("civicint.connectors.base.socket.gethostbyname", return_value="172.16.5.1")
    def test_rejects_private_172(self, mock_dns):
        assert is_safe_url("http://internal.example.com") is False

    @patch("civicint.connectors.base.socket.gethostbyname", return_value="192.168.1.1")
    def test_rejects_private_192(self, mock_dns):
        assert is_safe_url("http://internal.example.com") is False

    @patch("civicint.connectors.base.socket.gethostbyname", return_value="127.0.0.1")
    def test_rejects_localhost(self, mock_dns):
        assert is_safe_url("http://localhost") is False

    def test_rejects_file_scheme(self):
        assert is_safe_url("file:///etc/passwd") is False

    def test_rejects_ftp_scheme(self):
        assert is_safe_url("ftp://ftp.example.com/pub") is False

    def test_rejects_no_hostname(self):
        assert is_safe_url("http://") is False

    def test_rejects_empty_string(self):
        assert is_safe_url("") is False

    @patch("civicint.connectors.base.socket.gethostbyname", return_value="93.184.216.34")
    def test_allowed_domain_matches(self, mock_dns):
        assert is_safe_url("https://example.com/page", allowed_domain="example.com") is True

    @patch("civicint.connectors.base.socket.gethostbyname", return_value="93.184.216.34")
    def test_allowed_domain_subdomain(self, mock_dns):
        assert (
            is_safe_url("https://sub.example.com/page", allowed_domain="example.com") is True
        )

    @patch("civicint.connectors.base.socket.gethostbyname", return_value="93.184.216.34")
    def test_allowed_domain_rejects_other(self, mock_dns):
        assert is_safe_url("https://evil.com/page", allowed_domain="example.com") is False


# ---------------------------------------------------------------
# DocumentRef
# ---------------------------------------------------------------


class TestDocumentRef:
    """Validate DocumentRef dataclass behaviour."""

    def test_auto_generates_external_id(self):
        doc = DocumentRef(
            municipality="Rovaniemi",
            platform="cloudnc",
            body="Hallitus",
            meeting_date=None,
            published_at=None,
            doc_type="minutes",
            title="Test",
            source_url="https://example.com/doc/123",
        )
        assert doc.external_id != ""
        assert len(doc.external_id) == 16

    def test_preserves_explicit_external_id(self):
        doc = DocumentRef(
            municipality="Rovaniemi",
            platform="cloudnc",
            body="Hallitus",
            meeting_date=None,
            published_at=None,
            doc_type="minutes",
            title="Test",
            source_url="https://example.com/doc/123",
            external_id="custom-id-99",
        )
        assert doc.external_id == "custom-id-99"

    def test_same_url_produces_same_id(self):
        url = "https://example.com/doc/456"
        doc1 = DocumentRef(
            municipality="Inari",
            platform="dynasty",
            body="Valtuusto",
            meeting_date=None,
            published_at=None,
            doc_type="agenda",
            title="A",
            source_url=url,
        )
        doc2 = DocumentRef(
            municipality="Inari",
            platform="dynasty",
            body="Valtuusto",
            meeting_date=None,
            published_at=None,
            doc_type="agenda",
            title="B",
            source_url=url,
        )
        assert doc1.external_id == doc2.external_id


# ---------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------


class TestRateLimiter:
    """Validate per-domain rate limiting."""

    @pytest.mark.asyncio
    async def test_enforces_delay(self):
        limiter = RateLimiter(requests_per_second=10.0)  # 0.1 s interval

        start = time.monotonic()
        await limiter.acquire("example.com")
        await limiter.acquire("example.com")
        elapsed = time.monotonic() - start

        # Should have waited at least ~0.1 s for the second acquire
        assert elapsed >= 0.08  # small tolerance for timing jitter

    @pytest.mark.asyncio
    async def test_different_domains_independent(self):
        limiter = RateLimiter(requests_per_second=5.0)  # 0.2 s interval

        start = time.monotonic()
        await limiter.acquire("a.example.com")
        await limiter.acquire("b.example.com")
        elapsed = time.monotonic() - start

        # Different domains should not block each other
        assert elapsed < 0.15

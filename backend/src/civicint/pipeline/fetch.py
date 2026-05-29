"""Fetch pipeline stage -- download PDFs and attachments."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from civicint.config import get_settings
from civicint.models import Document, DocumentStatus, TextStatus
from civicint.pipeline.extract import safe_path_join

logger = logging.getLogger(__name__)


async def download_file(
    url: str, dest: Path, user_agent: str
) -> tuple[int, str]:
    """Download a file and return ``(size_bytes, sha256_hex)``.

    Args:
        url: Remote URL to fetch.
        dest: Local path to write the downloaded content.
        user_agent: User-Agent header value.

    Returns:
        A tuple of file size in bytes and the SHA-256 hex digest.
    """
    async with httpx.AsyncClient(
        headers={"User-Agent": user_agent}, timeout=60.0, follow_redirects=True
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

        content = response.content
        size = len(content)
        content_hash = hashlib.sha256(content).hexdigest()

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)

        return size, content_hash


async def run_fetch(document_id: int, session: Session) -> None:
    """Fetch all pending files for a document.

    Args:
        document_id: Database ID of the :class:`Document`.
        session: An open SQLAlchemy session.
    """
    settings = get_settings()
    storage_base = Path(settings.storage_path)

    doc = session.get(Document, document_id)
    if doc is None:
        raise ValueError(f"Document {document_id} not found")

    pending_files = [
        f
        for f in doc.files
        if f.text_status == TextStatus.PENDING and f.storage_path is None
    ]

    if not pending_files:
        return

    for file in pending_files:
        relative_path = f"{doc.source_id}/{file.id}.pdf"
        dest = safe_path_join(storage_base, relative_path)

        try:
            size, content_hash = await download_file(
                file.url, dest, settings.connector_user_agent
            )
            file.sha256 = content_hash
            file.storage_path = relative_path
            file.bytes = size
            file.fetched_at = datetime.now(UTC)

            if not doc.content_hash:
                doc.content_hash = content_hash

            logger.info("Fetched file %d for doc %d (%d bytes)", file.id, doc.id, size)

        except Exception:
            file.text_status = TextStatus.FAILED
            logger.exception("Failed to fetch file %d for doc %d", file.id, doc.id)

    # Advance document status if any file was fetched successfully
    fetched_any = any(f.storage_path is not None for f in doc.files)
    if fetched_any and doc.status == DocumentStatus.NEW:
        doc.status = DocumentStatus.FETCHED

    session.commit()

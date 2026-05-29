"""Discovery pipeline stage -- run connectors and find new documents."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from civicint.connectors import get_connector
from civicint.models import Document, DocumentStatus, File, Source, TextStatus

logger = logging.getLogger(__name__)


async def run_discover(source_id: int, session: Session) -> int:
    """Discover new documents for a single source.

    Args:
        source_id: Database ID of the :class:`Source` to scrape.
        session: An open SQLAlchemy session.

    Returns:
        The number of newly created documents.
    """
    source = session.get(Source, source_id)
    if source is None:
        raise ValueError(f"Source {source_id} not found")

    connector = get_connector(
        platform=source.platform,
        source_id=source.id,
        base_url=source.base_url,
        config=source.extra_config,
    )

    new_count = 0
    try:
        doc_refs = await connector.discover()

        for ref in doc_refs:
            # Dedup by (source_id, external_id) unique constraint
            existing = (
                session.query(Document)
                .filter_by(source_id=source.id, external_id=ref.external_id)
                .first()
            )
            if existing:
                continue

            doc = Document(
                source_id=source.id,
                external_id=ref.external_id,
                doc_type=ref.doc_type,
                title=ref.title,
                body=ref.body,
                meeting_date=ref.meeting_date,
                published_at=ref.published_at,
                source_url=ref.source_url,
                status=DocumentStatus.NEW,
            )
            session.add(doc)
            session.flush()

            for file_url in ref.file_urls:
                file = File(
                    document_id=doc.id,
                    url=file_url,
                    file_type="pdf",
                    text_status=TextStatus.PENDING,
                )
                session.add(file)

            new_count += 1

        # Update source health
        source.last_success_at = datetime.now(UTC)
        source.consecutive_failures = 0
        source.last_error = None

    except Exception as e:
        source.consecutive_failures = (source.consecutive_failures or 0) + 1
        source.last_error = str(e)[:2000]
        logger.exception("Error discovering source %s (%s)", source.municipality, source.platform)

    finally:
        await connector.close()

    session.commit()
    return new_count


async def run_discover_all(session: Session) -> int:
    """Discover documents from all enabled sources.

    Returns:
        Total number of newly created documents across all sources.
    """
    sources = session.query(Source).filter_by(enabled=True).all()
    total = 0
    for source in sources:
        logger.info("Discovering: %s (%s)", source.municipality, source.platform)
        count = await run_discover(source.id, session)
        logger.info("  Found %d new documents", count)
        total += count
    return total

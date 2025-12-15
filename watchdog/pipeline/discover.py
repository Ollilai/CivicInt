"""Discovery pipeline stage - run connectors and find new documents."""

import asyncio
from datetime import datetime, timezone
from typing import Tuple

from sqlalchemy.orm import Session

from watchdog.config import get_settings
from watchdog.db.models import Source, Document, File, get_session_factory
from watchdog.connectors.base import DocumentRef


def get_connector(source: Source):
    """Get the appropriate connector for a source."""
    from watchdog.connectors.cloudnc import CloudNCConnector
    from watchdog.connectors.dynasty import DynastyConnector
    from watchdog.connectors.tweb import TWebConnector
    from watchdog.connectors.municipal_website import MunicipalWebsiteConnector

    connector_map = {
        "cloudnc": CloudNCConnector,
        "dynasty": DynastyConnector,
        "tweb": TWebConnector,
        "municipal_website": MunicipalWebsiteConnector,
    }

    connector_class = connector_map.get(source.platform)
    if not connector_class:
        return None  # Unsupported platform, will be skipped

    return connector_class(
        source_id=source.id,
        base_url=source.base_url,
        config=source.config_json,
    )


async def discover_from_source(source: Source) -> Tuple[int, list[DocumentRef], str | None]:
    """
    Discover documents from a source asynchronously.

    Returns:
        Tuple of (source_id, document_refs, error_message or None)
    """
    connector = get_connector(source)
    if connector is None:
        return source.id, [], f"Unsupported platform: {source.platform}"

    try:
        doc_refs = await connector.discover()
        return source.id, doc_refs, None
    except Exception as e:
        return source.id, [], str(e)
    finally:
        await connector.close()


def save_discovered_documents(
    source: Source,
    doc_refs: list[DocumentRef],
    error: str | None,
    session: Session,
) -> int:
    """Save discovered documents to the database and return count of new documents."""
    new_count = 0

    if error:
        source.consecutive_failures += 1
        source.last_error = error
        print(f"  ✗ Error: {error}")
    else:
        for ref in doc_refs:
            # Check if document already exists
            existing = session.query(Document).filter_by(
                source_id=source.id,
                external_id=ref.external_id,
            ).first()

            if existing:
                continue

            # Create new document
            doc = Document(
                source_id=source.id,
                external_id=ref.external_id,
                doc_type=ref.doc_type,
                title=ref.title,
                body=ref.body,
                meeting_date=ref.meeting_date,
                published_at=ref.published_at,
                source_url=ref.source_url,
                status="new",
            )
            session.add(doc)
            session.flush()  # Get the ID

            # Add file references
            for file_url in ref.file_urls:
                file = File(
                    document_id=doc.id,
                    url=file_url,
                    file_type="pdf",
                    text_status="pending",
                )
                session.add(file)

            new_count += 1

        # Update source health
        source.last_success_at = datetime.now(timezone.utc)
        source.consecutive_failures = 0
        source.last_error = None

    return new_count


async def run_discovery_async(sources: list[Source]) -> dict[int, Tuple[list[DocumentRef], str | None]]:
    """Run discovery for all sources concurrently."""
    tasks = [discover_from_source(source) for source in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    result_map: dict[int, Tuple[list[DocumentRef], str | None]] = {}
    for result in results:
        if isinstance(result, Exception):
            # Handle unexpected exceptions
            continue
        source_id, doc_refs, error = result
        result_map[source_id] = (doc_refs, error)

    return result_map


def run():
    """Run discovery for all enabled sources concurrently."""
    SessionLocal = get_session_factory()

    with SessionLocal() as session:
        sources = session.query(Source).filter_by(enabled=True).all()

        if not sources:
            print("No enabled sources found.")
            return

        # Create a mapping for quick lookup
        source_map = {s.id: s for s in sources}

        print(f"Discovering from {len(sources)} sources concurrently...")

        # Run all discoveries concurrently
        results = asyncio.run(run_discovery_async(sources))

        # Save results to database (must be done synchronously with session)
        total_new = 0
        skipped = 0
        for source_id, (doc_refs, error) in results.items():
            source = source_map[source_id]
            print(f"  {source.municipality} ({source.platform}):", end=" ")

            # Track skipped unsupported platforms
            if error and "Unsupported platform" in error:
                print(f"⊘ skipped (unsupported)")
                skipped += 1
                continue

            new_count = save_discovered_documents(source, doc_refs, error, session)
            if not error:
                print(f"✓ {new_count} new documents")
            total_new += new_count

        session.commit()
        print(f"\nTotal new documents: {total_new}" + (f" ({skipped} sources skipped)" if skipped else ""))

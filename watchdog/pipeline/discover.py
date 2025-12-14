"""Discovery pipeline stage - run connectors and find new documents."""

import asyncio
import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from watchdog.config import get_settings
from watchdog.db.models import Source, Document, File, get_session_factory
from watchdog.connectors.base import DocumentRef


def get_connector(source: Source):
    """Get the appropriate connector for a source."""
    from watchdog.connectors.cloudnc import CloudNCConnector
    from watchdog.connectors.dynasty import DynastyConnector
    from watchdog.connectors.tweb import TWebConnector
    
    connector_map = {
        "cloudnc": CloudNCConnector,
        "dynasty": DynastyConnector,
        "tweb": TWebConnector,
    }
    
    connector_class = connector_map.get(source.platform)
    if not connector_class:
        return None  # Unsupported platform, will be skipped
    
    return connector_class(
        source_id=source.id,
        base_url=source.base_url,
        config=source.config_json,
    )


async def process_source(source: Source, session: Session) -> int:
    """Process a single source and return count of new documents."""
    connector = get_connector(source)
    if connector is None:
        return 0  # Skip unsupported platforms
    new_count = 0
    
    try:
        doc_refs = await connector.discover()
        
        for ref in doc_refs:
            # Check if document already exists
            existing = session.query(Document).filter_by(
                source_id=source.id,
                external_id=ref.external_id,
            ).first()
            
            if existing:
                # Check for updates via content hash later (during fetch)
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
        source.last_success_at = datetime.utcnow()
        source.consecutive_failures = 0
        source.last_error = None
        
    except Exception as e:
        source.consecutive_failures += 1
        source.last_error = str(e)
        print(f"Error processing {source.municipality}: {e}")
    
    finally:
        await connector.close()
    
    session.commit()
    return new_count


def run():
    """Run discovery for all enabled sources."""
    SessionLocal = get_session_factory()
    
    with SessionLocal() as session:
        sources = session.query(Source).filter_by(enabled=True).all()
        
        if not sources:
            print("No enabled sources found.")
            return
        
        total_new = 0
        skipped = 0
        supported_platforms = {"cloudnc", "dynasty", "tweb"}
        for source in sources:
            if source.platform not in supported_platforms:
                print(f"Skipping: {source.municipality} ({source.platform}) - unsupported platform")
                skipped += 1
                continue
            print(f"Discovering: {source.municipality} ({source.platform})")
            new_count = asyncio.run(process_source(source, session))
            print(f"  → Found {new_count} new documents")
            total_new += new_count
        
        print(f"\nTotal new documents: {total_new} ({skipped} sources skipped)")

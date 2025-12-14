"""Fetch pipeline stage - download PDFs and attachments."""

import asyncio
import hashlib
from datetime import datetime
from pathlib import Path

import httpx

from watchdog.config import get_settings
from watchdog.db.models import Document, File, DocumentStatus, TextStatus, get_session_factory


async def download_file(url: str, storage_path: Path, user_agent: str) -> tuple[int, str]:
    """
    Download a file and return (size, content_hash).
    """
    async with httpx.AsyncClient(headers={"User-Agent": user_agent}) as client:
        response = await client.get(url, follow_redirects=True, timeout=60.0)
        response.raise_for_status()
        
        content = response.content
        size = len(content)
        content_hash = hashlib.sha256(content).hexdigest()
        
        # Ensure directory exists
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        storage_path.write_bytes(content)
        
        return size, content_hash


def run():
    """Fetch all pending files."""
    settings = get_settings()
    storage_base = Path(settings.storage_path)
    
    SessionLocal = get_session_factory()
    
    with SessionLocal() as session:
        # Get documents with status 'new' that have pending files
        pending_files = session.query(File).filter(
            File.storage_path.is_(None),
            File.text_status == TextStatus.PENDING,
        ).all()
        
        if not pending_files:
            print("No files to fetch.")
            return
        
        print(f"Fetching {len(pending_files)} files...")
        
        for file in pending_files:
            doc = file.document
            source_id = doc.source_id
            
            # Storage path: ./data/files/{source_id}/{file_id}.pdf
            storage_path = storage_base / str(source_id) / f"{file.id}.pdf"
            
            try:
                size, content_hash = asyncio.run(
                    download_file(file.url, storage_path, settings.connector_user_agent)
                )
                
                file.storage_path = str(storage_path.relative_to(storage_base))
                file.bytes = size
                file.fetched_at = datetime.utcnow()
                
                # Update parent document hash (simplistic - just use first file's hash)
                if not doc.content_hash:
                    doc.content_hash = content_hash
                
                print(f"  ✓ {doc.title[:50]}... ({size:,} bytes)")
                
            except Exception as e:
                file.text_status = TextStatus.FAILED
                print(f"  ✗ {doc.title[:50]}... - Error: {e}")
        
        # Update document statuses
        for file in pending_files:
            if file.storage_path:
                doc = file.document
                if doc.status == DocumentStatus.NEW:
                    doc.status = DocumentStatus.FETCHED
        
        session.commit()
        print("Fetch complete.")

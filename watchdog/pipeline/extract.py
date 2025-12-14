"""Extract pipeline stage - extract text from PDFs."""

from pathlib import Path

from watchdog.config import get_settings
from watchdog.db.models import File, TextStatus, get_session_factory


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF file using pdfplumber."""
    import pdfplumber
    
    text_parts = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    
    return "\n\n".join(text_parts)


def ocr_pdf(pdf_path: Path) -> str:
    """OCR a PDF using Tesseract (Finnish language)."""
    import pytesseract
    from pdf2image import convert_from_path
    
    # Convert PDF to images
    images = convert_from_path(pdf_path)
    
    text_parts = []
    for image in images:
        text = pytesseract.image_to_string(image, lang="fin")
        text_parts.append(text)
    
    return "\n\n".join(text_parts)


def run():
    """Extract text from all fetched PDFs."""
    settings = get_settings()
    storage_base = Path(settings.storage_path)
    
    SessionLocal = get_session_factory()
    
    with SessionLocal() as session:
        # Get files with storage_path but no text content
        pending_files = session.query(File).filter(
            File.storage_path.isnot(None),
            File.text_status.in_([TextStatus.PENDING, TextStatus.OCR_QUEUED]),
        ).all()
        
        if not pending_files:
            print("No files to extract.")
            return
        
        print(f"Extracting text from {len(pending_files)} files...")
        
        for file in pending_files:
            pdf_path = storage_base / file.storage_path
            
            if not pdf_path.exists():
                print(f"  ✗ File not found: {file.storage_path}")
                file.text_status = TextStatus.FAILED
                continue
            
            try:
                # Try normal text extraction first
                if file.text_status == TextStatus.PENDING:
                    text = extract_text_from_pdf(pdf_path)
                    
                    # Check if we got enough text (100 chars threshold)
                    if len(text.strip()) < 100 and file.bytes and file.bytes > 10000:
                        # Likely a scanned PDF, queue for OCR
                        print(f"  ⏳ Queuing for OCR: {file.document.title[:40]}...")
                        file.text_status = TextStatus.OCR_QUEUED
                        continue
                    
                    file.text_content = text
                    file.text_status = TextStatus.EXTRACTED
                    print(f"  ✓ Extracted: {file.document.title[:40]}... ({len(text):,} chars)")
                
                # OCR for scanned PDFs
                elif file.text_status == TextStatus.OCR_QUEUED:
                    try:
                        text = ocr_pdf(pdf_path)
                        file.text_content = text
                        file.text_status = TextStatus.OCR_DONE
                        print(f"  ✓ OCR complete: {file.document.title[:40]}... ({len(text):,} chars)")
                    except Exception as e:
                        print(f"  ✗ OCR failed: {file.document.title[:40]}... - {e}")
                        file.text_status = TextStatus.FAILED
            
            except Exception as e:
                print(f"  ✗ Extraction failed: {file.document.title[:40]}... - {e}")
                file.text_status = TextStatus.FAILED
        
        session.commit()
        print("Extraction complete.")

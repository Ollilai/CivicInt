"""Extract pipeline stage -- extract text from PDFs."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from civicint.config import get_settings
from civicint.models import Document, DocumentStatus, FileText, TextStatus

logger = logging.getLogger(__name__)


def safe_path_join(base: Path, untrusted_path: str) -> Path:
    """Safely join a base path with an untrusted path component.

    SECURITY: Prevents path traversal attacks by ensuring the resolved
    path stays within the base directory.

    Raises:
        ValueError: If the path would escape the base directory.
    """
    base_resolved = base.resolve()
    joined_path = (base / untrusted_path).resolve()

    try:
        joined_path.relative_to(base_resolved)
    except ValueError as exc:
        raise ValueError(
            f"SECURITY: Path traversal attempt detected. "
            f"Path '{untrusted_path}' escapes base directory."
        ) from exc

    return joined_path


def _extract_text_from_pdf(pdf_path: Path) -> tuple[str, int]:
    """Extract text using pdfplumber. Returns ``(text, page_count)``."""
    import pdfplumber

    text_parts: list[str] = []
    page_count = 0

    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    return "\n\n".join(text_parts), page_count


def _ocr_pdf(pdf_path: Path) -> str:
    """OCR a PDF using Tesseract with Finnish language support."""
    import pytesseract
    from pdf2image import convert_from_path

    images = convert_from_path(pdf_path)
    text_parts: list[str] = []
    for image in images:
        text = pytesseract.image_to_string(image, lang="fin")
        text_parts.append(text)

    return "\n\n".join(text_parts)


def run_extract(document_id: int, session: Session) -> None:
    """Extract text from all fetched files belonging to a document.

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
        if f.storage_path is not None and f.text_status == TextStatus.PENDING
    ]

    if not pending_files:
        return

    for file in pending_files:
        try:
            pdf_path = safe_path_join(storage_base, file.storage_path)
        except ValueError:
            logger.error("Path traversal blocked for file %d", file.id)
            file.text_status = TextStatus.FAILED
            continue

        if not pdf_path.exists():
            logger.error("File not found on disk: %s", file.storage_path)
            file.text_status = TextStatus.FAILED
            continue

        try:
            text, page_count = _extract_text_from_pdf(pdf_path)
            file.page_count = page_count
            method = "pdfplumber"

            # If very little text from a sizable file, attempt OCR
            if len(text.strip()) < 100 and file.bytes and file.bytes > 10_000:
                try:
                    text = _ocr_pdf(pdf_path)
                    method = "tesseract"
                    file.text_status = TextStatus.OCR_DONE
                except Exception:
                    logger.exception("OCR failed for file %d", file.id)
                    file.text_status = TextStatus.FAILED
                    continue
            else:
                file.text_status = TextStatus.EXTRACTED

            file_text = FileText(
                file_id=file.id,
                content=text,
                extraction_method=method,
                char_count=len(text),
            )
            session.add(file_text)
            logger.info(
                "Extracted file %d (%s, %d chars, %d pages)",
                file.id,
                method,
                len(text),
                page_count,
            )

        except Exception:
            logger.exception("Extraction failed for file %d", file.id)
            file.text_status = TextStatus.FAILED

    # Advance document status if any file has text
    has_text = any(
        f.text_status in (TextStatus.EXTRACTED, TextStatus.OCR_DONE) for f in doc.files
    )
    if has_text and doc.status in (DocumentStatus.NEW, DocumentStatus.FETCHED):
        doc.status = DocumentStatus.EXTRACTED

    session.commit()

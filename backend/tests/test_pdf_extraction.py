import pytest
from app.services.pdf_extraction_service import pdf_extraction_service

try:
    import pymupdf as fitz
except ImportError:
    import fitz


def test_pdf_extraction_page_preservation():
    """Verify multi-page PDF extraction preserving page numbers and text counts."""
    doc = fitz.open()

    # Page 1
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text(
        (50, 72),
        "Page One: Section 1 of Department Circular on Agriculture and Fertilizer Subsidies.",
        fontsize=12,
    )

    # Page 2
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text(
        (50, 72),
        "Page Two: Section 2 detailing Aadhaar authentication, banking guidelines, and timeline.",
        fontsize=12,
    )

    pdf_bytes = doc.write()
    doc.close()

    status, pages, total_pages, ocr_reason = pdf_extraction_service.extract_text_from_bytes(
        pdf_bytes, original_filename="multipage.pdf"
    )

    assert status == "COMPLETED"
    assert total_pages == 2
    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert "Page One" in pages[0].text
    assert pages[1].page_number == 2
    assert "Page Two" in pages[1].text
    assert ocr_reason == ""


def test_pdf_extraction_scanned_ocr_detection():
    """Verify that documents with negligible text trigger OCR_REQUIRED status."""
    doc = fitz.open()
    doc.new_page(width=595, height=842)  # Blank page
    pdf_bytes = doc.write()
    doc.close()

    status, pages, total_pages, ocr_reason = pdf_extraction_service.extract_text_from_bytes(
        pdf_bytes, original_filename="scanned.pdf"
    )

    assert status == "OCR_REQUIRED"
    assert total_pages == 1
    assert len(pages) == 1
    assert "scanned" in ocr_reason.lower() or "ocr" in ocr_reason.lower()

import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

try:
    import pymupdf as fitz
except ImportError:
    import fitz

client = TestClient(app)


def create_sample_pdf(text: str = "Government Public Notice. Guidelines for welfare subsidies.") -> bytes:
    """Helper creating an in-memory single-page PDF with text wrapped in a bounding box."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    rect = fitz.Rect(50, 50, 545, 800)
    page.insert_textbox(rect, text, fontsize=12)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def test_upload_valid_pdf():
    """Verify successful upload, storage, and text extraction of a valid text PDF."""
    content_text = (
        "GOVERNMENT OF INDIA. Ministry of Agriculture and Farmers Welfare. "
        "Official Circular on PM-KISAN 16th Installment Disbursement. "
        "All eligible farmer beneficiaries are hereby informed that the upcoming direct transfer "
        "will be credited via Aadhaar enabled payment system. Please complete biometric eKYC."
    )
    pdf_bytes = create_sample_pdf(content_text)

    files = {"file": ("test_notice.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/documents/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "document_id" in data
    assert data["filename"] == "test_notice.pdf"
    assert data["page_count"] == 1
    assert data["processing_status"] in ("COMPLETED", "INDEXED")

    doc_id = data["document_id"]

    # Verify metadata endpoint
    meta_resp = client.get(f"/api/v1/documents/{doc_id}")
    assert meta_resp.status_code == 200
    meta_data = meta_resp.json()
    assert meta_data["document_id"] == doc_id
    assert meta_data["original_filename"] == "test_notice.pdf"

    # Verify pages endpoint
    pages_resp = client.get(f"/api/v1/documents/{doc_id}/pages")
    assert pages_resp.status_code == 200
    pages_data = pages_resp.json()
    assert pages_data["total_pages"] == 1
    assert len(pages_data["pages"]) == 1
    assert pages_data["pages"][0]["page_number"] == 1
    assert "PM-KISAN" in pages_data["pages"][0]["text"]

    # Verify deletion
    del_resp = client.delete(f"/api/v1/documents/{doc_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Verify 404 after deletion
    assert client.get(f"/api/v1/documents/{doc_id}").status_code == 404


def test_upload_invalid_extension():
    """Verify rejection of non-PDF files."""
    files = {"file": ("notice.txt", io.BytesIO(b"Just plain text file"), "text/plain")}
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 422


def test_upload_corrupt_pdf():
    """Verify rejection of corrupt files with PDF extension but invalid magic bytes."""
    corrupt_bytes = b"NOT_A_PDF_HEADER_THIS_IS_CORRUPT"
    files = {"file": ("fake.pdf", io.BytesIO(corrupt_bytes), "application/pdf")}
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 422


def test_upload_scanned_pdf_ocr_required():
    """Verify that PDFs with sparse or no text are correctly marked OCR_REQUIRED."""
    # Create empty PDF page with zero words
    doc = fitz.open()
    doc.new_page(width=595, height=842)
    empty_bytes = doc.write()
    doc.close()

    files = {"file": ("scanned_notice.pdf", io.BytesIO(empty_bytes), "application/pdf")}
    response = client.post("/api/v1/documents/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["processing_status"] == "OCR_REQUIRED"
    assert "OCR" in data["message"]


def test_get_nonexistent_document_404():
    """Verify 404 for unknown document ID."""
    response = client.get("/api/v1/documents/nonexistent-doc-uuid-12345")
    assert response.status_code == 404

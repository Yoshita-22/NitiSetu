import io
import logging
from typing import List, Tuple
from app.core.exceptions import FileProcessingError
from app.schemas.document_schemas import DocumentPage, ProcessingStatus

try:
    import pymupdf as fitz
except ImportError:
    import fitz

logger = logging.getLogger("nitsetu.pdf")


class PDFExtractionService:
    """Service handling PDF document text extraction and OCR necessity detection.

    Uses PyMuPDF to extract text page-by-page, preserving page numbering,
    and identifying scanned or image-only documents.
    """

    MIN_TOTAL_WORDS_FOR_TEXT_PDF = 10
    MIN_TOTAL_CHARS_FOR_TEXT_PDF = 40

    def extract_text_from_bytes(
        self, file_bytes: bytes, original_filename: str = "document.pdf"
    ) -> Tuple[ProcessingStatus, List[DocumentPage], int, str]:
        """Extract text page by page from PDF raw bytes.

        Returns:
            Tuple of (ProcessingStatus, List[DocumentPage], total_pages, ocr_reason)
        """
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            logger.error(f"PyMuPDF failed to parse PDF '{original_filename}': {e}")
            raise FileProcessingError(f"Corrupt or invalid PDF file format: {str(e)}")

        total_pages = len(doc)
        if total_pages == 0:
            doc.close()
            raise FileProcessingError("PDF document contains 0 pages.")

        pages: List[DocumentPage] = []
        total_word_count = 0
        total_char_count = 0

        for page_idx in range(total_pages):
            page_num = page_idx + 1
            try:
                page = doc.load_page(page_idx)
                raw_text = page.get_text("text") or ""
                clean_text = raw_text.strip()
                words = clean_text.split()
                w_count = len(words)
                c_count = len(clean_text)

                total_word_count += w_count
                total_char_count += c_count

                pages.append(
                    DocumentPage(
                        page_number=page_num,
                        text=clean_text,
                        word_count=w_count,
                        character_count=c_count,
                    )
                )
            except Exception as e:
                logger.warning(f"Error reading page {page_num} of '{original_filename}': {e}")
                pages.append(
                    DocumentPage(
                        page_number=page_num,
                        text="",
                        word_count=0,
                        character_count=0,
                    )
                )

        doc.close()

        # Assess whether the document is scanned / image-based and requires OCR
        if (
            total_word_count < self.MIN_TOTAL_WORDS_FOR_TEXT_PDF
            or total_char_count < self.MIN_TOTAL_CHARS_FOR_TEXT_PDF
        ):
            status: ProcessingStatus = "OCR_REQUIRED"
            ocr_reason = (
                f"Document contains insufficient extractable digital text ({total_word_count} words found across {total_pages} page(s)). "
                "This document appears to be a scanned notice or image-only circular requiring OCR processing."
            )
        else:
            status = "COMPLETED"
            ocr_reason = ""

        return status, pages, total_pages, ocr_reason


# Default service instance
pdf_extraction_service = PDFExtractionService()

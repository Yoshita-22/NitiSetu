import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile
from app.core.config import settings
from app.core.exceptions import FileProcessingError, NotFoundError, ValidationError
from app.repositories.document_repository import document_repository
from app.schemas.document_schemas import (
    DocumentMetadata,
    DocumentPagesResponse,
    DocumentUploadResponse,
)
from app.services.pdf_extraction_service import pdf_extraction_service
from app.storage.local_storage import local_storage


class DocumentService:
    """Orchestrates PDF validation, safe storage, and text extraction."""

    PDF_MAGIC_BYTES = b"%PDF-"
    MAX_FILE_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    async def process_pdf_upload(
        self, file: UploadFile, owner_id: str = "anonymous_dev"
    ) -> DocumentUploadResponse:
        """Validate, store, and extract text from an uploaded PDF file."""
        original_filename = file.filename or "uploaded_notice.pdf"

        # 1. Extension Validation
        if not original_filename.lower().endswith(".pdf"):
            raise ValidationError("Invalid file extension. Only .pdf files are supported.")

        # 2. Read File Bytes
        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise ValidationError("Uploaded file is empty (0 bytes).")

        # 3. File Size Validation
        if file_size > self.MAX_FILE_SIZE_BYTES:
            raise ValidationError(
                f"File size ({file_size / (1024 * 1024):.2f} MB) exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB} MB."
            )

        # 4. MIME Type Validation
        content_type = file.content_type or ""
        if content_type.lower() not in ["application/pdf", "application/x-pdf", "binary/octet-stream"]:
            raise ValidationError(f"Invalid MIME type '{content_type}'. Must be 'application/pdf'.")

        # 5. Magic Bytes Validation
        if not content.startswith(self.PDF_MAGIC_BYTES):
            raise ValidationError("Invalid PDF file signature. The file header does not match standard PDF magic bytes.")

        # 6. Generate Server-Side Unique Document ID
        document_id = str(uuid.uuid4())
        upload_time_iso = datetime.now(timezone.utc).isoformat()

        # 7. Safe File Storage (Filename is isolated from storage path)
        local_storage.save_file(document_id, content)

        # 8. Extract Text Page-by-Page
        status, pages, page_count, ocr_reason = pdf_extraction_service.extract_text_from_bytes(
            content, original_filename=original_filename
        )

        # 9. Register Document in Repository
        metadata = DocumentMetadata(
            document_id=document_id,
            original_filename=Path(original_filename).name,
            file_size_bytes=file_size,
            file_type="application/pdf",
            page_count=page_count,
            upload_timestamp=upload_time_iso,
            processing_status=status,
            owner_id=owner_id,
            ocr_required_reason=ocr_reason if ocr_reason else None,
        )
        document_repository.save_document(metadata, pages)

        # 10. Construct Friendly Response Message
        if status == "OCR_REQUIRED":
            msg = f"PDF uploaded successfully. However, {ocr_reason}"
        else:
            msg = f"PDF uploaded and text successfully extracted across {page_count} page(s)."

        return DocumentUploadResponse(
            success=True,
            document_id=document_id,
            filename=metadata.original_filename,
            page_count=page_count,
            file_size_bytes=file_size,
            processing_status=status,
            message=msg,
        )

    def get_document_metadata(self, document_id: str) -> DocumentMetadata:
        """Retrieve metadata for a specific document."""
        meta = document_repository.get_metadata(document_id)
        if not meta:
            raise NotFoundError(f"Document with ID '{document_id}' was not found.")
        return meta

    def get_document_pages(self, document_id: str) -> DocumentPagesResponse:
        """Retrieve all extracted pages for a document."""
        meta = self.get_document_metadata(document_id)
        pages = document_repository.get_pages(document_id) or []
        return DocumentPagesResponse(
            document_id=meta.document_id,
            original_filename=meta.original_filename,
            total_pages=meta.page_count,
            processing_status=meta.processing_status,
            pages=pages,
        )

    def delete_document(
        self, document_id: str, owner_id: Optional[str] = None
    ) -> bool:
        """Delete document file and metadata with ownership verification."""
        meta = document_repository.get_metadata(document_id)
        if not meta:
            raise NotFoundError(f"Document with ID '{document_id}' was not found.")

        # Check ownership if specified
        if owner_id and meta.owner_id and meta.owner_id != owner_id:
            raise ValidationError("You do not have authorization to delete this document.")

        # Remove physical file
        local_storage.delete_file(document_id)

        # Remove from repository
        document_repository.delete_document(document_id, owner_id=owner_id)
        return True

    def list_documents(self, owner_id: Optional[str] = None) -> List[DocumentMetadata]:
        """List uploaded documents."""
        return document_repository.list_documents(owner_id=owner_id)


# Default service instance
document_service = DocumentService()

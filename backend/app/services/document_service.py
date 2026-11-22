import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile
from app.core.config import settings
from app.core.exceptions import FileProcessingError, NotFoundError, ValidationError
from app.repositories.document_repository import document_repository
from app.schemas.document_schemas import (
    DocumentChunksResponse,
    DocumentIndexResponse,
    DocumentMetadata,
    DocumentPagesResponse,
    DocumentQueryResponse,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from app.services.chunking_service import chunking_service
from app.services.document_qa_service import document_qa_service
from app.services.embedding_service import embedding_service
from app.services.pdf_extraction_service import pdf_extraction_service
from app.services.text_cleaning_service import text_cleaning_service
from app.storage.chroma_storage import chroma_storage
from app.storage.local_storage import local_storage

logger = logging.getLogger("nitsetu.document_service")


class DocumentService:
    """Orchestrates PDF validation, safe storage, text extraction, cleaning,
    chunking, vector embedding, and ChromaDB indexing.
    """

    PDF_MAGIC_BYTES = b"%PDF-"
    MAX_FILE_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @staticmethod
    def _is_authorized(meta_owner: Optional[str], request_owner: Optional[str]) -> bool:
        """Verify ownership with support for interchangeable anonymous aliases."""
        if not meta_owner or not request_owner:
            return True
        if meta_owner == request_owner:
            return True
        anonymous_aliases = {"anonymous_citizen", "anonymous_dev"}
        if meta_owner in anonymous_aliases and request_owner in anonymous_aliases:
            return True
        return False

    async def process_pdf_upload(
        self, file: UploadFile, owner_id: str = "anonymous_dev"
    ) -> DocumentUploadResponse:
        """Validate, store, extract text, and automatically index a PDF file."""
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

        # 10. Automatically Index if Text Was Extracted
        chunks_indexed = 0
        if status in ("COMPLETED", "EXTRACTED"):
            try:
                index_res = self.index_document(document_id, owner_id=owner_id)
                chunks_indexed = index_res.chunks_indexed
                status = index_res.processing_status
            except Exception as e:
                logger.error(f"Auto-indexing failed for '{document_id}': {e}")

        # 11. Construct Friendly Response Message
        if status == "OCR_REQUIRED":
            msg = f"PDF uploaded successfully. However, {ocr_reason}"
        elif status == "INDEXED":
            msg = f"PDF uploaded, text extracted across {page_count} page(s), and {chunks_indexed} chunk(s) indexed for RAG."
        else:
            msg = f"PDF uploaded and text extracted across {page_count} page(s)."

        return DocumentUploadResponse(
            success=True,
            document_id=document_id,
            filename=metadata.original_filename,
            page_count=page_count,
            file_size_bytes=file_size,
            processing_status=status,
            message=msg,
            chunks_indexed=chunks_indexed,
        )

    def index_document(
        self, document_id: str, owner_id: str = "anonymous_dev"
    ) -> DocumentIndexResponse:
        """Executes full document indexing pipeline:
        EXTRACTED -> CLEANING -> CHUNKING -> EMBEDDING -> INDEXING -> INDEXED.
        """
        meta = self.get_document_metadata(document_id)

        # Verify ownership
        if not self._is_authorized(meta.owner_id, owner_id):
            raise ValidationError("You do not have authorization to index this document.")

        if meta.processing_status == "OCR_REQUIRED":
            return DocumentIndexResponse(
                success=False,
                document_id=document_id,
                processing_status="OCR_REQUIRED",
                chunks_indexed=0,
                embedding_model=settings.EMBEDDING_MODEL_NAME,
                message="Cannot index scanned document requiring OCR.",
            )

        try:
            pages = document_repository.get_pages(document_id) or []
            if not pages:
                raise FileProcessingError("No extractable pages found for document.")

            # 1. CLEANING
            document_repository.update_metadata(document_id, {"processing_status": "CLEANING"})
            cleaned_pages = text_cleaning_service.clean_document_pages(pages)

            # 2. CHUNKING
            document_repository.update_metadata(document_id, {"processing_status": "CHUNKING"})
            chunks = chunking_service.chunk_document(
                cleaned_pages,
                document_id=document_id,
                user_id=owner_id,
                source_filename=meta.original_filename,
            )

            if not chunks:
                document_repository.update_metadata(
                    document_id,
                    {"processing_status": "FAILED", "indexing_error": "Document produced 0 text chunks."},
                )
                raise FileProcessingError("No valid text chunks generated from document.")

            # 3. EMBEDDING
            document_repository.update_metadata(document_id, {"processing_status": "EMBEDDING"})
            chunk_texts = [c.content for c in chunks]
            embeddings = embedding_service.embed_documents(chunk_texts)

            # 4. INDEXING in ChromaDB
            document_repository.update_metadata(document_id, {"processing_status": "INDEXING"})
            indexed_count = chroma_storage.add_chunks(chunks, embeddings)

            # 5. INDEXED (Successful completion)
            now_iso = datetime.now(timezone.utc).isoformat()
            document_repository.update_metadata(
                document_id,
                {
                    "processing_status": "INDEXED",
                    "chunks_count": indexed_count,
                    "embedding_model": settings.EMBEDDING_MODEL_NAME,
                    "last_indexed_at": now_iso,
                    "indexing_error": None,
                },
            )

            return DocumentIndexResponse(
                success=True,
                document_id=document_id,
                processing_status="INDEXED",
                chunks_indexed=indexed_count,
                embedding_model=settings.EMBEDDING_MODEL_NAME,
                message=f"Successfully indexed {indexed_count} chunk(s) into ChromaDB.",
            )

        except Exception as e:
            logger.exception(f"Indexing failed for '{document_id}': {e}")
            document_repository.update_metadata(
                document_id,
                {
                    "processing_status": "FAILED",
                    "indexing_error": str(e),
                },
            )
            return DocumentIndexResponse(
                success=False,
                document_id=document_id,
                processing_status="FAILED",
                chunks_indexed=0,
                embedding_model=settings.EMBEDDING_MODEL_NAME,
                message=f"Indexing failed: {str(e)}",
            )

    def get_document_status(self, document_id: str) -> DocumentStatusResponse:
        """Retrieves comprehensive indexing and processing status."""
        meta = self.get_document_metadata(document_id)
        return DocumentStatusResponse(
            document_id=meta.document_id,
            original_filename=meta.original_filename,
            processing_status=meta.processing_status,
            page_count=meta.page_count,
            chunks_count=meta.chunks_count,
            embedding_model=meta.embedding_model,
            last_indexed_at=meta.last_indexed_at,
            ocr_required_reason=meta.ocr_required_reason,
            indexing_error=meta.indexing_error,
        )

    def get_document_chunks(
        self, document_id: str, owner_id: str = "anonymous_dev"
    ) -> DocumentChunksResponse:
        """Retrieves indexed chunks for a document with ownership verification."""
        meta = self.get_document_metadata(document_id)
        if meta.owner_id and not self._is_authorized(meta.owner_id, owner_id):
            raise ValidationError("You do not have authorization to view chunks for this document.")

        chunks = chroma_storage.get_document_chunks(document_id, user_id=owner_id)
        return DocumentChunksResponse(
            document_id=document_id,
            total_chunks=len(chunks),
            chunks=chunks,
        )

    async def query_document(
        self,
        query: str,
        user_id: str = "anonymous_citizen",
        document_id: Optional[str] = None,
        language: str = "en",
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
    ) -> DocumentQueryResponse:
        """Performs grounded RAG Q&A over a document or across user's authorized documents."""
        if document_id:
            # Validate document exists and check ownership if recorded
            meta = self.get_document_metadata(document_id)
            if meta.owner_id and not self._is_authorized(meta.owner_id, user_id):
                raise ValidationError("You do not have authorization to query this document.")

        return await document_qa_service.answer_document_query(
            query=query,
            user_id=user_id,
            document_id=document_id,
            language=language,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
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
        """Delete document file, vector chunks, and metadata with ownership verification."""
        meta = document_repository.get_metadata(document_id)
        if not meta:
            raise NotFoundError(f"Document with ID '{document_id}' was not found.")

        # Check ownership if specified
        if owner_id and meta.owner_id and not self._is_authorized(meta.owner_id, owner_id):
            raise ValidationError("You do not have authorization to delete this document.")

        # 1. Remove physical file
        local_storage.delete_file(document_id)

        # 2. Remove indexed vector chunks from ChromaDB
        chroma_storage.delete_document_chunks(document_id, user_id=owner_id)

        # 3. Remove from repository
        document_repository.delete_document(document_id, owner_id=owner_id)
        return True

    def list_documents(self, owner_id: Optional[str] = None) -> List[DocumentMetadata]:
        """List uploaded documents."""
        return document_repository.list_documents(owner_id=owner_id)


# Default service instance
document_service = DocumentService()

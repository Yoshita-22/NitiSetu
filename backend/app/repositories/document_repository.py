from typing import Any, Dict, List, Optional
from threading import Lock
from app.schemas.document_schemas import DocumentMetadata, DocumentPage


class DocumentRepository:
    """Repository managing document metadata and extracted text.

    Uses an in-memory thread-safe registry for Phase 1.
    Designed with a clean interface that can be backed by a database table
    or Supabase in production.
    """

    def __init__(self):
        self._metadata_store: Dict[str, DocumentMetadata] = {}
        self._pages_store: Dict[str, List[DocumentPage]] = {}
        self._lock = Lock()

    def save_document(
        self, metadata: DocumentMetadata, pages: List[DocumentPage]
    ) -> DocumentMetadata:
        """Store document metadata and its page-wise text extracts."""
        with self._lock:
            self._metadata_store[metadata.document_id] = metadata
            self._pages_store[metadata.document_id] = pages
            return metadata

    def get_metadata(self, document_id: str) -> Optional[DocumentMetadata]:
        """Retrieve metadata for a specific document."""
        with self._lock:
            return self._metadata_store.get(document_id)

    def update_metadata(
        self, document_id: str, updates: Dict[str, Any]
    ) -> Optional[DocumentMetadata]:
        """Updates specific fields of a document's metadata."""
        with self._lock:
            meta = self._metadata_store.get(document_id)
            if not meta:
                return None
            data = meta.model_dump()
            data.update(updates)
            updated_meta = DocumentMetadata(**data)
            self._metadata_store[document_id] = updated_meta
            return updated_meta

    def get_pages(self, document_id: str) -> Optional[List[DocumentPage]]:
        """Retrieve extracted pages for a specific document."""
        with self._lock:
            return self._pages_store.get(document_id)

    def delete_document(
        self, document_id: str, owner_id: Optional[str] = None
    ) -> bool:
        """Delete document metadata and pages.

        Enforces ownership match if owner_id is provided.
        """
        with self._lock:
            meta = self._metadata_store.get(document_id)
            if not meta:
                return False

            # Check owner isolation if owner_id is specified
            if owner_id and meta.owner_id and meta.owner_id != owner_id:
                return False

            self._metadata_store.pop(document_id, None)
            self._pages_store.pop(document_id, None)
            return True

    def list_documents(self, owner_id: Optional[str] = None) -> List[DocumentMetadata]:
        """List documents, filtered by owner if provided."""
        with self._lock:
            if owner_id:
                return [
                    doc for doc in self._metadata_store.values()
                    if doc.owner_id == owner_id
                ]
            return list(self._metadata_store.values())


# Default repository instance
document_repository = DocumentRepository()

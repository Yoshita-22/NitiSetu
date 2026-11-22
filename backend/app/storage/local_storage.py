import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from app.core.config import settings
from app.core.exceptions import FileProcessingError


class DocumentStorageInterface(ABC):
    """Abstract interface for document file storage.

    Allows replacing local filesystem storage with S3, Supabase Storage,
    or Azure Blob Storage without modifying business logic.
    """

    @abstractmethod
    def save_file(self, document_id: str, content: bytes) -> str:
        """Save file bytes and return storage reference key."""
        pass

    @abstractmethod
    def get_file(self, document_id: str) -> Optional[bytes]:
        """Retrieve stored file bytes by document ID."""
        pass

    @abstractmethod
    def delete_file(self, document_id: str) -> bool:
        """Delete stored file by document ID."""
        pass

    @abstractmethod
    def file_exists(self, document_id: str) -> bool:
        """Check if file exists in storage."""
        pass


class LocalStorage(DocumentStorageInterface):
    """Secure local filesystem storage implementation."""

    def __init__(self, base_directory: Optional[str] = None):
        upload_dir_setting = base_directory or settings.UPLOAD_DIRECTORY
        # Resolve to backend root if relative
        self.base_dir = Path(upload_dir_setting).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_safe_path(self, document_id: str) -> Path:
        """Ensure document_id is safe and strictly confined to base_dir."""
        # Sanitize to prevent path traversal
        clean_id = Path(document_id).name
        target_path = (self.base_dir / f"{clean_id}.pdf").resolve()
        if not str(target_path).startswith(str(self.base_dir)):
            raise FileProcessingError("Illegal path traversal detected.")
        return target_path

    def save_file(self, document_id: str, content: bytes) -> str:
        file_path = self._get_safe_path(document_id)
        try:
            with open(file_path, "wb") as f:
                f.write(content)
            return str(file_path)
        except Exception as e:
            raise FileProcessingError(f"Failed to persist file locally: {str(e)}")

    def get_file(self, document_id: str) -> Optional[bytes]:
        file_path = self._get_safe_path(document_id)
        if not file_path.exists() or not file_path.is_file():
            return None
        try:
            with open(file_path, "rb") as f:
                return f.read()
        except Exception as e:
            raise FileProcessingError(f"Failed to read stored file: {str(e)}")

    def delete_file(self, document_id: str) -> bool:
        file_path = self._get_safe_path(document_id)
        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
                return True
            except Exception as e:
                raise FileProcessingError(f"Failed to remove file from storage: {str(e)}")
        return False

    def file_exists(self, document_id: str) -> bool:
        file_path = self._get_safe_path(document_id)
        return file_path.exists() and file_path.is_file()


# Default singleton instance
local_storage = LocalStorage()

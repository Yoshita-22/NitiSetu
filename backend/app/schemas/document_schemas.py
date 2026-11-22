from typing import List, Literal, Optional
from pydantic import BaseModel, Field

ProcessingStatus = Literal["UPLOADED", "PROCESSING", "COMPLETED", "OCR_REQUIRED", "FAILED"]


class DocumentMetadata(BaseModel):
    """Metadata record for an uploaded document."""

    document_id: str = Field(..., description="Unique UUID for the document")
    original_filename: str = Field(..., description="User's original file name")
    file_size_bytes: int = Field(..., description="File size in bytes")
    file_type: str = Field("application/pdf", description="MIME content type")
    page_count: int = Field(..., description="Total pages in the PDF")
    upload_timestamp: str = Field(..., description="ISO 8601 upload timestamp")
    processing_status: ProcessingStatus = Field(..., description="Current processing state")
    owner_id: Optional[str] = Field("anonymous_dev", description="Owner or user identifier")
    ocr_required_reason: Optional[str] = Field(None, description="Reason if marked as OCR_REQUIRED")


class DocumentPage(BaseModel):
    """Extracted text content for an individual page."""

    page_number: int = Field(..., description="1-indexed page number")
    text: str = Field(..., description="Extracted text content for this page")
    word_count: int = Field(..., description="Word count extracted from page")
    character_count: int = Field(..., description="Character count extracted from page")


class DocumentUploadResponse(BaseModel):
    """Response returned upon uploading and processing a PDF."""

    success: bool = True
    document_id: str
    filename: str
    page_count: int
    file_size_bytes: int
    processing_status: ProcessingStatus
    message: str


class DocumentPagesResponse(BaseModel):
    """Response containing all pages of an uploaded document."""

    document_id: str
    original_filename: str
    total_pages: int
    processing_status: ProcessingStatus
    pages: List[DocumentPage]

from typing import List, Optional
from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from app.core.exceptions import FileProcessingError, NotFoundError, ValidationError
from app.schemas.common_schemas import BaseResponse
from app.schemas.document_schemas import (
    DocumentMetadata,
    DocumentPagesResponse,
    DocumentUploadResponse,
)
from app.services.document_service import document_service

router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload and Extract PDF Document Text",
    description=(
        "Accepts a government notice, circular, or gazette PDF via multipart/form-data. "
        "Validates file size, extension, MIME type, and magic bytes. Extracts text page-by-page "
        "using PyMuPDF and detects scanned/image-only documents that require OCR."
    ),
)
async def upload_document(
    file: UploadFile = File(..., description="PDF document file (max 10MB)"),
    x_user_id: Optional[str] = Header("anonymous_dev", description="Optional citizen / owner identifier"),
) -> DocumentUploadResponse:
    """Upload PDF and extract page-by-page content."""
    try:
        return await document_service.process_pdf_upload(file, owner_id=x_user_id or "anonymous_dev")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e.message))
    except FileProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e.message))


@router.get(
    "/{document_id}",
    response_model=DocumentMetadata,
    summary="Get Document Processing Metadata",
    description="Returns metadata, page count, and processing status for an uploaded document.",
)
def get_document_metadata(document_id: str) -> DocumentMetadata:
    """Retrieve document metadata by document ID."""
    try:
        return document_service.get_document_metadata(document_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.message))


@router.get(
    "/{document_id}/pages",
    response_model=DocumentPagesResponse,
    summary="Get Extracted Text Pages",
    description="Returns page-by-page extracted text, word counts, and page numbers for an uploaded document.",
)
def get_document_pages(document_id: str) -> DocumentPagesResponse:
    """Retrieve page-by-page extracted text."""
    try:
        return document_service.get_document_pages(document_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.message))


@router.delete(
    "/{document_id}",
    response_model=BaseResponse,
    summary="Delete Uploaded Document",
    description="Deletes a document and its stored extracts after verifying ownership.",
)
def delete_document(
    document_id: str,
    x_user_id: Optional[str] = Header("anonymous_dev", description="Owner identifier for authorization verification"),
) -> BaseResponse:
    """Delete uploaded document file and metadata."""
    try:
        document_service.delete_document(document_id, owner_id=x_user_id)
        return BaseResponse(success=True, message=f"Document '{document_id}' successfully deleted.")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.message))
    except ValidationError as e:
        raise HTTPException(status_code=403, detail=str(e.message))

import logging
from typing import List, Optional
from fastapi import APIRouter, File, Header, HTTPException, UploadFile, status
from app.core.exceptions import FileProcessingError, NotFoundError, ValidationError
from app.schemas.common_schemas import BaseResponse
from app.schemas.document_schemas import (
    DocumentChunksResponse,
    DocumentIndexResponse,
    DocumentMetadata,
    DocumentPagesResponse,
    DocumentQueryRequest,
    DocumentQueryResponse,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from app.services.document_service import document_service

logger = logging.getLogger("nitsetu.document_routes")

router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload and Extract PDF Document Text",
    description=(
        "Accepts a government notice, circular, or gazette PDF via multipart/form-data. "
        "Validates file size, extension, MIME type, and magic bytes. Extracts text page-by-page "
        "using PyMuPDF, detects scanned documents, and automatically initiates RAG indexing."
    ),
)
async def upload_document(
    file: UploadFile = File(..., description="PDF document file (max 10MB)"),
    x_user_id: Optional[str] = Header("anonymous_dev", description="Optional citizen / owner identifier"),
) -> DocumentUploadResponse:
    """Upload PDF, extract text, and index into ChromaDB."""
    try:
        return await document_service.process_pdf_upload(file, owner_id=x_user_id or "anonymous_dev")
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e.message))
    except FileProcessingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.message))


@router.get(
    "/",
    response_model=List[DocumentMetadata],
    summary="List Uploaded Documents",
    description="Returns metadata for all documents uploaded by the authenticated user.",
)
def list_documents(
    x_user_id: Optional[str] = Header("anonymous_dev", description="Citizen / owner identifier"),
) -> List[DocumentMetadata]:
    """List documents for the current user."""
    return document_service.list_documents(owner_id=x_user_id)


@router.post(
    "/{document_id}/index",
    response_model=DocumentIndexResponse,
    summary="Trigger or Retry Document Indexing",
    description="Executes the text cleaning, semantic chunking, embedding generation, and ChromaDB indexing lifecycle.",
)
def index_document(
    document_id: str,
    x_user_id: Optional[str] = Header("anonymous_dev", description="Owner identifier for authorization"),
) -> DocumentIndexResponse:
    """Trigger or retry document indexing."""
    try:
        return document_service.index_document(document_id, owner_id=x_user_id or "anonymous_dev")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e.message))
    except FileProcessingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e.message))


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Get Document Processing & Indexing Status",
    description="Returns detailed processing state, chunk counts, model used, and any indexing error.",
)
def get_document_status(document_id: str) -> DocumentStatusResponse:
    """Retrieve indexing and processing status for a document."""
    try:
        return document_service.get_document_status(document_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))


@router.post(
    "/{document_id}/query",
    response_model=DocumentQueryResponse,
    summary="Query a Specific Document via RAG",
    description="Performs semantic vector search across a specific document's chunks and synthesizes a grounded answer.",
)
async def query_specific_document(
    document_id: str,
    payload: DocumentQueryRequest,
    x_user_id: Optional[str] = Header(None, description="Optional header overriding user_id"),
) -> DocumentQueryResponse:
    """Query a specific document."""
    user = x_user_id or payload.user_id
    try:
        return await document_service.query_document(
            query=payload.query,
            user_id=user,
            document_id=document_id,
            top_k=payload.top_k,
            similarity_threshold=payload.similarity_threshold,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e.message))


@router.post(
    "/query",
    response_model=DocumentQueryResponse,
    summary="Semantic Search Across User's Documents",
    description="Performs semantic retrieval and answer synthesis across all documents authorized for the user.",
)
async def query_all_documents(
    payload: DocumentQueryRequest,
    x_user_id: Optional[str] = Header(None, description="Optional header overriding user_id"),
) -> DocumentQueryResponse:
    """Query across user's authorized documents."""
    user = x_user_id or payload.user_id
    try:
        return await document_service.query_document(
            query=payload.query,
            user_id=user,
            document_id=payload.document_id,
            top_k=payload.top_k,
            similarity_threshold=payload.similarity_threshold,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e.message))


@router.get(
    "/{document_id}/chunks",
    response_model=DocumentChunksResponse,
    summary="Get Document Chunks (Authorized Inspection)",
    description="Retrieves the indexed text chunks and metadata for inspection with user ownership validation.",
)
def get_document_chunks(
    document_id: str,
    x_user_id: Optional[str] = Header("anonymous_dev", description="Owner identifier for authorization"),
) -> DocumentChunksResponse:
    """Retrieve indexed chunks for a document."""
    try:
        return document_service.get_document_chunks(document_id, owner_id=x_user_id or "anonymous_dev")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e.message))


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))


@router.delete(
    "/{document_id}",
    response_model=BaseResponse,
    summary="Delete Uploaded Document",
    description="Deletes a document, its stored extracts, and ChromaDB vector chunks after verifying ownership.",
)
def delete_document(
    document_id: str,
    x_user_id: Optional[str] = Header("anonymous_dev", description="Owner identifier for authorization verification"),
) -> BaseResponse:
    """Delete uploaded document file, vector chunks, and metadata."""
    try:
        document_service.delete_document(document_id, owner_id=x_user_id)
        return BaseResponse(success=True, message=f"Document '{document_id}' successfully deleted.")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e.message))

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

ProcessingStatus = Literal[
    "UPLOADED",
    "EXTRACTING",
    "EXTRACTED",
    "COMPLETED",
    "OCR_REQUIRED",
    "CLEANING",
    "CHUNKING",
    "EMBEDDING",
    "INDEXING",
    "INDEXED",
    "FAILED",
]

GroundingStatus = Literal["GROUNDED", "PARTIALLY_GROUNDED", "INSUFFICIENT_CONTEXT"]


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
    chunks_count: int = Field(0, description="Total chunks indexed in ChromaDB")
    embedding_model: Optional[str] = Field(None, description="Model used to embed chunks")
    indexing_error: Optional[str] = Field(None, description="Error message if indexing failed")
    last_indexed_at: Optional[str] = Field(None, description="ISO timestamp of last successful indexing")


class DocumentPage(BaseModel):
    """Extracted text content for an individual page."""

    page_number: int = Field(..., description="1-indexed page number")
    text: str = Field(..., description="Extracted text content for this page")
    word_count: int = Field(..., description="Word count extracted from page")
    character_count: int = Field(..., description="Character count extracted from page")


class DocumentChunkMetadata(BaseModel):
    """Metadata attached to an individual chunk in ChromaDB."""

    document_id: str
    user_id: str
    chunk_id: str
    chunk_index: int
    page_number: int
    page_start: int
    page_end: int
    source_filename: str
    section_heading: Optional[str] = None
    token_count: int
    embedding_model: str


class DocumentChunk(BaseModel):
    """Structured text chunk prepared for vector embedding and retrieval."""

    chunk_id: str
    content: str
    metadata: DocumentChunkMetadata


class DocumentUploadResponse(BaseModel):
    """Response returned upon uploading and processing a PDF."""

    success: bool = True
    document_id: str
    filename: str
    page_count: int
    file_size_bytes: int
    processing_status: ProcessingStatus
    message: str
    chunks_indexed: int = 0


class DocumentPagesResponse(BaseModel):
    """Response containing all pages of an uploaded document."""

    document_id: str
    original_filename: str
    total_pages: int
    processing_status: ProcessingStatus
    pages: List[DocumentPage]


class DocumentIndexResponse(BaseModel):
    """Response returned after triggering document indexing into ChromaDB."""

    success: bool
    document_id: str
    processing_status: ProcessingStatus
    chunks_indexed: int
    embedding_model: str
    message: str


class DocumentStatusResponse(BaseModel):
    """Current processing and indexing status for a document."""

    document_id: str
    original_filename: str
    processing_status: ProcessingStatus
    page_count: int
    chunks_count: int
    embedding_model: Optional[str] = None
    last_indexed_at: Optional[str] = None
    ocr_required_reason: Optional[str] = None
    indexing_error: Optional[str] = None


class SourceReference(BaseModel):
    """Citation reference pointing to the exact document and page supporting a claim."""

    document_id: str
    filename: str
    page_number: int
    page_start: int = 1
    page_end: int = 1
    chunk_id: str
    similarity_score: Optional[float] = None
    snippet: Optional[str] = None


class DocumentQueryRequest(BaseModel):
    """Incoming query against an indexed document."""

    query: str = Field(..., min_length=2, description="Natural language question about the document")
    document_id: Optional[str] = Field(None, description="Optional specific document UUID. If omitted, searches across user's documents.")
    user_id: str = Field("anonymous_citizen", description="Citizen / owner identifier for isolation")
    top_k: Optional[int] = Field(5, description="Number of top chunks to retrieve")
    similarity_threshold: Optional[float] = Field(None, description="Minimum similarity score")


class DocumentQueryResponse(BaseModel):
    """Response generated from semantic retrieval and grounded Groq synthesis."""

    answer: str = Field(..., description="Grounded answer synthesized from retrieved document chunks")
    sources: List[SourceReference] = Field(default_factory=list, description="Page-level source references")
    grounding_status: GroundingStatus = Field(..., description="Confidence in grounding")
    retrieval_status: Literal["SUCCESS", "NO_RELEVANT_CONTEXT", "FAILED"] = Field(...)
    document_id: Optional[str] = None
    chunks_retrieved: int = 0


class DocumentChunksResponse(BaseModel):
    """Debug response listing chunks indexed for a document."""

    document_id: str
    total_chunks: int
    chunks: List[DocumentChunk]

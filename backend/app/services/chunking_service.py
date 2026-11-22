import logging
import re
from typing import List, Optional, Tuple
from app.core.config import settings
from app.schemas.document_schemas import (
    DocumentChunk,
    DocumentChunkMetadata,
    DocumentPage,
)

logger = logging.getLogger("nitsetu.chunking")


class ChunkingService:
    """Intelligent, heading- and page-aware document text chunker.

    Divides extracted document text into semantic chunks respecting paragraph,
    section heading, and sentence boundaries. Preserves exact page-span provenance.
    """

    # Heading detection patterns for Indian statutory & policy documents
    HEADING_PATTERNS = [
        re.compile(r"^(Section\s+\d+[A-Z]*[\.\:\s\-].*)$", re.IGNORECASE | re.MULTILINE),
        re.compile(r"^(Article\s+\d+[A-Z]*[\.\:\s\-].*)$", re.IGNORECASE | re.MULTILINE),
        re.compile(r"^(Chapter\s+[IVXLCDM\d]+[\.\:\s\-].*)$", re.IGNORECASE | re.MULTILINE),
        re.compile(r"^(Rule\s+\d+[\.\:\s\-].*)$", re.IGNORECASE | re.MULTILINE),
        re.compile(r"^([A-Z\s]{4,}:.*)$", re.MULTILINE),
    ]

    def __init__(
        self,
        chunk_size_tokens: Optional[int] = None,
        chunk_overlap_tokens: Optional[int] = None,
        embedding_model_name: Optional[str] = None,
    ):
        # 1 token ~= 4 characters on average in multilingual context
        self.chunk_size_tokens = chunk_size_tokens or settings.DOCUMENT_CHUNK_SIZE
        self.chunk_overlap_tokens = chunk_overlap_tokens or settings.DOCUMENT_CHUNK_OVERLAP
        self.embedding_model_name = embedding_model_name or settings.EMBEDDING_MODEL_NAME

        self.chunk_size_chars = self.chunk_size_tokens * 4
        self.chunk_overlap_chars = self.chunk_overlap_tokens * 4

    def extract_heading(self, text: str) -> Optional[str]:
        """Identifies prominent legal or administrative section headings in text."""
        for pattern in self.HEADING_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1).strip()[:100]
        return None

    def chunk_document(
        self,
        pages: List[DocumentPage],
        document_id: str,
        user_id: str = "anonymous_citizen",
        source_filename: str = "document.pdf",
    ) -> List[DocumentChunk]:
        """Chunks a sequence of document pages into overlapping, metadata-rich chunks.

        Maintains accurate page provenance (page_start and page_end).
        """
        if not pages:
            return []

        # 1. Build a continuous sequence of tagged paragraphs: (paragraph_text, page_number)
        tagged_paragraphs: List[Tuple[str, int]] = []
        for page in pages:
            text = (page.text or "").strip()
            if not text:
                continue

            # Split on double newline (paragraphs)
            paras = text.split("\n\n")
            for p in paras:
                p_clean = p.strip()
                if p_clean:
                    tagged_paragraphs.append((p_clean, page.page_number))

        if not tagged_paragraphs:
            return []

        chunks: List[DocumentChunk] = []
        chunk_index = 0

        current_paras: List[str] = []
        current_pages: List[int] = []
        current_char_len = 0

        for para_text, page_num in tagged_paragraphs:
            para_len = len(para_text)
            is_new_heading = bool(self.extract_heading(para_text))
            size_exceeded = (current_char_len + para_len > self.chunk_size_chars)

            # If this paragraph starts a prominent section heading or exceeds chunk size
            if (is_new_heading or size_exceeded) and current_paras:
                # Finalize current chunk
                chunk_content = "\n\n".join(current_paras).strip()
                if chunk_content:
                    page_start = min(current_pages)
                    page_end = max(current_pages)
                    heading = self.extract_heading(chunk_content)
                    token_count = max(1, len(chunk_content) // 4)

                    chunk_meta = DocumentChunkMetadata(
                        document_id=document_id,
                        user_id=user_id,
                        chunk_id=f"{document_id}_chunk_{chunk_index}",
                        chunk_index=chunk_index,
                        page_number=page_start,
                        page_start=page_start,
                        page_end=page_end,
                        source_filename=source_filename,
                        section_heading=heading,
                        token_count=token_count,
                        embedding_model=self.embedding_model_name,
                    )

                    chunks.append(
                        DocumentChunk(
                            chunk_id=chunk_meta.chunk_id,
                            content=chunk_content,
                            metadata=chunk_meta,
                        )
                    )
                    chunk_index += 1

                # Carry over overlap paragraphs (skip carryover across distinct section headings)
                overlap_paras: List[str] = []
                overlap_pages: List[int] = []
                if not is_new_heading:
                    overlap_len = 0
                    for p_t, p_n in reversed(list(zip(current_paras, current_pages))):
                        if overlap_len + len(p_t) <= self.chunk_overlap_chars:
                            overlap_paras.insert(0, p_t)
                            overlap_pages.insert(0, p_n)
                            overlap_len += len(p_t)
                        else:
                            break

                current_paras = list(overlap_paras)
                current_pages = list(overlap_pages)
                current_char_len = sum(len(p) for p in current_paras)

            # Append current paragraph
            current_paras.append(para_text)
            current_pages.append(page_num)
            current_char_len += para_len

        # Finalize remaining text
        if current_paras:
            chunk_content = "\n\n".join(current_paras).strip()
            if chunk_content:
                page_start = min(current_pages)
                page_end = max(current_pages)
                heading = self.extract_heading(chunk_content)
                token_count = max(1, len(chunk_content) // 4)

                chunk_meta = DocumentChunkMetadata(
                    document_id=document_id,
                    user_id=user_id,
                    chunk_id=f"{document_id}_chunk_{chunk_index}",
                    chunk_index=chunk_index,
                    page_number=page_start,
                    page_start=page_start,
                    page_end=page_end,
                    source_filename=source_filename,
                    section_heading=heading,
                    token_count=token_count,
                    embedding_model=self.embedding_model_name,
                )

                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_meta.chunk_id,
                        content=chunk_content,
                        metadata=chunk_meta,
                    )
                )

        return chunks


# Default singleton instance
chunking_service = ChunkingService()

import logging
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.schemas.document_schemas import SourceReference
from app.services.embedding_service import embedding_service
from app.storage.chroma_storage import chroma_storage

logger = logging.getLogger("nitsetu.document_retrieval")


class DocumentRetrievalService:
    """Semantic vector retrieval service for citizen-uploaded documents.

    Generates query embeddings and queries ChromaDB with strict user ownership isolation
    and calibrated relevance threshold filtering.
    """

    def __init__(self):
        self.default_top_k = settings.DOCUMENT_RETRIEVAL_TOP_K
        self.default_threshold = settings.DOCUMENT_RETRIEVAL_THRESHOLD

    async def retrieve_relevant_chunks(
        self,
        query: str,
        user_id: str = "anonymous_citizen",
        document_id: Optional[str] = None,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves top-k semantically relevant chunks for a user query."""
        trimmed_query = (query or "").strip()
        if not trimmed_query:
            return []

        k = top_k or self.default_top_k
        if similarity_threshold is not None:
            cutoff = similarity_threshold
        else:
            cutoff = 0.20 if document_id else self.default_threshold

        # 1. Generate query vector embedding locally
        query_vector = embedding_service.embed_query(trimmed_query)

        # 2. Search ChromaDB with mandatory user isolation
        matched_chunks = chroma_storage.search_similar_chunks(
            query_embedding=query_vector,
            user_id=user_id,
            document_id=document_id,
            top_k=k,
            threshold=cutoff,
        )

        logger.info(
            f"Retrieved {len(matched_chunks)} relevant chunk(s) for query: '{trimmed_query[:40]}...' "
            f"(user={user_id}, doc={document_id}, threshold={cutoff})"
        )

        # 3. Log top-k chunks directly to terminal for inspection
        separator = "=" * 80
        thin_sep = "-" * 80
        print(f"\n{separator}", flush=True)
        print(f"🔍 [RAG RETRIEVAL] TOP-{k} CHUNKS (Found: {len(matched_chunks)}, Cutoff: {cutoff:.2f})", flush=True)
        print(f"Query: \"{trimmed_query}\"", flush=True)
        print(f"Document ID: {document_id or 'ALL_DOCUMENTS'} | User: {user_id}", flush=True)
        print(separator, flush=True)

        if not matched_chunks:
            print("⚠️ No chunks met the similarity threshold.", flush=True)
        else:
            for idx, c in enumerate(matched_chunks, 1):
                meta = c.get("metadata", {})
                p_start = meta.get("page_start", meta.get("page_number", 1))
                p_end = meta.get("page_end", p_start)
                page_str = f"Page {p_start}" if p_start == p_end else f"Pages {p_start}-{p_end}"
                filename = meta.get("source_filename", "document.pdf")
                heading = meta.get("section_heading")
                heading_str = f" | Section: '{heading}'" if heading else ""
                sim = c.get("similarity", 0.0)
                content = c.get("content", "").strip()

                print(f"\n📄 [Chunk {idx}/{len(matched_chunks)}] | {filename} ({page_str}){heading_str} | Similarity: {sim:.2%}", flush=True)
                print(f"ID: {c.get('chunk_id')}", flush=True)
                print(thin_sep, flush=True)
                print(content, flush=True)
                print(thin_sep, flush=True)

        print(f"{separator}\n", flush=True)

        return matched_chunks

    def format_source_references(
        self, matched_chunks: List[Dict[str, Any]]
    ) -> List[SourceReference]:
        """Converts raw retrieved chunks into clean, user-facing source references."""
        sources: List[SourceReference] = []
        for c in matched_chunks:
            meta = c.get("metadata", {})
            sources.append(
                SourceReference(
                    document_id=meta.get("document_id", ""),
                    filename=meta.get("source_filename", "uploaded_document.pdf"),
                    page_number=meta.get("page_number", 1),
                    page_start=meta.get("page_start", 1),
                    page_end=meta.get("page_end", 1),
                    chunk_id=c.get("chunk_id", ""),
                    similarity_score=c.get("similarity"),
                    snippet=c.get("content", "")[:200] + "..." if len(c.get("content", "")) > 200 else c.get("content", ""),
                )
            )
        return sources


# Default singleton instance
document_retrieval_service = DocumentRetrievalService()

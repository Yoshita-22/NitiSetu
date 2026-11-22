import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.schemas.document_schemas import DocumentChunk, DocumentChunkMetadata

logger = logging.getLogger("nitsetu.chroma")


class ChromaStorage:
    """Thread-safe persistent vector database integration using ChromaDB.

    Enforces mandatory user ownership isolation, idempotent document indexing,
    and cosine similarity semantic search. Includes resilient in-memory fallback.
    """

    COLLECTION_NAME = "nitsetu_document_chunks"

    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_directory = persist_directory or settings.CHROMA_PERSIST_DIRECTORY
        self._client = None
        self._collection = None
        self._lock = threading.Lock()

        # In-memory fallback structures if chromadb is unavailable
        self._fallback_mode = False
        self._in_memory_docs: Dict[str, Dict[str, Any]] = {}

    def _get_collection(self):
        """Lazy load persistent ChromaDB client and collection."""
        if self._collection is not None:
            return self._collection

        with self._lock:
            if self._collection is not None:
                return self._collection

            try:
                import chromadb
                from chromadb.config import Settings

                # Ensure directory exists
                persist_path = Path(self.persist_directory).resolve()
                persist_path.mkdir(parents=True, exist_ok=True)

                self._client = chromadb.PersistentClient(
                    path=str(persist_path),
                    settings=Settings(anonymized_telemetry=False, allow_reset=True),
                )
                self._collection = self._client.get_or_create_collection(
                    name=self.COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info(f"Initialized persistent ChromaDB at '{persist_path}'")
                self._fallback_mode = False
            except Exception as e:
                logger.warning(
                    f"ChromaDB initialization failed ({e}). Engaging in-memory fallback vector store."
                )
                self._fallback_mode = True
                self._collection = "FALLBACK_MEMORY"

        return self._collection

    def add_chunks(
        self, chunks: List[DocumentChunk], embeddings: List[List[float]]
    ) -> int:
        """Indexes document chunks into ChromaDB idempotently.

        Removes any existing chunks for this document before inserting.
        """
        if not chunks or not embeddings:
            return 0

        doc_id = chunks[0].metadata.document_id
        user_id = chunks[0].metadata.user_id

        # 1. Clean existing chunks first to ensure idempotency
        self.delete_document_chunks(doc_id, user_id=user_id)

        coll = self._get_collection()

        # 2. In-Memory Fallback Path
        if self._fallback_mode or coll == "FALLBACK_MEMORY":
            with self._lock:
                for chunk, emb in zip(chunks, embeddings):
                    self._in_memory_docs[chunk.chunk_id] = {
                        "chunk": chunk,
                        "embedding": emb,
                        "document_id": doc_id,
                        "user_id": user_id,
                    }
            return len(chunks)

        # 3. Persistent ChromaDB Path
        ids = [c.chunk_id for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [
            {
                "document_id": c.metadata.document_id,
                "user_id": c.metadata.user_id,
                "chunk_id": c.metadata.chunk_id,
                "chunk_index": c.metadata.chunk_index,
                "page_number": c.metadata.page_number,
                "page_start": c.metadata.page_start,
                "page_end": c.metadata.page_end,
                "source_filename": c.metadata.source_filename,
                "section_heading": c.metadata.section_heading or "",
                "token_count": c.metadata.token_count,
                "embedding_model": c.metadata.embedding_model,
            }
            for c in chunks
        ]

        with self._lock:
            coll.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

        logger.info(f"Indexed {len(chunks)} chunk(s) for document '{doc_id}' in ChromaDB")
        return len(chunks)

    def search_similar_chunks(
        self,
        query_embedding: List[float],
        user_id: str,
        document_id: Optional[str] = None,
        top_k: int = 5,
        threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Searches ChromaDB for semantically similar chunks with mandatory user isolation."""
        coll = self._get_collection()
        cutoff = threshold if threshold is not None else settings.DOCUMENT_RETRIEVAL_THRESHOLD

        # 1. Fallback In-Memory Cosine Search
        if self._fallback_mode or coll == "FALLBACK_MEMORY":
            return self._fallback_search(
                query_embedding=query_embedding,
                user_id=user_id,
                document_id=document_id,
                top_k=top_k,
                threshold=cutoff,
            )

        # 2. ChromaDB Filter Formulation (Mandatory user_id isolation with anonymous alias support)
        anonymous_ids = {"anonymous_citizen", "anonymous_dev"}
        allowed_users = [user_id]
        if user_id in anonymous_ids:
            allowed_users = list(anonymous_ids)

        user_filter = (
            {"user_id": {"$in": allowed_users}}
            if len(allowed_users) > 1
            else {"user_id": {"$eq": allowed_users[0]}}
        )

        if document_id:
            where_filter = {
                "$and": [
                    user_filter,
                    {"document_id": {"$eq": document_id}},
                ]
            }
        else:
            where_filter = user_filter

        try:
            with self._lock:
                results = coll.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    where=where_filter,
                    include=["documents", "metadatas", "distances"],
                )
        except Exception as e:
            logger.error(f"ChromaDB query error: {e}")
            return []

        if not results or not results.get("ids") or not results["ids"][0]:
            return []

        matched_chunks: List[Dict[str, Any]] = []
        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results.get("distances", [[]])[0]

        for i in range(len(ids)):
            # ChromaDB cosine distance: distance = 1 - cosine_similarity
            distance = distances[i] if i < len(distances) else 0.0
            similarity = max(0.0, min(1.0, 1.0 - distance))

            if similarity >= cutoff:
                meta = metadatas[i]
                matched_chunks.append({
                    "chunk_id": ids[i],
                    "content": documents[i],
                    "metadata": meta,
                    "similarity": round(similarity, 4),
                    "distance": round(distance, 4),
                })

        return matched_chunks

    def _fallback_search(
        self,
        query_embedding: List[float],
        user_id: str,
        document_id: Optional[str],
        top_k: int,
        threshold: float,
    ) -> List[Dict[str, Any]]:
        """Cosine similarity search for in-memory fallback store."""
        scored: List[Tuple[float, Dict[str, Any]]] = []
        anonymous_ids = {"anonymous_citizen", "anonymous_dev"}

        with self._lock:
            for item in self._in_memory_docs.values():
                # Enforce user isolation with anonymous alias support
                item_user = item.get("user_id", "")
                if item_user != user_id and not (item_user in anonymous_ids and user_id in anonymous_ids):
                    continue
                # Enforce document filter
                if document_id and item["document_id"] != document_id:
                    continue

                emb = item["embedding"]
                dot = sum(a * b for a, b in zip(query_embedding, emb))
                norm_q = sum(a * a for a in query_embedding) ** 0.5 or 1.0
                norm_d = sum(b * b for b in emb) ** 0.5 or 1.0
                sim = max(0.0, min(1.0, dot / (norm_q * norm_d)))

                if sim >= threshold:
                    chunk: DocumentChunk = item["chunk"]
                    scored.append((
                        sim,
                        {
                            "chunk_id": chunk.chunk_id,
                            "content": chunk.content,
                            "metadata": chunk.metadata.model_dump(),
                            "similarity": round(sim, 4),
                            "distance": round(1.0 - sim, 4),
                        },
                    ))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    def delete_document_chunks(self, document_id: str, user_id: Optional[str] = None) -> int:
        """Deletes all chunks belonging to a document."""
        coll = self._get_collection()

        if self._fallback_mode or coll == "FALLBACK_MEMORY":
            with self._lock:
                keys_to_remove = [
                    k for k, v in self._in_memory_docs.items()
                    if v["document_id"] == document_id and (not user_id or v["user_id"] == user_id)
                ]
                for k in keys_to_remove:
                    self._in_memory_docs.pop(k, None)
                return len(keys_to_remove)

        try:
            where_clause: Dict[str, Any] = {"document_id": {"$eq": document_id}}
            if user_id:
                where_clause = {
                    "$and": [
                        {"document_id": {"$eq": document_id}},
                        {"user_id": {"$eq": user_id}},
                    ]
                }
            with self._lock:
                coll.delete(where=where_clause)
            return 1
        except Exception as e:
            logger.warning(f"ChromaDB delete error for '{document_id}': {e}")
            return 0

    def get_document_chunks(
        self, document_id: str, user_id: Optional[str] = None
    ) -> List[DocumentChunk]:
        """Retrieves raw chunks for inspection."""
        coll = self._get_collection()

        if self._fallback_mode or coll == "FALLBACK_MEMORY":
            with self._lock:
                chunks = []
                for v in self._in_memory_docs.values():
                    if v["document_id"] == document_id and (not user_id or v["user_id"] == user_id):
                        chunks.append(v["chunk"])
                chunks.sort(key=lambda c: c.metadata.chunk_index)
                return chunks

        where_clause: Dict[str, Any] = {"document_id": {"$eq": document_id}}
        if user_id:
            where_clause = {
                "$and": [
                    {"document_id": {"$eq": document_id}},
                    {"user_id": {"$eq": user_id}},
                ]
            }

        try:
            with self._lock:
                res = coll.get(where=where_clause, include=["documents", "metadatas"])
            chunks = []
            if res and res.get("ids"):
                for cid, doc, meta in zip(res["ids"], res["documents"], res["metadatas"]):
                    chunks.append(
                        DocumentChunk(
                            chunk_id=cid,
                            content=doc,
                            metadata=DocumentChunkMetadata(**meta),
                        )
                    )
            chunks.sort(key=lambda c: c.metadata.chunk_index)
            return chunks
        except Exception as e:
            logger.error(f"Error getting chunks for '{document_id}': {e}")
            return []

    def count_chunks(self, document_id: Optional[str] = None) -> int:
        """Returns total count of chunks stored."""
        coll = self._get_collection()
        if self._fallback_mode or coll == "FALLBACK_MEMORY":
            with self._lock:
                if document_id:
                    return sum(1 for v in self._in_memory_docs.values() if v["document_id"] == document_id)
                return len(self._in_memory_docs)

        try:
            if document_id:
                with self._lock:
                    res = coll.get(where={"document_id": {"$eq": document_id}}, include=[])
                return len(res["ids"]) if res and res.get("ids") else 0
            with self._lock:
                return coll.count()
        except Exception:
            return 0


# Default singleton instance
chroma_storage = ChromaStorage()

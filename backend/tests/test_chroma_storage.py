import pytest
from app.schemas.document_schemas import DocumentChunk, DocumentChunkMetadata
from app.services.embedding_service import embedding_service
from app.storage.chroma_storage import ChromaStorage


@pytest.fixture
def temp_chroma(tmp_path):
    """Fixture providing an isolated ChromaStorage instance using temporary directory."""
    chroma_dir = tmp_path / "chroma_test_store"
    storage = ChromaStorage(persist_directory=str(chroma_dir))
    return storage


def test_chroma_storage_add_and_search(temp_chroma):
    """Verify storing chunks and performing semantic vector retrieval."""
    content_1 = "The Ministry of Agriculture announced that PM Kisan installments will be released on March 15."
    content_2 = "Consumer Protection Act Section 21 empowers the Central Authority to issue safety notices."

    chunks = [
        DocumentChunk(
            chunk_id="doc1_chunk_0",
            content=content_1,
            metadata=DocumentChunkMetadata(
                document_id="doc_alpha",
                user_id="user_farmer_1",
                chunk_id="doc1_chunk_0",
                chunk_index=0,
                page_number=1,
                page_start=1,
                page_end=1,
                source_filename="pm_kisan_order.pdf",
                token_count=18,
                embedding_model="test-embedder",
            ),
        ),
        DocumentChunk(
            chunk_id="doc1_chunk_1",
            content=content_2,
            metadata=DocumentChunkMetadata(
                document_id="doc_alpha",
                user_id="user_farmer_1",
                chunk_id="doc1_chunk_1",
                chunk_index=1,
                page_number=2,
                page_start=2,
                page_end=2,
                source_filename="pm_kisan_order.pdf",
                token_count=16,
                embedding_model="test-embedder",
            ),
        ),
    ]

    embs = embedding_service.embed_documents([c.content for c in chunks])
    count = temp_chroma.add_chunks(chunks, embs)
    assert count == 2

    # Query matching chunk 1
    query = "When will PM Kisan installments be released?"
    q_emb = embedding_service.embed_query(query)

    results = temp_chroma.search_similar_chunks(
        query_embedding=q_emb,
        user_id="user_farmer_1",
        document_id="doc_alpha",
        top_k=2,
        threshold=0.0,
    )
    assert len(results) > 0
    top_result = results[0]
    assert "PM Kisan" in top_result["content"]
    assert top_result["metadata"]["document_id"] == "doc_alpha"


def test_chroma_storage_user_isolation(temp_chroma):
    """Verify strict user ownership isolation: User B cannot retrieve User A's chunks."""
    chunk = DocumentChunk(
        chunk_id="private_doc_chunk_0",
        content="Confidential personal income certificate of citizen John Doe.",
        metadata=DocumentChunkMetadata(
            document_id="doc_private_001",
            user_id="user_john",
            chunk_id="private_doc_chunk_0",
            chunk_index=0,
            page_number=1,
            page_start=1,
            page_end=1,
            source_filename="income_cert.pdf",
            token_count=10,
            embedding_model="test-embedder",
        ),
    )
    embs = embedding_service.embed_documents([chunk.content])
    temp_chroma.add_chunks([chunk], embs)

    # Search with another user's ID
    q_emb = embedding_service.embed_query("income certificate")
    results_unauthorized = temp_chroma.search_similar_chunks(
        query_embedding=q_emb,
        user_id="user_intruder",
        top_k=5,
        threshold=0.0,
    )
    assert len(results_unauthorized) == 0

    # Search with authorized user's ID
    results_authorized = temp_chroma.search_similar_chunks(
        query_embedding=q_emb,
        user_id="user_john",
        top_k=5,
        threshold=0.0,
    )
    assert len(results_authorized) == 1
    assert results_authorized[0]["chunk_id"] == "private_doc_chunk_0"


def test_chroma_storage_idempotent_reindexing(temp_chroma):
    """Verify that re-indexing the same document overwrites cleanly without creating duplicate chunks."""
    chunk = DocumentChunk(
        chunk_id="repeat_chunk_0",
        content="Initial notice content version 1.",
        metadata=DocumentChunkMetadata(
            document_id="doc_repeat",
            user_id="user_repeat",
            chunk_id="repeat_chunk_0",
            chunk_index=0,
            page_number=1,
            page_start=1,
            page_end=1,
            source_filename="notice.pdf",
            token_count=6,
            embedding_model="test-embedder",
        ),
    )
    embs = embedding_service.embed_documents([chunk.content])
    temp_chroma.add_chunks([chunk], embs)
    assert temp_chroma.count_chunks("doc_repeat") == 1

    # Re-index with updated content under the same document_id
    updated_chunk = DocumentChunk(
        chunk_id="repeat_chunk_0_v2",
        content="Updated notice content version 2 with amendments.",
        metadata=DocumentChunkMetadata(
            document_id="doc_repeat",
            user_id="user_repeat",
            chunk_id="repeat_chunk_0_v2",
            chunk_index=0,
            page_number=1,
            page_start=1,
            page_end=1,
            source_filename="notice.pdf",
            token_count=8,
            embedding_model="test-embedder",
        ),
    )
    updated_embs = embedding_service.embed_documents([updated_chunk.content])
    temp_chroma.add_chunks([updated_chunk], updated_embs)

    # Must still only have 1 chunk for this document
    assert temp_chroma.count_chunks("doc_repeat") == 1
    chunks = temp_chroma.get_document_chunks("doc_repeat", user_id="user_repeat")
    assert len(chunks) == 1
    assert "version 2" in chunks[0].content


def test_chroma_storage_deletion(temp_chroma):
    """Verify document chunks are completely removed upon deletion."""
    chunk = DocumentChunk(
        chunk_id="del_chunk_0",
        content="Temporary document content.",
        metadata=DocumentChunkMetadata(
            document_id="doc_del",
            user_id="user_del",
            chunk_id="del_chunk_0",
            chunk_index=0,
            page_number=1,
            page_start=1,
            page_end=1,
            source_filename="temp.pdf",
            token_count=4,
            embedding_model="test-embedder",
        ),
    )
    temp_chroma.add_chunks([chunk], embedding_service.embed_documents([chunk.content]))
    assert temp_chroma.count_chunks("doc_del") == 1

    temp_chroma.delete_document_chunks("doc_del", user_id="user_del")
    assert temp_chroma.count_chunks("doc_del") == 0

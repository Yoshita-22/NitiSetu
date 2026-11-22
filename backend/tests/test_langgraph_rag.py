import pytest
from langgraph.checkpoint.memory import MemorySaver
from app.graph.workflow import build_nitsetu_graph
from app.repositories.document_repository import document_repository
from app.schemas.document_schemas import DocumentMetadata, DocumentPage
from app.services.document_service import document_service


@pytest.fixture(scope="module")
def indexed_test_document():
    """Setup a sample government gazette for LangGraph RAG integration testing."""
    doc_id = "langgraph_rag_doc_777"
    user_id = "test_lg_citizen"

    pages = [
        DocumentPage(
            page_number=1,
            text=(
                "Ministry of Social Justice and Empowerment.\n"
                "Notification on Scholarship Disbursements.\n\n"
                "All eligible post-matric students shall receive direct bank transfer within 45 days. "
                "Minimum attendance requirement is set at 75% for continuation of scholarship."
            ),
            word_count=35,
            character_count=240,
        )
    ]

    meta = DocumentMetadata(
        document_id=doc_id,
        original_filename="scholarship_circular_2026.pdf",
        file_size_bytes=25000,
        file_type="application/pdf",
        page_count=1,
        upload_timestamp="2026-11-22T10:00:00Z",
        processing_status="EXTRACTED",
        owner_id=user_id,
    )

    document_repository.save_document(meta, pages)
    document_service.index_document(doc_id, owner_id=user_id)

    yield doc_id, user_id

    document_service.delete_document(doc_id, owner_id=user_id)


@pytest.mark.asyncio
async def test_langgraph_document_query_rag_flow(indexed_test_document):
    """Verify that DOCUMENT_QUERY intent triggers the upgraded document retrieval node,
    performs semantic RAG, and produces page-cited responses in the graph."""
    doc_id, user_id = indexed_test_document
    test_graph = build_nitsetu_graph(checkpointer=MemorySaver())

    initial_state = {
        "user_query": "What is the minimum attendance requirement in this document?",
        "conversation_id": "lg_rag_conv_01",
        "user_id": user_id,
        "document_id": doc_id,
        "law_results": [],
        "scheme_results": [],
        "document_results": [],
        "applicant_details": {},
        "errors": [],
        "task_status": {},
    }

    config = {"configurable": {"thread_id": "lg_rag_conv_01"}}
    res = await test_graph.ainvoke(initial_state, config=config)

    assert res.get("workflow_status") == "COMPLETED"
    task_status = res.get("task_status", {})
    assert task_status.get("document_retrieval") == "COMPLETED"

    # Verify RAG answer received context
    doc_results = res.get("document_results", [])
    assert len(doc_results) > 0
    doc_res = doc_results[0]
    assert "answer" in doc_res

    # Citations in response metadata
    citations = res.get("response_metadata", {}).get("citations", [])
    assert len(citations) > 0
    assert any("scholarship_circular_2026.pdf" in c.get("title", "") for c in citations)


@pytest.mark.asyncio
async def test_langgraph_multi_intent_document_and_law(indexed_test_document):
    """Verify parallel execution of Document RAG and NyayKosh Law Search preserves both results."""
    doc_id, user_id = indexed_test_document
    test_graph = build_nitsetu_graph(checkpointer=MemorySaver())

    initial_state = {
        "user_query": "Check this scholarship document and also explain Section 302 of IPC",
        "conversation_id": "lg_multi_doc_law_01",
        "user_id": user_id,
        "document_id": doc_id,
        "law_results": [],
        "scheme_results": [],
        "document_results": [],
        "applicant_details": {},
        "errors": [],
        "task_status": {},
    }

    config = {"configurable": {"thread_id": "lg_multi_doc_law_01"}}
    res = await test_graph.ainvoke(initial_state, config=config)

    assert res.get("workflow_status") == "COMPLETED"
    task_status = res.get("task_status", {})

    # Both parallel branches must be completed
    assert task_status.get("document_retrieval") == "COMPLETED"
    assert task_status.get("law_retrieval") == "COMPLETED"

    # Both results must be present
    assert len(res.get("document_results", [])) > 0
    assert len(res.get("law_results", [])) > 0

    # Citations should include both document and NyayKosh
    citations = res.get("response_metadata", {}).get("citations", [])
    types = [c.get("type", "") for c in citations]
    assert any("uploaded_user_pdf" in t for t in types)
    assert any("nyaykosh" in t for t in types)

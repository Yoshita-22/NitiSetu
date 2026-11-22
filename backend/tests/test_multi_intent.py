import pytest
from langgraph.checkpoint.memory import MemorySaver
from app.graph.workflow import build_nitsetu_graph


@pytest.mark.asyncio
async def test_multi_intent_aggregation_and_citations():
    """Verify that multi-intent execution aggregates multiple domain results
    and generates citations that distinguish live NeGD NyayKosh laws from verified demo scheme data."""
    test_graph = build_nitsetu_graph(checkpointer=MemorySaver())

    initial_state = {
        "user_query": "Explain Ayushman Bharat scheme and consumer rights under Consumer Protection Act",
        "conversation_id": "test_multi_001",
        "document_id": None,
        "law_results": [],
        "scheme_results": [],
        "document_results": [],
        "applicant_details": {},
        "errors": [],
        "task_status": {},
    }

    config = {"configurable": {"thread_id": "test_multi_001"}}
    res = await test_graph.ainvoke(initial_state, config=config)

    assert res.get("workflow_status") == "COMPLETED"
    citations = res.get("response_metadata", {}).get("citations", [])
    assert len(citations) >= 2

    # Check source badges distinguish the two sources
    nyaykosh_citations = [c for c in citations if "NyayKosh" in str(c.get("source", ""))]
    scheme_citations = [c for c in citations if "Verified Demo" in str(c.get("source", "")) or "Official Government" in str(c.get("source", ""))]
    assert len(nyaykosh_citations) > 0
    assert len(scheme_citations) > 0


@pytest.mark.asyncio
async def test_multi_intent_partial_failure():
    """Verify that when one branch fails (e.g., document not found),
    the workflow continues, aggregates the successful branch (law), and marks partial_failure=True."""
    test_graph = build_nitsetu_graph(checkpointer=MemorySaver())

    initial_state = {
        "user_query": "Check this document and explain Right to Information Act",
        "conversation_id": "test_partial_001",
        "document_id": "nonexistent-doc-uuid-99999",
        "law_results": [],
        "scheme_results": [],
        "document_results": [],
        "applicant_details": {},
        "errors": [],
        "task_status": {},
    }

    config = {"configurable": {"thread_id": "test_partial_001"}}
    res = await test_graph.ainvoke(initial_state, config=config)

    assert res.get("workflow_status") == "COMPLETED"
    task_status = res.get("task_status", {})

    # Law should have succeeded or run
    assert task_status.get("law_retrieval") == "COMPLETED"

    # Response metadata should indicate partial failure or document failure
    meta = res.get("response_metadata", {})
    assert meta.get("partial_failure") is True or len(res.get("errors", [])) > 0
    assert len(res.get("law_results", [])) > 0

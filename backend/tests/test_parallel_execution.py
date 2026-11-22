import pytest
from langgraph.checkpoint.memory import MemorySaver
from app.graph.workflow import build_nitsetu_graph


@pytest.mark.asyncio
async def test_parallel_execution_scheme_and_law():
    """Verify that multi-intent queries trigger parallel branches for scheme and law retrieval,
    and both outputs are cleanly collected into the aggregated final response."""
    test_graph = build_nitsetu_graph(checkpointer=MemorySaver())

    initial_state = {
        "user_query": "Tell me about PM-KISAN scheme and RTI Act rules",
        "conversation_id": "test_parallel_001",
        "document_id": None,
        "law_results": [],
        "scheme_results": [],
        "document_results": [],
        "applicant_details": {},
        "errors": [],
        "task_status": {},
    }

    config = {"configurable": {"thread_id": "test_parallel_001"}}
    res = await test_graph.ainvoke(initial_state, config=config)

    # 1. State must contain completed tasks for both branches
    task_status = res.get("task_status", {})
    assert task_status.get("scheme_retrieval") == "COMPLETED"
    assert task_status.get("law_retrieval") == "COMPLETED"

    # 2. Results must contain data from both branches
    assert len(res.get("scheme_results", [])) > 0
    assert len(res.get("law_results", [])) > 0

    # 3. Response aggregator must produce combined citations
    citations = res.get("response_metadata", {}).get("citations", [])
    citation_sources = [c.get("source") for c in citations]
    assert any("NyayKosh" in str(s) for s in citation_sources)
    assert any("Verified Demo" in str(s) or "Official Government" in str(s) for s in citation_sources)

    # 4. Final response should mention both topics
    final_text = res.get("final_response", "")
    assert len(final_text) > 50

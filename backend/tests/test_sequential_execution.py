import pytest
from langgraph.checkpoint.memory import MemorySaver
from app.graph.workflow import build_nitsetu_graph


@pytest.mark.asyncio
async def test_sequential_eligibility_fully_provided():
    """Verify that when applicant details are fully provided upfront,
    the workflow resolves the scheme, evaluates eligibility sequentially, and completes."""
    test_graph = build_nitsetu_graph(checkpointer=MemorySaver())

    # PM-KISAN required questions: is_landholding_farmer, holds_constitutional_post, is_income_tax_payer, is_government_employee
    full_applicant_details = {
        "is_landholding_farmer": True,
        "holds_constitutional_post": False,
        "is_income_tax_payer": False,
        "is_government_employee": False,
    }

    initial_state = {
        "user_query": "Check my PM-KISAN eligibility",
        "conversation_id": "test_seq_001",
        "document_id": None,
        "law_results": [],
        "scheme_results": [],
        "document_results": [],
        "applicant_details": full_applicant_details,
        "errors": [],
        "task_status": {},
    }

    config = {"configurable": {"thread_id": "test_seq_001"}}
    res = await test_graph.ainvoke(initial_state, config=config)

    # Should not be interrupted because all details are supplied
    assert "__interrupt__" not in res or not res["__interrupt__"]
    assert res.get("workflow_status") == "COMPLETED"
    assert "eligibility_results" in res
    assert res["eligibility_results"]["overall_result"] == "LIKELY_ELIGIBLE"
    assert res.get("task_status", {}).get("eligibility_workflow") == "COMPLETED"

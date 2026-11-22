import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from app.graph.workflow import build_nitsetu_graph


@pytest.mark.asyncio
async def test_checkpoint_thread_isolation():
    """Verify that multiple conversation threads maintain isolated state checkpoints."""
    checkpointer = MemorySaver()
    test_graph = build_nitsetu_graph(checkpointer=checkpointer)

    thread_a = "thread_alpha"
    thread_b = "thread_beta"

    config_a = {"configurable": {"thread_id": thread_a}}
    config_b = {"configurable": {"thread_id": thread_b}}

    # Thread A asks for eligibility (pauses)
    state_a = {
        "user_query": "Check PM-KISAN eligibility",
        "conversation_id": thread_a,
        "document_id": None,
        "law_results": [],
        "scheme_results": [],
        "document_results": [],
        "applicant_details": {},
        "errors": [],
        "task_status": {},
    }
    res_a = await test_graph.ainvoke(state_a, config=config_a)
    assert "__interrupt__" in res_a

    # Thread B asks for law information (completes directly)
    state_b = {
        "user_query": "What is Section 302 of IPC?",
        "conversation_id": thread_b,
        "document_id": None,
        "law_results": [],
        "scheme_results": [],
        "document_results": [],
        "applicant_details": {},
        "errors": [],
        "task_status": {},
    }
    res_b = await test_graph.ainvoke(state_b, config=config_b)
    assert res_b.get("workflow_status") == "COMPLETED"
    assert len(res_b.get("law_results", [])) > 0

    # Verify Thread A is still paused in checkpointer
    saved_state_a = await test_graph.aget_state(config_a)
    assert len(saved_state_a.tasks) > 0
    assert saved_state_a.next == ("eligibility_workflow_node",)

    # Resume Thread A without affecting Thread B
    answers_a = {
        "is_landholding_farmer": False,
        "holds_constitutional_post": True,
        "is_income_tax_payer": False,
        "is_government_employee": False,
    }
    resumed_a = await test_graph.ainvoke(Command(resume=answers_a), config=config_a)
    assert resumed_a.get("workflow_status") == "COMPLETED"
    assert resumed_a["eligibility_results"]["overall_result"] == "LIKELY_NOT_ELIGIBLE"

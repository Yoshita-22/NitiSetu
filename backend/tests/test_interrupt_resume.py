import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from app.graph.workflow import build_nitsetu_graph


@pytest.mark.asyncio
async def test_interrupt_and_resume_eligibility_flow():
    """Verify human-in-the-loop interruption when scheme details are missing,
    followed by resumption using Command(resume=answers)."""
    checkpointer = MemorySaver()
    test_graph = build_nitsetu_graph(checkpointer=checkpointer)

    thread_id = "test_hitl_thread_001"
    config = {"configurable": {"thread_id": thread_id}}

    # 1. Citizen asks for eligibility without providing applicant details
    initial_state = {
        "user_query": "Am I eligible for PM-KISAN?",
        "conversation_id": thread_id,
        "document_id": None,
        "law_results": [],
        "scheme_results": [],
        "document_results": [],
        "applicant_details": {},
        "errors": [],
        "task_status": {},
    }

    paused_res = await test_graph.ainvoke(initial_state, config=config)

    # 2. Verify graph paused with interrupt
    assert "__interrupt__" in paused_res
    interrupt_items = paused_res["__interrupt__"]
    assert len(interrupt_items) > 0
    interrupt_data = interrupt_items[0].value

    assert interrupt_data["type"] == "eligibility_questions"
    assert interrupt_data["scheme_id"] == "PM_KISAN"
    assert len(interrupt_data["questions"]) > 0

    # 3. Verify state in checkpointer
    saved_state = await test_graph.aget_state(config)
    assert saved_state.next == ("eligibility_workflow_node",)

    # 4. Citizen provides missing answers and resumes
    provided_answers = {
        "is_landholding_farmer": True,
        "holds_constitutional_post": False,
        "is_income_tax_payer": False,
        "is_government_employee": False,
    }

    resumed_res = await test_graph.ainvoke(Command(resume=provided_answers), config=config)

    # 5. Verify graph finished without further interrupts
    assert "__interrupt__" not in resumed_res or not resumed_res["__interrupt__"]
    assert resumed_res.get("workflow_status") == "COMPLETED"
    assert "eligibility_results" in resumed_res
    assert resumed_res["eligibility_results"]["overall_result"] == "LIKELY_ELIGIBLE"
    assert "final_response" in resumed_res
    assert len(resumed_res["final_response"]) > 20

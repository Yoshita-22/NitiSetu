import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from starlette.testclient import TestClient

from app.graph.workflow import build_nitsetu_graph
from app.main import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_langgraph_turn_by_turn_question_progression():
    """Verify LangGraph pauses and resumes turn-by-turn through multiple dialogue turns."""
    checkpointer = MemorySaver()
    test_graph = build_nitsetu_graph(checkpointer=checkpointer)

    thread_id = "test_multi_turn_graph_001"
    config = {"configurable": {"thread_id": thread_id}}

    # Turn 0: Initiate eligibility inquiry without answers
    res = await test_graph.ainvoke(
        {
            "user_query": "Am I eligible for PM-KISAN scheme?",
            "conversation_id": thread_id,
            "document_id": None,
            "law_results": [],
            "scheme_results": [],
            "document_results": [],
            "applicant_details": {},
            "errors": [],
            "task_status": {},
        },
        config=config,
    )

    # Must pause on question 1: is_landholding_farmer
    assert "__interrupt__" in res
    interrupt_data = res["__interrupt__"][0].value
    assert interrupt_data["scheme_id"] == "PM_KISAN"
    assert interrupt_data["current_question"]["field"] == "is_landholding_farmer"

    # Turn 1: Answer question 1 with natural language
    res = await test_graph.ainvoke(
        Command(resume="Yes, our family owns 4 acres of farmland in Guntur."),
        config=config,
    )

    # Must pause on question 2: holds_constitutional_post
    assert "__interrupt__" in res
    interrupt_data = res["__interrupt__"][0].value
    assert interrupt_data["current_question"]["field"] == "holds_constitutional_post"

    # Turn 2: Answer question 2 with natural language
    res = await test_graph.ainvoke(
        Command(resume="No, nobody holds any constitutional posts or political office."),
        config=config,
    )

    # Must pause on question 3: is_government_employee
    assert "__interrupt__" in res
    interrupt_data = res["__interrupt__"][0].value
    assert interrupt_data["current_question"]["field"] == "is_government_employee"

    # Turn 3: Answer question 3 with natural language
    res = await test_graph.ainvoke(
        Command(resume="No government employees in our household."),
        config=config,
    )

    # Must pause on question 4: is_income_tax_payer
    assert "__interrupt__" in res
    interrupt_data = res["__interrupt__"][0].value
    assert interrupt_data["current_question"]["field"] == "is_income_tax_payer"

    # Turn 4: Answer final required question
    res = await test_graph.ainvoke(
        Command(resume="No, we do not pay income tax."),
        config=config,
    )

    # Workflow must complete with deterministic evaluation
    assert "__interrupt__" not in res or not res["__interrupt__"]
    assert res.get("workflow_status") == "COMPLETED"
    assert "eligibility_results" in res
    assert res["eligibility_results"]["overall_result"] == "LIKELY_ELIGIBLE"
    assert res["applicant_details"]["is_landholding_farmer"] is True
    assert res["applicant_details"]["holds_constitutional_post"] is False
    assert res["applicant_details"]["is_government_employee"] is False
    assert res["applicant_details"]["is_income_tax_payer"] is False


@pytest.mark.asyncio
async def test_langgraph_composite_multi_answer_progression():
    """Verify initial utterance answering multiple criteria skips to remaining questions."""
    checkpointer = MemorySaver()
    test_graph = build_nitsetu_graph(checkpointer=checkpointer)

    thread_id = "test_composite_graph_002"
    config = {"configurable": {"thread_id": thread_id}}

    # Initial query provides 3 criteria answers upfront:
    # 1. owns agricultural land (is_landholding_farmer: True)
    # 2. no constitutional posts (holds_constitutional_post: False)
    # 3. no government jobs (is_government_employee: False)
    res = await test_graph.ainvoke(
        {
            "user_query": "Check PM-KISAN eligibility. We have agricultural land, no constitutional posts, and no one is in government job.",
            "conversation_id": thread_id,
            "document_id": None,
            "law_results": [],
            "scheme_results": [],
            "document_results": [],
            "applicant_details": {},
            "errors": [],
            "task_status": {},
        },
        config=config,
    )

    # Graph must skip the 3 answered criteria and interrupt directly on is_income_tax_payer (Order 4)
    assert "__interrupt__" in res
    interrupt_data = res["__interrupt__"][0].value
    assert interrupt_data["current_question"]["field"] == "is_income_tax_payer"

    # Resume with answer to Question 4
    res = await test_graph.ainvoke(
        Command(resume="No, we never paid income tax."),
        config=config,
    )

    assert "__interrupt__" not in res or not res["__interrupt__"]
    assert res.get("workflow_status") == "COMPLETED"
    assert res["eligibility_results"]["overall_result"] == "LIKELY_ELIGIBLE"


@pytest.mark.asyncio
async def test_langgraph_ambiguous_clarification_loop():
    """Verify ambiguous statements cause graph to re-prompt for clarification on the same question."""
    checkpointer = MemorySaver()
    test_graph = build_nitsetu_graph(checkpointer=checkpointer)

    thread_id = "test_ambig_graph_003"
    config = {"configurable": {"thread_id": thread_id}}

    # Start inquiry
    res = await test_graph.ainvoke(
        {
            "user_query": "Am I eligible for PM-KISAN?",
            "conversation_id": thread_id,
            "document_id": None,
            "law_results": [],
            "scheme_results": [],
            "document_results": [],
            "applicant_details": {},
            "errors": [],
            "task_status": {},
        },
        config=config,
    )
    assert res["__interrupt__"][0].value["current_question"]["field"] == "is_landholding_farmer"

    # User gives an ambiguous statement
    res = await test_graph.ainvoke(
        Command(resume="Maybe, sometimes my brother uses the land."),
        config=config,
    )

    # Must stay on is_landholding_farmer and mark clarification_required = True
    assert "__interrupt__" in res
    interrupt_data = res["__interrupt__"][0].value
    assert interrupt_data["current_question"]["field"] == "is_landholding_farmer"
    assert interrupt_data["clarification_required"] is True

    # User provides clear confirmation
    res = await test_graph.ainvoke(
        Command(resume="Yes, the land is officially registered in my name."),
        config=config,
    )

    # Must now advance to holds_constitutional_post
    assert "__interrupt__" in res
    interrupt_data = res["__interrupt__"][0].value
    assert interrupt_data["current_question"]["field"] == "holds_constitutional_post"
    assert interrupt_data["clarification_required"] is False


@pytest.mark.asyncio
async def test_langgraph_unknown_and_refusal_preservation():
    """Verify UNKNOWN and PREFER_NOT_TO_ANSWER are preserved honestly into evaluation."""
    checkpointer = MemorySaver()
    test_graph = build_nitsetu_graph(checkpointer=checkpointer)

    thread_id = "test_unknown_graph_004"
    config = {"configurable": {"thread_id": thread_id}}

    # Turn 0: Start
    await test_graph.ainvoke(
        {
            "user_query": "Check PM-KISAN eligibility",
            "conversation_id": thread_id,
            "document_id": None,
            "law_results": [],
            "scheme_results": [],
            "document_results": [],
            "applicant_details": {},
            "errors": [],
            "task_status": {},
        },
        config=config,
    )

    # Turn 1: Yes
    await test_graph.ainvoke(Command(resume="Yes, we own farmland"), config=config)

    # Turn 2: I don't know (UNKNOWN)
    await test_graph.ainvoke(Command(resume="I don't know"), config=config)

    # Turn 3: Refusal (PREFER_NOT_TO_ANSWER)
    await test_graph.ainvoke(Command(resume="I prefer not to say"), config=config)

    # Turn 4: No
    res = await test_graph.ainvoke(Command(resume="No income tax"), config=config)

    # Must complete evaluation
    assert res.get("workflow_status") == "COMPLETED"
    assert "eligibility_results" in res
    # UNKNOWN criteria must result in NEEDS_MORE_INFORMATION, NOT false disqualified!
    assert res["eligibility_results"]["overall_result"] == "NEEDS_MORE_INFORMATION"
    # Neither unknown nor refusal should appear in clean applicant details
    assert "holds_constitutional_post" not in res["applicant_details"]
    assert "is_government_employee" not in res["applicant_details"]


def test_chat_query_natural_language_multi_turn_continuation():
    """Verify that posting natural language messages to /api/v1/chat/query
    automatically resumes paused conversational threads without requiring /resume."""
    conv_id = "test_chat_nl_continuation_005"

    # Turn 1: Citizen asks initial question
    resp1 = client.post(
        "/api/v1/chat/query",
        json={"conversation_id": conv_id, "message": "Am I eligible for PM-KISAN?"},
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "waiting_for_user"
    assert len(data1["pending_questions"]) > 0
    assert data1["pending_questions"][0]["field"] == "is_landholding_farmer"

    # Turn 2: Citizen naturally replies to /query (NOT /resume!)
    resp2 = client.post(
        "/api/v1/chat/query",
        json={"conversation_id": conv_id, "message": "Yes, our family owns 5 acres of agricultural land."},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "waiting_for_user"
    assert len(data2["pending_questions"]) > 0
    # Advanced to holds_constitutional_post!
    assert data2["pending_questions"][0]["field"] == "holds_constitutional_post"

    # Turn 3: Complete remaining criteria via /resume
    resp3 = client.post(
        "/api/v1/chat/resume",
        json={
            "conversation_id": conv_id,
            "answers": {
                "holds_constitutional_post": False,
                "is_government_employee": False,
                "is_income_tax_payer": False,
            },
        },
    )
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["status"] == "completed"
    assert data3["results"]["eligibility_results"]["overall_result"] == "LIKELY_ELIGIBLE"

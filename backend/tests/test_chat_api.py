import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_chat_query_law_direct():
    """Verify POST /api/v1/chat/query directly completes for a legal question."""
    payload = {
        "conversation_id": "api_test_conv_law_001",
        "message": "What is Section 302 of Indian Penal Code?",
    }
    response = client.post("/api/v1/chat/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "completed"
    assert data["conversation_id"] == "api_test_conv_law_001"
    assert data["intent"] == "LAW_INFORMATION"
    assert len(data["answer"]) > 10
    assert "law_results" in data["results"]
    assert len(data["sources"]) > 0


def test_chat_query_scheme_direct():
    """Verify POST /api/v1/chat/query returns scheme info for general scheme inquiry."""
    payload = {
        "conversation_id": "api_test_conv_scheme_001",
        "message": "Tell me about Ayushman Bharat PM-JAY scheme",
    }
    response = client.post("/api/v1/chat/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "completed"
    assert "scheme_results" in data["results"]


def test_chat_query_eligibility_interrupt_and_resume():
    """Verify full end-to-end API lifecycle:
    1. Query triggers interrupt and returns waiting_for_user with pending_questions.
    2. Resume supplies answers and returns completed with eligibility evaluation."""
    conv_id = "api_test_conv_hitl_002"

    # Step 1: Initial query without applicant details
    query_payload = {
        "conversation_id": conv_id,
        "message": "Am I eligible for PM-KISAN scheme?",
    }
    response1 = client.post("/api/v1/chat/query", json=query_payload)
    assert response1.status_code == 200
    data1 = response1.json()

    assert data1["status"] == "waiting_for_user"
    assert len(data1["pending_questions"]) > 0
    question_fields = [q["field"] for q in data1["pending_questions"]]
    assert "is_landholding_farmer" in question_fields

    # Step 2: Resume with answers
    resume_payload = {
        "conversation_id": conv_id,
        "answers": {
            "is_landholding_farmer": True,
            "holds_constitutional_post": False,
            "is_income_tax_payer": False,
            "is_government_employee": False,
        },
    }
    response2 = client.post("/api/v1/chat/resume", json=resume_payload)
    assert response2.status_code == 200
    data2 = response2.json()

    assert data2["status"] == "completed"
    assert "eligibility_results" in data2["results"]
    assert data2["results"]["eligibility_results"]["overall_result"] == "LIKELY_ELIGIBLE"
    assert len(data2["pending_questions"]) == 0

    # Step 3: Check conversation history endpoint
    history_resp = client.get(f"/api/v1/chat/history/{conv_id}")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) >= 3  # user query, assistant prompt, user answers, assistant final


def test_chat_conversations_listing():
    """Verify GET /api/v1/chat/conversations returns active conversation list."""
    response = client.get("/api/v1/chat/conversations")
    assert response.status_code == 200
    conversations = response.json()
    assert isinstance(conversations, list)

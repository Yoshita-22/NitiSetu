import pytest
from starlette.testclient import TestClient

from app.main import app
from app.schemas.eligibility_schemas import AssessmentStatusResponse
from app.schemas.scheme_schemas import EligibilityEvaluationResponse

client = TestClient(app)


def test_start_assessment_endpoints():
    """Verify both /eligibility/start and /schemes/{scheme_id}/eligibility/start endpoints."""
    conv_id_1 = "api_test_start_001"
    payload_1 = {
        "conversation_id": conv_id_1,
        "scheme_id": "PM_KISAN",
        "language": "en",
    }
    resp1 = client.post("/api/v1/eligibility/start", json=payload_1)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["scheme_id"] == "PM_KISAN"
    assert data1["completed_count"] == 0
    assert data1["total_count"] == 5
    assert data1["current_question"] is not None
    assert data1["current_question"]["field"] == "is_landholding_farmer"
    assert data1["is_ready_for_evaluation"] is False

    # Test scheme-prefixed endpoint
    conv_id_2 = "api_test_start_002"
    payload_2 = {
        "conversation_id": conv_id_2,
        "language": "te",
    }
    resp2 = client.post("/api/v1/schemes/TELANGANA_RYTHU_BANDHU/eligibility/start", json=payload_2)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["scheme_id"] == "TELANGANA_RYTHU_BANDHU"
    assert data2["total_count"] == 3
    assert data2["current_question"]["field"] == "is_telangana_resident"


def test_start_assessment_invalid_scheme():
    """Verify starting an assessment for an invalid scheme returns 404."""
    resp = client.post(
        "/api/v1/eligibility/start",
        json={"conversation_id": "conv_invalid", "scheme_id": "NON_EXISTENT_SCHEME"},
    )
    assert resp.status_code == 404


def test_process_natural_language_message_endpoint():
    """Verify POST /eligibility/message extracts answers and advances questions turn-by-turn."""
    conv_id = "api_test_msg_003"
    client.post(
        "/api/v1/eligibility/start",
        json={"conversation_id": conv_id, "scheme_id": "PM_KISAN", "language": "en"},
    )

    # Turn 1: Citizen replies to Question 1 in natural language
    resp1 = client.post(
        "/api/v1/eligibility/message",
        json={
            "conversation_id": conv_id,
            "message": "Yes, our family owns 4 acres of farmland in Guntur.",
        },
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["completed_count"] == 1
    assert data1["current_question"]["field"] == "holds_constitutional_post"

    # Turn 2: Citizen replies to Question 2
    resp2 = client.post(
        "/api/v1/eligibility/message",
        json={
            "conversation_id": conv_id,
            "message": "No, nobody holds any constitutional posts or political office.",
        },
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["completed_count"] == 2
    assert data2["current_question"]["field"] == "is_government_employee"


def test_process_message_ambiguity_and_clarification():
    """Verify ambiguous answers block progression and trigger clarification prompts."""
    conv_id = "api_test_ambig_004"
    client.post(
        "/api/v1/eligibility/start",
        json={"conversation_id": conv_id, "scheme_id": "PM_KISAN", "language": "en"},
    )

    # Ambiguous statement
    resp1 = client.post(
        "/api/v1/eligibility/message",
        json={
            "conversation_id": conv_id,
            "message": "Maybe, sometimes my brother uses the land.",
        },
    )
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["clarification_required"] is True
    assert data1["collection_status"] == "NEEDS_CLARIFICATION"
    assert data1["current_question"]["field"] == "is_landholding_farmer"

    # Citizen clarifies
    resp2 = client.post(
        "/api/v1/eligibility/message",
        json={
            "conversation_id": conv_id,
            "message": "Yes, the land is officially registered in our family's name.",
        },
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["clarification_required"] is False
    assert data2["current_question"]["field"] == "holds_constitutional_post"


def test_submit_direct_structured_answers_endpoint():
    """Verify POST /eligibility/submit updates multiple answers directly."""
    conv_id = "api_test_direct_005"

    resp = client.post(
        "/api/v1/eligibility/submit",
        json={
            "conversation_id": conv_id,
            "scheme_id": "PM_KISAN",
            "answers": [
                {"field": "is_landholding_farmer", "value": True},
                {"field": "holds_constitutional_post", "value": False},
                {"field": "is_government_employee", "value": False},
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["completed_count"] == 3
    assert data["current_question"]["field"] == "is_income_tax_payer"
    assert data["is_ready_for_evaluation"] is False


def test_get_assessment_status_endpoint():
    """Verify GET /eligibility/{conversation_id}/status returns active state."""
    conv_id = "api_test_status_006"
    client.post(
        "/api/v1/eligibility/start",
        json={"conversation_id": conv_id, "scheme_id": "TELANGANA_RYTHU_BANDHU"},
    )

    resp = client.get(f"/api/v1/eligibility/{conv_id}/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["scheme_id"] == "TELANGANA_RYTHU_BANDHU"
    assert data["total_count"] == 3
    assert data["completed_count"] == 0
    assert data["current_question"]["field"] == "is_telangana_resident"


def test_evaluate_collected_assessment_endpoint():
    """Verify POST /eligibility/{conversation_id}/evaluate converts answers and executes evaluation."""
    conv_id = "api_test_eval_007"
    client.post(
        "/api/v1/eligibility/start",
        json={"conversation_id": conv_id, "scheme_id": "TELANGANA_RYTHU_BANDHU"},
    )

    # Provide all 3 required criteria
    client.post(
        "/api/v1/eligibility/submit",
        json={
            "conversation_id": conv_id,
            "scheme_id": "TELANGANA_RYTHU_BANDHU",
            "answers": [
                {"field": "is_telangana_resident", "value": True},
                {"field": "has_dharani_pattadar_passbook", "value": True},
                {"field": "is_cultivable_agricultural_land", "value": True},
            ],
        },
    )

    # Check status is ready
    status_resp = client.get(f"/api/v1/eligibility/{conv_id}/status")
    assert status_resp.json()["is_ready_for_evaluation"] is True

    # Evaluate
    eval_resp = client.post(f"/api/v1/eligibility/{conv_id}/evaluate")
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["overall_result"] == "LIKELY_ELIGIBLE"
    assert len(eval_data["conditions"]) == 3
    assert all(c["status"] == "MET" for c in eval_data["conditions"])


def test_clear_assessment_endpoint():
    """Verify DELETE /eligibility/{conversation_id} cleans up assessment session."""
    conv_id = "api_test_clear_008"
    client.post(
        "/api/v1/eligibility/start",
        json={"conversation_id": conv_id, "scheme_id": "PM_KISAN"},
    )

    # Delete assessment
    del_resp = client.delete(f"/api/v1/eligibility/{conv_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Status call must now return 404
    status_resp = client.get(f"/api/v1/eligibility/{conv_id}/status")
    assert status_resp.status_code == 404

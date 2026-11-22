from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_all_schemes():
    """Verify that GET /api/v1/schemes returns the 5 verified welfare schemes."""
    response = client.get("/api/v1/schemes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5

    scheme_ids = [s["scheme_id"] for s in data]
    assert "PM_KISAN" in scheme_ids
    assert "AYUSHMAN_BHARAT" in scheme_ids
    assert "PMAY_G" in scheme_ids
    assert "NSP_CSSS" in scheme_ids
    assert "TELANGANA_RYTHU_BANDHU" in scheme_ids


def test_get_scheme_by_id():
    """Verify retrieval of detailed scheme data for PM_KISAN."""
    response = client.get("/api/v1/schemes/PM_KISAN")
    assert response.status_code == 200
    data = response.json()
    assert data["scheme_id"] == "PM_KISAN"
    assert "Ministry of Agriculture" in data["ministry"]
    assert len(data["benefits"]) > 0
    assert len(data["eligibility_conditions"]) > 0
    assert len(data["exclusion_conditions"]) > 0
    assert len(data["required_documents"]) > 0
    assert data["data_source"] == "verified_demo_dataset"
    assert data["official_source_url"] == "https://pmkisan.gov.in/"


def test_get_unknown_scheme_404():
    """Verify that requesting a nonexistent scheme returns 404."""
    response = client.get("/api/v1/schemes/UNKNOWN_SCHEME_999")
    assert response.status_code == 404


def test_search_schemes():
    """Verify search filter across title, description, and target beneficiaries."""
    response = client.get("/api/v1/schemes/search?q=farmer")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2  # PM-KISAN and Rythu Bandhu

    response_telangana = client.get("/api/v1/schemes/search?q=Telangana")
    assert response_telangana.status_code == 200
    data_telangana = response_telangana.json()
    assert any(s["scheme_id"] == "TELANGANA_RYTHU_BANDHU" for s in data_telangana)


def test_get_scheme_eligibility_questions():
    """Verify that scheme questionnaire is returned with required field types."""
    response = client.get("/api/v1/schemes/PM_KISAN/eligibility/questions")
    assert response.status_code == 200
    data = response.json()
    assert data["scheme_id"] == "PM_KISAN"
    assert len(data["questions"]) >= 4

    question_ids = [q["id"] for q in data["questions"]]
    assert "is_landholding_farmer" in question_ids
    assert "holds_constitutional_post" in question_ids
    assert "is_income_tax_payer" in question_ids


def test_evaluate_eligibility_likely_eligible():
    """Verify deterministic evaluation when all positive conditions are met and no exclusions apply."""
    payload = {
        "applicant_data": {
            "is_landholding_farmer": True,
            "holds_constitutional_post": False,
            "is_income_tax_payer": False,
            "is_government_employee": False,
        }
    }
    response = client.post("/api/v1/schemes/PM_KISAN/eligibility/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["scheme_id"] == "PM_KISAN"
    assert data["overall_result"] == "LIKELY_ELIGIBLE"
    assert data["assessment_status"] == "PRELIMINARY"
    assert len(data["missing_information"]) == 0
    assert "disclaimer" in data


def test_evaluate_eligibility_likely_not_eligible():
    """Verify deterministic evaluation when an exclusion condition fails (income tax payer)."""
    payload = {
        "applicant_data": {
            "is_landholding_farmer": True,
            "holds_constitutional_post": False,
            "is_income_tax_payer": True,  # Excluded!
            "is_government_employee": False,
        }
    }
    response = client.post("/api/v1/schemes/PM_KISAN/eligibility/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_result"] == "LIKELY_NOT_ELIGIBLE"

    # Find the income tax condition result
    tax_cond = next((c for c in data["conditions"] if "income tax" in c["condition"].lower()), None)
    assert tax_cond is not None
    assert tax_cond["status"] == "NOT_MET"


def test_evaluate_eligibility_needs_more_information():
    """Verify evaluation when required fields are missing."""
    payload = {
        "applicant_data": {
            "is_landholding_farmer": True,
            # Omitting other required questions
        }
    }
    response = client.post("/api/v1/schemes/PM_KISAN/eligibility/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_result"] == "NEEDS_MORE_INFORMATION"
    assert len(data["missing_information"]) > 0

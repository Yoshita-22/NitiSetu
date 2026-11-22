from fastapi.testclient import TestClient
import pytest
from app.core.exceptions import NotFoundError
from app.main import app
from app.schemas.chat_query_schema import PendingQuestion
from app.schemas.eligibility_schemas import QuestionnaireItem
from app.services.eligibility_service import eligibility_service
from app.services.questionnaire_mapping_service import questionnaire_mapping_service

client = TestClient(app)

ALL_FIVE_SCHEMES = [
    "PM_KISAN",
    "AYUSHMAN_BHARAT",
    "PMAY_G",
    "NSP_CSSS",
    "TELANGANA_RYTHU_BANDHU",
]


def test_scheme_criteria_mapping_all_five_schemes():
    """Verify all five schemes have complete, valid questionnaire mappings."""
    for scheme_id in ALL_FIVE_SCHEMES:
        questions = questionnaire_mapping_service.get_questionnaire(scheme_id, language="en")
        assert len(questions) > 0, f"No questions mapped for scheme {scheme_id}"

        for q in questions:
            assert isinstance(q, QuestionnaireItem)
            assert q.id, f"Question missing ID in {scheme_id}"
            assert q.criterion_id == q.id, f"Question ID and criterion_id mismatch in {scheme_id}"
            assert q.label, f"Missing label for {q.id} in {scheme_id}"
            assert q.type in ("boolean", "number", "select", "text", "date")
            assert q.order > 0, f"Order must be positive in {scheme_id}"
            assert q.category is not None

            # Validation rule check
            assert q.validation_rule is not None
            assert q.validation_rule.criterion_id == q.id

            # Conversion to PendingQuestion contract check
            pending = q.to_pending_question()
            assert isinstance(pending, PendingQuestion)
            assert pending.field == q.id
            assert pending.question == q.label
            assert pending.input_type in ("boolean", "number", "text", "select")


def test_no_duplicate_question_or_criterion_ids():
    """Verify there are no duplicate question or criterion IDs within any scheme questionnaire."""
    for scheme_id in ALL_FIVE_SCHEMES:
        questions = questionnaire_mapping_service.get_questionnaire(scheme_id)
        q_ids = [q.id for q in questions]
        crit_ids = [q.criterion_id for q in questions]

        assert len(q_ids) == len(set(q_ids)), f"Duplicate question IDs found in {scheme_id}: {q_ids}"
        assert len(crit_ids) == len(set(crit_ids)), f"Duplicate criterion IDs found in {scheme_id}: {crit_ids}"


def test_invalid_scheme_id_raises_not_found():
    """Verify querying an invalid or non-existent scheme raises NotFoundError."""
    with pytest.raises(NotFoundError):
        questionnaire_mapping_service.get_questionnaire("UNKNOWN_SCHEME_XYZ")


def test_correct_ordering_of_questions():
    """Verify questions are strictly ordered by ascending sequence."""
    for scheme_id in ALL_FIVE_SCHEMES:
        questions = questionnaire_mapping_service.get_questionnaire(scheme_id)
        orders = [q.order for q in questions]
        assert orders == sorted(orders), f"Questions in {scheme_id} are not ordered correctly: {orders}"


def test_exclusion_condition_coverage():
    """Verify that exclusion conditions are categorized as 'exclusion' and correctly captured."""
    # PM-KISAN exclusions
    pm_kisan_map = questionnaire_mapping_service.get_criterion_mapping("PM_KISAN")
    assert pm_kisan_map["holds_constitutional_post"]["condition_type"] == "exclusion"
    assert pm_kisan_map["is_government_employee"]["condition_type"] == "exclusion"
    assert pm_kisan_map["is_income_tax_payer"]["condition_type"] == "exclusion"
    assert pm_kisan_map["monthly_pension_over_10k"]["condition_type"] == "exclusion"

    # Ayushman Bharat exclusions
    ab_map = questionnaire_mapping_service.get_criterion_mapping("AYUSHMAN_BHARAT")
    assert ab_map["owns_motorized_vehicle"]["condition_type"] == "exclusion"
    assert ab_map["is_government_employee"]["condition_type"] == "exclusion"

    # PMAY-G exclusions
    pmay_map = questionnaire_mapping_service.get_criterion_mapping("PMAY_G")
    assert pmay_map["owns_pucca_house"]["condition_type"] == "exclusion"
    assert pmay_map["monthly_income_over_15k"]["condition_type"] == "exclusion"
    assert pmay_map["owns_motorized_vehicle"]["condition_type"] == "exclusion"

    # NSP-CSSS exclusions
    nsp_map = questionnaire_mapping_service.get_criterion_mapping("NSP_CSSS")
    assert nsp_map["receives_other_scholarship"]["condition_type"] == "exclusion"


def test_multilingual_question_presentation():
    """Verify that stable IDs are preserved across en, te, hi and labels are properly localized."""
    for scheme_id in ALL_FIVE_SCHEMES:
        en_questions = questionnaire_mapping_service.get_questionnaire(scheme_id, language="en")
        te_questions = questionnaire_mapping_service.get_questionnaire(scheme_id, language="te")
        hi_questions = questionnaire_mapping_service.get_questionnaire(scheme_id, language="hi")

        assert len(en_questions) == len(te_questions) == len(hi_questions)

        for i in range(len(en_questions)):
            en_q = en_questions[i]
            te_q = te_questions[i]
            hi_q = hi_questions[i]

            # Critical: IDs and criterion_ids MUST NEVER change across languages
            assert en_q.id == te_q.id == hi_q.id
            assert en_q.criterion_id == te_q.criterion_id == hi_q.criterion_id
            assert en_q.type == te_q.type == hi_q.type
            assert en_q.required == te_q.required == hi_q.required

            # Labels and help texts must be localized and non-empty
            assert te_q.label and te_q.label != en_q.label, f"Telugu label missing or identical to English for {en_q.id}"
            assert hi_q.label and hi_q.label != en_q.label, f"Hindi label missing or identical to English for {en_q.id}"
            assert te_q.help_text, f"Telugu help text missing for {en_q.id}"
            assert hi_q.help_text, f"Hindi help text missing for {en_q.id}"

    # Unsupported language fallback test
    en_pmk = questionnaire_mapping_service.get_questionnaire("PM_KISAN", language="en")
    fallback_q = questionnaire_mapping_service.get_questionnaire("PM_KISAN", language="fr")
    assert fallback_q[0].label == en_pmk[0].label


def test_validation_rule_compatibility():
    """Verify criterion-specific validation rules work across types."""
    nsp_questions = questionnaire_mapping_service.get_questionnaire("NSP_CSSS")
    income_q = next(q for q in nsp_questions if q.id == "annual_family_income")

    assert income_q.type == "number"
    assert income_q.validation_rule is not None

    # Valid within bounds
    valid, _ = income_q.validation_rule.validate_value(300000)
    assert valid is True

    # Negative income
    valid, err = income_q.validation_rule.validate_value(-500)
    assert valid is False
    assert "at least 0.0" in err

    # Outlandish income exceeding 1 crore
    valid, err = income_q.validation_rule.validate_value(20000000)
    assert valid is False
    assert "cannot exceed 10000000.0" in err


def test_compatibility_with_existing_eligibility_evaluator():
    """Verify that questionnaires integrate perfectly with the deterministic evaluator for all 5 schemes."""
    # 1. PM-KISAN
    pmk_data = {
        "is_landholding_farmer": True,
        "holds_constitutional_post": False,
        "is_government_employee": False,
        "is_income_tax_payer": False,
    }
    resp = eligibility_service.evaluate_eligibility("PM_KISAN", pmk_data)
    assert resp.overall_result == "LIKELY_ELIGIBLE"

    # Disqualification check
    pmk_disqual = dict(pmk_data, is_income_tax_payer=True)
    resp = eligibility_service.evaluate_eligibility("PM_KISAN", pmk_disqual)
    assert resp.overall_result == "LIKELY_NOT_ELIGIBLE"

    # 2. AYUSHMAN BHARAT
    ab_data = {"is_senior_citizen_70_plus": True}
    resp = eligibility_service.evaluate_eligibility("AYUSHMAN_BHARAT", ab_data)
    assert resp.overall_result == "LIKELY_ELIGIBLE"

    # 3. PMAY-G
    pmay_data = {
        "is_rural_resident": True,
        "is_houseless_or_kutcha": True,
        "owns_pucca_house": False,
        "monthly_income_over_15k": False,
    }
    resp = eligibility_service.evaluate_eligibility("PMAY_G", pmay_data)
    assert resp.overall_result == "LIKELY_ELIGIBLE"

    # 4. NSP-CSSS
    nsp_data = {
        "class_12_percentile_above_80": True,
        "enrolled_regular_degree": True,
        "annual_family_income": 350000,
        "receives_other_scholarship": False,
    }
    resp = eligibility_service.evaluate_eligibility("NSP_CSSS", nsp_data)
    assert resp.overall_result == "LIKELY_ELIGIBLE"

    # Exceeding income
    nsp_high_inc = dict(nsp_data, annual_family_income=500000)
    resp = eligibility_service.evaluate_eligibility("NSP_CSSS", nsp_high_inc)
    assert resp.overall_result == "LIKELY_NOT_ELIGIBLE"

    # 5. TELANGANA RYTHU BANDHU
    rb_data = {
        "is_telangana_resident": True,
        "has_dharani_pattadar_passbook": True,
        "is_cultivable_agricultural_land": True,
    }
    resp = eligibility_service.evaluate_eligibility("TELANGANA_RYTHU_BANDHU", rb_data)
    assert resp.overall_result == "LIKELY_ELIGIBLE"


def test_unmapped_criteria_registry_coverage():
    """Verify that unmapped statutory criteria are properly registered with justifications."""
    for scheme_id in ALL_FIVE_SCHEMES:
        unmapped = questionnaire_mapping_service.get_unmapped_criteria(scheme_id)
        assert len(unmapped) > 0, f"Scheme {scheme_id} should have registered unmapped criteria"
        for item in unmapped:
            assert "condition" in item
            assert "type" in item
            assert "reason" in item
            assert len(item["reason"]) > 20


def test_api_route_multilingual_question_endpoint():
    """Verify GET /api/v1/schemes/{scheme_id}/eligibility/questions?lang=... endpoint."""
    # Test English default
    res_en = client.get("/api/v1/schemes/PM_KISAN/eligibility/questions")
    assert res_en.status_code == 200
    data_en = res_en.json()
    assert data_en["scheme_id"] == "PM_KISAN"
    assert "own cultivable agricultural land" in data_en["questions"][0]["label"]

    # Test Telugu parameter
    res_te = client.get("/api/v1/schemes/PM_KISAN/eligibility/questions?lang=te")
    assert res_te.status_code == 200
    data_te = res_te.json()
    assert data_te["questions"][0]["id"] == data_en["questions"][0]["id"]  # ID stays identical!
    assert "సాగు భూమి" in data_te["questions"][0]["label"]

    # Test Hindi parameter
    res_hi = client.get("/api/v1/schemes/PM_KISAN/eligibility/questions?lang=hi")
    assert res_hi.status_code == 200
    data_hi = res_hi.json()
    assert data_hi["questions"][0]["id"] == data_en["questions"][0]["id"]  # ID stays identical!
    assert "कृषि योग्य भूमि" in data_hi["questions"][0]["label"]

import pytest
from app.schemas.eligibility_schemas import (
    ExtractedAnswer,
    ExtractionResult,
)
from app.services.answer_validation_service import answer_validation_service
from app.services.questionnaire_mapping_service import questionnaire_mapping_service


@pytest.fixture
def pm_kisan_questions():
    return questionnaire_mapping_service.get_questionnaire("PM_KISAN")


@pytest.fixture
def nsp_questions():
    return questionnaire_mapping_service.get_questionnaire("NSP_CSSS")


@pytest.fixture
def pmay_questions():
    return questionnaire_mapping_service.get_questionnaire("PMAY_G")


def test_boolean_validation_valid_and_invalid(pm_kisan_questions):
    """Verify boolean validation for valid booleans and rejection of invalid data."""
    q_farmer = next(q for q in pm_kisan_questions if q.id == "is_landholding_farmer")

    # Valid True
    ans_true = ExtractedAnswer(criterion_id="is_landholding_farmer", extracted_value=True, status="ANSWERED")
    v_res = answer_validation_service.validate_answer(ans_true, q_farmer)
    assert v_res.is_valid is True
    assert v_res.validation_status == "VALID"
    assert v_res.normalized_value is True
    assert v_res.error_message is None

    # Valid False
    ans_false = ExtractedAnswer(criterion_id="is_landholding_farmer", extracted_value=False, status="ANSWERED")
    v_res = answer_validation_service.validate_answer(ans_false, q_farmer)
    assert v_res.is_valid is True
    assert v_res.normalized_value is False

    # Valid string representation
    ans_str = ExtractedAnswer(criterion_id="is_landholding_farmer", extracted_value="yes", status="ANSWERED")
    v_res = answer_validation_service.validate_answer(ans_str, q_farmer)
    assert v_res.is_valid is True
    assert v_res.normalized_value is True

    # Invalid non-boolean value
    ans_invalid = ExtractedAnswer(criterion_id="is_landholding_farmer", extracted_value=12345, status="ANSWERED")
    v_res = answer_validation_service.validate_answer(ans_invalid, q_farmer)
    assert v_res.is_valid is False
    assert v_res.validation_status == "INVALID"
    assert "Please answer Yes or No" in v_res.error_message


def test_numeric_bounds_validation(nsp_questions):
    """Verify numeric range, negative numbers, and boundary limits."""
    q_income = next(q for q in nsp_questions if q.id == "annual_family_income")

    # Valid income within range
    ans_valid = ExtractedAnswer(criterion_id="annual_family_income", extracted_value=300000.0, status="ANSWERED")
    v_res = answer_validation_service.validate_answer(ans_valid, q_income)
    assert v_res.is_valid is True
    assert v_res.normalized_value == 300000

    # Negative income (fails min_value=0.0)
    ans_neg = ExtractedAnswer(criterion_id="annual_family_income", extracted_value=-5000, status="ANSWERED")
    v_res = answer_validation_service.validate_answer(ans_neg, q_income)
    assert v_res.is_valid is False
    assert v_res.validation_status == "INVALID"
    assert "at least 0.0" in v_res.error_message

    # Exorbitant income (fails max_value=10,000,000)
    ans_huge = ExtractedAnswer(criterion_id="annual_family_income", extracted_value=25000000, status="ANSWERED")
    v_res = answer_validation_service.validate_answer(ans_huge, q_income)
    assert v_res.is_valid is False
    assert "cannot exceed 10000000.0" in v_res.error_message

    # Non-numeric input
    ans_text = ExtractedAnswer(criterion_id="annual_family_income", extracted_value="not_a_number", status="ANSWERED")
    v_res = answer_validation_service.validate_answer(ans_text, q_income)
    assert v_res.is_valid is False
    assert "valid numeric value" in v_res.error_message


def test_status_handling_unknown_and_refusal(pm_kisan_questions):
    """Verify that UNKNOWN, PREFER_NOT_TO_ANSWER, and NOT_APPLICABLE pass validation cleanly."""
    q_farmer = next(q for q in pm_kisan_questions if q.id == "is_landholding_farmer")

    # UNKNOWN
    ans_unknown = ExtractedAnswer(criterion_id="is_landholding_farmer", extracted_value=None, status="UNKNOWN")
    v_res = answer_validation_service.validate_answer(ans_unknown, q_farmer)
    assert v_res.is_valid is True
    assert v_res.validation_status == "VALID"
    assert v_res.normalized_value is None
    assert v_res.is_disqualifying is False  # Unknown is NOT disqualifying!

    # PREFER_NOT_TO_ANSWER
    ans_refusal = ExtractedAnswer(criterion_id="is_landholding_farmer", extracted_value=None, status="PREFER_NOT_TO_ANSWER")
    v_res = answer_validation_service.validate_answer(ans_refusal, q_farmer)
    assert v_res.is_valid is True
    assert v_res.validation_status == "VALID"
    assert v_res.normalized_value is None
    assert v_res.is_disqualifying is False  # Refusal is NOT disqualifying!

    # NOT_APPLICABLE
    ans_na = ExtractedAnswer(criterion_id="is_landholding_farmer", extracted_value=None, status="NOT_APPLICABLE")
    v_res = answer_validation_service.validate_answer(ans_na, q_farmer)
    assert v_res.is_valid is True
    assert v_res.normalized_value is None


def test_needs_clarification_status(pm_kisan_questions):
    """Verify that ambiguous answers flag clarification requirements."""
    q_farmer = next(q for q in pm_kisan_questions if q.id == "is_landholding_farmer")

    ans_ambig = ExtractedAnswer(
        criterion_id="is_landholding_farmer",
        extracted_value=None,
        status="NEEDS_CLARIFICATION",
        validation_status="AMBIGUOUS",
        clarification_prompt="Could you please clarify whether you or your family own cultivable land?",
    )
    v_res = answer_validation_service.validate_answer(ans_ambig, q_farmer)
    assert v_res.is_valid is False
    assert v_res.validation_status == "AMBIGUOUS"
    assert v_res.requires_clarification is True
    assert "Could you please clarify" in v_res.clarification_prompt


def test_statutory_disqualification_detection(pm_kisan_questions, pmay_questions, nsp_questions):
    """Verify early identification of disqualifying conditions without changing answers."""
    q_land = next(q for q in pm_kisan_questions if q.id == "is_landholding_farmer")
    q_post = next(q for q in pm_kisan_questions if q.id == "holds_constitutional_post")
    q_pucca = next(q for q in pmay_questions if q.id == "owns_pucca_house")
    q_income = next(q for q in nsp_questions if q.id == "annual_family_income")

    # PM-KISAN: Landless farmer is statutorily disqualified
    ans_landless = ExtractedAnswer(criterion_id="is_landholding_farmer", extracted_value=False, status="ANSWERED")
    v_land = answer_validation_service.validate_answer(ans_landless, q_land, scheme_id="PM_KISAN")
    assert v_land.is_valid is True
    assert v_land.is_disqualifying is True
    assert "Landless farmers" in v_land.statutory_note

    # PM-KISAN: Constitutional post holder is disqualified
    ans_minister = ExtractedAnswer(criterion_id="holds_constitutional_post", extracted_value=True, status="ANSWERED")
    v_post = answer_validation_service.validate_answer(ans_minister, q_post, scheme_id="PM_KISAN")
    assert v_post.is_valid is True
    assert v_post.is_disqualifying is True
    assert "Holders of constitutional posts" in v_post.statutory_note

    # PMAY-G: Pucca house owner is disqualified
    ans_pucca = ExtractedAnswer(criterion_id="owns_pucca_house", extracted_value=True, status="ANSWERED")
    v_pucca = answer_validation_service.validate_answer(ans_pucca, q_pucca, scheme_id="PMAY_G")
    assert v_pucca.is_valid is True
    assert v_pucca.is_disqualifying is True
    assert "owning a permanent pucca house" in v_pucca.statutory_note

    # NSP-CSSS: Income > 4.5 lakh is disqualified
    ans_high_inc = ExtractedAnswer(criterion_id="annual_family_income", extracted_value=500000.0, status="ANSWERED")
    v_inc = answer_validation_service.validate_answer(ans_high_inc, q_income, scheme_id="NSP_CSSS")
    assert v_inc.is_valid is True
    assert v_inc.is_disqualifying is True
    assert "exceeds the statutory Rs. 4,50,000" in v_inc.statutory_note

    # NSP-CSSS: Income <= 4.5 lakh is NOT disqualified
    ans_ok_inc = ExtractedAnswer(criterion_id="annual_family_income", extracted_value=350000.0, status="ANSWERED")
    v_ok = answer_validation_service.validate_answer(ans_ok_inc, q_income, scheme_id="NSP_CSSS")
    assert v_ok.is_valid is True
    assert v_ok.is_disqualifying is False


def test_multilingual_error_messages(pm_kisan_questions, nsp_questions):
    """Verify citizen-friendly error messages rendered in Telugu and Hindi."""
    q_land = next(q for q in pm_kisan_questions if q.id == "is_landholding_farmer")
    q_income = next(q for q in nsp_questions if q.id == "annual_family_income")

    # Invalid boolean in Telugu
    ans_bad_bool = ExtractedAnswer(criterion_id="is_landholding_farmer", extracted_value="not_bool", status="ANSWERED")
    v_te = answer_validation_service.validate_answer(ans_bad_bool, q_land, language="te")
    assert v_te.is_valid is False
    assert "అవును లేదా కాదు అని సమాధానం ఇవ్వండి" in v_te.error_message

    # Invalid boolean in Hindi
    v_hi = answer_validation_service.validate_answer(ans_bad_bool, q_land, language="hi")
    assert v_hi.is_valid is False
    assert "हाँ या नहीं में उत्तर दें" in v_hi.error_message

    # Negative number in Telugu
    ans_neg = ExtractedAnswer(criterion_id="annual_family_income", extracted_value=-100, status="ANSWERED")
    v_te_num = answer_validation_service.validate_answer(ans_neg, q_income, language="te")
    assert v_te_num.is_valid is False
    assert "కనీసం 0.0 ఉండాలి" in v_te_num.error_message

    # Negative number in Hindi
    v_hi_num = answer_validation_service.validate_answer(ans_neg, q_income, language="hi")
    assert v_hi_num.is_valid is False
    assert "कम से कम 0.0 होना चाहिए" in v_hi_num.error_message


def test_batch_validation_report(pm_kisan_questions):
    """Verify aggregate validation report over multiple answers."""
    extraction = ExtractionResult(
        answers=[
            ExtractedAnswer(criterion_id="is_landholding_farmer", extracted_value=True, status="ANSWERED"),
            ExtractedAnswer(criterion_id="is_income_tax_payer", extracted_value=False, status="ANSWERED"),
            ExtractedAnswer(criterion_id="holds_constitutional_post", extracted_value=None, status="UNKNOWN"),
        ],
        raw_message="Yes farmer, no tax, don't know about posts",
    )

    report = answer_validation_service.validate_extraction_result(
        extraction, pm_kisan_questions, scheme_id="PM_KISAN"
    )
    assert report.is_all_valid is True
    assert len(report.validated_answers) == 3
    assert len(report.errors) == 0
    assert report.has_disqualifying_condition is False
    assert report.requires_clarification is False


def test_validate_raw_answer_convenience():
    """Verify raw answer validation helper for direct API usage."""
    # Valid PM-KISAN answer
    v_res = answer_validation_service.validate_raw_answer(
        criterion_id="is_landholding_farmer",
        value=True,
        scheme_id="PM_KISAN",
    )
    assert v_res.is_valid is True
    assert v_res.normalized_value is True

    # Unknown criterion
    v_bad = answer_validation_service.validate_raw_answer(
        criterion_id="unknown_criterion_xyz",
        value=True,
        scheme_id="PM_KISAN",
    )
    assert v_bad.is_valid is False
    assert "not recognized" in v_bad.error_message

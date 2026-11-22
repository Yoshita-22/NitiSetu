from datetime import datetime
import pytest
from app.schemas.chat_query_schema import PendingQuestion
from app.schemas.eligibility_schemas import (
    AnswerHistoryEntry,
    AnswerStatus,
    AnswerSubmission,
    AnswerSubmissionRequest,
    ApplicantAnswer,
    AssessmentState,
    AssessmentStatusResponse,
    CriterionValidationRule,
    QuestionnaireItem,
    ValidationStatus,
)
from app.schemas.scheme_schemas import (
    EligibilityEvaluationRequest,
    EligibilityQuestion,
)


def test_criterion_validation_rule_boolean():
    """Verify boolean validation handles native booleans and common text representations."""
    rule = CriterionValidationRule(criterion_id="is_farmer", input_type="boolean")

    # Valid booleans
    valid, err = rule.validate_value(True)
    assert valid is True
    assert err is None

    valid, err = rule.validate_value(False)
    assert valid is True
    assert err is None

    # Text booleans
    valid, err = rule.validate_value("yes")
    assert valid is True
    valid, err = rule.validate_value("ha")
    assert valid is True
    valid, err = rule.validate_value("no")
    assert valid is True

    # Invalid boolean
    valid, err = rule.validate_value("maybe")
    assert valid is False
    assert "Please answer Yes or No" in err


def test_criterion_validation_rule_number():
    """Verify numeric boundaries and type checking."""
    rule = CriterionValidationRule(
        criterion_id="annual_income",
        input_type="number",
        min_value=0.0,
        max_value=1000000.0,
    )

    valid, _ = rule.validate_value(50000)
    assert valid is True

    # String convertible to number
    valid, _ = rule.validate_value("75000.50")
    assert valid is True

    # Below min
    valid, err = rule.validate_value(-10)
    assert valid is False
    assert "at least 0.0" in err

    # Above max
    valid, err = rule.validate_value(2000000)
    assert valid is False
    assert "cannot exceed 1000000.0" in err

    # Non-numeric
    valid, err = rule.validate_value("not_a_number")
    assert valid is False
    assert "valid numeric value" in err


def test_criterion_validation_rule_select():
    """Verify allowed values whitelist for select criteria."""
    rule = CriterionValidationRule(
        criterion_id="category",
        input_type="select",
        allowed_values=["SC", "ST", "OBC", "GEN"],
    )

    valid, _ = rule.validate_value("OBC")
    assert valid is True

    valid, err = rule.validate_value("INVALID_CAT")
    assert valid is False
    assert "Please choose from: SC, ST, OBC, GEN" in err


def test_questionnaire_item_conversion():
    """Verify QuestionnaireItem properly adapts to and from existing EligibilityQuestion."""
    eq = EligibilityQuestion(
        id="is_landholding_farmer",
        label="Do you own cultivable land?",
        type="boolean",
        help_text="Recorded in land revenue portal",
        required=True,
    )

    item = QuestionnaireItem.from_eligibility_question(
        eq,
        validation_rule=CriterionValidationRule(criterion_id=eq.id, input_type="boolean"),
        category="landholding",
    )

    assert item.id == "is_landholding_farmer"
    assert item.criterion_id == "is_landholding_farmer"
    assert item.category == "landholding"
    assert item.validation_rule is not None

    # Verify pending question contract compatibility
    pending = item.to_pending_question()
    assert isinstance(pending, PendingQuestion)
    assert pending.field == "is_landholding_farmer"
    assert pending.question == "Do you own cultivable land?"
    assert pending.input_type == "boolean"
    assert pending.help_text == "Recorded in land revenue portal"


def test_applicant_answer_statuses():
    """Verify all 5 required answer statuses are supported."""
    statuses = [
        "ANSWERED",
        "UNKNOWN",
        "NOT_APPLICABLE",
        "PREFER_NOT_TO_ANSWER",
        "NEEDS_CLARIFICATION",
    ]
    for s in statuses:
        ans = ApplicantAnswer(
            criterion_id="test_field",
            value=True if s == "ANSWERED" else None,
            status=s,  # type: ignore
        )
        assert ans.status == s

    ans_answered = ApplicantAnswer(criterion_id="c1", value=True, status="ANSWERED", validation_status="VALID")
    assert ans_answered.is_usable_for_evaluation() is True

    ans_unknown = ApplicantAnswer(criterion_id="c2", value=None, status="UNKNOWN", validation_status="VALID")
    assert ans_unknown.is_usable_for_evaluation() is False

    ans_pref = ApplicantAnswer(criterion_id="c3", value=None, status="PREFER_NOT_TO_ANSWER", validation_status="VALID")
    assert ans_pref.is_usable_for_evaluation() is False


def test_correction_tracking_and_history():
    """Verify that updating an applicant answer preserves full historical audit entries."""
    ans = ApplicantAnswer(
        criterion_id="annual_income",
        value=250000,
        raw_text="About 2.5 lakhs",
        status="ANSWERED",
        validation_status="VALID",
    )
    assert len(ans.history) == 0

    # User corrects their income
    ans.record_update(
        new_value=180000,
        new_status="ANSWERED",
        raw_text="Actually it is 1.8 lakhs after deductions",
        source="user_correction",
        reason="Citizen revised income figure with exact ITR proof",
        turn_number=2,
    )

    assert ans.value == 180000
    assert ans.raw_text == "Actually it is 1.8 lakhs after deductions"
    assert len(ans.history) == 1

    entry1 = ans.history[0]
    assert entry1.previous_value == 250000
    assert entry1.new_value == 180000
    assert entry1.source == "user_correction"
    assert entry1.turn_number == 2
    assert "revised income" in entry1.reason

    # Second correction: citizen marks as unknown
    ans.record_update(
        new_value=None,
        new_status="UNKNOWN",
        source="user_input",
        reason="Citizen forgot document details",
        turn_number=3,
    )
    assert ans.value is None
    assert ans.status == "UNKNOWN"
    assert len(ans.history) == 2
    assert ans.history[1].previous_value == 180000
    assert ans.history[1].new_value is None
    assert ans.history[1].previous_status == "ANSWERED"
    assert ans.history[1].new_status == "UNKNOWN"


def test_assessment_state_management():
    """Verify AssessmentState records answers, preserves history, and formats clean data."""
    state = AssessmentState(
        conversation_id="conv-12345",
        scheme_id="PM_KISAN",
        scheme_name="PM Kisan Samman Nidhi",
        language="en",
        unanswered_question_ids=["is_landholding_farmer", "is_income_tax_payer", "holds_constitutional_post"],
    )

    assert state.turn_count == 0
    assert len(state.answers) == 0

    # Answer 1: is_landholding_farmer -> True
    state.record_answer(
        criterion_id="is_landholding_farmer",
        value=True,
        raw_text="Yes, we own 3 acres in Andhra Pradesh",
    )
    assert "is_landholding_farmer" not in state.unanswered_question_ids
    assert state.turn_count == 1
    assert state.answers["is_landholding_farmer"].value is True

    # Answer 2: is_income_tax_payer -> False
    state.record_answer(
        criterion_id="is_income_tax_payer",
        value=False,
        raw_text="No, we don't pay income tax",
    )
    assert "is_income_tax_payer" not in state.unanswered_question_ids
    assert state.turn_count == 2

    # Answer 3: holds_constitutional_post -> PREFER_NOT_TO_ANSWER
    state.record_answer(
        criterion_id="holds_constitutional_post",
        value=None,
        status="PREFER_NOT_TO_ANSWER",
        raw_text="I don't want to say",
    )
    assert "holds_constitutional_post" not in state.unanswered_question_ids
    assert state.turn_count == 3

    # Clean applicant data extraction
    clean_data = state.get_clean_applicant_data()
    # ONLY answered, usable values must be in clean_data!
    assert clean_data == {
        "is_landholding_farmer": True,
        "is_income_tax_payer": False,
    }
    # PREFER_NOT_TO_ANSWER must NOT be present as False or None
    assert "holds_constitutional_post" not in clean_data

    # Compatibility check with EligibilityEvaluationRequest
    req = EligibilityEvaluationRequest(applicant_data=clean_data)
    assert req.applicant_data["is_landholding_farmer"] is True

    # Check is_ready_for_evaluation
    assert state.is_ready_for_evaluation(["is_landholding_farmer", "is_income_tax_payer", "holds_constitutional_post"]) is True


def test_assessment_correction_via_state():
    """Verify that updating an answer through state.record_answer tracks history properly."""
    state = AssessmentState(
        conversation_id="conv-12345",
        scheme_id="PM_KISAN",
        scheme_name="PM Kisan Samman Nidhi",
    )

    state.record_answer(
        criterion_id="is_landholding_farmer",
        value=False,
        raw_text="No, my father owns it not me",
    )
    assert state.answers["is_landholding_farmer"].value is False
    assert len(state.answers["is_landholding_farmer"].history) == 0

    # User corrects after clarifying that family ownership counts
    state.record_answer(
        criterion_id="is_landholding_farmer",
        value=True,
        raw_text="Yes, since family land counts, then yes",
        source="user_correction",
        reason="Clarified family land ownership clause",
    )

    assert state.answers["is_landholding_farmer"].value is True
    assert len(state.answers["is_landholding_farmer"].history) == 1
    assert state.answers["is_landholding_farmer"].history[0].previous_value is False
    assert state.answers["is_landholding_farmer"].history[0].new_value is True
    assert state.get_clean_applicant_data()["is_landholding_farmer"] is True

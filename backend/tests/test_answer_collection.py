import pytest
from app.core.exceptions import NotFoundError
from app.schemas.eligibility_schemas import AssessmentStatusResponse
from app.services.answer_collection_service import answer_collection_service
from app.services.eligibility_service import eligibility_service


@pytest.fixture(autouse=True)
def cleanup_assessments():
    """Ensure in-memory assessment session store is clean before and after each test."""
    answer_collection_service._active_assessments.clear()
    yield
    answer_collection_service._active_assessments.clear()


def test_start_assessment():
    """Verify initializing a new assessment state sets up correct question queue and lifecycle."""
    state = answer_collection_service.start_assessment(
        conversation_id="conv-pmk-001",
        scheme_id="PM_KISAN",
        user_id="farmer_citizen_1",
        language="en",
    )

    assert state.conversation_id == "conv-pmk-001"
    assert state.scheme_id == "PM_KISAN"
    assert state.collection_status == "WAITING_FOR_USER"
    assert len(state.unanswered_question_ids) == 5
    assert state.current_question_id == "is_landholding_farmer"
    assert len(state.answers) == 0


@pytest.mark.asyncio
async def test_single_question_turn_progression():
    """Verify processing single answers sequentially advances questions in strict order."""
    state = answer_collection_service.start_assessment(
        conversation_id="conv-seq-001",
        scheme_id="PM_KISAN",
        language="en",
    )

    # Turn 1: Answer first question (is_landholding_farmer)
    state, next_q, errors = await answer_collection_service.process_user_message(
        conversation_id="conv-seq-001",
        message="Yes, our family owns 4 acres of farmland in Guntur.",
    )

    assert len(errors) == 0
    assert "is_landholding_farmer" in state.answers
    assert state.answers["is_landholding_farmer"].value is True
    assert state.answers["is_landholding_farmer"].status == "ANSWERED"
    assert state.turn_count == 1

    # Next question must be holds_constitutional_post (Order 2)
    assert next_q is not None
    assert next_q.id == "holds_constitutional_post"
    assert state.current_question_id == "holds_constitutional_post"


@pytest.mark.asyncio
async def test_multi_answer_in_single_turn():
    """Verify extracting and storing multiple answers from a single composite utterance."""
    state = answer_collection_service.start_assessment(
        conversation_id="conv-multi-001",
        scheme_id="PM_KISAN",
        language="en",
    )

    # User answers 3 criteria in one single sentence:
    # 1. owns agricultural land (is_landholding_farmer: True)
    # 2. no one holds constitutional posts (holds_constitutional_post: False)
    # 3. no government employees (is_government_employee: False)
    utterance = "Yes we have agricultural land, no constitutional posts, and no one is in government job."
    state, next_q, errors = await answer_collection_service.process_user_message(
        conversation_id="conv-multi-001",
        message=utterance,
    )

    assert len(errors) == 0
    assert state.answers["is_landholding_farmer"].value is True
    assert state.answers["holds_constitutional_post"].value is False
    assert state.answers["is_government_employee"].value is False

    # The 3 answered questions are removed from unanswered queue
    assert "is_landholding_farmer" not in state.unanswered_question_ids
    assert "holds_constitutional_post" not in state.unanswered_question_ids
    assert "is_government_employee" not in state.unanswered_question_ids

    # Next question must jump forward to is_income_tax_payer (Order 4)
    assert next_q is not None
    assert next_q.id == "is_income_tax_payer"
    assert state.current_question_id == "is_income_tax_payer"


@pytest.mark.asyncio
async def test_correction_handling_with_history():
    """Verify updating a previously answered criterion preserves historical audit trail."""
    state = answer_collection_service.start_assessment(
        conversation_id="conv-corr-001",
        scheme_id="NSP_CSSS",
        language="en",
    )
    # Advance to annual_family_income
    state.current_question_id = "annual_family_income"
    answer_collection_service.save_assessment(state)

    # Initial answer: 2 lakh
    state, _, _ = await answer_collection_service.process_user_message(
        conversation_id="conv-corr-001",
        message="Our annual family income is ₹2 lakh",
    )
    assert state.answers["annual_family_income"].value == 200000.0
    assert len(state.answers["annual_family_income"].history) == 0

    # Correction turn: 1.5 lakh
    state, _, errors = await answer_collection_service.process_user_message(
        conversation_id="conv-corr-001",
        message="Actually, my annual family income is ₹1.5 lakh, not ₹2 lakh.",
    )
    assert len(errors) == 0
    income_ans = state.answers["annual_family_income"]
    assert income_ans.value == 150000.0
    assert len(income_ans.history) == 1

    history_entry = income_ans.history[0]
    assert history_entry.previous_value == 200000.0
    assert history_entry.new_value == 150000.0
    assert history_entry.source == "user_correction"


@pytest.mark.asyncio
async def test_uncertainty_and_refusal_preservation():
    """Verify UNKNOWN and PREFER_NOT_TO_ANSWER are preserved without False coercion."""
    state = answer_collection_service.start_assessment(
        conversation_id="conv-uncert-001",
        scheme_id="PM_KISAN",
        language="en",
    )

    # Answer is_landholding_farmer with Yes
    state, _, _ = await answer_collection_service.process_user_message(
        conversation_id="conv-uncert-001",
        message="Yes",
    )

    # Answer holds_constitutional_post with UNKNOWN
    state, next_q, _ = await answer_collection_service.process_user_message(
        conversation_id="conv-uncert-001",
        message="I don't know",
    )
    assert state.answers["holds_constitutional_post"].status == "UNKNOWN"
    assert state.answers["holds_constitutional_post"].value is None
    # CRITICAL: Must NOT be False!
    assert state.answers["holds_constitutional_post"].value is not False

    # Answer is_government_employee with REFUSAL
    state, next_q, _ = await answer_collection_service.process_user_message(
        conversation_id="conv-uncert-001",
        message="I don't want to share",
    )
    assert state.answers["is_government_employee"].status == "PREFER_NOT_TO_ANSWER"
    assert state.answers["is_government_employee"].value is None
    assert state.answers["is_government_employee"].value is not False

    # Clean applicant data must omit both UNKNOWN and PREFER_NOT_TO_ANSWER
    clean = state.get_clean_applicant_data()
    assert clean == {"is_landholding_farmer": True}
    assert "holds_constitutional_post" not in clean
    assert "is_government_employee" not in clean


@pytest.mark.asyncio
async def test_needs_clarification_blocks_progression():
    """Verify ambiguous statements require citizen clarification before moving to next question."""
    state = answer_collection_service.start_assessment(
        conversation_id="conv-ambig-001",
        scheme_id="PM_KISAN",
        language="en",
    )

    # Ambiguous answer for is_landholding_farmer
    state, next_q, _ = await answer_collection_service.process_user_message(
        conversation_id="conv-ambig-001",
        message="Maybe, but sometimes my father owns it",
    )

    assert state.clarification_required is True
    assert state.collection_status == "NEEDS_CLARIFICATION"
    assert state.answers["is_landholding_farmer"].status == "NEEDS_CLARIFICATION"

    # Progression must be blocked; next_q must remain is_landholding_farmer!
    assert next_q is not None
    assert next_q.id == "is_landholding_farmer"

    # Citizen clarifies in next turn
    state, next_q, errors = await answer_collection_service.process_user_message(
        conversation_id="conv-ambig-001",
        message="Yes, our family officially owns the land in revenue portal.",
    )
    assert len(errors) == 0
    assert state.clarification_required is False
    assert state.answers["is_landholding_farmer"].status == "ANSWERED"
    assert state.answers["is_landholding_farmer"].value is True

    # Now it advances to holds_constitutional_post
    assert next_q is not None
    assert next_q.id == "holds_constitutional_post"


@pytest.mark.asyncio
async def test_assessment_completion_readiness_and_evaluator_handoff():
    """Verify full completion of questions transitions state to READY_FOR_EVALUATION."""
    state = answer_collection_service.start_assessment(
        conversation_id="conv-rb-001",
        scheme_id="TELANGANA_RYTHU_BANDHU",
        language="en",
    )

    # Answer all 3 criteria in sequence
    # 1. Resident
    state, _, _ = await answer_collection_service.process_user_message(
        conversation_id="conv-rb-001",
        message="Yes, I am a permanent resident farmer of Telangana State.",
    )
    # 2. Dharani Passbook
    state, _, _ = await answer_collection_service.process_user_message(
        conversation_id="conv-rb-001",
        message="Yes, I have an active Dharani digital Pattadar passbook.",
    )
    # 3. Cultivable Land
    state, next_q, _ = await answer_collection_service.process_user_message(
        conversation_id="conv-rb-001",
        message="Yes, this is 5 acres of cultivable agricultural land.",
    )

    # Assessment is now complete
    assert next_q is None
    assert state.current_question_id is None
    assert state.collection_status == "READY_FOR_EVALUATION"

    # Test handoff to deterministic evaluator
    clean_data = state.get_clean_applicant_data()
    assert clean_data == {
        "is_telangana_resident": True,
        "has_dharani_pattadar_passbook": True,
        "is_cultivable_agricultural_land": True,
    }
    eval_resp = eligibility_service.evaluate_eligibility("TELANGANA_RYTHU_BANDHU", clean_data)
    assert eval_resp.overall_result == "LIKELY_ELIGIBLE"


def test_direct_answer_submission():
    """Verify direct submission of structured answers (e.g. from UI buttons)."""
    state = answer_collection_service.start_assessment(
        conversation_id="conv-direct-001",
        scheme_id="TELANGANA_RYTHU_BANDHU",
    )

    state, next_q, errors = answer_collection_service.submit_direct_answers(
        conversation_id="conv-direct-001",
        answers={
            "is_telangana_resident": True,
            "has_dharani_pattadar_passbook": True,
        },
    )

    assert len(errors) == 0
    assert state.answers["is_telangana_resident"].value is True
    assert state.answers["has_dharani_pattadar_passbook"].value is True
    assert next_q is not None
    assert next_q.id == "is_cultivable_agricultural_land"


def test_get_assessment_status_response():
    """Verify AssessmentStatusResponse contract generation."""
    answer_collection_service.start_assessment(
        conversation_id="conv-status-001",
        scheme_id="PM_KISAN",
    )
    answer_collection_service.submit_direct_answers(
        conversation_id="conv-status-001",
        answers={"is_landholding_farmer": True},
    )

    status_resp = answer_collection_service.get_assessment_status("conv-status-001")
    assert isinstance(status_resp, AssessmentStatusResponse)
    assert status_resp.scheme_id == "PM_KISAN"
    assert status_resp.completed_count == 1
    assert status_resp.total_count == 5
    assert status_resp.is_ready_for_evaluation is False
    assert status_resp.current_question is not None
    assert status_resp.current_question.field == "holds_constitutional_post"

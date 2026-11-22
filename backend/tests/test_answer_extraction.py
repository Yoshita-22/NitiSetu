from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.schemas.eligibility_schemas import (
    CriterionValidationRule,
    QuestionnaireItem,
)
from app.services.answer_extraction_service import (
    DeterministicAnswerExtractor,
    answer_extraction_service,
)
from app.services.questionnaire_mapping_service import questionnaire_mapping_service


@pytest.fixture
def pm_kisan_questions():
    return questionnaire_mapping_service.get_questionnaire("PM_KISAN")


@pytest.fixture
def nsp_questions():
    return questionnaire_mapping_service.get_questionnaire("NSP_CSSS")


@pytest.fixture
def rythu_bandhu_questions():
    return questionnaire_mapping_service.get_questionnaire("TELANGANA_RYTHU_BANDHU")


def test_boolean_extraction_english_telugu_hindi(pm_kisan_questions):
    """Verify Yes/No boolean extraction in English, Telugu, and Hindi."""
    context = {"current_question_id": "is_landholding_farmer"}

    # English Yes / No
    res_en_yes = DeterministicAnswerExtractor.extract(
        "Yes, we own cultivable land", pm_kisan_questions, context=context
    )
    assert len(res_en_yes.answers) == 1
    assert res_en_yes.answers[0].criterion_id == "is_landholding_farmer"
    assert res_en_yes.answers[0].extracted_value is True
    assert res_en_yes.answers[0].status == "ANSWERED"

    res_en_no = DeterministicAnswerExtractor.extract(
        "No, we don't own any land", pm_kisan_questions, context=context
    )
    assert len(res_en_no.answers) == 1
    assert res_en_no.answers[0].extracted_value is False

    # Telugu Yes / No (అవును / కాదు)
    res_te_yes = DeterministicAnswerExtractor.extract(
        "అవును, మాకు వ్యవసాయ భూమి ఉంది", pm_kisan_questions, context=context
    )
    assert len(res_te_yes.answers) == 1
    assert res_te_yes.answers[0].extracted_value is True

    res_te_no = DeterministicAnswerExtractor.extract(
        "లేదు, మా కుటుంబానికి భూమి లేదు", pm_kisan_questions, context=context
    )
    assert len(res_te_no.answers) == 1
    assert res_te_no.answers[0].extracted_value is False

    # Hindi Yes / No (हाँ / नहीं)
    res_hi_yes = DeterministicAnswerExtractor.extract(
        "हाँ, हमारे पास कृषि भूमि है", pm_kisan_questions, context=context
    )
    assert len(res_hi_yes.answers) == 1
    assert res_hi_yes.answers[0].extracted_value is True

    res_hi_no = DeterministicAnswerExtractor.extract(
        "नहीं, हमारे पास कोई जमीन नहीं है", pm_kisan_questions, context=context
    )
    assert len(res_hi_no.answers) == 1
    assert res_hi_no.answers[0].extracted_value is False


def test_numeric_formats_and_indian_numbering(nsp_questions):
    """Verify numeric parsing across Indian numbering, currency symbols, and languages."""
    context = {"current_question_id": "annual_family_income"}

    test_cases = [
        ("250000", 250000.0),
        ("₹2,00,000", 200000.0),
        ("Rs. 1,50,000", 150000.0),
        ("2 lakh", 200000.0),
        ("two lakh", 200000.0),
        ("రెండు లక్షలు", 200000.0),
        ("దో లాఖ్ (दो लाख)", 200000.0),
        ("1.5 lakh", 150000.0),
        ("1.5 లక్షలు", 150000.0),
        ("डेढ़ लाख", 150000.0),
        ("ढाई लाख", 250000.0),
        ("యాభై వేలు", 50000.0),
        ("पचास हज़ार", 50000.0),
    ]

    for raw_input, expected_val in test_cases:
        res = DeterministicAnswerExtractor.extract(
            raw_input, nsp_questions, context=context
        )
        assert len(res.answers) == 1, f"Failed on input: {raw_input}"
        ans = res.answers[0]
        assert ans.criterion_id == "annual_family_income"
        assert ans.extracted_value == expected_val, f"Mismatch for '{raw_input}': got {ans.extracted_value}, expected {expected_val}"
        assert ans.status == "ANSWERED"


def test_uncertainty_handling(pm_kisan_questions):
    """Verify uncertainty statements yield status UNKNOWN without false assumption."""
    context = {"current_question_id": "is_landholding_farmer"}

    uncertain_phrases = [
        "I don't know",
        "Not sure about this",
        "No idea really",
        "నాకు తెలియదు",
        "సరిగ్గా తెలియదు",
        "पता नहीं",
        "मुझे नहीं मालूम",
    ]

    for phrase in uncertain_phrases:
        res = DeterministicAnswerExtractor.extract(
            phrase, pm_kisan_questions, context=context
        )
        assert len(res.answers) == 1, f"Failed on phrase: {phrase}"
        ans = res.answers[0]
        assert ans.status == "UNKNOWN"
        # CRITICAL SAFETY RULE: UNKNOWN MUST NOT BE FALSE!
        assert ans.extracted_value is None
        assert ans.extracted_value is not False


def test_refusal_handling(pm_kisan_questions):
    """Verify refusal statements yield status PREFER_NOT_TO_ANSWER without false assumption."""
    context = {"current_question_id": "holds_constitutional_post"}

    refusal_phrases = [
        "I don't want to share",
        "Skip this question",
        "Prefer not to answer",
        "చెప్పదలచుకోలేదు",
        "దాటవేయండి",
        "मैं यह नहीं बताना चाहता",
        "छोड़ दो",
    ]

    for phrase in refusal_phrases:
        res = DeterministicAnswerExtractor.extract(
            phrase, pm_kisan_questions, context=context
        )
        assert len(res.answers) == 1, f"Failed on phrase: {phrase}"
        ans = res.answers[0]
        assert ans.status == "PREFER_NOT_TO_ANSWER"
        # CRITICAL SAFETY RULE: REFUSAL MUST NOT BE FALSE!
        assert ans.extracted_value is None
        assert ans.extracted_value is not False


def test_multi_answer_extraction(rythu_bandhu_questions, nsp_questions):
    """Verify extracting multiple answers from a single sentence only for active criteria."""
    utterance = "I am 35 years old, live in Telangana, and my annual family income is ₹2 lakh."

    # 1. When Rythu Bandhu is active:
    # Contains: is_telangana_resident -> True
    # Ignores: age 35, income 2 lakh (not part of Rythu Bandhu questionnaire)
    rb_res = DeterministicAnswerExtractor.extract(utterance, rythu_bandhu_questions)
    assert len(rb_res.answers) == 1
    assert rb_res.answers[0].criterion_id == "is_telangana_resident"
    assert rb_res.answers[0].extracted_value is True

    # 2. When NSP-CSSS is active:
    # Contains: annual_family_income -> 200000
    # Ignores: age 35, Telangana residency (not part of NSP-CSSS questionnaire)
    nsp_res = DeterministicAnswerExtractor.extract(utterance, nsp_questions)
    assert len(nsp_res.answers) == 1
    assert nsp_res.answers[0].criterion_id == "annual_family_income"
    assert nsp_res.answers[0].extracted_value == 200000.0


def test_correction_handling(nsp_questions):
    """Verify identifying corrections and capturing previous values."""
    context = {"current_question_id": "annual_family_income"}
    existing = {"annual_family_income": 200000.0}

    correction_msg = "Actually, my annual income is ₹1.5 lakh, not ₹2 lakh."
    res = DeterministicAnswerExtractor.extract(
        correction_msg, nsp_questions, existing_answers=existing, context=context
    )

    assert len(res.answers) == 1
    ans = res.answers[0]
    assert ans.criterion_id == "annual_family_income"
    assert ans.extracted_value == 150000.0
    assert ans.is_correction is True
    assert ans.previous_value == 200000.0


def test_ambiguous_answers_require_clarification(pm_kisan_questions):
    """Verify tentative/ambiguous statements trigger NEEDS_CLARIFICATION."""
    context = {"current_question_id": "is_landholding_farmer"}

    ambiguous_msg = "Maybe, but sometimes my father owns it"
    res = DeterministicAnswerExtractor.extract(
        ambiguous_msg, pm_kisan_questions, context=context
    )

    assert len(res.answers) == 1
    ans = res.answers[0]
    assert ans.status == "NEEDS_CLARIFICATION"
    assert ans.validation_status == "AMBIGUOUS"
    assert ans.clarification_prompt is not None


def test_irrelevant_messages(pm_kisan_questions):
    """Verify irrelevant statements result in zero extracted answers."""
    irrelevant_msgs = [
        "What is the capital of France?",
        "Please tell me the recipe for biryani",
        "What time is it?",
    ]
    for msg in irrelevant_msgs:
        res = DeterministicAnswerExtractor.extract(msg, pm_kisan_questions)
        assert len(res.answers) == 0


@pytest.mark.asyncio
async def test_groq_api_failure_fallback(nsp_questions):
    """Verify graceful fallback to deterministic extractor when Groq client fails."""
    # Force Groq client mock to raise an exception
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=RuntimeError("Groq API rate limit or network failure")
    )

    with patch.object(answer_extraction_service, "_get_client", return_value=mock_client):
        context = {"current_question_id": "annual_family_income"}
        res = await answer_extraction_service.extract_answers(
            "My annual income is 2 lakh", nsp_questions, context=context
        )

        # Must fall back gracefully!
        assert len(res.answers) == 1
        assert res.answers[0].criterion_id == "annual_family_income"
        assert res.answers[0].extracted_value == 200000.0
        assert res.source == "deterministic_fallback"


@pytest.mark.asyncio
async def test_groq_drops_hallucinated_criteria(nsp_questions):
    """Verify that any criterion ID returned by LLM that is not in active criteria is dropped."""
    mock_llm_json = {
        "answers": [
            {
                "criterion_id": "annual_family_income",
                "extracted_value": 300000.0,
                "status": "ANSWERED",
                "validation_status": "VALID",
                "raw_text": "3 lakh",
                "confidence": 0.95,
                "is_correction": False,
            },
            {
                "criterion_id": "fabricated_criterion_xyz",
                "extracted_value": "some_value",
                "status": "ANSWERED",
                "validation_status": "VALID",
                "raw_text": "fake",
                "confidence": 0.90,
                "is_correction": False,
            },
        ],
        "unmatched_text": None,
        "has_clarification_needed": False,
    }

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=str(mock_llm_json).replace("'", '"').replace("False", "false")))]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

    with patch.object(answer_extraction_service, "_get_client", return_value=mock_client):
        res = await answer_extraction_service.extract_answers(
            "My family income is 3 lakh", nsp_questions
        )

        assert len(res.answers) == 1
        assert res.answers[0].criterion_id == "annual_family_income"
        assert res.answers[0].extracted_value == 300000.0
        # The fabricated criterion was dropped!
        assert all(a.criterion_id != "fabricated_criterion_xyz" for a in res.answers)

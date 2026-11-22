import logging
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status

from app.core.exceptions import NotFoundError
from app.schemas.eligibility_schemas import (
    AnswerSubmissionRequest,
    AssessmentMessageRequest,
    AssessmentStatusResponse,
    StartAssessmentRequest,
)
from app.schemas.scheme_schemas import EligibilityEvaluationResponse
from app.services.answer_collection_service import answer_collection_service
from app.services.eligibility_service import eligibility_service

logger = logging.getLogger("nitsetu.eligibility_routes")

router = APIRouter()


@router.post(
    "/start",
    response_model=AssessmentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Start Multi-Turn Eligibility Assessment",
    description="Initializes a multi-turn eligibility collection workflow for a target welfare scheme.",
)
def start_assessment(payload: StartAssessmentRequest) -> AssessmentStatusResponse:
    """Initialize a multi-turn eligibility assessment session."""
    scheme_id = payload.scheme_id
    if not scheme_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target scheme_id is required to initiate an eligibility assessment.",
        )

    try:
        answer_collection_service.start_assessment(
            conversation_id=payload.conversation_id,
            scheme_id=scheme_id,
            language=payload.language,
            user_id=payload.user_id,
        )
        return answer_collection_service.get_assessment_status(payload.conversation_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))
    except Exception as e:
        logger.exception(f"Error starting assessment for conversation '{payload.conversation_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start assessment: {str(e)}",
        )


@router.post(
    "/message",
    response_model=AssessmentStatusResponse,
    summary="Submit Natural Language Answer for Active Assessment",
    description=(
        "Processes conversational citizen responses (English, Telugu, Hindi) for the current active question. "
        "Extracts criteria answers, runs validation, handles corrections and clarification loops, "
        "and advances questionnaire progression."
    ),
)
async def process_assessment_message(payload: AssessmentMessageRequest) -> AssessmentStatusResponse:
    """Process a natural language conversational message from a citizen."""
    state = answer_collection_service.get_assessment(payload.conversation_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active eligibility assessment found for conversation '{payload.conversation_id}'.",
        )

    try:
        await answer_collection_service.process_user_message(
            conversation_id=payload.conversation_id,
            message=payload.message,
            language=payload.language,
        )
        return answer_collection_service.get_assessment_status(payload.conversation_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))
    except Exception as e:
        logger.exception(f"Error processing message for conversation '{payload.conversation_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}",
        )


@router.post(
    "/submit",
    response_model=AssessmentStatusResponse,
    summary="Directly Submit Structured Answers",
    description="Submits typed or option-selected answers (e.g., from UI buttons or form controls) to active assessment.",
)
def submit_direct_answers(payload: AnswerSubmissionRequest) -> AssessmentStatusResponse:
    """Submit structured criteria answers directly into active assessment state."""
    state = answer_collection_service.get_assessment(payload.conversation_id)
    if not state:
        # Auto-initialize if not yet active
        try:
            answer_collection_service.start_assessment(
                conversation_id=payload.conversation_id,
                scheme_id=payload.scheme_id,
                language=payload.language or "en",
            )
        except NotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))

    try:
        answers_dict: Dict[str, Any] = {sub.field: sub.value for sub in payload.answers}
        answer_collection_service.submit_direct_answers(
            conversation_id=payload.conversation_id,
            answers=answers_dict,
            language=payload.language,
        )
        return answer_collection_service.get_assessment_status(payload.conversation_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))
    except Exception as e:
        logger.exception(f"Error submitting direct answers for '{payload.conversation_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit answers: {str(e)}",
        )


@router.get(
    "/{conversation_id}/status",
    response_model=AssessmentStatusResponse,
    summary="Get Eligibility Assessment Progress Status",
    description="Returns current progress, completed count, total criteria, active question, and readiness status.",
)
def get_assessment_status(conversation_id: str) -> AssessmentStatusResponse:
    """Retrieve the active assessment progress report for a conversation."""
    try:
        return answer_collection_service.get_assessment_status(conversation_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))


@router.post(
    "/{conversation_id}/evaluate",
    response_model=EligibilityEvaluationResponse,
    summary="Evaluate Collected Answers (Deterministic Handoff)",
    description=(
        "Converts collected applicant answers into clean evaluation input and runs deterministic assessment. "
        "Only valid ANSWERED criteria are evaluated; UNKNOWN and PREFER_NOT_TO_ANSWER are never coerced to False."
    ),
)
def evaluate_collected_assessment(conversation_id: str) -> EligibilityEvaluationResponse:
    """Evaluate applicant answers accumulated in the active assessment session."""
    state = answer_collection_service.get_assessment(conversation_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active eligibility assessment found for conversation '{conversation_id}'.",
        )

    try:
        clean_applicant_data = state.get_clean_applicant_data()
        eval_response = eligibility_service.evaluate_eligibility(
            scheme_id=state.scheme_id,
            applicant_data=clean_applicant_data,
        )
        state.collection_status = "COMPLETED"
        answer_collection_service.save_assessment(state)
        return eval_response
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e.message))
    except Exception as e:
        logger.exception(f"Error evaluating assessment for '{conversation_id}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate assessment: {str(e)}",
        )


@router.delete(
    "/{conversation_id}",
    summary="Reset / Clear Eligibility Assessment Session",
    description="Clears active assessment state from session memory when a citizen resets or starts over.",
)
def clear_assessment(conversation_id: str) -> Dict[str, Any]:
    """Reset or clear active assessment state."""
    state = answer_collection_service.get_assessment(conversation_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active assessment found for conversation '{conversation_id}'.",
        )

    answer_collection_service.clear_assessment(conversation_id)
    return {
        "success": True,
        "message": f"Assessment for conversation '{conversation_id}' has been reset.",
    }

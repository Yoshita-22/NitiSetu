"""Multi-Turn Conversation State Manager (Answer Collection Service) for NitiSetu.

Coordinates conversational eligibility questionnaire progression, answer extraction,
validation, state accumulation, correction tracking, and assessment completion readiness.
Preserves the canonical AssessmentState and ApplicantAnswer models.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
from app.core.exceptions import NotFoundError
from app.repositories.scheme_repository import scheme_repository
from app.schemas.eligibility_schemas import (
    AnswerStatus,
    ApplicantAnswer,
    AssessmentState,
    AssessmentStatusResponse,
    CollectionStatus,
    ExtractedAnswer,
    ExtractionResult,
    QuestionnaireItem,
    ValidatedAnswer,
    ValidationReport,
)
from app.services.answer_extraction_service import answer_extraction_service
from app.services.answer_validation_service import answer_validation_service
from app.services.questionnaire_mapping_service import questionnaire_mapping_service

logger = logging.getLogger("nitsetu.answer_collection")


class AnswerCollectionService:
    """Coordinates multi-turn civic questionnaire progression and assessment state management."""

    def __init__(self):
        # In-memory session store mapping conversation_id -> AssessmentState
        self._active_assessments: Dict[str, AssessmentState] = {}

    def start_assessment(
        self,
        conversation_id: str,
        scheme_id: str,
        user_id: str = "anonymous_citizen",
        language: str = "en",
    ) -> AssessmentState:
        """Initialize or reset an assessment session for a specific welfare scheme."""
        scheme = scheme_repository.get_by_id(scheme_id)
        if not scheme:
            raise NotFoundError(f"Scheme with ID '{scheme_id}' was not found.")

        questions = questionnaire_mapping_service.get_questionnaire(
            scheme.scheme_id, language=language
        )
        unanswered_ids = [q.id for q in questions]
        first_qid = unanswered_ids[0] if unanswered_ids else None

        state = AssessmentState(
            conversation_id=conversation_id,
            user_id=user_id,
            scheme_id=scheme.scheme_id,
            scheme_name=scheme.scheme_name,
            language=language,
            collection_status="WAITING_FOR_USER" if first_qid else "READY_FOR_EVALUATION",
            answers={},
            unanswered_question_ids=unanswered_ids,
            current_question_id=first_qid,
            clarification_required=False,
            turn_count=0,
            validation_errors=[],
        )

        self._active_assessments[conversation_id] = state
        logger.info(
            f"Started assessment {state.assessment_id} for scheme '{scheme.scheme_id}' "
            f"in conversation '{conversation_id}' with {len(unanswered_ids)} questions."
        )
        return state

    def get_assessment(self, conversation_id: str) -> Optional[AssessmentState]:
        """Retrieve the active assessment state for a conversation thread."""
        return self._active_assessments.get(conversation_id)

    def save_assessment(self, state: AssessmentState) -> None:
        """Persist or update assessment state in the session store."""
        state.updated_at = datetime.now(timezone.utc).isoformat()
        self._active_assessments[state.conversation_id] = state

    def clear_assessment(self, conversation_id: str) -> None:
        """Clear assessment state when conversation resets or concludes."""
        self._active_assessments.pop(conversation_id, None)

    def get_next_question(
        self, state: AssessmentState
    ) -> Optional[QuestionnaireItem]:
        """Determine and retrieve the next question requiring citizen input.

        Rules:
        1. If a question is in 'NEEDS_CLARIFICATION', it must be resolved first.
        2. Otherwise, select the earliest unanswered question in strict questionnaire order.
        3. Skip questions already answered with terminal statuses.
        4. If all criteria are addressed, update state lifecycle and return None.
        """
        all_questions = questionnaire_mapping_service.get_questionnaire(
            state.scheme_id, language=state.language
        )
        q_map = {q.id: q for q in all_questions}

        # Priority 1: Clarification required
        for cid, ans in state.answers.items():
            if ans.status == "NEEDS_CLARIFICATION":
                state.clarification_required = True
                state.current_question_id = cid
                state.collection_status = "NEEDS_CLARIFICATION"
                return q_map.get(cid)

        # Priority 2: Next unanswered in questionnaire order
        for q in all_questions:
            if q.id not in state.answers:
                state.clarification_required = False
                state.current_question_id = q.id
                state.collection_status = "WAITING_FOR_USER"
                return q

        # All questions have been addressed
        state.clarification_required = False
        state.current_question_id = None

        required_ids = [q.id for q in all_questions if q.required]
        if state.is_ready_for_evaluation(required_ids):
            state.collection_status = "READY_FOR_EVALUATION"
        else:
            state.collection_status = "IN_PROGRESS"

        return None

    async def process_user_message(
        self,
        conversation_id: str,
        message: str,
        language: Optional[str] = None,
    ) -> Tuple[AssessmentState, Optional[QuestionnaireItem], List[str]]:
        """Extract, validate, and store applicant answers from a citizen message.

        Coordinates:
        - Answer extraction across active questionnaire items.
        - Criterion-specific validation and statutory checks.
        - State update with correction history.
        - Next question progression.

        Returns:
            Tuple[AssessmentState, Optional[QuestionnaireItem], List[str]]:
            (updated_state, next_question_if_any, validation_errors_if_any)
        """
        state = self.get_assessment(conversation_id)
        if not state:
            raise NotFoundError(f"No active assessment found for conversation '{conversation_id}'.")

        lang = language or state.language
        state.language = lang
        state.validation_errors = []

        all_questions = questionnaire_mapping_service.get_questionnaire(
            state.scheme_id, language=lang
        )

        # 1. Answer Extraction
        context = {
            "scheme_id": state.scheme_id,
            "current_question_id": state.current_question_id,
        }
        extraction_res: ExtractionResult = await answer_extraction_service.extract_answers(
            user_message=message,
            active_questions=all_questions,
            existing_answers=state.answers,
            language=lang,
            context=context,
        )

        # If nothing could be extracted and a question was active:
        if not extraction_res.answers and state.current_question_id:
            logger.info(f"No answer extracted from message for '{state.current_question_id}'.")
            curr_q = next((q for q in all_questions if q.id == state.current_question_id), None)
            err_msg = (
                f"Could not understand response for '{curr_q.label if curr_q else state.current_question_id}'. "
                "Please answer with a direct response."
            )
            state.validation_errors.append(err_msg)
            self.save_assessment(state)
            return state, curr_q, state.validation_errors

        # 2. Answer Validation
        val_report: ValidationReport = answer_validation_service.validate_extraction_result(
            result=extraction_res,
            active_questions=all_questions,
            scheme_id=state.scheme_id,
            language=lang,
        )

        # 3. Apply validated answers to AssessmentState
        val_map = {v.criterion_id: v for v in val_report.validated_answers}
        for ext_ans in extraction_res.answers:
            cid = ext_ans.criterion_id
            v_ans = val_map.get(cid)
            if not v_ans:
                continue

            if not v_ans.is_valid:
                # Add validation error and do not commit invalid value
                if v_ans.error_message:
                    state.validation_errors.append(v_ans.error_message)
                if v_ans.requires_clarification:
                    state.clarification_required = True
                    # Record ambiguous status so next turn knows to resolve it
                    state.record_answer(
                        criterion_id=cid,
                        value=None,
                        status="NEEDS_CLARIFICATION",
                        validation_status="AMBIGUOUS",
                        raw_text=ext_ans.raw_text or message,
                        source="user_input",
                        reason=ext_ans.reasoning or "Ambiguous statement needing citizen clarification",
                    )
                continue

            # Handle valid answer (ANSWERED, UNKNOWN, PREFER_NOT_TO_ANSWER, NOT_APPLICABLE)
            source_type = "user_correction" if ext_ans.is_correction else "user_input"
            reason_text = (
                f"Citizen corrected answer. Previous: {ext_ans.previous_value}"
                if ext_ans.is_correction
                else ext_ans.reasoning or "Direct citizen answer"
            )

            state.record_answer(
                criterion_id=cid,
                value=v_ans.normalized_value,
                status=ext_ans.status,
                validation_status="VALID",
                raw_text=ext_ans.raw_text or message,
                source=source_type,
                reason=reason_text,
            )

        # Check if active clarification question has now been resolved
        if state.clarification_required:
            still_ambiguous = any(
                ans.status == "NEEDS_CLARIFICATION" for ans in state.answers.values()
            )
            state.clarification_required = still_ambiguous

        # 4. Progress to next question
        next_q = self.get_next_question(state)
        self.save_assessment(state)

        return state, next_q, state.validation_errors

    def submit_direct_answers(
        self,
        conversation_id: str,
        answers: Dict[str, Any],
        language: Optional[str] = None,
    ) -> Tuple[AssessmentState, Optional[QuestionnaireItem], List[str]]:
        """Directly submit structured answers (e.g. from UI buttons or form inputs)."""
        state = self.get_assessment(conversation_id)
        if not state:
            raise NotFoundError(f"No active assessment found for conversation '{conversation_id}'.")

        lang = language or state.language
        state.language = lang
        state.validation_errors = []

        all_questions = questionnaire_mapping_service.get_questionnaire(
            state.scheme_id, language=lang
        )
        q_map = {q.id: q for q in all_questions}

        for cid, val in answers.items():
            q = q_map.get(cid)
            if not q:
                continue

            # Determine status based on value
            if val is None or val == "UNKNOWN":
                status: AnswerStatus = "UNKNOWN"
                typed_val = None
            elif val == "PREFER_NOT_TO_ANSWER":
                status = "PREFER_NOT_TO_ANSWER"
                typed_val = None
            elif val == "NOT_APPLICABLE":
                status = "NOT_APPLICABLE"
                typed_val = None
            else:
                status = "ANSWERED"
                typed_val = val

            v_ans: ValidatedAnswer = answer_validation_service.validate_raw_answer(
                criterion_id=cid,
                value=typed_val,
                scheme_id=state.scheme_id,
                status=status,
                language=lang,
            )

            if not v_ans.is_valid:
                if v_ans.error_message:
                    state.validation_errors.append(v_ans.error_message)
                continue

            prev = state.answers.get(cid)
            is_corr = prev is not None and prev.value != v_ans.normalized_value

            state.record_answer(
                criterion_id=cid,
                value=v_ans.normalized_value,
                status=status,
                validation_status="VALID",
                raw_text=str(val),
                source="user_correction" if is_corr else "user_input",
                reason="Direct answer submission",
            )

        next_q = self.get_next_question(state)
        self.save_assessment(state)
        return state, next_q, state.validation_errors

    def get_assessment_status(self, conversation_id: str) -> AssessmentStatusResponse:
        """Generate structured progress report matching AssessmentStatusResponse contract."""
        state = self.get_assessment(conversation_id)
        if not state:
            raise NotFoundError(f"No active assessment found for conversation '{conversation_id}'.")

        all_questions = questionnaire_mapping_service.get_questionnaire(
            state.scheme_id, language=state.language
        )
        total_count = len(all_questions)
        completed_count = sum(
            1 for cid, ans in state.answers.items() if ans.status != "NEEDS_CLARIFICATION"
        )

        curr_q = None
        if state.current_question_id:
            q_item = next((q for q in all_questions if q.id == state.current_question_id), None)
            if q_item:
                curr_q = q_item.to_pending_question()

        required_ids = [q.id for q in all_questions if q.required]
        is_ready = state.is_ready_for_evaluation(required_ids)

        return AssessmentStatusResponse(
            assessment_id=state.assessment_id,
            scheme_id=state.scheme_id,
            scheme_name=state.scheme_name,
            collection_status=state.collection_status,
            completed_count=completed_count,
            total_count=total_count,
            current_question=curr_q,
            is_ready_for_evaluation=is_ready,
            clarification_required=state.clarification_required,
            validation_errors=list(state.validation_errors),
        )


# Default service instance
answer_collection_service = AnswerCollectionService()

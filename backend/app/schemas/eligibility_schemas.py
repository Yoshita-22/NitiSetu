from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
import uuid
from pydantic import BaseModel, Field

# Reuse existing models from scheme_schemas and chat_query_schema to avoid duplicates
from app.schemas.chat_query_schema import PendingQuestion
from app.schemas.scheme_schemas import (
    EligibilityConditionResult,
    EligibilityEvaluationRequest,
    EligibilityEvaluationResponse,
    EligibilityQuestion,
    EligibilityQuestionsResponse,
)

# -------------------------------------------------------------------------
# Core Enums and Types
# -------------------------------------------------------------------------

AnswerStatus = Literal[
    "ANSWERED",
    "UNKNOWN",
    "NOT_APPLICABLE",
    "PREFER_NOT_TO_ANSWER",
    "NEEDS_CLARIFICATION",
]

ValidationStatus = Literal[
    "VALID",
    "INVALID",
    "AMBIGUOUS",
    "CORRECTION",
]

CollectionStatus = Literal[
    "NOT_STARTED",
    "IN_PROGRESS",
    "WAITING_FOR_USER",
    "NEEDS_CLARIFICATION",
    "READY_FOR_EVALUATION",
    "COMPLETED",
    "FAILED",
]

CriterionInputType = Literal[
    "boolean",
    "number",
    "select",
    "text",
    "date",
]

UpdateSource = Literal[
    "user_input",
    "entity_extraction",
    "system_inferred",
    "user_correction",
]


# -------------------------------------------------------------------------
# Criterion-Specific Validation Rules
# -------------------------------------------------------------------------


class CriterionValidationRule(BaseModel):
    """Criterion-specific validation constraints.

    Allows fine-grained constraints (e.g., minimum age, income thresholds, valid option
    keys) without imposing global assumptions across differing schemes.
    """

    criterion_id: str = Field(..., description="Target criterion/question identifier")
    input_type: CriterionInputType = Field("boolean", description="Expected data type")
    min_value: Optional[float] = Field(None, description="Minimum numeric limit (inclusive)")
    max_value: Optional[float] = Field(None, description="Maximum numeric limit (inclusive)")
    allowed_values: Optional[List[Any]] = Field(None, description="Whitelist of acceptable discrete values")
    regex_pattern: Optional[str] = Field(None, description="Optional regex pattern for string input")
    error_message: Optional[str] = Field(None, description="Citizen-friendly error explanation if validation fails")
    clarification_hint: Optional[str] = Field(
        None, description="Contextual hint prompted when citizen response is ambiguous"
    )

    def validate_value(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate an applicant's value against this specific criterion rule.

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_or_clarification_message)
        """
        if value is None:
            return False, self.error_message or f"Value for '{self.criterion_id}' is required."

        if self.input_type == "boolean":
            if not isinstance(value, bool):
                if isinstance(value, str):
                    lower = value.strip().lower()
                    if lower in ("yes", "true", "1", "y", "ha", "avunu"):
                        return True, None
                    if lower in ("no", "false", "0", "n", "nahi", "kadu"):
                        return True, None
                return False, self.error_message or f"Please answer Yes or No for '{self.criterion_id}'."
            return True, None

        if self.input_type == "number":
            try:
                num = float(value)
            except (ValueError, TypeError):
                return False, self.error_message or f"Please enter a valid numeric value for '{self.criterion_id}'."

            if self.min_value is not None and num < self.min_value:
                return False, f"Value must be at least {self.min_value}. {self.error_message or ''}".strip()
            if self.max_value is not None and num > self.max_value:
                return False, f"Value cannot exceed {self.max_value}. {self.error_message or ''}".strip()
            return True, None

        if self.input_type == "select":
            if self.allowed_values is not None:
                if value not in self.allowed_values:
                    allowed_str = ", ".join(str(v) for v in self.allowed_values)
                    return False, self.error_message or f"Please choose from: {allowed_str}."
            return True, None

        if self.input_type == "text" and self.regex_pattern:
            if not isinstance(value, str) or not re.match(self.regex_pattern, value):
                return False, self.error_message or f"Input format for '{self.criterion_id}' is invalid."

        return True, None


# -------------------------------------------------------------------------
# Questionnaire Item & Criteria Definition
# -------------------------------------------------------------------------


class QuestionnaireItem(EligibilityQuestion):
    """Enriched question definition extending the basic EligibilityQuestion.

    Binds a citizen question to a specific criterion, UI input widget, and
    criterion-specific validation rules.
    """

    id: str = Field(..., description="Variable key matching evaluation field and criterion")
    label: str = Field(..., description="Citizen-facing question prompt")
    type: CriterionInputType = Field("boolean", description="Input widget and data type")  # type: ignore[assignment]
    options: Optional[List[Dict[str, Any]]] = Field(None, description="Selectable options for select inputs")
    help_text: Optional[str] = Field(None, description="Clarifying context or instructions for citizen")
    required: bool = Field(True, description="Whether an answer is mandatory for deterministic assessment")
    criterion_id: Optional[str] = Field(None, description="Underlying statutory condition ID")
    validation_rule: Optional[CriterionValidationRule] = Field(
        None, description="Criterion-specific validation parameters"
    )
    order: int = Field(0, description="Display or inquiry ordering sequence")
    category: Optional[str] = Field(None, description="Domain group e.g. demographic, income, landholding")

    def to_eligibility_question(self) -> EligibilityQuestion:
        """Convert to base EligibilityQuestion for backwards compatibility."""
        mapped_type: Literal["boolean", "number", "select"] = (
            self.type if self.type in ("boolean", "number", "select") else "select"
        )
        return EligibilityQuestion(
            id=self.id,
            label=self.label,
            type=mapped_type,
            options=self.options,
            help_text=self.help_text,
            required=self.required,
        )

    def to_pending_question(self) -> PendingQuestion:
        """Convert to PendingQuestion for LangGraph interrupt and ChatQueryResponse contract."""
        input_type_map: Dict[str, Literal["boolean", "number", "text", "select"]] = {
            "boolean": "boolean",
            "number": "number",
            "select": "select",
            "text": "text",
            "date": "text",
        }
        mapped_input = input_type_map.get(self.type, "text")
        return PendingQuestion(
            field=self.id,
            question=self.label,
            input_type=mapped_input,
            options=self.options,
            help_text=self.help_text,
        )

    @classmethod
    def from_eligibility_question(
        cls,
        q: EligibilityQuestion,
        validation_rule: Optional[CriterionValidationRule] = None,
        order: int = 0,
        category: Optional[str] = None,
    ) -> "QuestionnaireItem":
        """Factory constructor converting an existing EligibilityQuestion seamlessly."""
        return cls(
            id=q.id,
            label=q.label,
            type=q.type,
            options=q.options,
            help_text=q.help_text,
            required=q.required,
            criterion_id=q.id,
            validation_rule=validation_rule,
            order=order,
            category=category,
        )


# -------------------------------------------------------------------------
# Correction Tracking & Answer State
# -------------------------------------------------------------------------


class AnswerHistoryEntry(BaseModel):
    """Audit entry recording answer modification or state transition."""

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 timestamp of modification",
    )
    previous_value: Optional[Any] = Field(None, description="Value prior to this update")
    new_value: Optional[Any] = Field(None, description="Value after this update")
    previous_status: Optional[str] = Field(None, description="AnswerStatus before update")
    new_status: str = Field(..., description="AnswerStatus after update")
    turn_number: Optional[int] = Field(None, description="Conversation turn when modification occurred")
    source: UpdateSource = Field("user_input", description="Origin of this update")
    reason: Optional[str] = Field(None, description="Reason for correction or adjustment")


class ApplicantAnswer(BaseModel):
    """Rich citizen answer record for an individual criterion.

    Preserves full lifecycle: value, validation state, confidence, ambiguity,
    and historic audit trail of corrections.
    """

    criterion_id: str = Field(..., description="Matches questionnaire item ID")
    value: Optional[Any] = Field(None, description="Validated typed value (bool, float, int, str)")
    raw_text: Optional[str] = Field(None, description="Citizen's raw natural language utterance")
    status: AnswerStatus = Field("ANSWERED", description="Citizen interaction answer status")
    validation_status: ValidationStatus = Field("VALID", description="Verification state of this answer")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Extraction or classification confidence score")
    clarification_prompt: Optional[str] = Field(
        None, description="Clarification message prompted to citizen if status is NEEDS_CLARIFICATION"
    )
    history: List[AnswerHistoryEntry] = Field(
        default_factory=list, description="Audit log of previous values and corrections"
    )
    last_updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 timestamp of most recent change",
    )

    def record_update(
        self,
        new_value: Optional[Any],
        new_status: AnswerStatus,
        new_validation_status: ValidationStatus = "VALID",
        raw_text: Optional[str] = None,
        source: UpdateSource = "user_input",
        reason: Optional[str] = None,
        turn_number: Optional[int] = None,
    ) -> None:
        """Apply an update or correction to this answer and record in history."""
        # Record historical entry before mutation if there was a previous state
        entry = AnswerHistoryEntry(
            previous_value=self.value,
            new_value=new_value,
            previous_status=self.status,
            new_status=new_status,
            turn_number=turn_number,
            source=source,
            reason=reason,
        )
        self.history.append(entry)

        self.value = new_value
        self.status = new_status
        self.validation_status = new_validation_status
        if raw_text is not None:
            self.raw_text = raw_text
        self.last_updated_at = datetime.now(timezone.utc).isoformat()

    def is_usable_for_evaluation(self) -> bool:
        """Determine if this answer provides a definitive, validated value for rule evaluation."""
        return self.status == "ANSWERED" and self.validation_status == "VALID" and self.value is not None


# -------------------------------------------------------------------------
# Multi-Turn Assessment State
# -------------------------------------------------------------------------


class AssessmentState(BaseModel):
    """Comprehensive conversation and collection state for multi-turn eligibility inquiry.

    Maintains the state of answer collection across multiple dialogue turns,
    supporting single-question asks, correction handling, clarification requests,
    and eventual handoff to deterministic evaluation.
    """

    assessment_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this assessment workflow session",
    )
    conversation_id: str = Field(..., description="Underlying chat conversation thread UUID")
    user_id: Optional[str] = Field("anonymous_citizen", description="Citizen identifier")
    scheme_id: str = Field(..., description="Target scheme identifier e.g. PM_KISAN")
    scheme_name: str = Field(..., description="Official welfare scheme name")
    language: str = Field("en", description="Citizen selected language code (en, te, hi)")

    collection_status: CollectionStatus = Field(
        "NOT_STARTED", description="Progress lifecycle of answer collection"
    )
    answers: Dict[str, ApplicantAnswer] = Field(
        default_factory=dict, description="Map of criterion_id to ApplicantAnswer"
    )
    unanswered_question_ids: List[str] = Field(
        default_factory=list, description="Ordered list of question IDs awaiting answers"
    )
    current_question_id: Optional[str] = Field(
        None, description="The specific question currently presented to citizen"
    )
    clarification_required: bool = Field(
        False, description="True if workflow is waiting for applicant clarification"
    )
    turn_count: int = Field(0, description="Total dialogue turns in this assessment session")
    validation_errors: List[str] = Field(
        default_factory=list, description="Active validation error messages"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Session creation timestamp",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Session last update timestamp",
    )

    def record_answer(
        self,
        criterion_id: str,
        value: Optional[Any],
        status: AnswerStatus = "ANSWERED",
        validation_status: ValidationStatus = "VALID",
        raw_text: Optional[str] = None,
        source: UpdateSource = "user_input",
        reason: Optional[str] = None,
    ) -> ApplicantAnswer:
        """Register or update an applicant answer, automatically preserving history."""
        self.turn_count += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()

        if criterion_id in self.answers:
            answer = self.answers[criterion_id]
            answer.record_update(
                new_value=value,
                new_status=status,
                new_validation_status=validation_status,
                raw_text=raw_text,
                source=source,
                reason=reason,
                turn_number=self.turn_count,
            )
        else:
            answer = ApplicantAnswer(
                criterion_id=criterion_id,
                value=value,
                raw_text=raw_text,
                status=status,
                validation_status=validation_status,
                last_updated_at=self.updated_at,
            )
            self.answers[criterion_id] = answer

        # Update unanswered list if answered
        if status in ("ANSWERED", "UNKNOWN", "NOT_APPLICABLE", "PREFER_NOT_TO_ANSWER"):
            if criterion_id in self.unanswered_question_ids:
                self.unanswered_question_ids.remove(criterion_id)

        return answer

    def get_clean_applicant_data(self) -> Dict[str, Any]:
        """Convert collected answers into a clean dictionary for deterministic evaluation.

        Only includes validated, ANSWERED criteria. UNKNOWN, NOT_APPLICABLE, or
        PREFER_NOT_TO_ANSWER are not cast to False, keeping deterministic evaluation honest.
        """
        clean_data: Dict[str, Any] = {}
        for cid, ans in self.answers.items():
            if ans.is_usable_for_evaluation():
                clean_data[cid] = ans.value
        return clean_data

    def is_ready_for_evaluation(self, required_criteria_ids: List[str]) -> bool:
        """Check if all mandatory criteria have been addressed (either answered, unknown, etc.)."""
        for req_id in required_criteria_ids:
            if req_id not in self.answers:
                return False
            # If an answer requires clarification, it cannot proceed directly to evaluation
            if self.answers[req_id].status == "NEEDS_CLARIFICATION":
                return False
        return True


# -------------------------------------------------------------------------
# API Payloads & Handoff Schemas
# -------------------------------------------------------------------------


class AnswerSubmission(BaseModel):
    """Individual submitted answer payload from client / citizen."""

    field: str = Field(..., description="Target question/criterion identifier")
    value: Optional[Any] = Field(None, description="Answer value (boolean, number, string, option key)")
    status: AnswerStatus = Field("ANSWERED", description="Citizen status: ANSWERED, UNKNOWN, PREFER_NOT_TO_ANSWER, etc.")
    raw_text: Optional[str] = Field(None, description="Original natural language text or audio transcript")


class StartAssessmentRequest(BaseModel):
    """Payload to initiate a new multi-turn assessment session."""

    conversation_id: str = Field(..., description="UUID of the chat conversation thread")
    scheme_id: Optional[str] = Field(None, description="Target scheme ID if not specified in path")
    language: str = Field("en", description="Citizen language preference (en, te, hi)")
    user_id: Optional[str] = Field("anonymous_citizen", description="Citizen identifier")


class AssessmentMessageRequest(BaseModel):
    """Payload to submit a natural language response for an active assessment."""

    conversation_id: str = Field(..., description="UUID of the active assessment session")
    message: str = Field(..., min_length=1, description="Citizen conversational utterance or answer")
    language: Optional[str] = Field(None, description="Language code (en, te, hi)")


class AnswerSubmissionRequest(BaseModel):
    """Payload to submit one or more answers in an assessment session."""

    conversation_id: str = Field(..., description="UUID of the chat conversation")
    scheme_id: str = Field(..., description="Scheme ID being assessed")
    answers: List[AnswerSubmission] = Field(..., description="List of submitted answers")
    language: Optional[str] = Field("en", description="Language of submission (en, te, hi)")


class AssessmentStatusResponse(BaseModel):
    """Current progress report of the eligibility collection session."""

    assessment_id: str
    scheme_id: str
    scheme_name: str
    collection_status: CollectionStatus
    completed_count: int = Field(..., description="Number of criteria addressed so far")
    total_count: int = Field(..., description="Total number of criteria required for scheme")
    current_question: Optional[PendingQuestion] = Field(
        None, description="The current active question if waiting for citizen"
    )
    is_ready_for_evaluation: bool = Field(
        False, description="Whether sufficient information exists to run deterministic evaluation"
    )
    clarification_required: bool = Field(False)
    validation_errors: List[str] = Field(default_factory=list, description="Active validation errors")
    disclaimer: str = (
        "Preliminary eligibility assessment is for civic information only and does not constitute statutory approval."
    )


# -------------------------------------------------------------------------
# Answer Extraction Schemas
# -------------------------------------------------------------------------


class ExtractedAnswer(BaseModel):
    """Structured extraction of an applicant answer for a single questionnaire criterion."""

    criterion_id: str = Field(..., description="Target criterion/question identifier")
    extracted_value: Optional[Any] = Field(None, description="Typed parsed value (e.g. True, 250000, 'SC')")
    status: AnswerStatus = Field("ANSWERED", description="Inferred or direct status")
    validation_status: ValidationStatus = Field("VALID", description="Provisional extraction status")
    raw_text: Optional[str] = Field(None, description="Exact substring or full message corresponding to answer")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score of this extraction")
    is_correction: bool = Field(False, description="True if citizen is revising a previously submitted answer")
    previous_value: Optional[Any] = Field(None, description="Previous value if this extraction is a correction")
    source: Literal["llm", "deterministic_fallback"] = Field(
        "deterministic_fallback", description="Source engine of the extraction"
    )
    clarification_prompt: Optional[str] = Field(
        None, description="Clarification message prompted to citizen if status is NEEDS_CLARIFICATION"
    )
    reasoning: Optional[str] = Field(None, description="Rationale for the extracted value or status")


class ExtractionResult(BaseModel):
    """Container model returning all answers extracted from a single citizen utterance."""

    answers: List[ExtractedAnswer] = Field(default_factory=list, description="Extracted answers")
    unmatched_text: Optional[str] = Field(None, description="Parts of utterance not matching active criteria")
    has_clarification_needed: bool = Field(False, description="True if any extracted answer requires clarification")
    source: Literal["llm", "deterministic_fallback"] = Field("deterministic_fallback")
    raw_message: str = Field(..., description="Original raw citizen message")


# -------------------------------------------------------------------------
# Answer Validation Schemas
# -------------------------------------------------------------------------


class ValidatedAnswer(BaseModel):
    """Result of validating an extracted citizen answer against statutory criterion rules."""

    criterion_id: str = Field(..., description="Target criterion/question identifier")
    is_valid: bool = Field(True, description="Whether the answer conforms to data type and boundary constraints")
    validation_status: ValidationStatus = Field("VALID", description="Verification state of this answer")
    normalized_value: Optional[Any] = Field(None, description="Clean, type-coerced value (bool, float, int, str)")
    error_message: Optional[str] = Field(None, description="Citizen-friendly error message if validation failed")
    clarification_prompt: Optional[str] = Field(
        None, description="Contextual prompt presented if answer requires citizen clarification"
    )
    requires_clarification: bool = Field(False, description="True if status is NEEDS_CLARIFICATION or AMBIGUOUS")
    is_disqualifying: bool = Field(
        False, description="Informational flag indicating if this answer will statutorily exclude the applicant"
    )
    statutory_note: Optional[str] = Field(
        None, description="Explanatory statutory context regarding why this answer impacts scheme qualification"
    )


class ValidationReport(BaseModel):
    """Aggregated validation report over multiple answers."""

    is_all_valid: bool = Field(True, description="True if all answers passed validation without errors")
    validated_answers: List[ValidatedAnswer] = Field(
        default_factory=list, description="List of validated answer objects"
    )
    errors: List[str] = Field(default_factory=list, description="Collection of all validation error messages")
    has_disqualifying_condition: bool = Field(
        False, description="True if at least one answer triggers a statutory exclusion condition"
    )
    disqualifying_reasons: List[str] = Field(
        default_factory=list, description="Explanations of detected statutory disqualifications"
    )
    requires_clarification: bool = Field(False, description="True if any answer is ambiguous or needs clarification")

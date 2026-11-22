from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class PendingQuestion(BaseModel):
    """Structured question for human-in-the-loop workflow interruption."""

    field: str = Field(..., description="Target applicant attribute key (e.g. 'is_landholding_farmer', 'annual_income')")
    question: str = Field(..., description="Clear citizen-facing question text")
    input_type: Literal["boolean", "number", "text", "select"] = Field("boolean", description="Recommended UI input widget")
    options: Optional[List[Dict[str, Any]]] = Field(None, description="Options if input_type is select")
    help_text: Optional[str] = Field(None, description="Contextual guidance for the citizen")


class ChatQueryRequest(BaseModel):
    """Incoming citizen chat message payload for LangGraph workflow execution."""

    conversation_id: str = Field(..., description="UUID identifying the conversation thread", json_schema_extra={"example": "123e4567-e89b-12d3-a456-426614174000"})
    message: str = Field(..., min_length=1, description="Citizen query message", json_schema_extra={"example": "Am I eligible for PM-KISAN?"})
    document_id: Optional[str] = Field(None, description="Optional uploaded document UUID to contextualize query")
    user_id: Optional[str] = Field("anonymous_citizen", description="Optional citizen / owner identifier")


class ChatResumeRequest(BaseModel):
    """Payload to resume an interrupted LangGraph workflow with submitted answers."""

    conversation_id: str = Field(..., description="UUID of the interrupted conversation thread")
    answers: Dict[str, Any] = Field(..., description="Citizen answers keyed by field name", json_schema_extra={"example": {"is_landholding_farmer": True}})
    user_id: Optional[str] = Field("anonymous_citizen", description="Optional citizen / owner identifier")


class ExecutionStatus(BaseModel):
    """Execution progress metadata for multi-intent workflows."""

    completed_tasks: List[str] = Field(default_factory=list, description="Nodes/tasks executed successfully")
    failed_tasks: List[str] = Field(default_factory=list, description="Nodes/tasks that encountered an error")
    partial_failure: bool = Field(False, description="True if at least one branch succeeded while another failed")


class ChatQueryResponse(BaseModel):
    """Unified response returned by LangGraph workflow."""

    status: Literal["completed", "waiting_for_user", "failed"] = Field(..., description="Current lifecycle state")
    conversation_id: str = Field(..., description="Conversation thread identifier")
    language: str = Field("en", description="Response language (en, te, hi)")
    intent: str = Field(..., description="Primary classified intent")
    answer: str = Field(..., description="Natural language response or interrupt prompt")
    results: Dict[str, Any] = Field(default_factory=dict, description="Structured domain results (law, scheme, document, eligibility)")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Citations and official source references")
    execution: ExecutionStatus = Field(default_factory=ExecutionStatus, description="Execution tasks summary")
    pending_questions: List[PendingQuestion] = Field(default_factory=list, description="Questions requiring citizen input if interrupted")

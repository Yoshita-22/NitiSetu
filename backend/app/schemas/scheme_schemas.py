from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class SchemeSummary(BaseModel):
    """Lightweight representation of a government scheme for list view."""

    scheme_id: str = Field(..., description="Unique scheme identifier")
    scheme_name: str = Field(..., description="Official name of the welfare scheme")
    short_description: str = Field(..., description="Brief summary of scheme objectives")
    ministry: str = Field(..., description="Implementing Ministry or Department")
    target_beneficiaries: str = Field(..., description="Target group e.g. Farmers, Rural Poor, Students")
    state_applicability: str = Field(..., description="State or All India applicability")
    data_source: str = Field("verified_demo_dataset", description="Origin of scheme data")
    official_source_url: str = Field(..., description="Official government scheme portal URL")


class Scheme(SchemeSummary):
    """Full detail model for a government scheme."""

    benefits: List[str] = Field(default_factory=list, description="List of financial or in-kind entitlements")
    eligibility_conditions: List[str] = Field(default_factory=list, description="Official positive eligibility criteria")
    exclusion_conditions: List[str] = Field(default_factory=list, description="Official statutory disqualifications")
    required_documents: List[str] = Field(default_factory=list, description="Required documents for application")
    last_verified: str = Field(..., description="Date when official rules were verified (YYYY-MM-DD)")


class EligibilityQuestion(BaseModel):
    """Definition of an individual question for deterministic eligibility evaluation."""

    id: str = Field(..., description="Variable key matching evaluation field")
    label: str = Field(..., description="Clear citizen-facing question prompt")
    type: Literal["boolean", "number", "select"] = Field(..., description="Input widget type")
    options: Optional[List[Dict[str, Any]]] = Field(None, description="Options for select inputs")
    help_text: Optional[str] = Field(None, description="Clarifying context or instructions")
    required: bool = Field(True, description="Whether an answer is mandatory for full evaluation")


class EligibilityQuestionsResponse(BaseModel):
    """Questionnaire configuration for a specific scheme."""

    scheme_id: str
    scheme_name: str
    questions: List[EligibilityQuestion]


class EligibilityEvaluationRequest(BaseModel):
    """Citizen input answers submitted for eligibility assessment."""

    applicant_data: Dict[str, Any] = Field(
        ...,
        description="Key-value pairs of applicant profile matching scheme question IDs",
        json_schema_extra={"example": {"is_landholding_farmer": True, "holds_constitutional_post": False}},
    )


class EligibilityConditionResult(BaseModel):
    """Evaluation result for an individual scheme condition."""

    condition: str = Field(..., description="Condition rule statement")
    status: Literal["MET", "NOT_MET", "UNKNOWN"] = Field(..., description="Result of evaluating this rule")
    explanation: str = Field(..., description="Deterministic reasoning for condition status")


class EligibilityEvaluationResponse(BaseModel):
    """Deterministic eligibility assessment report."""

    scheme_id: str
    scheme_name: str
    assessment_status: Literal["PRELIMINARY"] = "PRELIMINARY"
    overall_result: Literal["LIKELY_ELIGIBLE", "LIKELY_NOT_ELIGIBLE", "NEEDS_MORE_INFORMATION"]
    conditions: List[EligibilityConditionResult]
    missing_information: List[str] = Field(
        default_factory=list, description="Required questions not answered by applicant"
    )
    official_source_url: str
    disclaimer: str = "This is a preliminary assessment and not an official approval. Official eligibility is verified by designated government authorities upon formal document submission."

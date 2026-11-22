from typing import List
from fastapi import APIRouter, HTTPException, Query
from app.core.exceptions import NotFoundError
from app.schemas.scheme_schemas import (
    EligibilityEvaluationRequest,
    EligibilityEvaluationResponse,
    EligibilityQuestionsResponse,
    Scheme,
    SchemeSummary,
)
from app.services.eligibility_service import eligibility_service
from app.services.scheme_service import scheme_service

router = APIRouter()


@router.get(
    "",
    response_model=List[SchemeSummary],
    summary="List All Verified Welfare Schemes",
    description="Returns verified government welfare schemes in summary format.",
)
def list_schemes() -> List[SchemeSummary]:
    """Return all available government schemes."""
    return scheme_service.get_all_schemes()


@router.get(
    "/search",
    response_model=List[SchemeSummary],
    summary="Search Welfare Schemes by Keyword",
    description="Search schemes by keyword across title, description, benefits, and target beneficiaries.",
)
def search_schemes(
    q: str = Query(..., min_length=1, description="Search keyword e.g. 'farmer', 'health', 'scholarship', 'telangana'")
) -> List[SchemeSummary]:
    """Search welfare schemes by keyword."""
    return scheme_service.search_schemes(q)


@router.get(
    "/{scheme_id}",
    response_model=Scheme,
    summary="Get Scheme Details by ID",
    description="Returns complete details, benefits, eligibility conditions, and documentation requirements for a scheme.",
)
def get_scheme(scheme_id: str) -> Scheme:
    """Retrieve detailed scheme information by scheme ID."""
    try:
        return scheme_service.get_scheme_by_id(scheme_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.message))


@router.get(
    "/{scheme_id}/eligibility/questions",
    response_model=EligibilityQuestionsResponse,
    summary="Get Scheme-Specific Eligibility Questionnaire",
    description="Retrieves the structured questionnaire configured for deterministic eligibility assessment of this scheme.",
)
def get_eligibility_questions(scheme_id: str) -> EligibilityQuestionsResponse:
    """Retrieve eligibility questionnaire for a specific scheme."""
    try:
        return eligibility_service.get_questions_for_scheme(scheme_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.message))


@router.post(
    "/{scheme_id}/eligibility/evaluate",
    response_model=EligibilityEvaluationResponse,
    summary="Evaluate Scheme Eligibility (Deterministic)",
    description=(
        "Deterministically evaluates applicant data against verified scheme criteria. "
        "Provides individual condition statuses (MET, NOT_MET, UNKNOWN), identifies missing information, "
        "and returns an overall preliminary assessment without hallucinated approvals."
    ),
)
def evaluate_eligibility(
    scheme_id: str, payload: EligibilityEvaluationRequest
) -> EligibilityEvaluationResponse:
    """Evaluate applicant answers against official scheme rules."""
    try:
        return eligibility_service.evaluate_eligibility(scheme_id, payload.applicant_data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.message))

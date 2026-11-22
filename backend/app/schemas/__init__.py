from app.schemas.health import HealthResponse
from app.schemas.chat import ChatTestRequest, ChatTestResponse
from app.schemas.common_schemas import BaseResponse, ErrorDetail
from app.schemas.law_schemas import LawSearchResultItem, LawSearchResponse
from app.schemas.scheme_schemas import (
    Scheme,
    SchemeSummary,
    EligibilityQuestion,
    EligibilityQuestionsResponse,
    EligibilityEvaluationRequest,
    EligibilityConditionResult,
    EligibilityEvaluationResponse,
)
from app.schemas.document_schemas import (
    DocumentMetadata,
    DocumentPage,
    DocumentUploadResponse,
    DocumentPagesResponse,
    ProcessingStatus,
)

__all__ = [
    "HealthResponse",
    "ChatTestRequest",
    "ChatTestResponse",
    "BaseResponse",
    "ErrorDetail",
    "LawSearchResultItem",
    "LawSearchResponse",
    "Scheme",
    "SchemeSummary",
    "EligibilityQuestion",
    "EligibilityQuestionsResponse",
    "EligibilityEvaluationRequest",
    "EligibilityConditionResult",
    "EligibilityEvaluationResponse",
    "DocumentMetadata",
    "DocumentPage",
    "DocumentUploadResponse",
    "DocumentPagesResponse",
    "ProcessingStatus",
]

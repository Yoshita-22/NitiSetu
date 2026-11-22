from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Supported intent categories in NitiSetu."""

    LAW_INFORMATION = "LAW_INFORMATION"
    SCHEME_INFORMATION = "SCHEME_INFORMATION"
    SCHEME_ELIGIBILITY = "SCHEME_ELIGIBILITY"
    DOCUMENT_QUERY = "DOCUMENT_QUERY"
    MULTI_INTENT = "MULTI_INTENT"
    GENERAL_QUERY = "GENERAL_QUERY"
    UNSUPPORTED_QUERY = "UNSUPPORTED_QUERY"


class ExtractedEntities(BaseModel):
    """Named entities and civic attributes extracted from citizen queries."""

    scheme_name: Optional[str] = Field(None, description="Identified welfare scheme name or acronym (e.g. PM-KISAN, Rythu Bandhu)")
    scheme_id: Optional[str] = Field(None, description="Normalized scheme identifier if recognized")
    law_name: Optional[str] = Field(None, description="Identified law or statute (e.g. Consumer Protection Act, DPDP Act)")
    act_name: Optional[str] = Field(None, description="Short Act name")
    section_number: Optional[str] = Field(None, description="Identified Article or Section number (e.g. Article 21, Section 6)")
    legal_topic: Optional[str] = Field(None, description="Legal subject matter (e.g. consumer rights, privacy, cyber crime)")
    document_id: Optional[str] = Field(None, description="Document UUID if mentioned in query or provided in context")
    applicant_info: Dict[str, Any] = Field(default_factory=dict, description="Applicant profile parameters provided in query")
    location_or_state: Optional[str] = Field(None, description="State or territory e.g. Telangana, All India")
    missing_or_ambiguous: List[str] = Field(default_factory=list, description="Missing or ambiguous parameters required for execution")


class IntentClassification(BaseModel):
    """Structured output returned by Groq intent classifier."""

    intent: IntentType = Field(..., description="Primary detected intent")
    secondary_intents: List[IntentType] = Field(default_factory=list, description="Secondary or co-occurring intents")
    detected_language: Literal["en", "te", "hi", "other"] = Field("en", description="Detected language code (en, te, hi, other)")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Classifier confidence score")
    extracted_entities: ExtractedEntities = Field(default_factory=ExtractedEntities, description="Structured extracted entities")
    source: Literal["groq", "fallback"] = Field("groq", description="Classifier origin: 'groq' or 'fallback'")
    reasoning: Optional[str] = Field(None, description="Brief explanation of classification decision")

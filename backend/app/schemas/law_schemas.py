from typing import List, Optional
from pydantic import BaseModel, Field


class LawSearchResultItem(BaseModel):
    """Individual legal provision or section retrieved."""

    law_name: str = Field(..., description="Official title of the law or statute")
    act_name: str = Field(..., description="Short name of the legislative Act")
    section_number: str = Field(..., description="Section, article, or rule number")
    content: str = Field(..., description="Verbatim or summary statutory text")
    source_url: str = Field(..., description="Official source URL or NeGD NyayKosh portal link")
    category: Optional[str] = Field(None, description="Legal subject domain e.g. Consumer, Privacy, IT")
    retrieval_timestamp: str = Field(..., description="ISO 8601 timestamp of API retrieval")


class LawSearchResponse(BaseModel):
    """Standardized response format for legal searches."""

    success: bool = Field(True, description="Whether the search succeeded")
    source: str = Field(..., description="Data provider: 'nyaykosh' or 'nyaykosh_mock_adapter'")
    is_live_data: bool = Field(..., description="True if retrieved from live NeGD API; False if mock adapter")
    query: str = Field(..., description="The original search query executed")
    total_results: int = Field(..., description="Count of retrieved provisions")
    results: List[LawSearchResultItem] = Field(default_factory=list, description="List of matching statutory provisions")
    message: Optional[str] = Field(None, description="Informational note on live or fallback status")

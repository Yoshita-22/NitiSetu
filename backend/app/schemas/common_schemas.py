from typing import Any, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Structured error detail representation."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error explanation")
    details: Optional[Any] = Field(None, description="Additional debug or field error context")


class BaseResponse(BaseModel):
    """Standardized base response envelope."""

    success: bool = Field(..., description="Operation success indicator")
    message: Optional[str] = Field(None, description="Optional informational or status message")

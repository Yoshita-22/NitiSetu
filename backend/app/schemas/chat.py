from pydantic import BaseModel, Field, field_validator


class ChatTestRequest(BaseModel):
    """Schema for test chat endpoint requests in Phase 0."""

    message: str = Field(
        ...,
        description="User query or message sent to verify backend connectivity",
        json_schema_extra={"example": "Explain PM Kisan scheme"},
    )

    @field_validator("message")
    @classmethod
    def validate_message_not_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Message cannot be empty or whitespace only.")
        return trimmed


class ChatTestResponse(BaseModel):
    """Schema for test chat endpoint responses in Phase 0."""

    success: bool = Field(..., description="Indicates successful receipt and response", json_schema_extra={"example": True})
    message: str = Field(
        ...,
        description="Development verification response notice",
        json_schema_extra={"example": "This is a development response from PolicyPilot backend."},
    )
    received_message: str = Field(
        ...,
        description="Echo of the input message received by the server",
        json_schema_extra={"example": "Explain PM Kisan scheme"},
    )

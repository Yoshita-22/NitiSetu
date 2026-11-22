from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema representing health check status."""

    status: str = Field(..., description="Current service health status", json_schema_extra={"example": "healthy"})
    application: str = Field(..., description="Application service name", json_schema_extra={"example": "PolicyPilot API"})
    version: str = Field(..., description="API semantic version", json_schema_extra={"example": "1.0.0"})

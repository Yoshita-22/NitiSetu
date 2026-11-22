from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check API",
    description="Confirms that the PolicyPilot backend service is operational and reports version info.",
)
def get_health() -> HealthResponse:
    """Return current service health and version."""
    return HealthResponse(
        status="healthy",
        application=settings.PROJECT_NAME,
        version=settings.VERSION,
    )

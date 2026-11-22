from fastapi import APIRouter, Query
from app.schemas.law_schemas import LawSearchResponse
from app.services.nyaykosh_service import nyaykosh_service

router = APIRouter()


@router.get(
    "/search",
    response_model=LawSearchResponse,
    summary="Search Indian Laws & Statutory Provisions via NyayKosh",
    description=(
        "Retrieves statutory legal sections, acts, and provisions using the NeGD NyayKosh platform. "
        "Returns verified provisions with law name, act name, section number, official text, "
        "and source URLs. Transparently falls back to the development mock adapter if NeGD is unreachable."
    ),
)
async def search_laws(
    q: str = Query(..., min_length=1, description="Legal query term e.g. 'consumer rights', 'data privacy', 'aadhaar'")
) -> LawSearchResponse:
    """Execute statutory law search through NyayKosh service."""
    return await nyaykosh_service.search_laws(q)

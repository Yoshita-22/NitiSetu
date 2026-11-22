from typing import List
from app.core.exceptions import NotFoundError
from app.repositories.scheme_repository import scheme_repository
from app.schemas.scheme_schemas import Scheme, SchemeSummary


class SchemeService:
    """Business service coordinating scheme retrieval and search."""

    def get_all_schemes(self) -> List[SchemeSummary]:
        """Retrieve all verified welfare schemes in summary format."""
        return scheme_repository.get_summaries()

    def get_scheme_by_id(self, scheme_id: str) -> Scheme:
        """Retrieve full details of a specific welfare scheme."""
        scheme = scheme_repository.get_by_id(scheme_id)
        if not scheme:
            raise NotFoundError(f"Scheme with ID '{scheme_id}' was not found.")
        return scheme

    def search_schemes(self, query: str) -> List[SchemeSummary]:
        """Search schemes by keyword across title, description, and benefits."""
        schemes = scheme_repository.search(query)
        return [
            SchemeSummary(
                scheme_id=s.scheme_id,
                scheme_name=s.scheme_name,
                short_description=s.short_description,
                ministry=s.ministry,
                target_beneficiaries=s.target_beneficiaries,
                state_applicability=s.state_applicability,
                data_source=s.data_source,
                official_source_url=s.official_source_url,
            )
            for s in schemes
        ]


# Default service instance
scheme_service = SchemeService()

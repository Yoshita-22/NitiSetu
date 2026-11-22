import json
from pathlib import Path
from typing import List, Optional
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.schemas.scheme_schemas import Scheme, SchemeSummary


class SchemeRepository:
    """Repository managing retrieval of verified government welfare schemes."""

    def __init__(self, data_path: Optional[str] = None):
        configured_path = data_path or settings.SCHEMES_DATA_PATH
        # Resolve path relative to backend root
        resolved = Path(configured_path)
        if not resolved.is_absolute():
            backend_root = Path(__file__).resolve().parent.parent
            resolved = (backend_root / configured_path.replace("app/", "")).resolve()
            if not resolved.exists():
                # Fallback to direct path
                resolved = Path(__file__).resolve().parent.parent / "data" / "schemes.json"
        self.data_file = resolved
        self._cache: Optional[List[Scheme]] = None

    def _load_schemes(self) -> List[Scheme]:
        if self._cache is not None:
            return self._cache

        if not self.data_file.exists():
            return []

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            self._cache = [Scheme(**item) for item in raw_data]
            return self._cache
        except Exception as e:
            raise RuntimeError(f"Failed to load schemes dataset from {self.data_file}: {e}")

    def get_all(self) -> List[Scheme]:
        """Return all verified schemes."""
        return self._load_schemes()

    def get_summaries(self) -> List[SchemeSummary]:
        """Return lightweight summary models for scheme listings."""
        schemes = self._load_schemes()
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

    def get_by_id(self, scheme_id: str) -> Optional[Scheme]:
        """Find scheme by unique identifier."""
        schemes = self._load_schemes()
        normalized_id = scheme_id.strip().upper()
        for s in schemes:
            if s.scheme_id.upper() == normalized_id:
                return s
        return None

    def search(self, query: str) -> List[Scheme]:
        """Search schemes by keyword in name, description, benefits, or beneficiaries."""
        schemes = self._load_schemes()
        if not query or not query.strip():
            return schemes

        term = query.strip().lower()
        results = []
        for s in schemes:
            text_corpus = (
                f"{s.scheme_name} {s.short_description} {s.target_beneficiaries} "
                f"{s.ministry} {' '.join(s.benefits)} {' '.join(s.eligibility_conditions)}"
            ).lower()
            if term in text_corpus:
                results.append(s)
        return results


# Default repository instance
scheme_repository = SchemeRepository()

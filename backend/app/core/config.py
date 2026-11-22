from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""

    PROJECT_NAME: str = "NitiSetu API"
    VERSION: str = "1.1.0"
    DESCRIPTION: str = (
        "NitiSetu – AI-Powered Multilingual Civic Information Assistant API. "
        "Provides plain-language translations, legal statutory retrieval, welfare scheme eligibility, "
        "and document processing for citizen empowerment."
    )
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"

    # Configurable CORS origins
    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Source A: NyayKosh API Configuration
    NYAYKOSH_BASE_URL: str = "https://lawascode.negd.in/laac-api/v1"
    NYAYKOSH_API_KEY: Optional[str] = None
    NYAYKOSH_TIMEOUT_SECONDS: float = 8.0

    # Source B: Scheme Dataset Configuration
    SCHEMES_DATA_PATH: str = "app/data/schemes.json"

    # Source C: PDF Document Upload Configuration
    UPLOAD_DIRECTORY: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[List[str], str]) -> List[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

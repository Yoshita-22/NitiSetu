from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""

    PROJECT_NAME: str = "NitiSetu API"
    VERSION: str = "2.0.0"
    DESCRIPTION: str = (
        "NitiSetu – AI-Powered Multilingual Civic Information Assistant API. "
        "Phase 2: Intelligent Query Orchestration using LangGraph, Groq intent classification, "
        "human-in-the-loop interrupts, and multi-source civic data aggregation."
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

    # Phase 2: Groq LLM Configuration for Intent Classification & Aggregation
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TIMEOUT_SECONDS: float = 10.0

    # Phase 2: Checkpointing & Supabase Persistence
    POSTGRES_CHECKPOINTER_URI: Optional[str] = None
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None

    # Phase 3: Document RAG & Vector Search Configuration
    CHROMA_PERSIST_DIRECTORY: str = "storage/chroma"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    DOCUMENT_CHUNK_SIZE: int = 800
    DOCUMENT_CHUNK_OVERLAP: int = 150
    DOCUMENT_RETRIEVAL_TOP_K: int = 5
    DOCUMENT_RETRIEVAL_THRESHOLD: float = 0.35

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

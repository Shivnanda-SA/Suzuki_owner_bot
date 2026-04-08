from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_API_DIR = Path(__file__).resolve().parent.parent
_ROOT_DIR = _API_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_DIR / ".env"), str(_API_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = Field(
        default="postgresql+psycopg://postgres:admin@localhost:5432/suzuki",
        validation_alias=AliasChoices("DATABASE_URL", "CAA_DB_URL"),
    )
    chroma_persist_dir: str = Field(
        default=str(_ROOT_DIR / "data" / "chroma"),
        validation_alias=AliasChoices("CHROMA_PERSIST_DIR"),
    )
    chroma_collection: str = "suzuki_owner_kb"
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001"
    )
    suzuki_source_base_url: str = "https://www.suzukimotorcycle.co.in"
    admin_token: str | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: object) -> object:
        """SQLAlchemy + psycopg3 expects postgresql+psycopg://"""
        if v is None or not isinstance(v, str):
            return v
        s = v.strip()
        if s.startswith("postgresql://") and not s.startswith("postgresql+psycopg"):
            return s.replace("postgresql://", "postgresql+psycopg://", 1)
        return s

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

"""Validated configuration. Secrets are never serialized in operational responses."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    database_url: SecretStr = SecretStr("")
    postgres_host: str = "localhost"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = "documind"
    postgres_user: str = "documind"
    postgres_password: SecretStr | None = None
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None
    jwt_secret: SecretStr | None = None
    jwt_expiry_minutes: int = Field(default=30, ge=1, le=1440)
    cors_origins: list[str] = ["http://localhost:5173"]
    storage_root: Path = Path("data/documents")
    max_upload_bytes: int = Field(default=25 * 1024 * 1024, ge=1024, le=1024**3)
    max_upload_files: int = Field(default=10, ge=1, le=100)
    health_timeout_seconds: float = Field(default=3, gt=0, le=30)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = Field(default=384, ge=1, le=65536)
    embedding_device: str = "cpu"
    embedding_batch_size: int = Field(default=32, ge=1, le=1024)
    reranker_enabled: bool = False
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = ""
    llm_api_key: SecretStr | None = None
    retrieval_top_k: int = Field(default=8, ge=1, le=100)
    retrieval_min_score: float = Field(default=0.35, ge=-1, le=1)

    @model_validator(mode="after")
    def validate_deployment(self) -> Self:
        if not self.database_url.get_secret_value():
            if self.app_env == "test":
                self.database_url = SecretStr("sqlite+pysqlite:///:memory:")
            else:
                if not self.postgres_password or not self.postgres_password.get_secret_value():
                    raise ValueError("POSTGRES_PASSWORD is required unless DATABASE_URL is set")
                url = URL.create(
                    "postgresql+psycopg",
                    username=self.postgres_user,
                    password=self.postgres_password.get_secret_value(),
                    host=self.postgres_host,
                    port=self.postgres_port,
                    database=self.postgres_db,
                )
                self.database_url = SecretStr(url.render_as_string(hide_password=False))
        url = make_url(self.database_url.get_secret_value())
        if url.get_backend_name() not in {"postgresql", "sqlite"}:
            raise ValueError("Only PostgreSQL and test SQLite databases are supported")
        if url.get_backend_name() == "sqlite" and self.app_env != "test":
            raise ValueError("Set DATABASE_URL to PostgreSQL; SQLite is restricted to APP_ENV=test")
        if self.app_env == "production":
            if self.jwt_secret is None or len(self.jwt_secret.get_secret_value()) < 32:
                raise ValueError("Production requires a JWT_SECRET of at least 32 characters")
            if not self.cors_origins or any(
                not origin.startswith("https://") or "*" in origin for origin in self.cors_origins
            ):
                raise ValueError("Production requires explicit HTTPS CORS origins")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

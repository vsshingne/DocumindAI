import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_sqlite() -> None:
    with pytest.raises(ValidationError, match="SQLite"):
        Settings(_env_file=None, app_env="production", database_url="sqlite+pysqlite:///:memory:")


def test_postgres_url_is_built_without_logging_password() -> None:
    settings = Settings(
        _env_file=None,
        app_env="development",
        postgres_user="tenant_user",
        postgres_password="colon:@/value",
        postgres_host="postgres",
    )
    assert settings.database_url.get_secret_value() == (
        "postgresql+psycopg://tenant_user:colon%3A%40%2Fvalue@postgres:5432/documind"
    )
    assert "colon:@/value" not in repr(settings)
    assert "colon:@/value" not in settings.model_dump_json()


def test_development_requires_database_credential() -> None:
    with pytest.raises(ValidationError, match="POSTGRES_PASSWORD"):
        Settings(_env_file=None, app_env="development")


def test_production_requires_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql+psycopg://user@localhost/documind",
        )


@pytest.mark.parametrize("origins", [["*"], ["http://example.com"], []])
def test_production_requires_explicit_https(origins: list[str]) -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            _env_file=None,
            app_env="production",
            jwt_secret="a" * 32,
            database_url="postgresql+psycopg://user@localhost/documind",
            cors_origins=origins,
        )


@pytest.mark.parametrize(
    "values",
    [
        {"max_upload_bytes": 0},
        {"embedding_dimension": 0},
        {"retrieval_top_k": 101},
        {"health_timeout_seconds": 0},
        {"embedding_batch_size": 0},
    ],
)
def test_invalid_limits(values: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="test", **values)


def test_secrets_are_redacted() -> None:
    settings = Settings(_env_file=None, app_env="test", jwt_secret="private-value")
    assert "private-value" not in repr(settings)
    assert "private-value" not in settings.model_dump_json()

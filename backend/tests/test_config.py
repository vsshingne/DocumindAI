import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_sqlite() -> None:
    with pytest.raises(ValidationError, match="SQLite"):
        Settings(_env_file=None, app_env="production")


def test_production_requires_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql+psycopg://user:secret@localhost/documind",
        )


@pytest.mark.parametrize("origins", [["*"], ["http://example.com"], []])
def test_production_requires_explicit_https(origins: list[str]) -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            _env_file=None,
            app_env="production",
            jwt_secret="a" * 32,
            database_url="postgresql+psycopg://user:secret@localhost/documind",
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

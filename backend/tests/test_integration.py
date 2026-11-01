"""Real dependency tests; opt in with DOCUMIND_INTEGRATION=1 on an isolated DB."""

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.database import build_engine
from app.core.health import Readiness

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("DOCUMIND_INTEGRATION") != "1", reason="Real services not enabled"
    ),
]


async def test_live_dependencies_and_migration() -> None:
    get_settings.cache_clear()
    settings = Settings()
    assert settings.database_url.get_secret_value().startswith("postgresql"), (
        "Use isolated PostgreSQL"
    )
    command.upgrade(Config("alembic.ini"), "head")
    engine = build_engine(settings)
    try:
        assert await Readiness(settings, engine).check() == {
            "postgresql": True,
            "redis": True,
            "qdrant": True,
        }
        with engine.begin() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM tenants")).scalar_one() >= 0
        command.check(Config("alembic.ini"))
    finally:
        engine.dispose()
        get_settings.cache_clear()

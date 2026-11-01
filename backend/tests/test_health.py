import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.core.health import SCHEMA_REVISION, Readiness
from app.core.telemetry import JsonFormatter
from app.main import create_app


@asynccontextmanager
async def api_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://testserver",
        ) as client,
    ):
        yield client


async def test_liveness_independent_of_dependencies(settings: Settings) -> None:
    async with api_client(create_app(settings)) as client:
        response = await client.get("/api/v1/health/live", headers={"X-Request-ID": "untrusted"})
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "dependencies": {}}
        uuid.UUID(response.headers["x-request-id"])
        assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize("ready", [True, False])
async def test_readiness_status(settings: Settings, ready: bool) -> None:
    app = create_app(settings)
    deps = {"postgresql": True, "redis": True, "qdrant": ready}
    app.state.readiness.check = AsyncMock(return_value=deps)
    async with api_client(app) as client:
        response = await client.get("/api/v1/health/ready")
    assert response.status_code == (200 if ready else 503)
    assert response.json()["dependencies"] == deps


async def test_failed_probe_is_explicit_and_sanitized(settings: Settings, engine: Engine) -> None:
    checker = Readiness(settings, engine)
    checker.database = AsyncMock(side_effect=RuntimeError("password=secret"))
    checker.redis = AsyncMock()
    checker.qdrant = AsyncMock()
    assert await checker.check() == {"postgresql": False, "redis": True, "qdrant": True}


async def test_probe_timeout(settings: Settings, engine: Engine) -> None:
    settings.health_timeout_seconds = 0.01
    checker = Readiness(settings, engine)

    async def slow() -> None:
        await asyncio.sleep(1)

    checker.database = slow
    checker.redis = AsyncMock()
    checker.qdrant = AsyncMock()
    assert (await checker.check())["postgresql"] is False


async def test_database_probe_requires_current_migration(
    settings: Settings, engine: Engine
) -> None:
    checker = Readiness(settings, engine)
    with pytest.raises(OperationalError):
        await checker.database()
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))
        connection.execute(text("INSERT INTO alembic_version VALUES ('old')"))
    with pytest.raises(RuntimeError, match="revision"):
        await checker.database()
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE alembic_version SET version_num=:v"), {"v": SCHEMA_REVISION}
        )
    await checker.database()


async def test_metrics_use_bounded_labels(settings: Settings) -> None:
    async with api_client(create_app(settings)) as client:
        await client.get("/private-document-name?token=secret")
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert 'route="unmatched"' in response.text
        assert "private-document-name" not in response.text
        assert "secret" not in response.text


def add_error_route(app: FastAPI) -> None:
    @app.get("/test-error")
    def fail() -> None:
        raise RuntimeError("secret database password")


async def test_unexpected_errors_are_sanitized(settings: Settings) -> None:
    app = create_app(settings)
    add_error_route(app)
    async with api_client(app) as client:
        response = await client.get("/test-error")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert "password" not in response.text


async def test_validation_does_not_echo_input(settings: Settings) -> None:
    app = create_app(settings)

    @app.get("/test-validation")
    def validated(value: int) -> dict[str, int]:
        return {"value": value}

    async with api_client(app) as client:
        response = await client.get("/test-validation?value=secret")
    assert response.status_code == 422
    assert "secret" not in response.text


def test_json_logs_allowlist_extras() -> None:
    record = logging.LogRecord("documind", logging.INFO, "", 1, "event", (), None)
    record.request_id = "123"
    record.password = "secret"
    payload = json.loads(JsonFormatter().format(record))
    assert payload["request_id"] == "123"
    assert "secret" not in json.dumps(payload)

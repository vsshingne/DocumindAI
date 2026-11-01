"""Independent, bounded readiness probes; dependency details never include secrets."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal

import httpx
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import Engine, text

from app.core.config import Settings

SCHEMA_REVISION = "0001_foundation"


class HealthResponse(BaseModel):
    status: Literal["ok", "not_ready"]
    dependencies: dict[str, bool] = {}


class Readiness:
    def __init__(self, settings: Settings, engine: Engine) -> None:
        self.settings = settings
        self.engine = engine

    async def database(self) -> None:
        def check() -> None:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                revision = connection.execute(text("SELECT version_num FROM alembic_version"))
                if revision.scalars().all() != [SCHEMA_REVISION]:
                    raise RuntimeError("Schema revision mismatch")

        await asyncio.to_thread(check)

    async def redis(self) -> None:
        async with Redis.from_url(
            self.settings.redis_url.get_secret_value(),
            socket_connect_timeout=self.settings.health_timeout_seconds,
            socket_timeout=self.settings.health_timeout_seconds,
        ) as client:
            await client.ping()

    async def qdrant(self) -> None:
        headers = {}
        if self.settings.qdrant_api_key:
            headers["api-key"] = self.settings.qdrant_api_key.get_secret_value()
        async with httpx.AsyncClient(timeout=self.settings.health_timeout_seconds) as client:
            response = await client.get(
                self.settings.qdrant_url.rstrip("/") + "/readyz", headers=headers
            )
            response.raise_for_status()

    async def check(self) -> dict[str, bool]:
        async def probe(check: Callable[[], Awaitable[None]]) -> bool:
            try:
                await asyncio.wait_for(check(), timeout=self.settings.health_timeout_seconds)
            except Exception:
                # Dependency failure is represented explicitly; do not leak driver exceptions.
                return False
            return True

        names = ("postgresql", "redis", "qdrant")
        results = await asyncio.gather(
            *(probe(c) for c in (self.database, self.redis, self.qdrant))
        )
        return dict(zip(names, results, strict=True))

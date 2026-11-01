"""Application factory: import has no connections, migrations or model downloads."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.exceptions import HTTPException

from app.api.v1.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.database import build_engine, session_factory
from app.core.health import Readiness
from app.core.telemetry import Metrics, RequestTelemetry, configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or get_settings()
    configure_logging(config.log_level)
    engine = build_engine(config)
    metrics = Metrics()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    app = FastAPI(
        title="DocuMind",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if config.app_env != "production" else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if config.app_env != "production" else None,
    )
    app.state.settings = config
    app.state.engine = engine
    app.state.sessions = session_factory(engine)
    app.state.readiness = Readiness(config, engine)
    app.state.metrics = metrics
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestTelemetry, metrics=metrics)
    app.include_router(health_router, prefix="/api/v1")

    @app.get("/metrics", include_in_schema=False)
    def prometheus_metrics() -> Response:
        # Operational endpoint: restrict to internal network at ingress.
        return Response(
            generate_latest(metrics.registry), headers={"Content-Type": CONTENT_TYPE_LATEST}
        )

    def error(request: Request, code: str, message: str, status: int) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unavailable")
        return JSONResponse(
            {"error": {"code": code, "message": message, "request_id": request_id}},
            status_code=status,
            headers={"X-Request-ID": request_id},
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        response = error(
            request, f"http_{exc.status_code}", "Request could not be completed", exc.status_code
        )
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _: RequestValidationError) -> JSONResponse:
        # Pydantic errors can include secret input values; do not return raw errors.
        return error(request, "validation_error", "Request validation failed", 422)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logging.getLogger("documind").error(
            "request_failed",
            extra={
                "request_id": getattr(request.state, "request_id", "unavailable"),
                "error_category": type(exc).__name__,
                "stage": "http",
            },
        )
        return error(request, "internal_error", "An internal error occurred", 500)

    return app

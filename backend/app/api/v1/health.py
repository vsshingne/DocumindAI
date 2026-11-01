from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.health import HealthResponse, Readiness

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", response_model=HealthResponse)
async def live() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
async def ready(request: Request) -> JSONResponse:
    readiness: Readiness = request.app.state.readiness
    dependencies = await readiness.check()
    healthy = all(dependencies.values())
    result = HealthResponse(status="ok" if healthy else "not_ready", dependencies=dependencies)
    return JSONResponse(result.model_dump(), status_code=200 if healthy else 503)

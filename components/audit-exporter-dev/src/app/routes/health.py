"""Health and readiness routes."""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from src.core.state import BootstrapRuntimeState

router = APIRouter()


def _runtime_state(request: Request) -> BootstrapRuntimeState:
    return request.app.state.runtime_state


@router.get("/healthz")
async def healthz(request: Request) -> dict[str, str | bool]:
    state = _runtime_state(request)
    return {
        "status": "ok",
        "live": True,
        "phase": state.phase.value,
        "startup_complete": state.startup_complete,
    }


@router.get("/readyz")
async def readyz(request: Request) -> JSONResponse:
    state = _runtime_state(request)
    payload = state.readiness_payload()
    status_code = status.HTTP_200_OK if payload["ready"] else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=payload)

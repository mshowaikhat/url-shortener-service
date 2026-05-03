"""Liveness and readiness endpoints."""

from fastapi import APIRouter, Response, status

from app.firestore_client import ping
from app.models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    """Liveness — process is up. Does NOT check Firestore."""
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=HealthResponse)
async def readyz(response: Response) -> HealthResponse:
    """Readiness — true only if Firestore is reachable."""
    firestore_ok = await ping()
    if not firestore_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(
            status="degraded",
            details={"firestore": "unreachable"},
        )
    return HealthResponse(status="ok", details={"firestore": "ok"})

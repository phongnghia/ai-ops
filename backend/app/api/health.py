"""Health check route.

Exposes ``GET /health`` for container and load-balancer health probes. The
endpoint returns a minimal, static payload so orchestration tooling (Docker
``HEALTHCHECK``, Docker Compose ``condition: service_healthy``) can cheaply
confirm the service process is up and serving HTTP.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])

_HEALTH_OK_PAYLOAD = {"status": "ok"}


@router.get("/health")
def get_health() -> JSONResponse:
    """Report service liveness.

    Returns:
        A JSON response ``{"status": "ok"}`` with HTTP 200.
    """
    return JSONResponse(status_code=status.HTTP_200_OK, content=_HEALTH_OK_PAYLOAD)

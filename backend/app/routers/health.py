"""
Health check endpoints.

GET /health -> component-level status (API + database + offline mode)
GET /       -> simple service info
"""

import logging

from fastapi import APIRouter

from app.config import settings
from app.database import check_database_connection
from app.schemas.health import ComponentStatus, HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check for API and database",
)
def health_check() -> HealthResponse:
    """
    Returns the overall service status.

    - status "ok"       -> API and database are healthy
    - status "degraded" -> API is up but the database is not reachable
    """
    db_ok = check_database_connection()

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        offline_mode=settings.OFFLINE_MODE,
        components={
            "api": ComponentStatus(
                status="ok",
                detail=f"{settings.APP_NAME} API is running ({settings.APP_ENV})",
            ),
            "database": ComponentStatus(
                status="ok" if db_ok else "error",
                detail="SQLite connection verified" if db_ok else "SQLite connection failed",
            ),
        },
    )


@router.get("/", summary="Service info")
def root() -> dict:
    """Friendly landing payload so anyone can confirm the API is alive."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Offline-first AI classroom language bridge (Hindi -> Santhali / Ol Chiki)",
        "docs_url": "/docs",
        "health_url": "/health",
    }

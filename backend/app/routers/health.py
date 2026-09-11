"""
Health check endpoints.

GET /health -> component-level status (API + database + offline mode + AI models)
GET /       -> simple service info
"""

import logging

from fastapi import APIRouter

from app.ai.asr_service import asr_service
from app.ai.model_manager import model_manager
from app.config import settings
from app.database import check_database_connection
from app.schemas.health import ComponentStatus, HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


def _asr_component() -> ComponentStatus:
    """ASR readiness: model cached locally = offline-ready (not_downloaded = setup needed)."""
    st = asr_service.status()
    if st["status"] == "ready":
        return ComponentStatus(status="ok", detail=f"ASR loaded - {st['detail']}")
    if st["downloaded"]:
        return ComponentStatus(
            status="ok",
            detail="ASR model cached (offline-ready); loads on first use",
        )
    return ComponentStatus(
        status="not_ready",
        detail="ASR model not downloaded yet - run scripts\\download_asr_model.py once",
    )


def _translation_component() -> ComponentStatus:
    st = model_manager.translation_status()
    if st["status"] == "ready":
        return ComponentStatus(status="ok", detail=f"Translation model {st['status']}")
    if st["status"] == "error":
        return ComponentStatus(status="error", detail=st["detail"] or "Translation model failed to load")
    return ComponentStatus(status="not_ready", detail=f"Translation model {st['status']}")


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
            "asr": _asr_component(),
            "translation": _translation_component(),
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

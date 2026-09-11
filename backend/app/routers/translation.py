"""
Translation endpoints (Phase 2).

POST /api/translate/text   Hindi text -> Santali (Ol Chiki) via local IndicTrans2
GET  /api/models/status    Honest model load status

Every request (success or failure) is recorded in translation_history.
"""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai import translation_service
from app.ai.model_manager import model_manager
from app.config import settings
from app.database import get_db
from app.models import TranslationHistory
from app.schemas.translation import (
    ModelStatusResponse,
    TranslateTextRequest,
    TranslateTextResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Translation"])


def _record_history(
    db: Session,
    payload: TranslateTextRequest,
    translated_text: str | None,
    latency_ms: int,
    success: bool,
    error_message: str | None,
    model_name: str | None = None,
) -> None:
    """Persist the request to translation_history (DB problems are non-fatal)."""
    try:
        db.add(
            TranslationHistory(
                source_language=payload.source_language,
                target_language=payload.target_language,
                input_text=payload.text,
                translated_text=translated_text,
                latency_ms=latency_ms,
                success=success,
                error_message=error_message,
                model_name=model_name,
            )
        )
        db.commit()
    except Exception:
        logger.exception("Failed to save translation history (non-fatal)")
        db.rollback()


@router.post(
    "/translate/text",
    response_model=TranslateTextResponse,
    summary="Hindi text -> Santali text (Ol Chiki), local AI inference",
)
def translate_text(payload: TranslateTextRequest, db: Session = Depends(get_db)) -> TranslateTextResponse:
    started = time.perf_counter()
    try:
        result = translation_service.translate_text(payload.text)
    except translation_service.TranslationModelError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record_history(
            db, payload,
            translated_text=None,
            latency_ms=latency_ms,
            success=False,
            error_message=exc.user_message,
        )
        raise HTTPException(status_code=exc.suggested_status, detail=exc.user_message) from exc

    _record_history(
        db, payload,
        translated_text=result["translated_text"],
        latency_ms=result["latency_ms"],
        success=True,
        error_message=None,
        model_name=result["model"],
    )

    return TranslateTextResponse(
        input_text=payload.text,
        translated_text=result["translated_text"],
        source_language=payload.source_language,
        target_language=payload.target_language,
        latency_ms=result["latency_ms"],
        model=result["model"],
        offline=settings.OFFLINE_MODE,
    )


@router.get(
    "/models/status",
    response_model=ModelStatusResponse,
    summary="Honest AI model load status",
)
def models_status() -> ModelStatusResponse:
    snapshot = model_manager.status_snapshot()
    return ModelStatusResponse(
        offline=snapshot["offline"],
        translation=snapshot["translation"],
    )

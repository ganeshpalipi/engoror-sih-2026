"""
Classroom phrase pack endpoints (Phase 5).

GET  /api/phrases                List phrases (optional category filter)
POST /api/phrases/{id}/translate Hindi -> Santali via the existing Phase 2 service
POST /api/phrases/{id}/audio     Santali text -> audio via the existing Phase 4 TTS

Flow per phrase: Hindi phrase -> IndicTrans2 -> Santali text -> TTS -> Play.
The existing services are reused; no second engine is created.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai import translation_service
from app.ai.tts_service import TTSModelError
from app.config import settings
from app.database import get_db
from app.models import ClassroomPhrase
from app.schemas.content import (
    ContentAudioResponse,
    PhraseListResponse,
    PhraseOut,
    PhraseTranslateResponse,
)
from app.services import content_service
from app.services.content_serializers import (
    get_phrase_or_404,
    phrase_out,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/phrases", tags=["Classroom Phrase Pack (Phase 5)"])


@router.get(
    "",
    response_model=PhraseListResponse,
    summary="List classroom phrases (optional category filter)",
)
def list_phrases(
    category: str | None = None,
    db: Session = Depends(get_db),
) -> PhraseListResponse:
    query = db.query(ClassroomPhrase)
    if category:
        query = query.filter(ClassroomPhrase.category == category)
    phrases = query.order_by(ClassroomPhrase.category, ClassroomPhrase.id).all()
    categories = [
        row[0]
        for row in db.query(ClassroomPhrase.category)
        .distinct()
        .order_by(ClassroomPhrase.category)
        .all()
    ]
    return PhraseListResponse(
        count=len(phrases),
        categories=[c for c in categories if c],
        phrases=[phrase_out(row) for row in phrases],
    )


@router.post(
    "/{phrase_id}/translate",
    response_model=PhraseTranslateResponse,
    summary="Generate the Santali (Ol Chiki) translation for a phrase (offline MT)",
)
def translate_phrase(phrase_id: int, db: Session = Depends(get_db)) -> PhraseTranslateResponse:
    phrase = get_phrase_or_404(db, phrase_id)
    try:
        meta = content_service.translate_phrase(db, phrase)
    except translation_service.TranslationModelError as exc:
        raise HTTPException(status_code=exc.suggested_status, detail=exc.user_message) from exc
    return PhraseTranslateResponse(
        phrase=phrase_out(phrase),
        translation_latency_ms=meta["latency_ms"],
        model=meta["model"],
        offline=settings.OFFLINE_MODE,
    )


@router.post(
    "/{phrase_id}/audio",
    response_model=ContentAudioResponse,
    summary="Generate Santali audio for a phrase (offline TTS)",
)
def phrase_audio(phrase_id: int, db: Session = Depends(get_db)) -> ContentAudioResponse:
    phrase = get_phrase_or_404(db, phrase_id)
    try:
        result = content_service.generate_audio(db, phrase)
    except TTSModelError as exc:
        raise HTTPException(status_code=exc.suggested_status, detail=exc.user_message) from exc
    return ContentAudioResponse(**result, offline=settings.OFFLINE_MODE)

"""
Flashcard endpoints (Phase 5).

GET  /api/flashcards             List flashcards (optional topic filter)
GET  /api/flashcards/topics      Topic catalogue with labels + card counts
POST /api/flashcards/{id}/audio  Santali text -> audio via the existing Phase 4 TTS

Visuals are LOCAL only: an emoji character and/or a bundled SVG asset from
frontend/public/flashcards/<image_key>.svg. No external image is ever loaded.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai import translation_service
from app.ai.tts_service import TTSModelError
from app.config import settings
from app.database import get_db
from app.models import Flashcard
from app.schemas.content import (
    ContentAudioResponse,
    FlashcardListResponse,
    FlashcardOut,
)
from app.services import content_service
from app.services.content_data import FLASHCARD_TOPICS
from app.services.content_serializers import (
    flashcard_out,
    get_flashcard_or_404,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/flashcards", tags=["Flashcards (Phase 5)"])


@router.get(
    "",
    response_model=FlashcardListResponse,
    summary="List flashcards (optional topic filter)",
)
def list_flashcards(
    topic: str | None = None,
    db: Session = Depends(get_db),
) -> FlashcardListResponse:
    query = db.query(Flashcard)
    if topic:
        query = query.filter(Flashcard.topic == topic)
    cards = query.order_by(Flashcard.topic, Flashcard.id).all()

    topics = []
    for spec in FLASHCARD_TOPICS:
        count = (
            db.query(Flashcard)
            .filter(Flashcard.topic == spec["topic"])
            .count()
        )
        topics.append({
            "topic": spec["topic"],
            "label_hindi": spec["label_hindi"],
            "label_english": spec["label_english"],
            "count": count,
        })

    return FlashcardListResponse(
        count=len(cards),
        topics=topics,
        flashcards=[flashcard_out(card) for card in cards],
    )


@router.get(
    "/topics",
    response_model=list[dict],
    summary="Flashcard topic catalogue",
)
def flashcard_topics(db: Session = Depends(get_db)) -> list[dict]:
    out = []
    for spec in FLASHCARD_TOPICS:
        count = db.query(Flashcard).filter(Flashcard.topic == spec["topic"]).count()
        out.append({
            "topic": spec["topic"],
            "label_hindi": spec["label_hindi"],
            "label_english": spec["label_english"],
            "count": count,
        })
    return out


@router.post(
    "/{card_id}/translate",
    response_model=dict,
    summary="Generate the Santali (Ol Chiki) word for a flashcard (offline MT)",
)
def translate_flashcard(card_id: int, db: Session = Depends(get_db)) -> dict:
    card = get_flashcard_or_404(db, card_id)
    try:
        meta = content_service.translate_flashcard(db, card)
    except translation_service.TranslationModelError as exc:
        raise HTTPException(status_code=exc.suggested_status, detail=exc.user_message) from exc
    return {
        "success": True,
        "flashcard": flashcard_out(card).model_dump(),
        "translation_latency_ms": meta["latency_ms"],
        "model": meta["model"],
        "offline": settings.OFFLINE_MODE,
    }


@router.post(
    "/{card_id}/audio",
    response_model=ContentAudioResponse,
    summary="Generate Santali audio for a flashcard (offline TTS)",
)
def flashcard_audio(card_id: int, db: Session = Depends(get_db)) -> ContentAudioResponse:
    card = get_flashcard_or_404(db, card_id)
    try:
        result = content_service.generate_audio(db, card)
    except TTSModelError as exc:
        raise HTTPException(status_code=exc.suggested_status, detail=exc.user_message) from exc
    return ContentAudioResponse(**result, offline=settings.OFFLINE_MODE)

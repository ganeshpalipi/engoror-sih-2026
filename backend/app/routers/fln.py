"""
FLN lesson endpoints (Phase 5).

GET  /api/fln/lessons            List lessons (optional skill/category/grade filters)
GET  /api/fln/lessons/{id}       One lesson
POST /api/fln/lessons/{id}/translate   Hindi -> Santali via the existing Phase 2 service
POST /api/fln/lessons/{id}/audio       Santali text -> audio via the existing Phase 4 TTS

No new AI code lives here - everything reuses translation_service and
tts_service so the offline behaviour stays identical to Phases 2-4.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai import translation_service
from app.ai.tts_service import TTSModelError
from app.config import settings
from app.database import get_db
from app.models import FlnLesson
from app.schemas.content import (
    ContentAudioResponse,
    LessonListResponse,
    LessonOut,
    LessonTranslateResponse,
)
from app.services import content_service
from app.services.content_serializers import (
    get_lesson_or_404,
    lesson_out,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fln", tags=["FLN Lessons (Phase 5)"])


@router.get(
    "/lessons",
    response_model=LessonListResponse,
    summary="List FLN lessons (filters: skill, category, grade)",
)
def list_lessons(
    skill: str | None = None,
    category: str | None = None,
    grade: int | None = None,
    db: Session = Depends(get_db),
) -> LessonListResponse:
    query = db.query(FlnLesson)
    if skill:
        query = query.filter(FlnLesson.subject == skill)
    if category:
        query = query.filter(FlnLesson.category == category)
    if grade:
        query = query.filter(FlnLesson.class_level == grade)
    lessons = query.order_by(FlnLesson.subject, FlnLesson.class_level, FlnLesson.id).all()
    return LessonListResponse(
        count=len(lessons),
        lessons=[lesson_out(row) for row in lessons],
    )


@router.get(
    "/lessons/{lesson_id}",
    response_model=LessonOut,
    summary="One FLN lesson",
)
def get_lesson(lesson_id: int, db: Session = Depends(get_db)) -> LessonOut:
    return lesson_out(get_lesson_or_404(db, lesson_id))


@router.post(
    "/lessons/{lesson_id}/translate",
    response_model=LessonTranslateResponse,
    summary="Generate the Santali (Ol Chiki) translation for a lesson (offline MT)",
)
def translate_lesson(lesson_id: int, db: Session = Depends(get_db)) -> LessonTranslateResponse:
    lesson = get_lesson_or_404(db, lesson_id)
    try:
        meta = content_service.translate_lesson(db, lesson)
    except translation_service.TranslationModelError as exc:
        raise HTTPException(status_code=exc.suggested_status, detail=exc.user_message) from exc
    return LessonTranslateResponse(
        lesson=lesson_out(lesson),
        translation_latency_ms=meta["latency_ms"],
        model=meta["model"],
        offline=settings.OFFLINE_MODE,
    )


@router.post(
    "/lessons/{lesson_id}/audio",
    response_model=ContentAudioResponse,
    summary="Generate Santali audio for a lesson (offline TTS)",
)
def lesson_audio(lesson_id: int, db: Session = Depends(get_db)) -> ContentAudioResponse:
    lesson = get_lesson_or_404(db, lesson_id)
    try:
        result = content_service.generate_audio(db, lesson)
    except TTSModelError as exc:
        raise HTTPException(status_code=exc.suggested_status, detail=exc.user_message) from exc
    return ContentAudioResponse(**result, offline=settings.OFFLINE_MODE)

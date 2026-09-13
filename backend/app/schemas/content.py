"""Pydantic schemas for the Phase 5 content endpoints (lessons/phrases/flashcards)."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.services.content_data import NIPUN_NOTE, VALIDATION_NOTICE


class LessonOut(BaseModel):
    """One FLN lesson (list + detail + translate responses)."""

    id: int
    title_hindi: str
    title_english: str
    category: str = ""
    skill: str = ""
    grade_level: int = Field(description="Class level 1-3 (field name per Phase 5 spec)")
    subject: str = Field(description="literacy | numeracy")
    hindi_text: str
    santali_ol_chiki: str
    validation_status: str = Field(description="PLACEHOLDER | AI_GENERATED")
    learning_objective: str = ""
    activity_instruction: str = ""
    audio_available: bool = False
    audio_url: str | None = None
    created_at: datetime | None = None
    nipun_note: str = NIPUN_NOTE


class LessonListResponse(BaseModel):
    count: int
    lessons: list[LessonOut]


class LessonTranslateResponse(BaseModel):
    success: bool = True
    lesson: LessonOut
    translation_latency_ms: int
    model: str
    offline: bool = True
    validation_notice: str = VALIDATION_NOTICE


class PhraseOut(BaseModel):
    id: int
    category: str
    hindi_text: str = Field(validation_alias="hindi")
    english: str = ""
    santali_ol_chiki: str
    validation_status: str
    audio_available: bool = False
    audio_url: str | None = None
    nipun_note: str = NIPUN_NOTE

    model_config = {"populate_by_name": True}


class PhraseListResponse(BaseModel):
    count: int
    categories: list[str]
    phrases: list[PhraseOut]


class PhraseTranslateResponse(BaseModel):
    success: bool = True
    phrase: PhraseOut
    translation_latency_ms: int
    model: str
    offline: bool = True
    validation_notice: str = VALIDATION_NOTICE


class FlashcardOut(BaseModel):
    id: int
    topic: str
    hindi_word: str
    english_word: str
    visual_emoji: str = ""
    image_key: str | None = Field(
        default=None,
        description="Optional bundled SVG asset under /flashcards/<image_key>.svg (local only)",
    )
    santali_ol_chiki: str
    validation_status: str
    audio_available: bool = False
    audio_url: str | None = None
    nipun_note: str = NIPUN_NOTE


class FlashcardListResponse(BaseModel):
    count: int
    topics: list[dict]
    flashcards: list[FlashcardOut]


class FlashcardAudioResponse(BaseModel):
    """Response for all Phase 5 audio endpoints (phrase/lesson/flashcard)."""

    success: bool = True
    audio_url: str
    cached: bool = Field(description="True when a previously generated WAV was reused")
    duration_sec: float | None = None
    latency_ms: int | None = None
    model: str = ""
    offline: bool = True
    validation_notice: str = VALIDATION_NOTICE


class ContentAudioResponse(FlashcardAudioResponse):
    """Same shape as FlashcardAudioResponse (kept for semantic clarity)."""


class ContentTranslateMeta(BaseModel):
    translation_latency_ms: int
    model: str

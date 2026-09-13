"""Row -> API-schema serializers for Phase 5 content endpoints."""

from sqlalchemy.orm import Session

from app.models import ClassroomPhrase, Flashcard, FlnLesson
from app.schemas.content import FlashcardOut, LessonOut, PhraseOut


def _audio_fields(audio_path: str | None) -> tuple[bool, str | None]:
    """audio_available + audio_url based on the cached WAV file (if any)."""
    if not audio_path:
        return False, None
    from app.config import settings

    if (settings.generated_files_path / audio_path).is_file():
        return True, f"/api/tts/audio/{audio_path}"
    return False, None  # expired (TTS retention) - will be regenerated on demand


def lesson_out(lesson: FlnLesson) -> LessonOut:
    available, url = _audio_fields(lesson.audio_path)
    return LessonOut(
        id=lesson.id,
        title_hindi=lesson.title_hindi,
        title_english=lesson.title_english,
        category=lesson.category,
        skill=lesson.skill,
        grade_level=lesson.class_level,
        subject=lesson.subject,
        hindi_text=lesson.hindi_text,
        santali_ol_chiki=lesson.santhali_ol_chiki,
        validation_status=lesson.validation_status,
        learning_objective=lesson.learning_objective or "",
        activity_instruction=lesson.activity_instruction or "",
        audio_available=available,
        audio_url=url,
        created_at=lesson.created_at,
    )


def phrase_out(phrase: ClassroomPhrase) -> PhraseOut:
    available, url = _audio_fields(phrase.audio_path)
    return PhraseOut(
        id=phrase.id,
        category=phrase.category,
        hindi_text=phrase.hindi,
        english=phrase.english,
        santali_ol_chiki=phrase.santhali_ol_chiki,
        validation_status=phrase.validation_status,
        audio_available=available,
        audio_url=url,
    )


def flashcard_out(card: Flashcard) -> FlashcardOut:
    available, url = _audio_fields(card.audio_path)
    return FlashcardOut(
        id=card.id,
        topic=card.topic,
        hindi_word=card.hindi_word,
        english_word=card.english_word,
        visual_emoji=card.visual_emoji,
        image_key=card.image_key,
        santali_ol_chiki=card.santhali_ol_chiki,
        validation_status=card.validation_status,
        audio_available=available,
        audio_url=url,
    )


def get_lesson_or_404(db: Session, lesson_id: int) -> FlnLesson:
    from fastapi import HTTPException

    lesson = db.get(FlnLesson, lesson_id)
    if lesson is None:
        raise HTTPException(
            status_code=404,
            detail="This lesson was not found. Please open the FLN Lessons page again.",
        )
    return lesson


def get_phrase_or_404(db: Session, phrase_id: int) -> ClassroomPhrase:
    from fastapi import HTTPException

    phrase = db.get(ClassroomPhrase, phrase_id)
    if phrase is None:
        raise HTTPException(
            status_code=404,
            detail="This phrase was not found. Please open the Phrase Pack page again.",
        )
    return phrase


def get_flashcard_or_404(db: Session, card_id: int) -> Flashcard:
    from fastapi import HTTPException

    card = db.get(Flashcard, card_id)
    if card is None:
        raise HTTPException(
            status_code=404,
            detail="This flashcard was not found. Please open the Flashcards page again.",
        )
    return card

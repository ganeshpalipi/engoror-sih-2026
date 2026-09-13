"""
Phase 5 content service: fills Santali (Ol Chiki) fields and generates
audio for lessons / phrases / flashcards by REUSING the existing Phase 2
translation service and Phase 4 TTS service.

No second translation or TTS engine exists in this project. Everything here
delegates:

  Hindi text  -> app.ai.translation_service.translate_text  (IndicTrans2)
  Ol Chiki    -> app.ai.tts_service.synthesize_to_file      (Piper VITS)

Honesty rules:
  - Content starts as REQUIRES_LANGUAGE_VALIDATION (placeholder).
  - After the MT service fills it, validation_status becomes AI_GENERATED
    and the UI keeps showing
    "AI-generated — Requires native-speaker validation".
  - Audio generated from AI-translated text carries the same notice.

Audio caching: the generated WAV filename is stored in the row's audio_path.
If the file still exists on disk it is reused (offline-friendly; the TTS
service keeps steady-state synthesis to tens of milliseconds, but reuse also
keeps generated_files small). If the file has expired (TTS retention), it is
transparently regenerated on the next request.
"""

import logging

from sqlalchemy.orm import Session

from app.ai import translation_service
from app.ai.tts_service import TTSModelError, tts_service
from app.config import settings
from app.models import ClassroomPhrase, Flashcard, FlnLesson

logger = logging.getLogger(__name__)

# validation_status vocabulary for translated content
AI_GENERATED = "AI_GENERATED"
PLACEHOLDER = "REQUIRES_LANGUAGE_VALIDATION"


def _is_pending(item) -> bool:
    """True when the Santali field is still the untranslated placeholder."""
    return (
        not item.santhali_ol_chiki
        or item.santhali_ol_chiki == PLACEHOLDER
        or item.validation_status == "PLACEHOLDER"
    )


def translate_lesson(db: Session, lesson: FlnLesson) -> dict:
    """Hindi lesson text -> Santali via the existing IndicTrans2 service."""
    result = translation_service.translate_text(lesson.hindi_text)
    lesson.santhali_ol_chiki = result["translated_text"]
    lesson.validation_status = AI_GENERATED
    lesson.audio_path = None  # text changed -> old audio is stale
    db.commit()
    return {
        "latency_ms": result["latency_ms"],
        "model": result["model"],
    }


def translate_phrase(db: Session, phrase: ClassroomPhrase) -> dict:
    """Hindi phrase -> Santali via the existing IndicTrans2 service."""
    result = translation_service.translate_text(phrase.hindi)
    phrase.santhali_ol_chiki = result["translated_text"]
    phrase.validation_status = AI_GENERATED
    phrase.audio_path = None
    db.commit()
    return {
        "latency_ms": result["latency_ms"],
        "model": result["model"],
    }


def translate_flashcard(db: Session, card: Flashcard) -> dict:
    """Hindi word -> Santali via the existing IndicTrans2 service."""
    result = translation_service.translate_text(card.hindi_word)
    card.santhali_ol_chiki = result["translated_text"]
    card.validation_status = AI_GENERATED
    card.audio_path = None
    db.commit()
    return {
        "latency_ms": result["latency_ms"],
        "model": result["model"],
    }


def translate_lines_batched(lines: list[str]) -> tuple[list[str], dict]:
    """
    Translate up to 40 short Hindi strings in one or few MT calls.

    The existing service accepts up to 10 lines per call, so longer lists
    are translated in chunks. Used by the worksheet generator; nothing is
    persisted here (worksheet vocabulary without a DB home is translated
    on the fly).
    """
    out: list[str] = []
    total_latency = 0
    model = ""
    for start in range(0, len(lines), translation_service.MAX_LINES):
        chunk = lines[start : start + translation_service.MAX_LINES]
        result = translation_service.translate_text("\n".join(chunk))
        out.extend(result["translated_text"].splitlines())
        total_latency += result["latency_ms"]
        model = result["model"]
    meta = {"latency_ms": total_latency, "model": model}
    return out, meta


def generate_audio(db: Session, item) -> dict:
    """
    Synthesize Santali audio for any content row that has
    santhali_ol_chiki + audio_path columns (lesson / phrase / flashcard).

    Reuses the Phase 4 TTS service and the whitelisted Phase 4 audio
    endpoint (/api/tts/audio/<file>). Raises TTSModelError with a
    teacher-facing message on failure (router converts to HTTP).
    """
    if _is_pending(item):
        raise TTSModelError(
            "This content has no Santali translation yet. Generate the "
            "Santali text first (use the Translate button), then play the "
            "audio.", 400,
        )

    cached_name = item.audio_path
    if cached_name:
        cached_path = settings.generated_files_path / cached_name
        if cached_path.is_file():
            return {
                "audio_url": f"/api/tts/audio/{cached_name}",
                "cached": True,
                "model": tts_service.model_label,
            }

    result = tts_service.synthesize_to_file(item.santhali_ol_chiki)
    item.audio_path = result["filename"]
    db.commit()
    return {
        "audio_url": f"/api/tts/audio/{result['filename']}",
        "cached": False,
        "duration_sec": result["duration_sec"],
        "latency_ms": result["latency_ms"],
        "model": result["model"],
    }

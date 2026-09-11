"""
Speech recognition endpoints (Phase 3).

POST /api/asr/transcribe            Hindi audio -> Hindi text (offline faster-whisper)
POST /api/classroom/speech-translate Hindi audio -> Hindi text -> Santali (Ol Chiki)

The speech-translate endpoint REUSES the existing Phase 2 translation service
(app.ai.translation_service) - there is no second translation implementation.

Every request (success or failure) is recorded locally:
- asr_transcriptions table  (ASR layer)
- translation_history table (translation step, same as text translation)
"""

import logging
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.ai import translation_service
from app.ai.asr_service import ASRModelError, asr_service
from app.config import settings
from app.database import get_db
from app.models import AsrTranscription, TranslationHistory
from app.schemas.asr import SpeechTranslateResponse, TranscribeResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Speech Recognition (ASR)"])

NO_SPEECH_MESSAGE = (
    "No speech was detected in the recording. Hold the record button, "
    "speak clearly, and try again."
)

# Content types browsers commonly send for recordings.
_KNOWN_AUDIO_TYPES = (
    "wav", "webm", "mp3", "m4a", "ogg", "oga", "opus", "flac", "aac",
)


def _sniff_audio_format(upload: UploadFile) -> str:
    """Best-effort label for the DB row (never used for validation)."""
    name = (upload.filename or "").lower()
    for ext in _KNOWN_AUDIO_TYPES:
        if name.endswith(f".{ext}"):
            return ext
    content_type = (upload.content_type or "").lower()
    for ext in _KNOWN_AUDIO_TYPES:
        if ext in content_type:
            return ext
    return (content_type.split("/")[-1] or "unknown")[:20]


def _read_upload(upload: UploadFile) -> bytes:
    try:
        return upload.file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="The audio upload could not be read. Please record again.",
        ) from exc


def _record_asr_row(
    db: Session,
    *,
    language: str,
    text: str | None,
    audio_format: str | None,
    duration_sec: float | None,
    latency_ms: int | None,
    success: bool,
    error_message: str | None,
    model_name: str | None,
) -> None:
    """Persist the ASR request to asr_transcriptions (DB problems are non-fatal)."""
    try:
        db.add(
            AsrTranscription(
                language=language,
                text=text,
                audio_format=audio_format,
                duration_sec=duration_sec,
                latency_ms=latency_ms,
                success=success,
                error_message=error_message,
                model_name=model_name,
            )
        )
        db.commit()
    except Exception:
        logger.exception("Failed to save ASR history (non-fatal)")
        db.rollback()


def _record_translation_row(
    db: Session,
    *,
    hindi_text: str,
    translated_text: str | None,
    latency_ms: int | None,
    success: bool,
    error_message: str | None,
    model_name: str | None,
) -> None:
    """Reuse translation_history for the translation step of the pipeline."""
    try:
        db.add(
            TranslationHistory(
                source_language="hin_Deva",
                target_language="sat_Olck",
                input_text=hindi_text,
                translated_text=translated_text,
                latency_ms=latency_ms,
                success=success,
                error_message=error_message,
                model_name=model_name,
            )
        )
        db.commit()
    except Exception:
        logger.exception("Failed to save pipeline translation history (non-fatal)")
        db.rollback()


@router.post(
    "/asr/transcribe",
    response_model=TranscribeResponse,
    summary="Hindi audio -> Hindi text (offline ASR, local CPU)",
)
def transcribe(
    file: UploadFile = File(..., description="Recorded audio (WAV or WebM)"),
    language: str = Form(default="", description="'hi' (default) or 'auto'"),
    db: Session = Depends(get_db),
) -> TranscribeResponse:
    audio_format = _sniff_audio_format(file)
    data = _read_upload(file)

    started = time.perf_counter()
    try:
        result = asr_service.transcribe_bytes(data, language=language or None)
    except ASRModelError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        _record_asr_row(
            db,
            language=language or settings.ASR_LANGUAGE,
            text=None,
            audio_format=audio_format,
            duration_sec=None,
            latency_ms=latency_ms,
            success=False,
            error_message=exc.user_message,
            model_name=asr_service.model_label,
        )
        raise HTTPException(status_code=exc.suggested_status, detail=exc.user_message) from exc

    message = None
    if not result["text"]:
        message = NO_SPEECH_MESSAGE

    _record_asr_row(
        db,
        language=result["language"],
        text=result["text"] or None,
        audio_format=audio_format,
        duration_sec=result["duration_sec"],
        latency_ms=result["latency_ms"],
        success=True,
        error_message=None,
        model_name=result["model"],
    )

    return TranscribeResponse(
        success=True,
        language=result["language"],
        text=result["text"],
        duration_sec=result["duration_sec"],
        latency_ms=result["latency_ms"],
        model=result["model"],
        offline=settings.OFFLINE_MODE,
        message=message,
    )


@router.post(
    "/classroom/speech-translate",
    response_model=SpeechTranslateResponse,
    summary="Hindi audio -> Hindi text -> Santali (Ol Chiki), fully local",
)
def speech_translate(
    file: UploadFile = File(..., description="Recorded Hindi audio (WAV or WebM)"),
    language: str = Form(default="", description="'hi' (default) or 'auto'"),
    db: Session = Depends(get_db),
) -> SpeechTranslateResponse:
    pipeline_started = time.perf_counter()
    audio_format = _sniff_audio_format(file)
    data = _read_upload(file)

    # ---- Step 1: offline ASR (Phase 3) ---------------------------------
    asr_started = time.perf_counter()
    try:
        asr = asr_service.transcribe_bytes(data, language=language or None)
    except ASRModelError as exc:
        _record_asr_row(
            db,
            language=language or settings.ASR_LANGUAGE,
            text=None,
            audio_format=audio_format,
            duration_sec=None,
            latency_ms=int((time.perf_counter() - asr_started) * 1000),
            success=False,
            error_message=exc.user_message,
            model_name=asr_service.model_label,
        )
        raise HTTPException(status_code=exc.suggested_status, detail=exc.user_message) from exc

    _record_asr_row(
        db,
        language=asr["language"],
        text=asr["text"] or None,
        audio_format=audio_format,
        duration_sec=asr["duration_sec"],
        latency_ms=asr["latency_ms"],
        success=True,
        error_message=None,
        model_name=asr["model"],
    )

    hindi_text = asr["text"]
    if not hindi_text:
        return SpeechTranslateResponse(
            success=False,
            recognized_hindi="",
            santali_ol_chiki="",
            asr_model=asr["model"],
            translation_model=settings.MT_MODEL_ID,
            asr_latency_ms=asr["latency_ms"],
            translation_latency_ms=0,
            total_latency_ms=int((time.perf_counter() - pipeline_started) * 1000),
            offline=settings.OFFLINE_MODE,
            message=NO_SPEECH_MESSAGE,
        )

    # ---- Step 2: EXISTING Phase 2 translation service (reused as-is) ----
    try:
        translation = translation_service.translate_text(hindi_text)
    except translation_service.TranslationModelError as exc:
        _record_translation_row(
            db,
            hindi_text=hindi_text,
            translated_text=None,
            latency_ms=None,
            success=False,
            error_message=exc.user_message,
            model_name=None,
        )
        raise HTTPException(
            status_code=exc.suggested_status, detail=exc.user_message
        ) from exc

    _record_translation_row(
        db,
        hindi_text=hindi_text,
        translated_text=translation["translated_text"],
        latency_ms=translation["latency_ms"],
        success=True,
        error_message=None,
        model_name=translation["model"],
    )

    return SpeechTranslateResponse(
        success=True,
        recognized_hindi=hindi_text,
        santali_ol_chiki=translation["translated_text"],
        asr_model=asr["model"],
        translation_model=translation["model"],
        asr_latency_ms=asr["latency_ms"],
        translation_latency_ms=translation["latency_ms"],
        total_latency_ms=int((time.perf_counter() - pipeline_started) * 1000),
        offline=settings.OFFLINE_MODE,
        message=None,
    )

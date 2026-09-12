"""Pydantic schemas for the Phase 3 ASR / speech-translate endpoints."""

from pydantic import BaseModel, Field

# SIH honesty: AI output is never presented as linguistically verified
VALIDATION_NOTICE = "Requires native-speaker validation"


class TranscribeResponse(BaseModel):
    """Response for POST /api/asr/transcribe."""

    success: bool = True
    language: str = Field(description="Recognized/forced language code, e.g. 'hi'")
    text: str = Field(default="", description="Hindi (Devanagari) transcript")
    duration_sec: float = Field(description="Audio length in seconds")
    latency_ms: int = Field(description="Local ASR inference time in ms")
    model: str = Field(description="ASR model, e.g. faster-whisper/small")
    offline: bool = True
    message: str | None = Field(
        default=None, description="Extra teacher-facing hint (e.g. no speech detected)"
    )


class SpeechTranslateResponse(BaseModel):
    """Response for POST /api/classroom/speech-translate (Phase 3+4 pipeline)."""

    success: bool
    recognized_hindi: str = ""
    santali_ol_chiki: str = ""
    asr_model: str
    translation_model: str = ""
    asr_latency_ms: int = 0
    translation_latency_ms: int = 0
    total_latency_ms: int = 0
    offline: bool = True
    validation_notice: str = VALIDATION_NOTICE
    message: str | None = None
    # ---- Phase 4 additions (Santali audio for the student) ----
    # All optional with safe defaults so the Phase 3 response shape is
    # preserved for every existing consumer.
    audio_available: bool = False
    audio_url: str | None = None
    tts_model: str = ""
    tts_latency_ms: int = 0
    tts_message: str | None = Field(
        default=None,
        description="Why Santali audio is not available (e.g. model not downloaded)",
    )

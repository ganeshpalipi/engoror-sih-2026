"""Pydantic schemas for the Phase 4 TTS endpoints."""

from pydantic import BaseModel, Field

# SIH honesty: synthesized speech is AI output, never presented as
# linguistically verified (same notice as the translated text).
VALIDATION_NOTICE = "AI-generated — Requires native-speaker validation"


class SynthesizeRequest(BaseModel):
    """Request body for POST /api/tts/synthesize."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Santali text in Ol Chiki script to speak aloud.",
    )


class SynthesizeResponse(BaseModel):
    """Response for POST /api/tts/synthesize."""

    success: bool = True
    text: str = Field(description="The Santali (Ol Chiki) text that was requested")
    tts_input_text: str = Field(
        default="",
        description="Normalized text actually spoken (digits mapped, unsupported chars removed)",
    )
    unsupported_chars_removed: str = Field(
        default="",
        description="Characters removed because the voice does not know them (empty = none)",
    )
    model: str = Field(description="TTS voice/model id")
    sample_rate: int = Field(description="WAV sample rate in Hz")
    duration_sec: float = Field(description="Generated audio length in seconds")
    latency_ms: int = Field(description="Local synthesis time in ms")
    rtf: float = Field(description="Real-time factor (latency / audio duration)")
    audio_url: str = Field(description="Relative URL of the generated WAV file")
    offline: bool = True
    validation_notice: str = VALIDATION_NOTICE

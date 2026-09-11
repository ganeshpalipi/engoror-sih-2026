"""Pydantic schemas for the translation endpoints (Phase 2)."""

from pydantic import BaseModel, Field, model_validator

# Phase 2 supports exactly one direction. More pairs arrive when verified
# data/models are available.
SUPPORTED_DIRECTIONS: set[tuple[str, str]] = {("hin_Deva", "sat_Olck")}


class TranslateTextRequest(BaseModel):
    """Request body for POST /api/translate/text."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Hindi (Devanagari) text to translate. Up to 10 lines.",
    )
    source_language: str = Field(default="hin_Deva")
    target_language: str = Field(default="sat_Olck")

    @model_validator(mode="after")
    def check_direction(self) -> "TranslateTextRequest":
        if (self.source_language, self.target_language) not in SUPPORTED_DIRECTIONS:
            raise ValueError(
                "Unsupported language pair "
                f"'{self.source_language} -> {self.target_language}'. "
                "The prototype currently supports only hin_Deva -> sat_Olck."
            )
        return self


class TranslateTextResponse(BaseModel):
    """Response for POST /api/translate/text."""

    input_text: str
    translated_text: str
    source_language: str
    target_language: str
    latency_ms: int
    model: str
    offline: bool = True
    # SIH honesty: AI output is never presented as linguistically verified
    validation_notice: str = "Requires native-speaker validation"


class TranslationModelStatus(BaseModel):
    """Status of the machine-translation model."""

    model: str
    direction: str
    status: str = Field(description="not_loaded | loading | ready | error")
    device: str | None = None
    detail: str = ""


class ASRModelStatus(BaseModel):
    """Status of the offline speech-recognition model (Phase 3)."""

    model: str
    direction: str
    status: str = Field(
        description="not_downloaded | not_loaded | loading | ready | error"
    )
    downloaded: bool = False
    device: str | None = None
    detail: str = ""


class ModelStatusResponse(BaseModel):
    """Response for GET /api/models/status."""

    offline: bool
    translation: TranslationModelStatus
    asr: ASRModelStatus | None = None  # Phase 3 (additive)

"""
Text-to-speech endpoints (Phase 4).

POST /api/tts/synthesize     Santali (Ol Chiki) text -> WAV + metadata
GET  /api/tts/audio/{file}   Serve a generated WAV to the frontend
GET  /api/tts/status         Honest TTS voice status

The synthesizer is fully local (Piper-format VITS voice via onnxruntime,
CPU) and never downloads anything during normal requests. If the model is
missing, callers get a friendly 503 telling them to run the one-time
download script.

Audio serving is deliberately whitelist-only: only files that match the
exact generated filename pattern `tts_<hex>.wav` inside generated_files/
can be fetched - no arbitrary file-path access is possible.
"""

import logging
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.ai.tts_service import TTSModelError, tts_service
from app.config import settings
from app.schemas.tts import SynthesizeRequest, SynthesizeResponse
from app.schemas.translation import TTSModelStatusOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tts", tags=["Speech Synthesis (TTS)"])

# Generated files are always named by this service: tts_<32 hex>.wav
_SAFE_FILENAME = re.compile(r"^tts_[0-9a-f]{32}\.wav$")


@router.post(
    "/synthesize",
    response_model=SynthesizeResponse,
    summary="Santali (Ol Chiki) text -> Santali speech (offline, local CPU)",
)
def synthesize(payload: SynthesizeRequest) -> SynthesizeResponse:
    try:
        result = tts_service.synthesize_to_file(payload.text)
    except TTSModelError as exc:
        raise HTTPException(status_code=exc.suggested_status, detail=exc.user_message) from exc

    return SynthesizeResponse(
        success=True,
        text=payload.text,
        tts_input_text=result["tts_input_text"],
        unsupported_chars_removed=result["unsupported_chars_removed"],
        model=result["model"],
        sample_rate=result["sample_rate"],
        duration_sec=result["duration_sec"],
        latency_ms=result["latency_ms"],
        rtf=result["rtf"],
        audio_url=f"/api/tts/audio/{result['filename']}",
        offline=settings.OFFLINE_MODE,
    )


@router.get(
    "/audio/{filename}",
    summary="Serve a generated Santali WAV file (whitelist: tts_<hex>.wav)",
)
def serve_audio(filename: str) -> FileResponse:
    if not _SAFE_FILENAME.match(filename):
        raise HTTPException(
            status_code=404,
            detail="Audio file not found. Please synthesize the sentence again.",
        )
    path = settings.generated_files_path / filename
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="This Santali audio file has expired. Please play the "
            "sentence again to regenerate it.",
        )
    return FileResponse(
        path,
        media_type="audio/wav",
        filename=filename,
    )


@router.get(
    "/status",
    response_model=TTSModelStatusOut,
    summary="Honest Santali TTS voice status",
)
def tts_status() -> TTSModelStatusOut:
    return TTSModelStatusOut(**tts_service.status())

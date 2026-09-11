"""
Offline Hindi ASR service (Phase 3) - faster-whisper.

REAL local speech recognition with faster-whisper (CTranslate2 port of
OpenAI Whisper). Open weights, CPU INT8 inference, NO cloud API - no
OpenAI/Google/Azure/AWS speech service is used anywhere.

Offline-first policy (mirrors model_manager.py):
- The model downloads ONCE (public HF repo `Systran/faster-whisper-<size>`,
  no token needed) into backend/model_cache/asr/ - a folder that is
  deliberately SEPARATE from the translation cache (model_cache/hf) so the
  working Phase 2 IndicTrans2 files can never be touched.
- After that one download, loading always resolves to the local snapshot
  and inference works with Wi-Fi fully off.

Heavy libraries (faster_whisper, av) are imported lazily inside functions
so the API can boot and serve /health even when ASR deps are not installed.

Audio decoding uses PyAV (bundled FFmpeg libraries inside the `av` wheel),
so browser recordings (WebM/Opus) and WAV files both work on Windows 11
without installing the ffmpeg.exe binary.
"""

import io
import logging
import threading
import time
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# faster-whisper hosts open copies of Whisper under the `Systran` org.
ASR_HF_ORG = "Systran"
# Guard rails for classroom recordings.
MIN_AUDIO_SECONDS = 0.2
MAX_UPLOAD_MB = 25


class ASRModelError(Exception):
    """Domain error carrying a teacher-facing message + suggested HTTP status."""

    def __init__(self, user_message: str, suggested_status: int = 503):
        super().__init__(user_message)
        self.user_message = user_message
        self.suggested_status = suggested_status


class ASRService:
    """Lazy, thread-safe, load-once wrapper around faster-whisper."""

    def __init__(self) -> None:
        self._model = None
        self._loaded_label: str = ""
        self._load_lock = threading.RLock()
        self._infer_lock = threading.Lock()  # CPU inference is serialized

    # ---------------------------------------------------------------- status
    @property
    def model_label(self) -> str:
        return f"faster-whisper/{settings.ASR_MODEL_SIZE}"

    @property
    def repo_id(self) -> str:
        return f"{ASR_HF_ORG}/faster-whisper-{settings.ASR_MODEL_SIZE}"

    def local_model_path(self) -> Path | None:
        """
        Return the local snapshot directory if the model is already in
        backend/model_cache/asr, else None. Never touches the network.
        """
        cache_dir = settings.asr_model_path
        pattern = f"models--{ASR_HF_ORG}--faster-whisper-{settings.ASR_MODEL_SIZE}"
        base = cache_dir / pattern / "snapshots"
        if not base.is_dir():
            return None
        for snapshot in sorted(base.iterdir()):
            if (snapshot / "model.bin").is_file():
                return snapshot
        return None

    def is_downloaded(self) -> bool:
        """True when the ASR weights are cached locally (offline-ready)."""
        return self.local_model_path() is not None

    def is_loaded(self) -> bool:
        return self._model is not None

    def status(self) -> dict:
        """Honest status for /health and /api/models/status."""
        downloaded = self.is_downloaded()
        if self._model is not None:
            state, detail = "ready", self._loaded_label
        elif downloaded:
            state = "not_loaded"
            detail = "Model cached - loads on first use"
        else:
            state = "not_downloaded"
            detail = (
                "Run: python scripts\\download_asr_model.py (needs internet once)"
            )
        return {
            "model": self.model_label,
            "direction": "hindi speech -> hindi text",
            "status": state,
            "downloaded": downloaded,
            "device": settings.ASR_DEVICE,
            "detail": detail,
        }

    # ---------------------------------------------------------------- loading
    def ensure_model_loaded(self, allow_download: bool = True) -> None:
        """Load the ASR model once; later calls reuse the in-memory model."""
        with self._load_lock:
            if self._model is not None:
                return
            self._model = self._load_model(allow_download=allow_download)
            self._loaded_label = (
                f"{self.model_label} "
                f"({settings.ASR_COMPUTE_TYPE}, {settings.ASR_DEVICE})"
            )
            logger.info("ASR model READY: %s", self._loaded_label)

    def _load_model(self, allow_download: bool):
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # deps not installed
            raise ASRModelError(
                "The ASR engine (faster-whisper) is not installed. "
                "Activate the venv and run: pip install -r requirements.txt",
                500,
            ) from exc

        started = time.perf_counter()
        load_kwargs = dict(
            device=settings.ASR_DEVICE,
            compute_type=settings.ASR_COMPUTE_TYPE,
            cpu_threads=settings.ASR_CPU_THREADS,
        )

        # 1) Offline-first: use the local snapshot if it is already cached.
        local_path = self.local_model_path()
        if local_path is not None:
            logger.info("Loading ASR model from local cache: %s", local_path)
            return WhisperModel(str(local_path), **load_kwargs)

        # 2) Not cached yet.
        if not allow_download or settings.OFFLINE_MODE:
            raise ASRModelError(
                "The ASR model is not downloaded yet. Connect to the internet "
                "ONCE and run: python scripts\\download_asr_model.py "
                "(weights are cached in backend\\model_cache\\asr). "
                "Afterwards speech recognition works fully offline.",
                503,
            )

        # 3) One-time download (needs internet, public repo, no token).
        logger.info(
            "ASR model %s not in cache - downloading once (~0.5 GB)...",
            self.repo_id,
        )
        try:
            return WhisperModel(
                settings.ASR_MODEL_SIZE,
                download_root=str(settings.asr_model_path),
                local_files_only=False,
                **load_kwargs,
            )
        except Exception as exc:
            raise ASRModelError(_friendly_download_error(exc), 503) from exc

    def download_model(self) -> Path:
        """
        Explicit one-time download of the ASR weights (needs internet).

        Used by scripts/download_asr_model.py. Deliberately bypasses the
        OFFLINE_MODE guard (that flag describes runtime inference, not this
        one-time setup). Safe to run repeatedly: a cached model is reused.
        """
        with self._load_lock:
            if self._model is not None:
                return self.local_model_path() or settings.asr_model_path
            local = self.local_model_path()
            if local is not None:
                logger.info("ASR model already cached: %s", local)
                return local
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise ASRModelError(
                    "faster-whisper is not installed. Activate the venv and "
                    "run: pip install -r requirements.txt", 500,
                ) from exc
            logger.info("Downloading ASR model %s (one-time, ~0.5 GB)...", self.repo_id)
            try:
                self._model = WhisperModel(
                    settings.ASR_MODEL_SIZE,
                    download_root=str(settings.asr_model_path),
                    local_files_only=False,
                    device=settings.ASR_DEVICE,
                    compute_type=settings.ASR_COMPUTE_TYPE,
                    cpu_threads=settings.ASR_CPU_THREADS,
                )
                self._loaded_label = (
                    f"{self.model_label} "
                    f"({settings.ASR_COMPUTE_TYPE}, {settings.ASR_DEVICE})"
                )
            except Exception as exc:
                raise ASRModelError(_friendly_download_error(exc), 503) from exc
            return self.local_model_path() or settings.asr_model_path

    def load_from_cache_in_background(self) -> None:
        """Optional startup warm-up (never downloads; disabled by default)."""
        thread = threading.Thread(
            target=self._safe_preload, daemon=True
        )
        thread.start()

    def _safe_preload(self) -> None:
        try:
            self.ensure_model_loaded(allow_download=False)
        except Exception as exc:
            logger.info("ASR model not preloaded (%s)", exc)

    # ---------------------------------------------------------------- inference
    def transcribe_bytes(self, data: bytes, language: str | None = None) -> dict:
        """
        Transcribe Hindi speech from raw audio bytes (WAV, WebM/Opus, MP3, ...).

        Returns {"text", "language", "duration_sec", "latency_ms", "model"}.
        Raises ASRModelError with a teacher-facing message on any failure.
        """
        started = time.perf_counter()

        if not data:
            raise ASRModelError(
                "The recording is empty. Please record again.", 400
            )
        if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
            raise ASRModelError(
                f"The recording is larger than {MAX_UPLOAD_MB} MB. "
                "Please record a short classroom sentence.", 413
            )

        audio, duration = self._decode_audio(data)
        if duration < MIN_AUDIO_SECONDS:
            raise ASRModelError(
                "The recording is too short (or silent). Hold the record "
                "button and speak clearly.", 400
            )
        if duration > settings.ASR_MAX_AUDIO_SECONDS:
            raise ASRModelError(
                f"The recording is {duration:.0f}s long but the limit is "
                f"{settings.ASR_MAX_AUDIO_SECONDS:.0f}s. Please record one "
                "classroom sentence at a time.", 413
            )

        forced_language = (language or settings.ASR_LANGUAGE).strip().lower()
        if forced_language in ("", "none"):
            forced_language = settings.ASR_LANGUAGE

        try:
            with self._infer_lock:
                model = self._require_model()
                segments, info = model.transcribe(
                    audio,
                    language=None if forced_language == "auto" else forced_language,
                    beam_size=settings.ASR_BEAM_SIZE,
                    vad_filter=True,                    # skip silence (avoids hallucinated text)
                    condition_on_previous_text=False,   # short independent classroom sentences
                )
                chunks = [seg.text.strip() for seg in segments]
        except ASRModelError:
            raise
        except Exception as exc:
            logger.exception("ASR transcription failed")
            raise ASRModelError(
                "Speech recognition failed on this device. Please try again; "
                "if it keeps failing, check the Model Status panel.", 500
            ) from exc

        text = " ".join(c for c in chunks if c).strip()
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "ASR: %.1fs audio -> %d chars in %d ms (language=%s)",
            duration, len(text), latency_ms, info.language,
        )
        return {
            "text": text,
            "language": info.language or forced_language,
            "duration_sec": round(float(duration), 2),
            "latency_ms": latency_ms,
            "model": self.model_label,
        }

    def _require_model(self):
        if self._model is None:
            # Defensive: never download during a request unless allowed.
            self.ensure_model_loaded(allow_download=not settings.OFFLINE_MODE)
        return self._model

    def _decode_audio(self, data: bytes):
        """
        Decode any common container/codec to 16 kHz mono float32 using PyAV
        (bundled FFmpeg libraries - Windows-safe, no ffmpeg.exe needed).
        Returns (audio, duration_seconds).
        """
        try:
            import numpy as np  # faster-whisper already depends on numpy
            from faster_whisper.audio import decode_audio
        except ImportError as exc:
            raise ASRModelError(
                "The ASR engine (faster-whisper) is not installed. "
                "Activate the venv and run: pip install -r requirements.txt",
                500,
            ) from exc

        try:
            audio = decode_audio(io.BytesIO(data), sampling_rate=16000)
        except Exception as exc:
            logger.warning("Audio decode failed: %s", exc)
            raise ASRModelError(
                "This audio could not be read. Supported: WAV, WebM/Opus, "
                "MP3, M4A, OGG. The file may also be corrupted - please "
                "record again.", 400
            ) from exc

        audio = np.asarray(audio, dtype="float32")
        if audio.ndim > 1:  # safety: downmix if a split ever sneaks through
            audio = audio.mean(axis=1)
        duration = float(audio.shape[0]) / 16000.0
        if not np.isfinite(audio).all():
            raise ASRModelError(
                "The recording contains invalid audio data. Please record again.",
                400,
            )
        return audio, duration


def _friendly_download_error(exc: Exception) -> str:
    text = str(exc).lower()
    if "connection" in text or "timed out" in text or "max retries" in text or "offline" in text:
        return (
            "The ASR model is not in the local cache and the one-time download "
            "failed (no internet). Connect to the internet once, then run: "
            "python scripts\\download_asr_model.py - afterwards everything "
            "runs offline."
        )
    return f"ASR model download failed: {exc}"


# Process-wide singleton
asr_service = ASRService()

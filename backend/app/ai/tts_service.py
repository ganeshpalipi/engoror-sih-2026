"""
Offline Santali TTS service (Phase 4) - Piper-format VITS via onnxruntime.

REAL local speech synthesis. Open weights, CPU inference, NO cloud API - no
Google/Azure/AWS/OpenAI/ElevenLabs speech service is used anywhere.

Model selection (verified, not assumed):
- `facebook/mms-tts-sat` does NOT exist. The complete Meta MMS TTS catalog
  (1100+ languages) has no Santali (`sat`) entry, and the official Piper
  voices catalog (rhasspy/piper-voices) has no Santali voice either.
- The selected voice `Ashraf01k/vernacular-pedagogy-santhali` is a
  Piper-format VITS model (~60 MB, MIT license) whose phoneme_id_map covers
  the Ol Chiki Unicode block (U+1C50-U+1C7F) directly. Verified in this
  project by real inference: Ol Chiki text in -> speech-shaped WAV out,
  RTF ~0.05-0.07 on CPU, and acoustic profile matching the model's own
  published samples.
- Pronunciation quality still requires native-speaker validation (the
  frontend keeps the "AI-generated" notice for the audio too).

Offline-first policy (mirrors asr_service.py):
- The model downloads ONCE (public HF repo, no token) into
  backend/model_cache/tts/ - a folder deliberately SEPARATE from the
  translation (model_cache/hf) and ASR (model_cache/asr) caches so the
  working Phase 2/3 files can never be touched.
- After that one download, loading always resolves to the local snapshot
  and synthesis works with Wi-Fi fully off. Normal requests NEVER download.

Input script support (verified against the model config):
- Ol Chiki Unicode goes in directly, character by character (phoneme_type
  "text"): no transliteration step is needed.
- ASCII digits 0-9 are NOT in the model vocabulary; they are transparently
  converted to the Ol Chiki digits U+1C50-U+1C59.
- The Devanagari danda (।) is mapped to the Ol Chiki danda (U+1C7E).
- Any other unsupported character is dropped and reported, never guessed.
- Devanagari Hindi text is NOT a valid input - the service answers with a
  friendly error instead of pretending a Hindi voice is Santali.

Heavy libraries (onnxruntime, numpy) are imported lazily inside functions so
the API can boot and serve /health even when TTS deps are not installed.
"""

import logging
import re
import threading
import time
import unicodedata
import uuid
import wave
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# ASCII digit -> Ol Chiki digit (U+1C50..U+1C59). The model vocabulary has
# Ol Chiki digits only; this keeps "10 books" style input working.
_ASCII_DIGITS = "0123456789"
_OL_CHIKI_DIGITS = "᱐᱑᱒᱓᱔᱕᱖᱗᱘᱙"
_DIGIT_TABLE = str.maketrans(_ASCII_DIGITS, _OL_CHIKI_DIGITS)

# Devanagari danda -> Ol Chiki danda (the model knows the Ol Chiki one).
_DANDA_TABLE = {ord("।"): "᱾", ord("|"): "᱾"}

# Audio shaping.
TRIM_THRESHOLD = 0.01          # absolute amplitude treated as silence
TRIM_PAD_SECONDS = 0.03        # keep a little natural padding
MIN_OUTPUT_SECONDS = 0.15      # shorter than this = synthesis failed
MAX_TTS_FILE_MB = 20           # generated WAV guard (paranoia)


class TTSModelError(Exception):
    """Domain error carrying a teacher-facing message + suggested HTTP status."""

    def __init__(self, user_message: str, suggested_status: int = 503):
        super().__init__(user_message)
        self.user_message = user_message
        self.suggested_status = suggested_status


class TTSService:
    """Lazy, thread-safe, load-once wrapper around the Santali VITS voice."""

    def __init__(self) -> None:
        self._session = None          # onnxruntime InferenceSession
        self._id_map: dict | None = None
        self._sample_rate: int = settings.TTS_SAMPLE_RATE
        self._noise_scale: float = 0.667
        self._length_scale: float = 1.0
        self._noise_w: float = 0.8
        self._pad_id = 0
        self._bos_id = 1
        self._eos_id = 2
        self._loaded_label: str = ""
        self._error: str | None = None
        self._load_lock = threading.RLock()
        self._infer_lock = threading.Lock()  # CPU inference is serialized

    # ---------------------------------------------------------------- status
    @property
    def model_label(self) -> str:
        return settings.TTS_MODEL_ID

    def local_model_dir(self) -> Path | None:
        """
        Local snapshot directory containing BOTH the .onnx and its .onnx.json,
        or None. Never touches the network.
        """
        repo = settings.TTS_MODEL_ID
        pattern = f"models--{repo.split('/')[0]}--{repo.split('/')[1]}"
        base = settings.tts_model_path / pattern / "snapshots"
        if not base.is_dir():
            return None
        for snapshot in sorted(base.iterdir()):
            if (
                (snapshot / settings.TTS_MODEL_FILE).is_file()
                and (snapshot / settings.TTS_CONFIG_FILE).is_file()
            ):
                return snapshot
        return None

    def is_downloaded(self) -> bool:
        """True when the TTS weights are cached locally (offline-ready)."""
        return self.local_model_dir() is not None

    def is_loaded(self) -> bool:
        return self._session is not None

    def status(self) -> dict:
        """Honest status for /health and /api/models/status."""
        downloaded = self.is_downloaded()
        if self._session is not None:
            state, detail = "ready", self._loaded_label
        elif self._error:
            state, detail = "error", self._error
        elif downloaded:
            state = "not_loaded"
            detail = "Model cached - loads on first use"
        else:
            state = "not_downloaded"
            detail = (
                "Run: python scripts\\download_tts_model.py (needs internet once)"
            )
        return {
            "model": self.model_label,
            "direction": "santali ol chiki text -> santali speech",
            "status": state,
            "downloaded": downloaded,
            "device": settings.TTS_DEVICE,
            "detail": detail,
        }

    # ---------------------------------------------------------------- loading
    def ensure_model_loaded(self, allow_download: bool = True) -> None:
        """Load the TTS model once; later calls reuse the in-memory session."""
        with self._load_lock:
            if self._session is not None:
                return
            try:
                self._load_model(allow_download=allow_download)
                self._error = None
            except Exception as exc:
                self._error = str(getattr(exc, "user_message", exc))
                raise

    def _load_model(self, allow_download: bool) -> None:
        try:
            import onnxruntime as ort
        except ImportError as exc:  # deps not installed
            raise TTSModelError(
                "The TTS engine (onnxruntime) is not installed. Activate the "
                "venv and run: pip install -r requirements.txt",
                500,
            ) from exc

        # 1) Offline-first: use the local snapshot if it is already cached.
        local_dir = self.local_model_dir()
        if local_dir is None:
            if not allow_download or settings.OFFLINE_MODE:
                raise TTSModelError(
                    "The Santali TTS model is not downloaded yet. Connect to "
                    "the internet ONCE and run: "
                    "python scripts\\download_tts_model.py (weights are "
                    "cached in backend\\model_cache\\tts). Afterwards Santali "
                    "speech works fully offline.",
                    503,
                )
            # 2) One-time download (needs internet, public repo, no token).
            logger.info(
                "TTS model %s not in cache - downloading once (~60 MB)...",
                self.model_label,
            )
            try:
                from huggingface_hub import snapshot_download

                snapshot_download(
                    repo_id=self.model_label,
                    cache_dir=str(settings.tts_model_path),
                    allow_patterns=[
                        settings.TTS_MODEL_FILE,
                        settings.TTS_CONFIG_FILE,
                    ],
                )
            except Exception as exc:
                raise TTSModelError(_friendly_download_error(exc), 503) from exc
            local_dir = self.local_model_dir()
            if local_dir is None:
                raise TTSModelError(
                    "The TTS download finished but the model files could not "
                    "be found in the cache. Please run: "
                    "python scripts\\download_tts_model.py",
                    503,
                )

        model_path = local_dir / settings.TTS_MODEL_FILE
        config_path = local_dir / settings.TTS_CONFIG_FILE
        try:
            import json

            with open(config_path, "r", encoding="utf-8") as fh:
                config = json.load(fh)
        except Exception as exc:
            raise TTSModelError(
                "The TTS model configuration file is damaged. Delete "
                "backend\\model_cache\\tts and re-run the download script.",
                503,
            ) from exc

        started = time.perf_counter()
        session_options = ort.SessionOptions()
        if settings.TTS_NUM_THREADS > 0:
            session_options.intra_op_num_threads = settings.TTS_NUM_THREADS
            session_options.inter_op_num_threads = settings.TTS_NUM_THREADS
        try:
            self._session = ort.InferenceSession(
                str(model_path),
                session_options,
                providers=["CPUExecutionProvider"],
            )
        except Exception as exc:
            raise TTSModelError(
                "The Santali TTS model could not be loaded on this device. "
                "If this keeps happening, delete backend\\model_cache\\tts "
                "and re-run: python scripts\\download_tts_model.py",
                503,
            ) from exc

        self._apply_config(config)
        self._loaded_label = (
            f"{self.model_label} "
            f"({self._sample_rate} Hz, {settings.TTS_DEVICE}, "
            f"{time.perf_counter() - started:.1f}s load)"
        )
        logger.info("TTS model READY: %s", self._loaded_label)

    def _apply_config(self, config: dict) -> None:
        """Read the Piper voice config (id map, rate, inference scales)."""
        self._id_map = dict(config.get("phoneme_id_map") or {})
        if not self._id_map:
            raise TTSModelError(
                "The TTS voice config has no phoneme map - the cached model "
                "is unusable. Delete backend\\model_cache\\tts and re-run "
                "the download script.",
                503,
            )
        self._sample_rate = int(
            (config.get("audio") or {}).get("sample_rate", settings.TTS_SAMPLE_RATE)
        )
        inference = config.get("inference") or {}
        self._noise_scale = float(inference.get("noise_scale", 0.667))
        self._length_scale = float(inference.get("length_scale", 1.0))
        self._noise_w = float(inference.get("noise_w", 0.8))
        self._pad_id = int(self._id_map.get("_", [0])[0])
        self._bos_id = int(self._id_map.get("^", [1])[0])
        self._eos_id = int(self._id_map.get("$", [2])[0])

    def download_model(self) -> Path:
        """
        Explicit one-time download of the TTS weights (needs internet).

        Used by scripts/download_tts_model.py. Deliberately bypasses the
        OFFLINE_MODE guard (that flag describes runtime inference, not this
        one-time setup). Safe to run repeatedly: a cached model is reused.
        """
        with self._load_lock:
            local = self.local_model_dir()
            if local is not None:
                logger.info("TTS model already cached: %s", local)
                return local
            try:
                from huggingface_hub import snapshot_download

                snapshot_download(
                    repo_id=self.model_label,
                    cache_dir=str(settings.tts_model_path),
                    allow_patterns=[
                        settings.TTS_MODEL_FILE,
                        settings.TTS_CONFIG_FILE,
                    ],
                )
            except Exception as exc:
                raise TTSModelError(_friendly_download_error(exc), 503) from exc
            local = self.local_model_dir()
            if local is None:
                raise TTSModelError(
                    "Download finished but the model files are missing. "
                    "Please retry: python scripts\\download_tts_model.py",
                    503,
                )
            return local

    def load_from_cache_in_background(self) -> None:
        """Optional startup warm-up (never downloads; disabled by default)."""
        thread = threading.Thread(target=self._safe_preload, daemon=True)
        thread.start()

    def _safe_preload(self) -> None:
        try:
            self.ensure_model_loaded(allow_download=False)
        except Exception as exc:
            logger.info("TTS model not preloaded (%s)", exc)

    # ---------------------------------------------------------------- text
    def prepare_text(self, text: str) -> tuple[str, str]:
        """
        Normalize Ol Chiki text for the voice. Returns (clean_text, removed).

        Transparent, documented steps (no transliteration - Ol Chiki is
        supported directly by the model):
        1. Unicode NFC normalization
        2. ASCII digits 0-9 -> Ol Chiki digits U+1C50-U+1C59
        3. Devanagari danda -> Ol Chiki danda
        4. Drop every character the voice does not know (reported, never guessed)
        """
        normalized = unicodedata.normalize("NFC", text)
        normalized = normalized.translate(_DIGIT_TABLE)
        normalized = normalized.translate(_DANDA_TABLE)

        kept: list[str] = []
        removed: list[str] = []
        assert self._id_map is not None
        for ch in normalized:
            if ch in self._id_map or ch.isspace():
                kept.append(ch)
            elif ch not in removed:
                removed.append(ch)
        clean = re.sub(r"\s+", " ", "".join(kept)).strip()
        return clean, "".join(removed)

    # ---------------------------------------------------------------- inference
    def synthesize_to_file(self, text: str) -> dict:
        """
        Santali Ol Chiki text -> WAV file in backend/generated_files.

        Returns metadata dict; raises TTSModelError with a teacher-facing
        message on any failure.
        """
        started = time.perf_counter()

        if not text or not text.strip():
            raise TTSModelError(
                "There is no text to speak. Type or generate some Santali "
                "(Ol Chiki) text first.", 400,
            )
        if len(text) > settings.TTS_MAX_TEXT_LENGTH:
            raise TTSModelError(
                f"The text is too long ({len(text)} characters). The limit "
                f"is {settings.TTS_MAX_TEXT_LENGTH} characters - please use "
                "one classroom sentence at a time.", 400,
            )

        with self._infer_lock:
            # Ensure config is available for prepare_text (loads model once).
            self.ensure_model_loaded(allow_download=not settings.OFFLINE_MODE)
            clean, removed = self.prepare_text(text)
            if not clean:
                raise TTSModelError(
                    "This text does not contain any Ol Chiki (ᱚᱞ ᱪᱤᱠᱤ) "
                    "characters that the Santali voice can speak. Santali "
                    "text in Ol Chiki is required - Hindi text cannot be "
                    "spoken by the Santali voice.", 400,
                )

            audio = self._generate_audio(clean)

        audio = self._trim_silence(audio)
        duration_sec = float(len(audio)) / float(self._sample_rate)
        if duration_sec < MIN_OUTPUT_SECONDS:
            raise TTSModelError(
                "The voice produced no audible speech for this text. Please "
                "try a different Santali sentence.", 500,
            )

        out_path = self._save_wav(audio)

        latency_ms = int((time.perf_counter() - started) * 1000)
        rtf = (latency_ms / 1000.0) / duration_sec if duration_sec else 0.0
        logger.info(
            "TTS: %d chars -> %.2fs audio in %d ms (RTF %.3f)",
            len(clean), duration_sec, latency_ms, rtf,
        )
        return {
            "filename": out_path.name,
            "audio_path": str(out_path),
            "sample_rate": self._sample_rate,
            "duration_sec": round(duration_sec, 2),
            "latency_ms": latency_ms,
            "rtf": round(rtf, 3),
            "model": self.model_label,
            "input_text": text,
            "tts_input_text": clean,
            "unsupported_chars_removed": removed,
        }

    def _generate_audio(self, clean_text: str):
        """Run the VITS ONNX graph (Piper protocol) and return float32 audio."""
        import numpy as np

        assert self._id_map is not None
        phoneme_ids = [self._pad_id, self._bos_id]
        for ch in clean_text:
            if ch == " ":
                phoneme_ids.extend(self._id_map[" "])
            else:
                phoneme_ids.extend(self._id_map[ch])
        phoneme_ids.extend([self._eos_id, self._pad_id])

        scales = np.array(
            [self._noise_scale, self._length_scale, self._noise_w],
            dtype=np.float32,
        )
        try:
            audio = self._session.run(
                ["output"],
                {
                    "input": np.array([phoneme_ids], dtype=np.int64),
                    "input_lengths": np.array([len(phoneme_ids)], dtype=np.int64),
                    "scales": scales,
                },
            )[0]
        except TTSModelError:
            raise
        except Exception as exc:
            logger.exception("TTS synthesis failed")
            raise TTSModelError(
                "Speech synthesis failed on this device. Please try again; "
                "if it keeps failing, check the Model Status panel.", 500,
            ) from exc

        audio = np.asarray(audio, dtype=np.float32).squeeze()
        if audio.size == 0 or not np.isfinite(audio).all():
            raise TTSModelError(
                "Speech synthesis produced invalid audio. Please try again.",
                500,
            )
        return audio

    def _trim_silence(self, audio):
        """Trim leading/trailing near-silence, keeping a small natural pad."""
        import numpy as np

        mag = np.abs(audio)
        loud = np.where(mag > TRIM_THRESHOLD)[0]
        if loud.size == 0:
            return audio
        pad = int(TRIM_PAD_SECONDS * self._sample_rate)
        start = max(0, int(loud[0]) - pad)
        end = min(len(audio), int(loud[-1]) + pad)
        return audio[start:end]

    def _save_wav(self, audio) -> Path:
        """16-bit PCM mono WAV into backend/generated_files (stdlib wave)."""
        out_dir = settings.generated_files_path
        out_path = out_dir / f"tts_{uuid.uuid4().hex}.wav"
        try:
            import numpy as np

            clipped = np.clip(audio, -1.0, 1.0)
            pcm = (clipped * 32767.0).astype(np.int16)
            with wave.open(str(out_path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(self._sample_rate)
                wav.writeframes(pcm.tobytes())
        except Exception as exc:
            logger.exception("Failed to write TTS WAV file")
            raise TTSModelError(
                "The Santali audio file could not be saved on this device. "
                "Please try again.", 500,
            ) from exc
        if out_path.stat().st_size > MAX_TTS_FILE_MB * 1024 * 1024:
            out_path.unlink(missing_ok=True)
            raise TTSModelError(
                "The generated audio was unexpectedly large. Please use a "
                "shorter sentence.", 400,
            )
        self._cleanup_old_files(keep=50)
        return out_path

    def _cleanup_old_files(self, keep: int = 50) -> None:
        """Best-effort retention so generated_files cannot grow forever."""
        try:
            files = sorted(
                settings.generated_files_path.glob("tts_*.wav"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for old in files[keep:]:
                old.unlink(missing_ok=True)
        except Exception:  # non-fatal housekeeping
            logger.debug("TTS file cleanup skipped", exc_info=True)


def _friendly_download_error(exc: Exception) -> str:
    text = str(exc).lower()
    if "connection" in text or "timed out" in text or "max retries" in text or "offline" in text:
        return (
            "The Santali TTS model is not in the local cache and the "
            "one-time download failed (no internet). Connect to the "
            "internet once, then run: python scripts\\download_tts_model.py "
            "- afterwards everything runs offline."
        )
    return f"Santali TTS model download failed: {exc}"


# Process-wide singleton
tts_service = TTSService()

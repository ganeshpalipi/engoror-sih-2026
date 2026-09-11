"""
Central AI model manager.

Responsibilities (SIH Phase 2):
- Lazy, thread-safe, load-once model loading (model stays cached in RAM)
- Offline-first: loads from the local Hugging Face cache first; downloads
  only when the model is missing (one-time setup, needs internet once)
- Honest status reporting - never claims READY without a loaded model
- Persists load status into the model_metadata table (best effort)

Heavy libraries (torch, transformers, IndicTransTokenizer) are imported
lazily inside functions so the API can boot and serve /health even when the
AI dependencies are not installed yet.
"""

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable

from app.config import settings
from app.database import SessionLocal
from app.models import ModelMetadata

logger = logging.getLogger(__name__)

# Route every Hugging Face download/cache into backend/model_cache/hf so the
# whole AI setup lives in one git-ignored folder. Must happen before
# transformers / huggingface_hub are imported anywhere in the process.
os.environ.setdefault("HF_HOME", str(settings.model_cache_path / "hf"))
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
# The official AI4Bharat IndicTrans2 repos are gated ("auto"): a FREE Hugging
# Face account + one-time acceptance of the model conditions is required.
# The user's READ token goes into backend/.env as HF_TOKEN (never committed).
if settings.HF_TOKEN:
    os.environ.setdefault("HF_TOKEN", settings.HF_TOKEN)
    os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", settings.HF_TOKEN)

TRANSLATION_DIRECTION = "hin_Deva -> sat_Olck"


class ModelStatus:
    """Honest model lifecycle states (mirrored into model_metadata.status)."""

    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


class _TranslationRuntime:
    """Holds the loaded tokenizer/processor/model for the MT model plus status."""

    def __init__(self) -> None:
        self.model_id: str = settings.MT_MODEL_ID
        self.status: str = ModelStatus.NOT_LOADED
        self.device: str | None = None
        self.detail: str = ""
        self.tokenizer: Any = None   # HF AutoTokenizer (custom code from the model repo)
        self.processor: Any = None   # IndicProcessor (normalization + language tags)
        self.model: Any = None


class ModelManager:
    """Registry + lifecycle for AI models (Phase 2: translation only)."""

    def __init__(self) -> None:
        self._translation = _TranslationRuntime()
        self._load_lock = threading.RLock()
        self._infer_lock = threading.Lock()

    # ------------------------------------------------------------------ status
    def translation_status(self) -> dict:
        rt = self._translation
        return {
            "model": rt.model_id,
            "direction": TRANSLATION_DIRECTION,
            "status": rt.status,
            "device": rt.device,
            "detail": rt.detail,
        }

    def status_snapshot(self) -> dict:
        return {
            "offline": settings.OFFLINE_MODE,
            "translation": self.translation_status(),
        }

    # ------------------------------------------------------------------ loading
    def ensure_translation_loaded(self, allow_download: bool = True) -> None:
        """Load the MT model once; later calls reuse the in-memory model."""
        with self._load_lock:
            rt = self._translation
            if rt.status == ModelStatus.READY:
                return
            try:
                self._load_translation(rt, allow_download=allow_download)
            except Exception as exc:
                rt.status = ModelStatus.ERROR
                rt.detail = _friendly_load_error(exc)
                logger.exception("Translation model failed to load")
                self._record_metadata(rt)
                raise

    def _load_translation(self, rt: _TranslationRuntime, allow_download: bool) -> None:
        rt.status = ModelStatus.LOADING
        rt.detail = "Loading model..."
        self._record_metadata(rt)

        started = time.perf_counter()

        import torch  # lazy: keep API boot independent of AI deps
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        cache_dir = str(settings.model_cache_path / "hf")
        common = dict(
            cache_dir=cache_dir,
            trust_remote_code=True,
            token=settings.HF_TOKEN or None,
        )

        # 1) Offline-first: use the local cache if the model is already there
        try:
            model = AutoModelForSeq2SeqLM.from_pretrained(
                rt.model_id, local_files_only=True, torch_dtype=torch.float32, **common
            )
            tokenizer = AutoTokenizer.from_pretrained(
                rt.model_id, local_files_only=True, **common
            )
            logger.info("Translation model loaded from local cache")
        except Exception:
            if not allow_download:
                raise RuntimeError(
                    "Model is not in the local cache yet "
                    f"({cache_dir}). The one-time download was skipped."
                )
            # 2) First-time setup: download once (needs internet + HF token),
            #    then it lives in model_cache/hf forever - no cloud after.
            logger.info(
                "Model %s not in cache - downloading once (~1.3 GB, needs internet)...",
                rt.model_id,
            )
            model = AutoModelForSeq2SeqLM.from_pretrained(
                rt.model_id, torch_dtype=torch.float32, **common
            )
            tokenizer = AutoTokenizer.from_pretrained(rt.model_id, **common)

        processor = _build_indic_processor()

        device = "cuda" if torch.cuda.is_available() else "cpu"  # GPU optional
        model.to(device)
        model.eval()

        rt.tokenizer = tokenizer
        rt.processor = processor
        rt.model = model
        rt.device = device
        rt.status = ModelStatus.READY
        rt.detail = f"Loaded in {time.perf_counter() - started:.1f}s"
        logger.info("Translation model READY on %s (%s)", device, rt.detail)
        self._record_metadata(rt)

    def load_from_cache_in_background(self) -> None:
        """Warm the model from the local cache at startup (never downloads)."""
        if not settings.PRELOAD_MODEL_ON_STARTUP:
            logger.info("Model preload disabled by configuration")
            return
        thread = threading.Thread(target=self._safe_preload, daemon=True)
        thread.start()

    def _safe_preload(self) -> None:
        try:
            self.ensure_translation_loaded(allow_download=False)
        except Exception as exc:
            logger.info(
                "Model not preloaded (%s). It will load on the first translation request.",
                exc,
            )

    # ------------------------------------------------------------------ inference
    def run_inference(self, fn: Callable[[Any, Any, Any, str], Any]) -> Any:
        """
        Run fn(tokenizer, processor, model, device) serialized under the
        inference lock (CPU generate() is not thread-safe; classroom load is
        sequential anyway).
        """
        with self._infer_lock:
            rt = self._translation
            if rt.status != ModelStatus.READY or rt.model is None:
                raise RuntimeError("Translation model is not loaded")
            return fn(rt.tokenizer, rt.processor, rt.model, rt.device)

    # ------------------------------------------------------------------ metadata
    def _record_metadata(self, rt: _TranslationRuntime) -> None:
        """Best-effort persistence of load status (DB problems are non-fatal)."""
        try:
            with SessionLocal() as db:
                row = db.query(ModelMetadata).filter_by(model_type="mt").first()
                if row is None:
                    row = ModelMetadata(model_type="mt", model_name=rt.model_id)
                    db.add(row)
                row.model_name = rt.model_id
                row.direction = TRANSLATION_DIRECTION
                row.status = rt.status
                row.device = rt.device
                row.detail = rt.detail or None
                row.loaded_at = (
                    datetime.now(timezone.utc) if rt.status == ModelStatus.READY else None
                )
                db.commit()
        except Exception:
            logger.exception("Could not update model_metadata table (non-fatal)")


def _build_indic_processor() -> Any:
    """
    Build the IndicProcessor (text normalization + language tagging) from the
    official IndicTransToolkit. Supports both package import layouts:
      - new (recommended):  pip install git+https://github.com/VarunGumma/IndicTransToolkit.git
                            -> from IndicTransToolkit import IndicProcessor
      - legacy module name: from IndicTransTokenizer import IndicProcessor
    """
    try:
        from IndicTransToolkit import IndicProcessor

        return IndicProcessor(inference=True)
    except ImportError:
        from IndicTransTokenizer import IndicProcessor

        return IndicProcessor(inference=True)


def _friendly_load_error(exc: Exception) -> str:
    """Translate common load failures into actionable teacher-facing messages."""
    text = str(exc)
    lowered = text.lower()
    if (
        "restricted" in lowered
        or "must have access" in lowered
        or "log in" in lowered
        or "401" in lowered
        or "403" in lowered
    ):
        return (
            "The model repository requires a FREE Hugging Face account and "
            "one-time acceptance of the model conditions. Open the model page, "
            "click to request/accept access (instant), then put your READ token "
            "in backend/.env as HF_TOKEN=... and retry. See README section "
            "'AI model setup'."
        )
    if "connection" in lowered or "timed out" in lowered or "offline" in lowered or "max retries" in lowered:
        return (
            "Model not in local cache and the one-time download failed "
            "(no internet). Connect to the internet once, then retry - "
            "afterwards everything runs offline."
        )
    return f"Model load failed: {text}"


# Process-wide singleton
model_manager = ModelManager()

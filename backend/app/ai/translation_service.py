"""
Hindi -> Santali (Ol Chiki) machine translation service.

REAL local inference with AI4Bharat IndicTrans2 (Indic->Indic distilled model).
No Google Translate, no OpenAI, no paid/cloud API - inference runs on this
device. The very first model download needs internet once; afterwards the
model lives in backend/model_cache/hf and everything is offline.

HONESTY RULE (SIH):
Every output of this service is AI-GENERATED and must be treated as
REQUIRES_LANGUAGE_VALIDATION until a native Santali speaker reviews it.
"""

import logging
import time

from app.ai.model_manager import model_manager
from app.config import settings

logger = logging.getLogger(__name__)

SOURCE_LANG = "hin_Deva"
TARGET_LANG = "sat_Olck"
MAX_LINES = 10
MAX_LINE_CHARS = 300


class TranslationModelError(Exception):
    """Domain error carrying a teacher-facing message + suggested HTTP status."""

    def __init__(self, user_message: str, suggested_status: int = 503):
        super().__init__(user_message)
        self.user_message = user_message
        self.suggested_status = suggested_status


def _split_lines(text: str) -> list[str]:
    """Split input into non-empty lines (IndicTrans2 works best per sentence)."""
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        raise TranslationModelError("Please enter some Hindi text to translate.", 400)
    if len(lines) > MAX_LINES:
        raise TranslationModelError(
            f"Please translate up to {MAX_LINES} lines at a time.", 400
        )
    for line in lines:
        if len(line) > MAX_LINE_CHARS:
            raise TranslationModelError(
                f"Each line can have up to {MAX_LINE_CHARS} characters. "
                "Please translate shorter sentences.", 400
            )
    return lines


def translate_text(text: str) -> dict:
    """
    Translate Hindi text to Santali (Ol Chiki) using the local IndicTrans2 model.

    Returns {"translated_text", "latency_ms", "model"}.
    Raises TranslationModelError with a teacher-facing message on any failure.
    """
    started = time.perf_counter()
    lines = _split_lines(text)

    # Lazy, thread-safe, load-once (may download once if not cached)
    try:
        model_manager.ensure_translation_loaded(allow_download=True)
    except TranslationModelError:
        raise
    except Exception as exc:
        raise TranslationModelError(
            "The translation model is not available right now. "
            "See the Model Status panel for details.",
            503,
        ) from exc

    def _run(tokenizer, processor, model, device):
        import torch  # lazy import

        # 1) IndicProcessor: Unicode normalization + source language tagging
        processed = processor.preprocess_batch(
            lines, src_lang=SOURCE_LANG, tgt_lang=TARGET_LANG
        )
        # 2) Tokenize with the model repo's custom tokenizer (trust_remote_code)
        encoded = tokenizer(
            processed,
            truncation=True,
            padding="longest",
            return_tensors="pt",
            return_attention_mask=True,
        )
        encoded = encoded.to(device)
        # 3) Beam-search generation on CPU
        with torch.no_grad():
            generated = model.generate(
                **encoded,
                use_cache=True,
                min_length=0,
                max_length=settings.MT_MAX_LENGTH,
                num_beams=settings.MT_NUM_BEAMS,
                num_return_sequences=1,
            )
        # 4) Decode target tokens
        with tokenizer.as_target_tokenizer():
            decoded = tokenizer.batch_decode(
                generated.detach().cpu().tolist(),
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )
        # 5) Strip language tags / postprocess into clean Ol Chiki text
        result = processor.postprocess_batch(decoded, lang=TARGET_LANG)
        if isinstance(result, str):
            result = [result]
        return [str(item) for item in result]

    try:
        translated_lines = model_manager.run_inference(_run)
    except TranslationModelError:
        raise
    except Exception as exc:
        logger.exception("Translation inference failed")
        raise TranslationModelError(
            "Translation failed on this device. Please try again; if it keeps "
            "failing, check the Model Status panel.", 500
        ) from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "Translated %d line(s) -> %d Ol Chiki line(s) in %d ms",
        len(lines), len(translated_lines), latency_ms,
    )
    return {
        "translated_text": "\n".join(translated_lines),
        "latency_ms": latency_ms,
        "model": settings.MT_MODEL_ID,
    }

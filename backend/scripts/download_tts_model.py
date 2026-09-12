"""
ONE-TIME setup: download the offline Santali TTS model (Piper-format VITS).

Run from the backend/ folder (venv active, internet ON for this one step):

    python scripts\\download_tts_model.py

- Downloads the PUBLIC voice `Ashraf01k/vernacular-pedagogy-santhali`
  (no HF token needed, no account needed) into backend\\model_cache\\tts.
  Only the voice files (~60 MB) are fetched - not the repo's translation
  bundle.
- After this single download, Santali TTS works with Wi-Fi completely OFF.
- Safe to run again: an already-cached model is reused, never re-downloaded.

The translation cache (backend\\model_cache\\hf) and the ASR cache
(backend\\model_cache\\asr) are NOT touched.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # backend/

from app.ai.tts_service import TTSModelError, tts_service  # noqa: E402
from app.config import settings  # noqa: E402

WARMUP_TEXT = "ᱥᱟᱱᱛᱟᱲᱤ ᱯᱟᱹᱨᱥᱤ"  # "Santali language" - real Ol Chiki phrase


def main() -> int:
    print("=" * 60)
    print("RootVerse - one-time Santali TTS model download")
    print("=" * 60)
    print(f"Model     : {tts_service.model_label}")
    print(f"Voice file: {settings.TTS_MODEL_FILE} (~60 MB)")
    print(f"Cache dir : {settings.tts_model_path}")
    print()

    if tts_service.is_downloaded():
        print("Model is already cached - nothing to download.")
    else:
        print("Downloading (~60 MB; one-time, public repo)...")
        try:
            path = tts_service.download_model()
        except TTSModelError as exc:
            print(f"\nFAILED: {exc.user_message}")
            return 1
        print(f"Downloaded/cached at: {path}")

    print("\nLoading model + running a warm-up synthesis...")
    started = time.perf_counter()
    try:
        tts_service.ensure_model_loaded(allow_download=False)
        result = tts_service.synthesize_to_file(WARMUP_TEXT)
    except TTSModelError as exc:
        print(f"\nFAILED during load/warm-up: {exc.user_message}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\nFAILED during load/warm-up: {exc}")
        return 1

    print(f"Loaded in {time.perf_counter() - started:.1f}s.")
    print()
    print("Santali text : " + WARMUP_TEXT)
    print(f"Model        : {result['model']}")
    print(f"Latency      : {result['latency_ms']} ms (audio {result['duration_sec']}s)")
    print(f"Audio        : {result['audio_path']}")
    print()
    print("SUCCESS - Santali TTS is now available offline.")
    print("You can turn Wi-Fi OFF now; every later request runs locally")
    print("from backend\\model_cache\\tts.")
    print()
    print("Next test: python scripts\\tts_demo.py --text \"<Santali Ol Chiki text>\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())

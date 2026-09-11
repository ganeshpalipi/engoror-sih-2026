"""
ONE-TIME setup: download the offline Hindi ASR model (faster-whisper).

Run from the backend/ folder (venv active, internet ON for this one step):

    python scripts\\download_asr_model.py

- Downloads the PUBLIC model `Systran/faster-whisper-<size>` (no HF token
  needed, no account needed) into backend\\model_cache\\asr.
- After this single download, ASR works with Wi-Fi completely OFF.
- Safe to run again: an already-cached model is reused, never re-downloaded.

The IndicTrans2 translation cache (backend\\model_cache\\hf) is NOT touched.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # backend/

import numpy as np  # noqa: E402  (comes with faster-whisper)

from app.ai.asr_service import ASRModelError, asr_service  # noqa: E402
from app.config import settings  # noqa: E402


def main() -> int:
    print("=" * 60)
    print("RootVerse - one-time ASR model download (faster-whisper)")
    print("=" * 60)
    print(f"Model     : {asr_service.repo_id}")
    print(f"Cache dir : {settings.asr_model_path}")
    print()

    if asr_service.is_downloaded() and asr_service.local_model_path() is not None:
        print("Model is already cached - nothing to download.")
    else:
        print("Downloading (~0.5 GB for 'small'; one-time, public repo)...")
        try:
            path = asr_service.download_model()
        except ASRModelError as exc:
            print(f"\nFAILED: {exc.user_message}")
            return 1
        print(f"Downloaded/cached at: {path}")

    print("\nLoading model + running a 1-second warm-up check...")
    started = time.perf_counter()
    try:
        asr_service.ensure_model_loaded(allow_download=False)
        silence = np.zeros(16000, dtype="float32")  # 1 s of silence
        import io

        from faster_whisper.audio import decode_audio  # noqa: F401  (engine check)

        # Warm-up uses the same inference entry point as the API.
        asr_service.transcribe_bytes(_silence_wav_bytes())
    except ASRModelError as exc:
        print(f"\nFAILED during load/warm-up: {exc.user_message}")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\nFAILED during load/warm-up: {exc}")
        return 1

    print(f"Warm-up OK (loaded in {time.perf_counter() - started:.1f}s).")
    print()
    print("SUCCESS - you can now turn Wi-Fi OFF. Speech recognition is")
    print("fully offline and stored in backend\\model_cache\\asr.")
    print("Next test: python scripts\\asr_demo.py --file <hindi-audio-file>")
    return 0


def _silence_wav_bytes() -> bytes:
    """1 second of silent 16 kHz mono WAV (stdlib only, no ffmpeg needed)."""
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(np.zeros(16000, dtype="int16").tobytes())
    return buf.getvalue()


if __name__ == "__main__":
    sys.exit(main())

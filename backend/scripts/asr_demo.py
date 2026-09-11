"""
Offline Hindi ASR demo: audio file -> Hindi (Devanagari) text.

Run from the backend/ folder (venv active):

    python scripts\\asr_demo.py --file path\\to\\recording.wav
    python scripts\\asr_demo.py --file path\\to\\recording.webm --language hi

Supported audio: WAV, WebM/Opus (browser recordings), MP3, M4A, OGG.
Works fully offline once `python scripts\\download_asr_model.py` has run once.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # backend/

from app.ai.asr_service import ASRModelError, asr_service  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="RootVerse offline Hindi ASR demo")
    parser.add_argument("--file", required=True, help="Path to a Hindi audio file")
    parser.add_argument(
        "--language",
        default="",
        help="'hi' (default), or 'auto' to let Whisper detect",
    )
    args = parser.parse_args()

    audio_path = Path(args.file)
    if not audio_path.is_file():
        print(f"Audio file not found: {audio_path}")
        return 1

    print("=" * 60)
    print("RootVerse - offline Hindi ASR (faster-whisper, local CPU)")
    print("=" * 60)
    print(f"File  : {audio_path.name}  ({audio_path.stat().st_size / 1024:.0f} KB)")
    print("Loading model from local cache (no download)...")
    try:
        asr_service.ensure_model_loaded(allow_download=False)
        result = asr_service.transcribe_bytes(
            audio_path.read_bytes(), language=args.language or None
        )
    except ASRModelError as exc:
        print(f"\nFAILED: {exc.user_message}")
        return 1

    print("-" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("-" * 60)
    if result["text"]:
        print(f"Hindi text: {result['text']}")
    else:
        print("No speech was detected in this file.")
    print(f"Latency   : {result['latency_ms']} ms for {result['duration_sec']}s audio")
    print("(Transcript is AI-generated - verify before classroom use.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

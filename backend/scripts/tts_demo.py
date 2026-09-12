"""
Offline Santali TTS demo (Phase 4).

Run from the backend/ folder (venv active; Wi-Fi can be OFF):

    python scripts\\tts_demo.py --text "ᱟᱢᱟᱜ ᱯᱚᱛᱚᱵ ᱠᱚᱞᱚᱢ ᱟᱹᱜᱩᱭ ᱢᱮ"
    python scripts\\tts_demo.py                # uses the built-in sample text

- Loads ONLY from the local cache when OFFLINE_MODE=true (the default) -
  it never downloads. If the voice is missing it prints the exact fix.
- Synthesizes Santali speech and saves a WAV into backend/generated_files/.
- Prints model, text, sample rate, latency, output path and offline status.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # backend/

from app.ai.tts_service import TTSModelError, tts_service  # noqa: E402
from app.config import settings  # noqa: E402

# Real Santali (Ol Chiki) sample sentence - "bring your book and pen".
SAMPLE_TEXT = "ᱟᱢᱟᱜ ᱯᱚᱛᱚᱵ ᱠᱚᱞᱚᱢ ᱟᱹᱜᱩᱭ ᱢᱮ"


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline Santali TTS demo")
    parser.add_argument(
        "--text",
        default=SAMPLE_TEXT,
        help="Santali text in Ol Chiki script (default: a sample sentence)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("RootVerse - offline Santali TTS demo")
    print("=" * 60)
    print(f"Model     : {tts_service.model_label}")
    print(f"Cache dir : {settings.tts_model_path}")
    print(f"Offline   : {settings.OFFLINE_MODE}")
    print()

    if not tts_service.is_downloaded():
        print("The Santali TTS model is not downloaded yet.")
        print("Connect to the internet ONCE and run:")
        print("    python scripts\\download_tts_model.py")
        print("Then turn Wi-Fi OFF and re-run this demo.")
        return 1

    try:
        result = tts_service.synthesize_to_file(args.text)
    except TTSModelError as exc:
        print(f"FAILED: {exc.user_message}")
        return 1

    print("Santali text : " + args.text)
    if result["tts_input_text"] != args.text:
        print("Spoken as    : " + result["tts_input_text"])
    if result["unsupported_chars_removed"]:
        print(
            "Removed chars: "
            + " ".join(result["unsupported_chars_removed"])
            + " (not in the voice vocabulary)"
        )
    print(f"Model        : {result['model']}")
    print(f"Sample rate  : {result['sample_rate']} Hz")
    print(f"Latency      : {result['latency_ms']} ms (audio {result['duration_sec']}s, RTF {result['rtf']})")
    print(f"Audio        : {result['audio_path']}")
    print(f"Offline      : {str(settings.OFFLINE_MODE).lower()}")
    print()
    print("Play it (PowerShell):  Start-Process '" + result["audio_path"] + "'")
    print()
    print("NOTE: AI-generated Santali speech - requires native-speaker")
    print("validation before classroom use.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

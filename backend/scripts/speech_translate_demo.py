"""
Full Phase 3 pipeline demo: Hindi audio -> Hindi text -> Santali (Ol Chiki).

Run from the backend/ folder (venv active):

    python scripts\\speech_translate_demo.py --file path\\to\\recording.wav

Step 1 (ASR) is the new Phase 3 offline faster-whisper service.
Step 2 (translation) REUSES the existing Phase 2 IndicTrans2 service -
there is no second translation implementation anywhere in this project.

Works fully offline once BOTH models have been downloaded one time
(`scripts\\download_asr_model.py` + the IndicTrans2 setup from Phase 2).

NOTE: Santali output is AI-GENERATED - REQUIRES NATIVE-SPEAKER VALIDATION.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # backend/

from app.ai.asr_service import ASRModelError, asr_service  # noqa: E402
from app.ai import translation_service  # noqa: E402


def _ensure_tables() -> None:
    """Same idempotent create_all the server lifespan does, so this demo also
    works before the first `uvicorn` boot (e.g. on a fresh machine)."""
    import app.models  # noqa: F401  (registers all ORM tables)
    from app.database import Base, engine

    Base.metadata.create_all(bind=engine)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="RootVerse speech -> Hindi text -> Santali (Ol Chiki) demo"
    )
    parser.add_argument("--file", required=True, help="Path to a Hindi audio file")
    parser.add_argument("--language", default="", help="'hi' (default) or 'auto'")
    args = parser.parse_args()

    audio_path = Path(args.file)
    if not audio_path.is_file():
        print(f"Audio file not found: {audio_path}")
        return 1

    print("=" * 60)
    print("RootVerse - speech -> Hindi -> Santali (Ol Chiki), all local")
    print("=" * 60)
    print(f"Audio file: {audio_path.name}")

    _ensure_tables()

    # ---- Step 1: offline ASR -------------------------------------------
    print("\n[1/2] Offline Hindi ASR (faster-whisper, local CPU)...")
    try:
        asr = asr_service.transcribe_bytes(
            audio_path.read_bytes(), language=args.language or None
        )
    except ASRModelError as exc:
        print(f"ASR FAILED: {exc.user_message}")
        return 1

    hindi_text = asr["text"]
    print(f"    Heard : {hindi_text or '(no speech detected)'}")
    print(f"    ASR   : {asr['latency_ms']} ms for {asr['duration_sec']}s audio "
          f"({asr['model']})")
    if not hindi_text:
        print("\nNothing to translate - record a clear Hindi sentence.")
        return 1

    # ---- Step 2: EXISTING Phase 2 translation service -------------------
    print("\n[2/2] Hindi -> Santali via the existing IndicTrans2 service...")
    try:
        tr = translation_service.translate_text(hindi_text)
    except translation_service.TranslationModelError as exc:
        print(f"TRANSLATION FAILED: {exc.user_message}")
        print("(ASR itself worked - check the Model Status panel / HF_TOKEN "
              "for the translation model.)")
        return 1

    print("-" * 60)
    print("Teacher speech  : (microphone audio)")
    print(f"Hindi (ASR)     : {hindi_text}")
    print(f"Santali (Ol Chiki): {tr['translated_text']}")
    print("-" * 60)
    print(f"Latency: ASR {asr['latency_ms']} ms + translation "
          f"{tr['latency_ms']} ms")
    print("NOTE: AI-generated Santali - REQUIRES NATIVE-SPEAKER VALIDATION.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

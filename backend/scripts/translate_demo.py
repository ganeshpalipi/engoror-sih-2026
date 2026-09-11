"""
Real local translation sanity check: Hindi -> Santali (Ol Chiki).

Run from the backend/ folder (venv active):
    python scripts/translate_demo.py

The first run loads/downloads the model (~1.2 GB, one-time internet);
afterwards it is fully offline.

NOTE: output is AI-GENERATED and REQUIRES NATIVE-SPEAKER VALIDATION.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # backend/

from app.ai import translation_service  # noqa: E402

SENTENCES = [
    "अपनी किताब खोलो।",
    "एक से दस तक गिनो।",
    "ध्यान से सुनो।",
    "अपना नाम लिखो।",
]


def main() -> None:
    print("=" * 56)
    print("RootVerse - real Hindi -> Santali (Ol Chiki) local inference")
    print("=" * 56)
    text = "\n".join(SENTENCES)
    print("Loading model (first run downloads ~1.2 GB once)...")
    started = time.perf_counter()
    result = translation_service.translate_text(text)
    print(f"\nFinished in {result['latency_ms']} ms  (model: {result['model']})")
    print("-" * 56)
    for src, out in zip(SENTENCES, result["translated_text"].split("\n")):
        print(f"Hindi   : {src}")
        print(f"Santali : {out}")
        print("-" * 56)
    print("NOTE: AI-generated output - REQUIRES NATIVE-SPEAKER VALIDATION.")


if __name__ == "__main__":
    main()

"""
Pytest configuration for RootVerse.

Makes `backend/app` importable and points the test run at a separate test
database so the real rootverse.db is never touched.
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent  # RootVerse/
BACKEND_DIR = ROOT_DIR / "backend"

# Make `app.*` modules importable
sys.path.insert(0, str(BACKEND_DIR))

# Test settings - MUST be set before app modules are imported.
# We FORCE these values (not setdefault) so an ambient DATABASE_URL from the
# machine can never redirect tests at a real database.
os.environ["DATABASE_URL"] = f"sqlite:///{(BACKEND_DIR / 'test_rootverse.db').as_posix()}"
os.environ["DEBUG"] = "false"
os.environ["PRELOAD_MODEL_ON_STARTUP"] = "false"  # unit tests never load AI models
os.environ.setdefault("MODEL_CACHE_DIR", str(BACKEND_DIR / "model_cache"))
os.environ.setdefault("GENERATED_FILES_DIR", str(BACKEND_DIR / "generated_files"))

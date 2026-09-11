"""
Central logging setup for RootVerse.

Every module should use:  logger = logging.getLogger(__name__)
Configuration happens once, when app.main is imported.
"""

import logging
import sys

from app.config import settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging() -> None:
    """Configure root logging once per process (idempotent)."""
    root = logging.getLogger()
    if root.handlers:  # already configured (e.g. app imported twice in tests)
        return

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.setLevel(level)
    root.addHandler(handler)

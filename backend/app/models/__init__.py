"""
ORM models package.

Importing this package registers every table on the SQLAlchemy Base, so
`Base.metadata.create_all()` (app.main lifespan) sees all of them.
"""

from app.models.classroom_phrase import REQUIRES_LANGUAGE_VALIDATION, ClassroomPhrase
from app.models.fln_lesson import FlnLesson
from app.models.model_metadata import ModelMetadata
from app.models.translation_history import TranslationHistory

__all__ = [
    "ClassroomPhrase",
    "FlnLesson",
    "ModelMetadata",
    "TranslationHistory",
    "REQUIRES_LANGUAGE_VALIDATION",
]

"""
ORM models package.

Importing this package registers every table on the SQLAlchemy Base, so
`Base.metadata.create_all()` (app.main lifespan) sees all of them.
"""

from app.models.asr_transcription import AsrTranscription
from app.models.classroom_phrase import REQUIRES_LANGUAGE_VALIDATION, ClassroomPhrase
from app.models.flashcard import Flashcard
from app.models.fln_lesson import FlnLesson
from app.models.model_metadata import ModelMetadata
from app.models.translation_history import TranslationHistory

__all__ = [
    "AsrTranscription",
    "ClassroomPhrase",
    "Flashcard",
    "FlnLesson",
    "ModelMetadata",
    "TranslationHistory",
    "REQUIRES_LANGUAGE_VALIDATION",
]

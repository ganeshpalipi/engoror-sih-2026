"""
Phase 5 content seeding + schema upgrade (idempotent, additive only).

What it does (safe to run on every startup, and safe on an EXISTING
Phase 1-4 database — no row is ever deleted):

1. ensure_phase5_schema(): adds the new `category` / `skill` columns to an
   existing fln_lessons table via ALTER TABLE (fresh databases already get
   them from create_all). Nothing else in the schema is touched.
2. seed_phase5_content():
   - upgrades the four legacy Phase 1-2 seed lessons in place with a
     category + skill (matched by their English title),
   - inserts the Phase 5 lesson bank (skipping titles that already exist),
   - inserts the new classroom phrase pack rows (skipping exact Hindi
     duplicates),
   - inserts the flashcard pack into the new flashcards table.

SIH language rule: NO Santali text is written here. Every Santali column is
the placeholder REQUIRES_LANGUAGE_VALIDATION until the existing IndicTrans2
service translates it on demand (validation_status -> AI_GENERATED).
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models import ClassroomPhrase, Flashcard, FlnLesson
from app.services.content_data import (
    FLASHCARD_PACK,
    LEGACY_LESSON_CATEGORIES,
    LESSON_BANK,
    PHRASE_PACK_ADDITIONS,
    PLACEHOLDER,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema upgrade (existing databases)
# ---------------------------------------------------------------------------

def ensure_phase5_schema(engine) -> dict[str, bool]:
    """
    Add Phase 5 columns to existing tables when they are missing.

    Uses plain ALTER TABLE through the SQLAlchemy connection so it works on
    the user's existing rootverse.db without any migration tool. Idempotent:
    columns are only added when the inspector reports them missing.
    """
    added: dict[str, bool] = {}
    try:
        inspector = inspect(engine)
        lesson_columns = {col["name"] for col in inspector.get_columns("fln_lessons")}
        with engine.begin() as conn:
            if "category" not in lesson_columns:
                conn.execute(text(
                    "ALTER TABLE fln_lessons ADD COLUMN category VARCHAR(60) "
                    "NOT NULL DEFAULT ''"
                ))
                added["fln_lessons.category"] = True
            if "skill" not in lesson_columns:
                conn.execute(text(
                    "ALTER TABLE fln_lessons ADD COLUMN skill VARCHAR(80) "
                    "NOT NULL DEFAULT ''"
                ))
                added["fln_lessons.skill"] = True
    except Exception:  # non-fatal: a locked/odd database must not stop boot
        logger.exception("Phase 5 schema upgrade failed (non-fatal)")
        return added
    if added:
        logger.info("Phase 5 schema upgrade applied: %s", sorted(added))
    return added


# ---------------------------------------------------------------------------
# Content seeding
# ---------------------------------------------------------------------------

def _upgrade_legacy_lessons(db: Session) -> int:
    """Assign category/skill to pre-Phase 5 lesson rows (matched by title)."""
    updated = 0
    rows = db.query(FlnLesson).filter(FlnLesson.category == "").all()
    for row in rows:
        mapping = LEGACY_LESSON_CATEGORIES.get(row.title_english)
        if mapping:
            row.category, row.skill = mapping
            updated += 1
    return updated


def _seed_lesson_bank(db: Session) -> int:
    """Insert Phase 5 lessons whose English title is not already stored."""
    existing_titles = {
        row.title_english for row in db.query(FlnLesson.title_english).all()
    }
    added = 0
    for spec in LESSON_BANK:
        if spec.title_english in existing_titles:
            continue
        db.add(
            FlnLesson(
                title_hindi=spec.title_hindi,
                title_english=spec.title_english,
                class_level=spec.class_level,
                subject=spec.subject,
                category=spec.category,
                skill=spec.skill,
                hindi_text=spec.hindi_text,
                learning_objective=spec.learning_objective,
                activity_instruction=spec.activity_instruction,
                santhali_ol_chiki=PLACEHOLDER,
                validation_status="PLACEHOLDER",
                audio_path=None,
            )
        )
        added += 1
    return added


def _seed_phrase_pack(db: Session) -> int:
    """Insert Phase 5 phrases whose exact Hindi text is not already stored."""
    existing_hindi = {
        row.hindi for row in db.query(ClassroomPhrase.hindi).all()
    }
    added = 0
    for spec in PHRASE_PACK_ADDITIONS:
        if spec["hindi"] in existing_hindi:
            continue
        db.add(
            ClassroomPhrase(
                hindi=spec["hindi"],
                english=spec["english"],
                category=spec["category"],
                santhali_ol_chiki=PLACEHOLDER,
                validation_status="PLACEHOLDER",
                audio_path=None,
            )
        )
        added += 1
    return added


def _seed_flashcards(db: Session) -> int:
    """Fill the flashcards table (skip any topic+word pair already present)."""
    existing_pairs = {
        (row.topic, row.hindi_word)
        for row in db.query(Flashcard.topic, Flashcard.hindi_word).all()
    }
    added = 0
    for spec in FLASHCARD_PACK:
        if (spec.topic, spec.hindi_word) in existing_pairs:
            continue
        db.add(
            Flashcard(
                topic=spec.topic,
                hindi_word=spec.hindi_word,
                english_word=spec.english_word,
                visual_emoji=spec.visual_emoji,
                image_key=spec.image_key,
                santhali_ol_chiki=PLACEHOLDER,
                validation_status="PLACEHOLDER",
                audio_path=None,
            )
        )
        added += 1
    return added


def seed_phase5_content() -> dict[str, int]:
    """
    Idempotent Phase 5 content seeding.

    Returns the number of rows added/updated per group so callers (lifespan,
    prepare_content.py, tests) can log or assert on it. Failures never stop
    the server from booting.
    """
    from app.database import SessionLocal

    counts: dict[str, int] = {}
    try:
        with SessionLocal() as db:
            counts["lessons_updated"] = _upgrade_legacy_lessons(db)
            counts["lessons_added"] = _seed_lesson_bank(db)
            counts["phrases_added"] = _seed_phrase_pack(db)
            counts["flashcards_added"] = _seed_flashcards(db)
            db.commit()
        if any(counts.values()):
            logger.info("Phase 5 content seeding: %s", counts)
    except Exception:  # non-fatal, same policy as seed_if_empty()
        logger.exception("Phase 5 content seeding failed (non-fatal)")
    return counts

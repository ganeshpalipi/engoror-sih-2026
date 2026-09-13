"""Database + seed tests: tables exist, safe seed data present, history persists."""

import pytest

from app.database import SessionLocal
from app.models import ClassroomPhrase, Flashcard, FlnLesson, ModelMetadata, TranslationHistory


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:  # lifespan: create_all + seed
        yield test_client


def test_seed_data_present(client):
    with SessionLocal() as db:
        assert db.query(ClassroomPhrase).count() >= 8
        # Phase 5: lesson bank grew from the 4 legacy seed rows to 18
        # (10 literacy + 8 numeracy categories), and flashcards were added.
        assert db.query(FlnLesson).count() == 18
        assert db.query(FlnLesson).filter(FlnLesson.category != "").count() == 18
        flashcards = db.query(Flashcard).all()
        assert len(flashcards) == 40
        assert {c.topic for c in flashcards} == {
            "numbers", "colours", "animals", "fruits", "classroom-objects", "shapes",
        }
        metadata_row = db.query(ModelMetadata).filter_by(model_type="mt").first()
        assert metadata_row is not None
        assert metadata_row.status in {"not_loaded", "ready"}


def test_phase5_seed_is_idempotent(client):
    """Running the Phase 5 seeding twice must not duplicate anything."""
    from app.services.content_seed import seed_phase5_content

    counts = seed_phase5_content()
    assert counts["lessons_added"] == 0
    assert counts["phrases_added"] == 0
    assert counts["flashcards_added"] == 0


def test_seed_santali_fields_are_placeholders_only(client):
    """SIH rule: seed data must never contain invented Santali text."""
    with SessionLocal() as db:
        for phrase in db.query(ClassroomPhrase).all():
            assert phrase.santhali_ol_chiki == "REQUIRES_LANGUAGE_VALIDATION"
            assert phrase.validation_status == "PLACEHOLDER"
        for lesson in db.query(FlnLesson).all():
            assert lesson.santhali_ol_chiki == "REQUIRES_LANGUAGE_VALIDATION"
            assert lesson.validation_status == "PLACEHOLDER"


def test_translation_history_persists(client):
    # NOTE: "STORAGE_TEST_OUTPUT" is a storage-layer fixture value,
    # NOT a claimed Santali translation.
    with SessionLocal() as db:
        row = TranslationHistory(
            source_language="hin_Deva",
            target_language="sat_Olck",
            input_text="परीक्षण वाक्य",
            translated_text="STORAGE_TEST_OUTPUT",
            latency_ms=42,
            success=True,
            model_name="storage-test",
        )
        db.add(row)
        db.commit()
        assert row.id is not None

        fetched = db.get(TranslationHistory, row.id)
        assert fetched is not None
        assert fetched.success is True
        assert fetched.latency_ms == 42
        assert fetched.created_at is not None

        db.delete(fetched)
        db.commit()
        assert db.get(TranslationHistory, row.id) is None

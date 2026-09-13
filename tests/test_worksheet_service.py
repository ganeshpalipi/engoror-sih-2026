"""
Phase 5 worksheet generator tests.

The translation model is NOT required: Santali content is written directly
into the database (test fixture values) or the MT call is monkeypatched.
Covers: deterministic generation, the six worksheet types, validation,
Hindi-only fallback when MT is unavailable, file serving safety, and the
seed-upgrade behavior on a legacy-style database.
"""

import re
from pathlib import Path

import pytest

from app.ai import translation_service
from app.config import settings
from app.database import SessionLocal
from app.models import ClassroomPhrase, Flashcard, FlnLesson
from app.services import worksheet_service
from app.services.content_seed import ensure_phase5_schema, seed_phase5_content


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def translated_flashcards():
    """Fill the flashcard pack with test fixture Santali values, then restore."""
    with SessionLocal() as db:
        cards = db.query(Flashcard).all()
        saved = [(c.id, c.santhali_ol_chiki, c.validation_status) for c in cards]
        for card in cards:
            # deterministic per-word fixture value (NOT a language claim)
            card.santhali_ol_chiki = f"TEST_OL_CHIKI_{card.id}"
            card.validation_status = "AI_GENERATED"
        db.commit()
    yield
    with SessionLocal() as db:
        for card_id, text, status in saved:
            row = db.get(Flashcard, card_id)
            if row is not None:
                row.santhali_ol_chiki = text
                row.validation_status = status
        db.commit()


def _generated_html_files() -> list[Path]:
    return sorted(
        (settings.generated_files_path / "worksheets").glob("ws_*.html"),
        key=lambda p: p.stat().st_mtime,
    )


@pytest.fixture(autouse=True)
def _cleanup_worksheet_files():
    yield
    for path in _generated_html_files():
        path.unlink(missing_ok=True)


# ------------------------------------------------------------- API level


def test_worksheet_meta_endpoint(client):
    resp = client.get("/api/worksheets/meta")
    assert resp.status_code == 200
    data = resp.json()
    assert data["grades"] == [1, 2, 3]
    assert set(data["skills"]) == {"literacy", "numeracy"}
    assert data["counts"] == [5, 10]
    topic_slugs = {t["topic"] for t in data["topics"]}
    assert "animals" in topic_slugs and "numbers-1-10" in topic_slugs
    assert set(data["type_legend"].keys()) == {"A", "B", "C", "D", "E", "F"}


def test_generate_numeracy_worksheet(client):
    resp = client.post(
        "/api/worksheets/generate",
        json={"grade": 1, "skill": "numeracy", "topic": "numbers-1-10", "count": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["question_count"] == 5
    assert data["skill"] == "numeracy"
    assert data["types_included"], "worksheet must contain at least one type"
    assert set(data["types_included"]) <= {"A", "B", "C", "D", "E", "F"}
    assert data["html_url"].startswith("/api/worksheets/file/ws_")
    assert data["nipun_note"].startswith("Designed around")


def test_generate_literacy_worksheet_with_santali(client, translated_flashcards):
    resp = client.post(
        "/api/worksheets/generate",
        json={"grade": 2, "skill": "literacy", "topic": "animals", "count": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["question_count"] == 5
    assert data["santali_available"] is True
    assert data["validation_notice"] == "AI-generated — Requires native-speaker validation"


def test_worksheet_deterministic_for_same_seed(client, translated_flashcards):
    resp1 = client.post(
        "/api/worksheets/generate",
        json={"grade": 1, "skill": "literacy", "topic": "fruits", "count": 5, "seed": 42},
    )
    resp2 = client.post(
        "/api/worksheets/generate",
        json={"grade": 1, "skill": "literacy", "topic": "fruits", "count": 5, "seed": 42},
    )
    assert resp1.status_code == resp2.status_code == 200
    files = _generated_html_files()
    assert len(files) >= 2
    contents = [p.read_text(encoding="utf-8") for p in files[-2:]]
    assert contents[0] == contents[1], "same seed must produce an identical sheet"


def test_worksheet_validation_errors(client):
    resp = client.post(
        "/api/worksheets/generate",
        json={"grade": 7, "skill": "literacy", "topic": "animals", "count": 5},
    )
    assert resp.status_code == 422

    resp = client.post(
        "/api/worksheets/generate",
        json={"grade": 1, "skill": "literacy", "topic": "animals", "count": 7},
    )
    assert resp.status_code == 422

    resp = client.post(
        "/api/worksheets/generate",
        json={"grade": 1, "skill": "numeracy", "topic": "animals", "count": 5},
    )
    assert resp.status_code == 400
    assert "not a numeracy topic" in resp.json()["detail"]


def test_worksheet_hindi_only_fallback_when_mt_unavailable(client, monkeypatch):
    """Without the MT model the sheet is still generated - Hindi-only + notice."""

    def failing(text):
        raise translation_service.TranslationModelError("MT not available", 503)

    monkeypatch.setattr(translation_service, "translate_text", failing)
    resp = client.post(
        "/api/worksheets/generate",
        json={"grade": 1, "skill": "literacy", "topic": "animals", "count": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["santali_available"] is False
    assert data["validation_notice"] == ""


def test_worksheet_file_serving_whitelist(client, translated_flashcards):
    resp = client.post(
        "/api/worksheets/generate",
        json={"grade": 1, "skill": "literacy", "topic": "animals", "count": 5, "seed": 1},
    )
    filename = resp.json()["filename"]
    assert re.match(r"^ws_[0-9a-f]{32}\.html$", filename)

    page = client.get(f"/api/worksheets/file/{filename}")
    assert page.status_code == 200
    assert "text/html" in page.headers["content-type"]
    assert "RootVerse" in page.text
    # self-contained: Ol Chiki font embedded, no external requests
    assert "data:font/woff2;base64," in page.text
    assert "src=\"http" not in page.text and "href=\"http" not in page.text

    # download mode
    dl = client.get(f"/api/worksheets/file/{filename}", params={"download": 1})
    assert dl.status_code == 200
    assert "attachment" in dl.headers.get("content-disposition", "")


def test_worksheet_file_rejects_bad_names(client):
    assert client.get("/api/worksheets/file/../../etc/passwd").status_code == 404
    assert client.get("/api/worksheets/file/abc.html").status_code == 404
    assert client.get(
        "/api/worksheets/file/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.html"
    ).status_code == 404


# ---------------------------------------------------------- service level


def test_all_six_types_reachable_across_topics(client, translated_flashcards):
    """Across representative topics, all six worksheet types get used."""
    seen = set()
    for payload in [
        {"grade": 1, "skill": "numeracy", "topic": "numbers-1-10", "count": 10},
        {"grade": 2, "skill": "literacy", "topic": "animals", "count": 10},
        {"grade": 2, "skill": "numeracy", "topic": "patterns", "count": 5},
        {"grade": 3, "skill": "numeracy", "topic": "addition", "count": 5},
        {"grade": 2, "skill": "literacy", "topic": "sentences", "count": 10},
    ]:
        resp = client.post("/api/worksheets/generate", json={**payload, "seed": 7})
        assert resp.status_code == 200, payload
        seen.update(resp.json()["types_included"])
    assert seen == {"A", "B", "C", "D", "E", "F"}


def test_worksheet_html_contains_bilingual_sections(client, translated_flashcards):
    resp = client.post(
        "/api/worksheets/generate",
        json={"grade": 2, "skill": "literacy", "topic": "animals", "count": 10, "seed": 3},
    )
    filename = resp.json()["filename"]
    html = (settings.generated_files_path / "worksheets" / filename).read_text(
        encoding="utf-8"
    )
    assert "बिलिंगुअल वर्कशीट" in html
    assert "Answer Key" in html or "उत्तर कुंजी" in html
    assert "NIPUN" in html or "NIPUN Bharat" in html


def test_legacy_database_upgrade(tmp_path, monkeypatch):
    """
    An existing Phase 1-4 style database (fln_lessons without category/skill
    columns, 4 placeholder lessons) must be upgraded in place: columns added,
    legacy rows categorized, bank completed - with nothing deleted.
    """
    import sqlite3
    import sqlalchemy

    db_file = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_file)
    conn.execute(
        "CREATE TABLE fln_lessons (id INTEGER PRIMARY KEY, title_hindi VARCHAR(200),"
        " title_english VARCHAR(200), class_level INTEGER, subject VARCHAR(40),"
        " hindi_text TEXT, santhali_ol_chiki TEXT, validation_status VARCHAR(20),"
        " learning_objective TEXT, activity_instruction TEXT, audio_path VARCHAR(300),"
        " created_at DATETIME)"
    )
    conn.execute(
        "INSERT INTO fln_lessons (title_hindi, title_english, class_level, subject,"
        " hindi_text, santhali_ol_chiki, validation_status, learning_objective,"
        " activity_instruction) VALUES ('गिनती', 'Numbers: One to Ten', 1, 'numeracy',"
        " 'आज हम एक से दस तक गिनती सीखेंगे।', 'REQUIRES_LANGUAGE_VALIDATION',"
        " 'PLACEHOLDER', 'obj', 'act')"
    )
    conn.commit()
    conn.close()

    engine = sqlalchemy.create_engine(f"sqlite:///{db_file.as_posix()}")
    added = ensure_phase5_schema(engine)
    assert added.get("fln_lessons.category") is True
    assert added.get("fln_lessons.skill") is True

    # re-run must be a no-op
    assert ensure_phase5_schema(engine) == {}

    # create the new tables (flashcards etc.) without altering fln_lessons
    from app import database as app_database

    app_database.Base.metadata.create_all(bind=engine)

    # seeding against the upgraded schema completes the bank (monkeypatched
    # SessionLocal so no other database is touched)
    orig_sessionlocal = app_database.SessionLocal
    test_session = app_database.sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(app_database, "SessionLocal", test_session)
    try:
        counts = seed_phase5_content()
        assert counts["lessons_updated"] == 1
        assert counts["lessons_added"] == 17  # 18 bank - 1 legacy-matched title
        assert counts["flashcards_added"] == 40

        counts2 = seed_phase5_content()
        assert counts2 == {
            "lessons_updated": 0,
            "lessons_added": 0,
            "phrases_added": 0,
            "flashcards_added": 0,
        }
        with test_session() as db:
            rows = db.query(FlnLesson).all()
            assert len(rows) == 18
            legacy = next(r for r in rows if r.title_english == "Numbers: One to Ten")
            assert legacy.category == "numbers-1-10"
            assert legacy.santhali_ol_chiki == "REQUIRES_LANGUAGE_VALIDATION"
    finally:
        monkeypatch.setattr(app_database, "SessionLocal", orig_sessionlocal)

"""
Phase 5 endpoint tests: FLN lessons, classroom phrase pack, flashcards.

The heavy AI models are NOT required - translation and TTS are monkeypatched
(the same approach as the Phase 2-4 tests). These tests verify the HTTP
layer, honest validation statuses, the placeholder -> AI_GENERATED flow, and
that audio generation reuses the Phase 4 TTS service and whitelist endpoint.

Rows mutated by the translate/audio tests are restored afterwards so the
seed-policy tests stay valid on every run.
"""

import math
import struct
import wave
from pathlib import Path

import pytest

from app.ai import translation_service
from app.ai.tts_service import TTSModelError
from app.config import settings
from app.database import SessionLocal
from app.models import ClassroomPhrase, Flashcard, FlnLesson
from app.services.content_service import AI_GENERATED, PLACEHOLDER

SAMPLE_OL_CHIKI = "ᱟᱢᱟᱜ ᱯᱚᱛᱚᱵ ᱠᱚᱞᱚᱢ ᱟᱹᱜᱩᱭ ᱢᱮ"


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:  # lifespan: create_all + seed
        yield test_client


def _make_wav(path: Path, seconds: float = 0.3, rate: int = 16000) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        frames = b"".join(
            struct.pack(
                "<h",
                int(9000 * math.sin(2 * math.pi * 300 * i / rate)),
            )
            for i in range(int(rate * seconds))
        )
        wav.writeframes(frames)


@pytest.fixture()
def restore_lesson():
    """Reset a lesson's Phase 5 mutable fields after a test mutates it."""
    lesson_ids: list[int] = []

    def _mark(lesson_id: int) -> int:
        lesson_ids.append(lesson_id)
        return lesson_id

    yield _mark
    with SessionLocal() as db:
        for lesson_id in lesson_ids:
            row = db.get(FlnLesson, lesson_id)
            if row is not None:
                row.santhali_ol_chiki = PLACEHOLDER
                row.validation_status = "PLACEHOLDER"
                row.audio_path = None
        db.commit()


@pytest.fixture()
def restore_phrase():
    phrase_ids: list[int] = []

    def _mark(phrase_id: int) -> int:
        phrase_ids.append(phrase_id)
        return phrase_id

    yield _mark
    with SessionLocal() as db:
        for phrase_id in phrase_ids:
            row = db.get(ClassroomPhrase, phrase_id)
            if row is not None:
                row.santhali_ol_chiki = PLACEHOLDER
                row.validation_status = "PLACEHOLDER"
                row.audio_path = None
        db.commit()


@pytest.fixture()
def restore_flashcard():
    card_ids: list[int] = []

    def _mark(card_id: int) -> int:
        card_ids.append(card_id)
        return card_id

    yield _mark
    with SessionLocal() as db:
        for card_id in card_ids:
            row = db.get(Flashcard, card_id)
            if row is not None:
                row.santhali_ol_chiki = PLACEHOLDER
                row.validation_status = "PLACEHOLDER"
                row.audio_path = None
        db.commit()


@pytest.fixture()
def generated_wavs():
    created: list[Path] = []

    def _create(filename: str) -> str:
        path = settings.generated_files_path / filename
        _make_wav(path)
        created.append(path)
        return filename

    yield _create
    for path in created:
        path.unlink(missing_ok=True)


# ------------------------------------------------------------- FLN lessons


def test_lessons_list_contains_full_bank(client):
    resp = client.get("/api/fln/lessons")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 18
    subjects = {l["subject"] for l in data["lessons"]}
    assert subjects == {"literacy", "numeracy"}
    first = data["lessons"][0]
    for field in (
        "id", "title_hindi", "title_english", "category", "skill",
        "grade_level", "subject", "hindi_text", "santali_ol_chiki",
        "validation_status", "nipun_note",
    ):
        assert field in first


def test_lessons_filters(client):
    resp = client.get("/api/fln/lessons", params={"skill": "numeracy"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 8

    resp = client.get("/api/fln/lessons", params={"category": "animals"})
    data = resp.json()
    assert data["count"] >= 1
    assert all(l["category"] == "animals" for l in data["lessons"])

    resp = client.get("/api/fln/lessons", params={"grade": 2})
    assert resp.status_code == 200
    assert all(l["grade_level"] == 2 for l in resp.json()["lessons"])


def test_lesson_detail_and_404(client):
    resp = client.get("/api/fln/lessons/1")
    assert resp.status_code == 200
    assert resp.json()["id"] == 1

    resp = client.get("/api/fln/lessons/999999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_lesson_translate_success(client, monkeypatch, restore_lesson):
    def fake_translate(text):
        return {
            "translated_text": SAMPLE_OL_CHIKI,
            "latency_ms": 123,
            "model": "fake-mt",
        }

    monkeypatch.setattr(translation_service, "translate_text", fake_translate)
    lesson_id = restore_lesson(1)
    resp = client.post(f"/api/fln/lessons/{lesson_id}/translate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["lesson"]["santali_ol_chiki"] == SAMPLE_OL_CHIKI
    assert data["lesson"]["validation_status"] == AI_GENERATED
    assert data["translation_latency_ms"] == 123
    assert data["validation_notice"] == "AI-generated — Requires native-speaker validation"
    # persisted
    with SessionLocal() as db:
        row = db.get(FlnLesson, lesson_id)
        assert row.santhali_ol_chiki == SAMPLE_OL_CHIKI
        assert row.validation_status == AI_GENERATED


def test_lesson_translate_model_unavailable(client, monkeypatch, restore_lesson):
    def failing(text):
        raise translation_service.TranslationModelError(
            "The translation model is not downloaded yet.", 503,
        )

    monkeypatch.setattr(translation_service, "translate_text", failing)
    lesson_id = restore_lesson(1)
    resp = client.post(f"/api/fln/lessons/{lesson_id}/translate")
    assert resp.status_code == 503
    assert "not downloaded" in resp.json()["detail"].lower()
    # placeholder preserved (nothing faked)
    with SessionLocal() as db:
        row = db.get(FlnLesson, lesson_id)
        assert row.santhali_ol_chiki == PLACEHOLDER


def test_lesson_audio_without_santali_is_friendly_400(client, restore_lesson):
    lesson_id = restore_lesson(1)
    resp = client.post(f"/api/fln/lessons/{lesson_id}/audio")
    assert resp.status_code == 400
    assert "santali" in resp.json()["detail"].lower()


def test_lesson_audio_success_and_serving(client, monkeypatch, restore_lesson, generated_wavs):
    lesson_id = restore_lesson(1)
    with SessionLocal() as db:
        row = db.get(FlnLesson, lesson_id)
        row.santhali_ol_chiki = SAMPLE_OL_CHIKI
        row.validation_status = AI_GENERATED
        db.commit()

    calls = {"n": 0}

    def fake_tts(text):
        calls["n"] += 1
        filename = f"tts_{'a' * 32}.wav"
        generated_wavs(filename)
        return {
            "filename": filename,
            "audio_path": str(settings.generated_files_path / filename),
            "sample_rate": 16000,
            "duration_sec": 0.3,
            "latency_ms": 50,
            "rtf": 0.15,
            "model": "fake-tts",
            "input_text": text,
            "tts_input_text": text,
            "unsupported_chars_removed": "",
        }

    from app.ai import tts_service

    monkeypatch.setattr(tts_service.tts_service, "synthesize_to_file", fake_tts)

    resp = client.post(f"/api/fln/lessons/{lesson_id}/audio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["audio_url"].startswith("/api/tts/audio/tts_")
    assert data["cached"] is False
    assert data["validation_notice"].startswith("AI-generated")

    audio = client.get(data["audio_url"])
    assert audio.status_code == 200
    assert audio.headers["content-type"].startswith("audio/wav")

    # second call reuses the cached file (no new synthesis)
    resp2 = client.post(f"/api/fln/lessons/{lesson_id}/audio")
    assert resp2.status_code == 200
    assert resp2.json()["cached"] is True
    assert calls["n"] == 1


# ----------------------------------------------------------- phrase pack


def test_phrases_list_and_categories(client):
    resp = client.get("/api/phrases")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 13
    assert "instruction" in data["categories"]
    phrases = data["phrases"]
    hindi_texts = {p["hindi_text"] for p in phrases}
    # Phase 5 additions are present next to the Phase 1-2 seed
    assert "बैठ जाओ।" in hindi_texts
    assert "अपनी किताब खोलो।" in hindi_texts
    for field in ("id", "category", "hindi_text", "santali_ol_chiki", "validation_status"):
        assert field in phrases[0]


def test_phrases_category_filter(client):
    resp = client.get("/api/phrases", params={"category": "praise"})
    data = resp.json()
    assert data["count"] >= 1
    assert all(p["category"] == "praise" for p in data["phrases"])


def test_phrase_translate_success(client, monkeypatch, restore_phrase):
    def fake_translate(text):
        return {"translated_text": SAMPLE_OL_CHIKI, "latency_ms": 88, "model": "fake-mt"}

    monkeypatch.setattr(translation_service, "translate_text", fake_translate)
    phrase_id = restore_phrase(1)
    resp = client.post(f"/api/phrases/{phrase_id}/translate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["phrase"]["santali_ol_chiki"] == SAMPLE_OL_CHIKI
    assert data["phrase"]["validation_status"] == AI_GENERATED


def test_phrase_translate_offline_without_model(client, monkeypatch, restore_phrase):
    def failing(text):
        raise translation_service.TranslationModelError(
            "The Santali TTS/MT model is not in the local cache.", 503,
        )

    monkeypatch.setattr(translation_service, "translate_text", failing)
    phrase_id = restore_phrase(1)
    resp = client.post(f"/api/phrases/{phrase_id}/translate")
    assert resp.status_code == 503


def test_phrase_audio_flow(client, monkeypatch, restore_phrase, generated_wavs):
    phrase_id = restore_phrase(1)
    with SessionLocal() as db:
        row = db.get(ClassroomPhrase, phrase_id)
        row.santhali_ol_chiki = SAMPLE_OL_CHIKI
        row.validation_status = AI_GENERATED
        db.commit()

    def fake_tts(text):
        filename = f"tts_{'b' * 32}.wav"
        generated_wavs(filename)
        return {
            "filename": filename,
            "audio_path": str(settings.generated_files_path / filename),
            "sample_rate": 16000,
            "duration_sec": 0.3,
            "latency_ms": 45,
            "rtf": 0.15,
            "model": "fake-tts",
            "input_text": text,
            "tts_input_text": text,
            "unsupported_chars_removed": "",
        }

    from app.ai import tts_service

    monkeypatch.setattr(tts_service.tts_service, "synthesize_to_file", fake_tts)
    resp = client.post(f"/api/phrases/{phrase_id}/audio")
    assert resp.status_code == 200
    assert resp.json()["audio_url"].endswith(".wav")
    assert client.get(resp.json()["audio_url"]).status_code == 200


def test_phrase_404(client):
    resp = client.post("/api/phrases/999999/translate")
    assert resp.status_code == 404


# ------------------------------------------------------------- flashcards


def test_flashcards_list_and_topics(client):
    resp = client.get("/api/flashcards")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 40
    topics = {t["topic"]: t["count"] for t in data["topics"]}
    assert topics["numbers"] == 10
    assert topics["animals"] == 6
    card = data["flashcards"][0]
    for field in ("id", "topic", "hindi_word", "english_word", "visual_emoji",
                  "santali_ol_chiki", "validation_status"):
        assert field in card


def test_flashcards_topic_filter(client):
    resp = client.get("/api/flashcards", params={"topic": "fruits"})
    data = resp.json()
    assert data["count"] == 6
    assert all(c["topic"] == "fruits" for c in data["flashcards"])


def test_flashcards_local_visuals_only(client):
    """No card may reference a remote image - local assets only (SIH rule)."""
    resp = client.get("/api/flashcards")
    for card in resp.json()["flashcards"]:
        if card["image_key"]:
            assert "http" not in card["image_key"]
            assert "/" not in card["image_key"]  # a bare asset key, served locally


def test_flashcard_translate_and_audio(client, monkeypatch, restore_flashcard, generated_wavs):
    def fake_translate(text):
        return {"translated_text": SAMPLE_OL_CHIKI, "latency_ms": 40, "model": "fake-mt"}

    monkeypatch.setattr(translation_service, "translate_text", fake_translate)
    card_id = restore_flashcard(1)
    resp = client.post(f"/api/flashcards/{card_id}/translate")
    assert resp.status_code == 200
    card = resp.json()["flashcard"]
    assert card["santali_ol_chiki"] == SAMPLE_OL_CHIKI
    assert card["validation_status"] == AI_GENERATED

    def fake_tts(text):
        filename = f"tts_{'c' * 32}.wav"
        generated_wavs(filename)
        return {
            "filename": filename,
            "audio_path": str(settings.generated_files_path / filename),
            "sample_rate": 16000,
            "duration_sec": 0.3,
            "latency_ms": 40,
            "rtf": 0.15,
            "model": "fake-tts",
            "input_text": text,
            "tts_input_text": text,
            "unsupported_chars_removed": "",
        }

    from app.ai import tts_service

    monkeypatch.setattr(tts_service.tts_service, "synthesize_to_file", fake_tts)
    resp = client.post(f"/api/flashcards/{card_id}/audio")
    assert resp.status_code == 200
    assert resp.json()["audio_url"].startswith("/api/tts/audio/")


def test_flashcard_audio_before_translate_400(client, restore_flashcard):
    card_id = restore_flashcard(1)
    resp = client.post(f"/api/flashcards/{card_id}/audio")
    assert resp.status_code == 400


def test_flashcard_404(client):
    resp = client.post("/api/flashcards/999999/audio")
    assert resp.status_code == 404


# --------------------------------------------------------- offline safety


def test_tts_missing_model_gives_download_hint(client, monkeypatch, restore_flashcard):
    """When the TTS voice is missing, the error must be actionable, offline-aware."""
    card_id = restore_flashcard(1)
    with SessionLocal() as db:
        row = db.get(Flashcard, card_id)
        row.santhali_ol_chiki = SAMPLE_OL_CHIKI
        row.validation_status = AI_GENERATED
        db.commit()

    def failing(text):
        raise TTSModelError(
            "The Santali TTS model is not downloaded yet. "
            "Run: python scripts\\download_tts_model.py", 503,
        )

    from app.ai import tts_service

    monkeypatch.setattr(tts_service.tts_service, "synthesize_to_file", failing)
    resp = client.post(f"/api/flashcards/{card_id}/audio")
    assert resp.status_code == 503
    assert "download_tts_model.py" in resp.json()["detail"]

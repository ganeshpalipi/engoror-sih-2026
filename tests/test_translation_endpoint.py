"""
Endpoint tests for POST /api/translate/text and GET /api/models/status.

The heavy IndicTrans2 model is NOT loaded during unit tests - the service is
monkeypatched so these tests verify the HTTP layer, validation, history
persistence and error handling. Real-model inference is verified separately
via `python scripts/translate_demo.py`.
"""

import pytest

from app.ai import translation_service
from app.database import SessionLocal
from app.models import TranslationHistory


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def _cleanup_history(input_text: str) -> None:
    with SessionLocal() as db:
        for row in db.query(TranslationHistory).filter_by(input_text=input_text).all():
            db.delete(row)
        db.commit()


def test_translate_endpoint_success(client, monkeypatch):
    def fake_translate(text: str):
        return {"translated_text": "TEST_OUTPUT", "latency_ms": 12, "model": "test-model"}

    monkeypatch.setattr(translation_service, "translate_text", fake_translate)
    text = "अपनी किताब खोलो।"
    try:
        resp = client.post("/api/translate/text", json={"text": text})
        assert resp.status_code == 200
        data = resp.json()
        assert data["translated_text"] == "TEST_OUTPUT"
        assert data["input_text"] == text
        assert data["source_language"] == "hin_Deva"
        assert data["target_language"] == "sat_Olck"
        assert data["latency_ms"] == 12
        assert data["model"] == "test-model"
        assert data["offline"] is True
        assert "native-speaker" in data["validation_notice"].lower()

        with SessionLocal() as db:
            row = db.query(TranslationHistory).filter_by(input_text=text).first()
            assert row is not None
            assert row.success is True
            assert row.model_name == "test-model"
            assert row.translated_text == "TEST_OUTPUT"
    finally:
        _cleanup_history(text)


def test_translate_endpoint_model_error(client, monkeypatch):
    def failing_translate(text: str):
        raise translation_service.TranslationModelError(
            "Model not available in this test", 503
        )

    monkeypatch.setattr(translation_service, "translate_text", failing_translate)
    text = "ध्यान से सुनो।"
    try:
        resp = client.post("/api/translate/text", json={"text": text})
        assert resp.status_code == 503
        assert "Model not available" in resp.json()["detail"]

        with SessionLocal() as db:
            row = db.query(TranslationHistory).filter_by(input_text=text).first()
            assert row is not None
            assert row.success is False
            assert row.translated_text is None
            assert row.error_message is not None
    finally:
        _cleanup_history(text)


def test_translate_endpoint_unsupported_pair(client):
    resp = client.post(
        "/api/translate/text",
        json={"text": "नमस्ते", "source_language": "eng_Latn", "target_language": "sat_Olck"},
    )
    assert resp.status_code == 422
    assert "Unsupported language pair" in resp.json()["detail"][0]["msg"]


def test_translate_endpoint_empty_text(client):
    # Whitespace-only text passes Pydantic (length >= 1) and is then caught by
    # the service, which returns a friendly 400 instead of a raw 422.
    resp = client.post("/api/translate/text", json={"text": "   "})
    assert resp.status_code == 400
    assert "enter some Hindi text" in resp.json()["detail"]


def test_models_status_endpoint(client):
    resp = client.get("/api/models/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["offline"] is True
    assert data["translation"]["direction"] == "hin_Deva -> sat_Olck"
    assert data["translation"]["status"] in ("not_loaded", "loading", "ready", "error")

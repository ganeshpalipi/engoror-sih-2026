"""
Phase 4 endpoint tests: /api/tts/* and the TTS additions to
/api/classroom/speech-translate.

The heavy voice model is NOT required - the service is monkeypatched. These
tests verify the HTTP layer, validation, audio serving safety, and that the
Phase 3 speech-translate response stays compatible while gaining audio fields.
"""

import re
import wave
from pathlib import Path

import pytest

from app.ai import tts_service
from app.ai.tts_service import TTSModelError
from app.config import settings

SAMPLE_OL_CHIKI = "ᱟᱢᱟᱜ ᱯᱚᱛᱚᱵ ᱠᱚᱞᱚᱢ ᱟᱹᱜᱩᱭ ᱢᱮ"


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def _make_wav(path: Path, seconds: float = 0.4, rate: int = 16000) -> None:
    import math
    import struct

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


def _fake_tts_result(filename: str) -> dict:
    return {
        "filename": filename,
        "audio_path": str(settings.generated_files_path / filename),
        "sample_rate": 16000,
        "duration_sec": 0.4,
        "latency_ms": 87,
        "rtf": 0.218,
        "model": settings.TTS_MODEL_ID,
        "input_text": SAMPLE_OL_CHIKI,
        "tts_input_text": SAMPLE_OL_CHIKI,
        "unsupported_chars_removed": "",
    }


@pytest.fixture()
def generated_wav():
    """Create one whitelisted WAV and clean up any created files after."""
    created: list[Path] = []

    def _create(filename: str) -> str:
        path = settings.generated_files_path / filename
        _make_wav(path)
        created.append(path)
        return filename

    yield _create
    for path in created:
        path.unlink(missing_ok=True)


# ------------------------------------------------------------ validation


def test_synthesize_empty_text_422(client):
    resp = client.post("/api/tts/synthesize", json={"text": ""})
    assert resp.status_code == 422


def test_synthesize_whitespace_text_400(client):
    resp = client.post("/api/tts/synthesize", json={"text": "   "})
    assert resp.status_code == 400
    assert "no text" in resp.json()["detail"].lower()


def test_synthesize_too_long_422(client):
    resp = client.post("/api/tts/synthesize", json={"text": "ᱟ" * 501})
    assert resp.status_code == 422


def test_synthesize_missing_body_422(client):
    resp = client.post("/api/tts/synthesize", json={})
    assert resp.status_code == 422


# ------------------------------------------------------ error handling


def test_synthesize_missing_model_503_with_download_hint(client, monkeypatch):
    def failing(text):
        raise TTSModelError(
            "The Santali TTS model is not downloaded yet. Connect to the "
            "internet ONCE and run: python scripts\\download_tts_model.py",
            503,
        )

    monkeypatch.setattr(tts_service.tts_service, "synthesize_to_file", failing)
    resp = client.post("/api/tts/synthesize", json={"text": SAMPLE_OL_CHIKI})
    assert resp.status_code == 503
    assert "download_tts_model.py" in resp.json()["detail"]


def test_synthesize_engine_failure_is_friendly_500(client, monkeypatch):
    def failing(text):
        raise TTSModelError(
            "Speech synthesis failed on this device. Please try again; "
            "if it keeps failing, check the Model Status panel.", 500,
        )

    monkeypatch.setattr(tts_service.tts_service, "synthesize_to_file", failing)
    resp = client.post("/api/tts/synthesize", json={"text": SAMPLE_OL_CHIKI})
    assert resp.status_code == 500
    assert "synthesis failed" in resp.json()["detail"].lower()


# -------------------------------------------------------- success path


def test_synthesize_success_metadata_and_audio_url(client, monkeypatch, generated_wav):
    filename = generated_wav("tts_" + "a" * 32 + ".wav")
    monkeypatch.setattr(
        tts_service.tts_service,
        "synthesize_to_file",
        lambda text: _fake_tts_result(filename),
    )
    resp = client.post("/api/tts/synthesize", json={"text": SAMPLE_OL_CHIKI})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["text"] == SAMPLE_OL_CHIKI
    assert data["model"] == settings.TTS_MODEL_ID
    assert data["sample_rate"] == 16000
    assert data["duration_sec"] == 0.4
    assert data["latency_ms"] == 87
    assert data["offline"] is True
    assert data["audio_url"] == f"/api/tts/audio/{filename}"
    assert "native-speaker" in data["validation_notice"].lower()
    # The audio URL must immediately serve the real generated WAV.
    audio = client.get(data["audio_url"])
    assert audio.status_code == 200
    assert audio.headers["content-type"] == "audio/wav"


def test_synthesize_reports_removed_unsupported_chars(client, monkeypatch, generated_wav):
    filename = generated_wav("tts_" + "b" * 32 + ".wav")
    result = _fake_tts_result(filename)
    result["tts_input_text"] = "ᱯᱚᱛᱚᱵ"
    result["unsupported_chars_removed"] = "#"
    monkeypatch.setattr(
        tts_service.tts_service, "synthesize_to_file", lambda text: result
    )
    resp = client.post("/api/tts/synthesize", json={"text": "ᱯᱚᱛᱚᱵ #"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["tts_input_text"] == "ᱯᱚᱛᱚᱵ"
    assert data["unsupported_chars_removed"] == "#"


# ------------------------------------------------------ audio serving


def test_audio_serving_rejects_unknown_names(client):
    assert client.get("/api/tts/audio/does_not_exist.wav").status_code == 404
    assert client.get("/api/tts/audio/tts_short.wav").status_code == 404
    # traversal attempts can never match the whitelist pattern
    assert client.get("/api/tts/audio/..%2F..%2Fapp%2Fmain.py").status_code == 404
    assert client.get("/api/tts/audio/tts_" + "c" * 40 + ".wav").status_code == 404


def test_audio_serving_404_when_file_expired(client):
    resp = client.get("/api/tts/audio/" + "tts_" + "d" * 32 + ".wav")
    assert resp.status_code == 404
    assert "expired" in resp.json()["detail"].lower()


# ------------------------------------------------------- status surfaces


def test_tts_status_endpoint(client):
    resp = client.get("/api/tts/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == settings.TTS_MODEL_ID
    assert data["direction"] == "santali ol chiki text -> santali speech"
    assert data["status"] in ("not_downloaded", "not_loaded", "ready", "error")


def test_health_includes_tts_component(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    components = resp.json()["components"]
    assert components["tts"]["status"] in ("ok", "not_ready", "error")


def test_models_status_includes_tts(client):
    resp = client.get("/api/models/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tts"]["model"] == settings.TTS_MODEL_ID
    assert data["tts"]["status"] in ("not_downloaded", "not_loaded", "ready", "error")


# ------------------------------------ speech-translate response compat


def _mock_asr(monkeypatch):
    from app.ai.asr_service import asr_service

    def fake_transcribe(data, language=None):
        return {
            "text": "अपनी किताब खोलो",
            "language": "hi",
            "duration_sec": 1.8,
            "latency_ms": 321,
            "model": "faster-whisper/test-marker",
        }

    monkeypatch.setattr(asr_service, "transcribe_bytes", fake_transcribe)


def _mock_translation(monkeypatch):
    from app.ai import translation_service

    def fake_translate(text):
        return {
            "translated_text": SAMPLE_OL_CHIKI,
            "latency_ms": 450,
            "model": "test-mt",
        }

    monkeypatch.setattr(translation_service, "translate_text", fake_translate)


def test_speech_translate_includes_santali_audio(client, monkeypatch, generated_wav):
    """Full pipeline: ASR -> MT -> TTS, all mocked; audio fields populated."""
    from app.database import SessionLocal
    from app.models import AsrTranscription, TranslationHistory

    filename = generated_wav("tts_" + "e" * 32 + ".wav")
    _mock_asr(monkeypatch)
    _mock_translation(monkeypatch)
    monkeypatch.setattr(
        tts_service.tts_service,
        "synthesize_to_file",
        lambda text: _fake_tts_result(filename),
    )
    try:
        resp = client.post(
            "/api/classroom/speech-translate",
            files={"file": ("rec.webm", b"fakeaudio", "audio/webm")},
            data={"language": "hi"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Phase 3 fields preserved
        assert data["success"] is True
        assert data["recognized_hindi"] == "अपनी किताब खोलो"
        assert data["santali_ol_chiki"] == SAMPLE_OL_CHIKI
        assert data["asr_model"] == "faster-whisper/test-marker"
        assert data["translation_model"] == "test-mt"
        assert data["validation_notice"]
        # Phase 4 audio fields
        assert data["audio_available"] is True
        assert data["audio_url"] == f"/api/tts/audio/{filename}"
        assert data["tts_model"] == settings.TTS_MODEL_ID
        assert data["tts_latency_ms"] >= 0
        assert data["tts_message"] is None
        assert re.match(r"^/api/tts/audio/tts_[0-9a-f]{32}\.wav$", data["audio_url"])
        audio = client.get(data["audio_url"])
        assert audio.status_code == 200
    finally:
        with SessionLocal() as db:
            for row in db.query(AsrTranscription).filter_by(
                model_name="faster-whisper/test-marker"
            ).all():
                db.delete(row)
            for row in db.query(TranslationHistory).filter_by(
                input_text="अपनी किताब खोलो"
            ).all():
                db.delete(row)
            db.commit()


def test_speech_translate_tts_failure_keeps_text_result(client, monkeypatch):
    """TTS problems must never break the working Phase 3 text pipeline."""
    from app.database import SessionLocal
    from app.models import AsrTranscription, TranslationHistory

    _mock_asr(monkeypatch)
    _mock_translation(monkeypatch)

    def failing_tts(text):
        raise TTSModelError(
            "The Santali TTS model is not downloaded yet. Connect to the "
            "internet ONCE and run: python scripts\\download_tts_model.py",
            503,
        )

    monkeypatch.setattr(tts_service.tts_service, "synthesize_to_file", failing_tts)
    try:
        resp = client.post(
            "/api/classroom/speech-translate",
            files={"file": ("rec.webm", b"fakeaudio", "audio/webm")},
            data={"language": "hi"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["santali_ol_chiki"] == SAMPLE_OL_CHIKI  # text survived
        assert data["audio_available"] is False
        assert data["audio_url"] is None
        assert "download_tts_model.py" in data["tts_message"]
    finally:
        with SessionLocal() as db:
            for row in db.query(AsrTranscription).filter_by(
                model_name="faster-whisper/test-marker"
            ).all():
                db.delete(row)
            for row in db.query(TranslationHistory).filter_by(
                input_text="अपनी किताब खोलो"
            ).all():
                db.delete(row)
            db.commit()


# ----------------------------------------------------- real engine (opt)


@pytest.mark.skipif(
    not tts_service.tts_service.is_downloaded(),
    reason="Real TTS test needs the voice - run scripts/download_tts_model.py once",
)
def test_real_synthesize_endpoint_generates_wav(client):
    resp = client.post("/api/tts/synthesize", json={"text": SAMPLE_OL_CHIKI})
    assert resp.status_code == 200
    data = resp.json()
    assert data["audio_available" if "audio_available" in data else "success"] is True
    audio = client.get(data["audio_url"])
    assert audio.status_code == 200
    assert audio.headers["content-type"] == "audio/wav"
    assert len(audio.content) > 1000  # real audio, not an empty file

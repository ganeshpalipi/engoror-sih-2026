"""
Phase 4 TTS service tests.

Most tests mock the ONNX session so CI never needs the voice model. One test
exercises the REAL model (skipped automatically when it is not downloaded -
run `python scripts/download_tts_model.py` first to enable it everywhere).
"""

import wave
from pathlib import Path

import pytest

from app.ai.tts_service import (
    TTSModelError,
    TTSService,
    tts_service,
)
from app.config import settings

SAMPLE_OL_CHIKI = "ᱟᱢᱟᱜ ᱯᱚᱛᱚᱵ ᱠᱚᱞᱚᱢ ᱟᱹᱜᱩᱭ ᱢᱮ"
HINDI_TEXT = "अपनी किताब खोलो"


@pytest.fixture()
def fresh_service():
    """A TTSService instance with no loaded model (per-test isolation)."""
    return TTSService()


def _prime_fake_model(service: TTSService, monkeypatch):
    """Pretend the model is loaded, without touching onnxruntime."""
    # Mirror the REAL voice vocabulary: the full Ol Chiki block
    # (U+1C50-U+1C7F) plus the ASCII punctuation the voice knows.
    chars = {chr(cp) for cp in range(0x1C50, 0x1C80)} | set(" !\"$'(),-./:;?[]^_`~")
    service._id_map = {ch: [10 + i] for i, ch in enumerate(sorted(chars))}
    service._id_map["_"] = [0]
    service._id_map["^"] = [1]
    service._id_map["$"] = [2]
    service._sample_rate = 16000

    def fake_audio(clean_text):
        import numpy as np

        # 0.5 s of a gentle sine wave - enough to be valid, trimmable audio.
        t = np.linspace(0, 0.5, int(16000 * 0.5), endpoint=False)
        return (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)

    monkeypatch.setattr(service, "_generate_audio", fake_audio)
    monkeypatch.setattr(
        service, "ensure_model_loaded", lambda allow_download=True: None
    )
    return service


# ---------------------------------------------------------------- status


def test_status_not_downloaded(fresh_service, monkeypatch):
    monkeypatch.setattr(fresh_service, "local_model_dir", lambda: None)
    st = fresh_service.status()
    assert st["status"] == "not_downloaded"
    assert st["downloaded"] is False
    assert "download_tts_model.py" in st["detail"]


def test_status_not_loaded_when_cached(fresh_service, monkeypatch):
    monkeypatch.setattr(fresh_service, "local_model_dir", lambda: Path("."))
    st = fresh_service.status()
    assert st["status"] == "not_loaded"
    assert st["downloaded"] is True
    assert "loads on first use" in st["detail"]


def test_status_ready_after_load(fresh_service, monkeypatch):
    _prime_fake_model(fresh_service, monkeypatch)
    fresh_service._loaded_label = "fake-voice"
    fresh_service._session = object()  # pretend loaded
    st = fresh_service.status()
    assert st["status"] == "ready"
    assert st["model"] == settings.TTS_MODEL_ID


def test_status_error_state(fresh_service, monkeypatch):
    monkeypatch.setattr(fresh_service, "local_model_dir", lambda: Path("."))
    fresh_service._error = "boom"
    st = fresh_service.status()
    assert st["status"] == "error"


# ------------------------------------------------------------ text prep


def test_prepare_text_maps_digits(fresh_service, monkeypatch):
    _prime_fake_model(fresh_service, monkeypatch)
    clean, removed = fresh_service.prepare_text("ᱯᱚᱛᱚᱵ 2 ᱴᱟᱲᱟᱝ")
    # ASCII digits are converted to Ol Chiki digits, not dropped.
    assert clean == "ᱯᱚᱛᱚᱵ ᱒ ᱴᱟᱲᱟᱝ"
    assert removed == ""


def test_prepare_text_maps_danda_and_collapses_space(fresh_service, monkeypatch):
    _prime_fake_model(fresh_service, monkeypatch)
    clean, removed = fresh_service.prepare_text("ᱟᱭ ᱾  ᱵᱟᱰ |  \n")
    assert "᱾" in clean
    assert "  " not in clean
    assert clean == clean.strip()


def test_prepare_text_reports_unsupported_chars(fresh_service, monkeypatch):
    _prime_fake_model(fresh_service, monkeypatch)
    clean, removed = fresh_service.prepare_text("ᱯᱚᱛᱚᱵ #!" + HINDI_TEXT)
    assert "#" in removed and "अ" in removed
    assert all(ch not in clean for ch in removed)


def test_prepare_text_keeps_ol_chiki_untouched(fresh_service, monkeypatch):
    _prime_fake_model(fresh_service, monkeypatch)
    clean, removed = fresh_service.prepare_text(SAMPLE_OL_CHIKI)
    assert clean == SAMPLE_OL_CHIKI
    assert removed == ""


# --------------------------------------------------------- validation


def test_synthesize_empty_text_rejected(fresh_service):
    with pytest.raises(TTSModelError) as exc:
        fresh_service.synthesize_to_file("   ")
    assert exc.value.suggested_status == 400


def test_synthesize_too_long_rejected(fresh_service):
    with pytest.raises(TTSModelError) as exc:
        fresh_service.synthesize_to_file("ᱟ" * (settings.TTS_MAX_TEXT_LENGTH + 1))
    assert exc.value.suggested_status == 400
    assert "too long" in exc.value.user_message


def test_synthesize_non_ol_chiki_rejected(fresh_service, monkeypatch):
    """Hindi (Devanagari) must NOT be spoken by the Santali voice."""
    _prime_fake_model(fresh_service, monkeypatch)
    with pytest.raises(TTSModelError) as exc:
        fresh_service.synthesize_to_file(HINDI_TEXT)
    assert exc.value.suggested_status == 400
    assert "Ol Chiki" in exc.value.user_message


# -------------------------------------------------- missing model paths


def test_missing_model_offline_gives_download_hint(fresh_service, monkeypatch):
    monkeypatch.setattr(fresh_service, "local_model_dir", lambda: None)
    with pytest.raises(TTSModelError) as exc:
        fresh_service.synthesize_to_file(SAMPLE_OL_CHIKI)
    assert exc.value.suggested_status == 503
    assert "download_tts_model.py" in exc.value.user_message


def test_missing_model_engine_not_installed(fresh_service, monkeypatch):
    """No cache + no onnxruntime => friendly install hint, no crash."""
    monkeypatch.setattr(fresh_service, "local_model_dir", lambda: None)
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "onnxruntime":
            raise ImportError("No module named 'onnxruntime'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(TTSModelError) as exc:
        fresh_service.synthesize_to_file(SAMPLE_OL_CHIKI)
    assert "onnxruntime" in exc.value.user_message


# --------------------------------------------------- synthesis (mocked)


def _patch_files_dir(monkeypatch, tmp_path):
    """Point the service at a temp generated-files dir (class property)."""
    monkeypatch.setattr(
        type(settings),
        "generated_files_path",
        property(lambda self: tmp_path),
    )


def test_synthesize_success_writes_valid_wav(fresh_service, monkeypatch, tmp_path):
    _prime_fake_model(fresh_service, monkeypatch)
    _patch_files_dir(monkeypatch, tmp_path)
    result = fresh_service.synthesize_to_file(" ᱟᱢᱟᱜ ᱯᱚᱛᱚᱵ 2 ")

    assert result["model"] == settings.TTS_MODEL_ID
    assert result["sample_rate"] == 16000
    assert result["duration_sec"] > 0
    assert result["latency_ms"] >= 0
    assert result["unsupported_chars_removed"] == ""

    out = Path(result["audio_path"])
    assert out.is_file()
    assert out.parent == tmp_path
    with wave.open(str(out), "rb") as wav:
        assert wav.getframerate() == 16000
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getnframes() > 0


def test_synthesize_filename_pattern_is_whitelist_safe(
    fresh_service, monkeypatch, tmp_path
):
    import re

    _prime_fake_model(fresh_service, monkeypatch)
    _patch_files_dir(monkeypatch, tmp_path)
    result = fresh_service.synthesize_to_file(SAMPLE_OL_CHIKI)
    assert re.match(r"^tts_[0-9a-f]{32}\.wav$", result["filename"])


# ----------------------------------------------------- real engine (opt)


@pytest.mark.skipif(
    not tts_service.is_downloaded(),
    reason="Real TTS test needs the voice - run scripts/download_tts_model.py once",
)
def test_real_engine_generates_santali_speech():
    """Real path: Ol Chiki text -> valid WAV with audible content."""
    result = tts_service.synthesize_to_file(SAMPLE_OL_CHIKI)
    path = Path(result["audio_path"])
    assert path.is_file()
    with wave.open(str(path), "rb") as wav:
        assert wav.getframerate() == result["sample_rate"]
        frames = wav.getnframes()
    assert frames / result["sample_rate"] > 0.2  # audible length
    assert 0 < result["latency_ms"] < 60_000

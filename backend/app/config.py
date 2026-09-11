"""
RootVerse application configuration.

All settings are loaded from environment variables with optional `.env` file
support (pydantic-settings). See `backend/.env.example` for every variable.

NOTE: Run the server from the `backend/` folder so relative paths
(./rootverse.db, ./model_cache, ./generated_files) resolve correctly.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ folder (this file lives in backend/app/)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Environment-driven settings with safe development defaults."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # ----- Application -----
    APP_NAME: str = "RootVerse"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"  # development | production
    DEBUG: bool = True
    # Core promise: once models/content are downloaded, no cloud API is needed.
    OFFLINE_MODE: bool = True

    # ----- Server -----
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # ----- Database (SQLite for the prototype) -----
    DATABASE_URL: str = "sqlite:///./rootverse.db"

    # ----- Storage (relative to the backend/ folder) -----
    MODEL_CACHE_DIR: str = "./model_cache"
    GENERATED_FILES_DIR: str = "./generated_files"

    # ----- Frontend dev server (comma separated origins) -----
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ----- AI / machine translation (Phase 2) -----
    # AI4Bharat IndicTrans2 (Indic -> Indic distilled). First download needs
    # internet once (~1.2 GB into backend/model_cache/hf), then it is offline.
    MT_MODEL_ID: str = "ai4bharat/indictrans2-indic-indic-dist-320M"
    MT_NUM_BEAMS: int = 4
    MT_MAX_LENGTH: int = 256
    PRELOAD_MODEL_ON_STARTUP: bool = True  # load from local cache at boot (no download)
    # FREE Hugging Face READ token (one-time gated download of the open
    # weights; inference itself is local). Put it in backend/.env - never commit it.
    HF_TOKEN: str = ""

    # ----- AI / speech recognition (Phase 3) -----
    # Offline Hindi ASR with faster-whisper (CTranslate2 port of OpenAI Whisper,
    # open weights, local CPU inference, no cloud API). The model downloads ONCE
    # into backend/model_cache/asr (public repo - no HF token needed), then it
    # is fully offline.
    # "small" is the practical accuracy/speed balance for Hindi on a laptop CPU;
    # set ASR_MODEL_SIZE=base on low-end hardware (less accurate, faster).
    ASR_MODEL_SIZE: str = "small"        # tiny | base | small | medium
    ASR_DEVICE: str = "cpu"              # CPU required baseline; "cuda" optional
    ASR_COMPUTE_TYPE: str = "int8"       # INT8 quantisation on CPU (set "float32" if issues)
    ASR_LANGUAGE: str = "hi"             # force Hindi ("auto" = let Whisper detect)
    ASR_BEAM_SIZE: int = 1
    ASR_CPU_THREADS: int = 0             # 0 = let faster-whisper use all logical cores
    ASR_MAX_AUDIO_SECONDS: float = 120.0 # classroom sentences are short; guard RAM
    ASR_PRELOAD_ON_STARTUP: bool = False # lazy-load on first request keeps boot fast

    # ----- Logging -----
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        """Comma-separated CORS_ORIGINS -> list of origins."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def model_cache_path(self) -> Path:
        """Model cache directory, created on demand (Windows-safe)."""
        path = Path(self.MODEL_CACHE_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def generated_files_path(self) -> Path:
        """Generated-files directory, created on demand (Windows-safe)."""
        path = Path(self.GENERATED_FILES_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def asr_model_path(self) -> Path:
        """
        ASR model cache directory: backend/model_cache/asr.

        Deliberately SEPARATE from the translation cache (model_cache/hf) so a
        Phase 3 re-download can never touch the working IndicTrans2 files.
        """
        path = self.model_cache_path / "asr"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor (settings are read once per process)."""
    return Settings()


settings = get_settings()

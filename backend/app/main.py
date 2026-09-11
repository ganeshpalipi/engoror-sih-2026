"""
RootVerse backend - FastAPI application entry point.

Run from the `backend/` folder (Windows PowerShell):

    uvicorn app.main:app --reload

Interactive API docs: http://127.0.0.1:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import Base, engine
from app.models import FlnLesson, ClassroomPhrase, ModelMetadata, TranslationHistory  # noqa: F401 (registers tables)
from app.ai.model_manager import model_manager
from app.routers import health, translation
from app.services.seed_service import seed_if_empty
from app.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown logic. Runs once per server process."""
    logger.info(
        "Starting %s v%s (env=%s, offline_mode=%s)",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.APP_ENV,
        settings.OFFLINE_MODE,
    )
    # Ensure required storage folders exist (Windows-safe paths, idempotent)
    logger.info("Model cache dir: %s", settings.model_cache_path)
    logger.info("Generated files dir: %s", settings.generated_files_path)

    # Create tables for every ORM model imported so far.
    Base.metadata.create_all(bind=engine)
    logger.info("Database ready: %s", settings.DATABASE_URL)

    # Seed safe development data (idempotent, no invented Santali text)
    seed_if_empty()

    # Warm the translation model from the local cache in the background
    # (never downloads; if missing, the first request handles setup)
    model_manager.load_from_cache_in_background()

    yield

    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Offline-first AI classroom language bridge.\n\n"
        "Pipeline: Hindi speech -> offline ASR -> Hindi text -> Hindi-to-Santhali MT "
        "-> Santhali text (Ol Chiki) -> offline TTS -> classroom audio.\n\n"
        "Prototype target language: **Santhali (Ol Chiki script)**."
    ),
    lifespan=lifespan,
)

# Allow the Vite dev server (and later a deployed frontend) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Routers (one per domain, added phase by phase) -----
app.include_router(health.router)
app.include_router(translation.router)


# ----- Global safety net -----
# One unhandled error must never crash the whole server (SIH rule #17).
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on the server. Please try again."},
    )

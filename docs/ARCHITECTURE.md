# RootVerse — Architecture

> Team RootVerse | SIH 2026
> Offline-first AI classroom language bridge: **Hindi speech → Santhali audio (Ol Chiki script)**

## 1. System overview

```
                       ┌──────────────────────────────────────────────────┐
                       │              TEACHER DEVICE (Windows 11)          │
                       │                                                  │
 Teacher speaks Hindi  │  ┌────────────┐   ┌────────────┐   ┌───────────┐ │
 ─────────────────────▶│  │ Offline    │──▶│ Hindi text │──▶│ Hindi →   │ │
 (microphone)          │  | Hindi ASR  │   │            │   │ Santhali  │ │
                       │  └────────────┘   └────────────┘   │ MT        │ │
                       │                                    │(IndicTrans2)│
                       │  ┌────────────┐   ┌────────────┐   └─────┬─────┘ │
                       │  │ Santhali   │◀──│ Ol Chiki   │◀────────┘       │
                       │  │ TTS        │   │ text       │                 │
                       │  └─────┬──────┘   └────────────┘                 │
                       └────────┼─────────────────────────────────────────┘
                                ▼
                    Students hear Santhali audio (classroom speaker)
```

## 2. Module map

| Layer | Module | Responsibility |
|---|---|---|
| API | `backend/app/main.py` | FastAPI app, CORS, lifespan, global error handler |
| API | `backend/app/routers/` | One router per feature (health, translate, asr, tts, phrases, lessons, worksheets, flashcards, sync, models) |
| Config | `backend/app/config.py` | Environment-driven settings (pydantic-settings), Windows-safe paths |
| Data | `backend/app/database.py` | SQLAlchemy engine + session (SQLite), `get_db` dependency |
| Data | `backend/app/models/` | ORM tables (Phase 3) |
| Validation | `backend/app/schemas/` | Pydantic request/response schemas |
| Logic | `backend/app/services/` | Phrase store, lesson store, worksheet builder, sync service |
| AI | `backend/app/ai/` | Modular pipeline (Phase 4–7), see below |
| UI | `frontend/src/pages/` | One page per teacher workflow (12 pages) |
| UI | `frontend/src/services/api.js` | Single HTTP layer with human-friendly errors |
| Tests | `tests/` | Endpoint + service tests, Hindi classroom test sentences |

## 3. AI pipeline (modular, built in Phases 4–7)

```
Audio input (WAV)
   │
   ▼
asr_service.py          Offline Hindi ASR (CPU-friendly; candidate: IndicConformer)
   │  Hindi text
   ▼
language_detection.py   Language / code-switch check (Hindi expected)
   │
   ▼
translation_service.py  Hindi → Santhali MT
   │                    Candidate: AI4Bharat IndicTrans2 (hin_Deva → sat_Olck)
   │  Santhali text (Ol Chiki)
   ▼
tts_service.py          Offline Santhali TTS (pluggable provider +
   │                    fallback pre-recorded phrase audio)
   ▼
Audio output (WAV) → returned to the classroom speaker

pipeline.py orchestrates the flow and records per-stage latency:
ASR time, MT time, TTS time, total time.
model_manager.py handles lazy loading, model caching and status reporting.
```

Rules for the AI layer:

- **Load once, cache forever** — models are loaded lazily on first use and kept in memory.
- **No fake outputs** — if a real model is unavailable, the module returns an explicit
  "model not loaded" error and the model status endpoint reports the truth.
- **Mock fallback only for development**, clearly labelled.
- **CPU first** — CUDA is optional; ONNX/TFLite are future optimisation paths.
- **No cloud APIs in the core pipeline** (no OpenAI / Google Translate / paid APIs).

## 4. Operating modes

| Mode | Where | AI models | Purpose |
|---|---|---|---|
| **Mode 1 — Local Offline AI** | Teacher's Windows 11 laptop | Full offline models (ASR/MT/TTS) | Real classroom use. The core product. |
| **Mode 2 — Web Demo** | Vercel/Netlify + lightweight host (e.g. Render) | Mock / limited models | Judges demo when hosting cannot fit multi-GB weights. |

Mode 2 never replaces Mode 1 — it is an optional demo facade over the same API contract.

## 5. Offline-first strategy

- All content (lessons, phrases, flashcards) lives in the local SQLite database.
- Models live in `backend/model_cache/` after a one-time download.
- Generated audio/worksheets are written to `backend/generated_files/`.
- **BRC Sync (Phase 11):** at a connected Block Resource Centre the device can
  import/export a ZIP (or folder) containing updated lessons, phrases and language
  packs. Wi-Fi / USB / SD-card imports all reduce to "deliver a folder or ZIP",
  so the same code path serves all transports.

## 6. Language-data integrity rule (important)

Santhali content shown to users is either **linguistically verified** or marked
`REQUIRES_LANGUAGE_VALIDATION`. Prototype placeholders are never presented as
verified translations. See `datasets/README.md`.

## 7. Windows 11 development notes

- Python venv: `python -m venv .venv` then `.venv\Scripts\activate`
- Backend run from `backend/`: `uvicorn app.main:app --reload`
- Frontend run from `frontend/`: `npm run dev` (Vite on port 5173)
- Vite proxies `/api/*` (and `/health`) to `http://127.0.0.1:8000` in dev.
- All paths use `pathlib` so nothing depends on Linux filesystem conventions.

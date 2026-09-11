# RootVerse 🌱

> **AI-Powered Vernacular Pedagogy and Real-Time Translation Tool for Mother Tongue-Based Primary Education**
> Smart India Hackathon 2026 · Team RootVerse
>
> An **offline-first** classroom language bridge: a Hindi-speaking teacher speaks —
> students hear **Santhali** in the **Ol Chiki** script.

**Build status: PHASE 2 complete** (SQLite foundation + real Hindi → Santali translation with IndicTrans2 + API + UI).
The remaining AI pipeline lands phase-by-phase — see [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md).

---

## 1. Problem

In tribal areas of India, primary-school teachers often know **Hindi** but not the
local tribal language (prototype target: **Santhali**). Young students often do not
fully understand Hindi. Internet connectivity is unreliable, so cloud translation
services cannot be trusted in the classroom.

## 2. Solution

A Windows-laptop application that runs **entirely offline** after a one-time model
download:

```
Teacher speaks Hindi
   → Offline Hindi ASR            (speech → Hindi text)
   → Hindi → Santhali MT          (IndicTrans2: hin_Deva → sat_Olck)
   → Santhali text in Ol Chiki    (shown on screen)
   → Offline Santhali TTS         (text → Santhali audio)
   → Students hear Santhali audio
```

Plus classroom tooling built around the bridge: FLN lessons, a classroom phrase
pack, printable bilingual worksheets, flashcards, and Block-Resource-Centre sync —
all local-first.

## 3. Architecture

```
RootVerse/
├── backend/                 FastAPI (Python 3.11) + SQLAlchemy + SQLite
│   ├── app/
│   │   ├── main.py          App entry, CORS, lifespan, global error handler
│   │   ├── config.py        Env-driven settings (pydantic-settings)
│   │   ├── database.py      Engine + session + Base (SQLite)
│   │   ├── routers/         API routers (health now; translate/asr/tts/... next)
│   │   ├── schemas/         Pydantic request/response models
│   │   ├── models/          ORM tables (Phase 3)
│   │   ├── services/        Business logic (phrases, lessons, worksheets, sync)
│   │   ├── ai/              Modular AI: asr / translation / tts / pipeline / model_manager
│   │   ├── utils/           Logging and helpers
│   │   └── static/          Static assets served by the API
│   ├── model_cache/         Downloaded AI model weights (git-ignored)
│   ├── generated_files/     Generated audio/worksheets (git-ignored)
│   ├── requirements.txt
│   └── .env.example
├── frontend/                Vite + React (JavaScript) SPA, 12 pages
│   └── src/
│       ├── components/      Layout shell (sidebar nav, sticky footer)
│       ├── pages/           Home, Live/Text Translation, Lessons, Phrases,
│       │                    Worksheets, Flashcards, History, Offline Content,
│       │                    Sync, Settings, Model Status
│       ├── services/api.js  Single HTTP layer with human-friendly errors
│       ├── hooks/           Reusable data-fetching hooks
│       └── utils/           Small formatting helpers
├── datasets/                classroom_phrases/ · fln_lessons/ · translation_samples/
├── docs/                    ARCHITECTURE.md · PROJECT_PLAN.md
├── tests/                   Pytest suite + Hindi classroom test sentences
├── .gitignore
└── README.md
```

## 4. Features

**Available now (Phase 1–2)**
- ✅ FastAPI backend with health endpoint reporting API + database status
- ✅ SQLite tables: classroom_phrases, fln_lessons, translation_history, model_metadata (auto-created + seeded at startup)
- ✅ **Real Hindi → Santali (Ol Chiki) translation** — AI4Bharat IndicTrans2 (indic-indic distilled 320M), local CPU inference, load-once caching, offline after one-time download
- ✅ `POST /api/translate/text` + `GET /api/models/status` with honest status reporting
- ✅ Every request recorded in translation_history (input, output, latency, success)
- ✅ React Text Translation page (live model status, latency, validation notice)
- ✅ Windows-first setup (PowerShell, venv, VS Code)
- ✅ Pytest suite (11 tests)

**Coming in later phases**
- 🔜 Offline Hindi ASR (IndicConformer-class model)
- 🔜 Offline Santhali TTS with pre-recorded phrase fallback
- 🔜 Full speech-to-speech pipeline with per-stage latency (ASR/MT/TTS/total)
- 🔜 Classroom phrase pack + FLN lessons UI (NIPUN Bharat-aligned, not certified)
- 🔜 Bilingual worksheet generator (PDF) and flashcards
- 🔜 ZIP/folder-based offline sync for Block Resource Centres

## 5. Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn, Pydantic v2, pydantic-settings |
| Database | SQLite via SQLAlchemy 2.x (local file, zero setup) |
| Frontend | Vite 5, React 18, React Router 6, plain CSS (classroom-friendly palette) |
| AI (later) | IndicTrans2 (MT), offline Hindi ASR, offline Santhali TTS — CPU-first, ONNX-ready |
| Testing | Pytest + FastAPI TestClient |
| Platform | Windows 11, VS Code, PowerShell |

## 6. Windows installation (PowerShell)

Prerequisites: **Python 3.11**, **Node.js 18+ (LTS)**, **Git**, **VS Code**.

```powershell
# 0) Open the project in VS Code
cd C:\path\to\RootVerse
code .

# 1) Backend — create and activate a virtual environment
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip

# 2) Configure environment
copy .env.example .env

# 3) Install backend dependencies
pip install -r requirements.txt

# 4) Frontend — open a SECOND PowerShell terminal
cd ..\frontend
npm install
```

### Run the backend (terminal 1)

```powershell
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload
```

### Run the frontend (terminal 2)

```powershell
cd frontend
npm run dev
```

## 7. URLs

| URL | What |
|---|---|
| `http://127.0.0.1:8000/health` | Backend health (API + DB status) |
| `http://127.0.0.1:8000/docs` | Interactive Swagger API docs |
| `http://localhost:5173` | React frontend (dev server) |

The Vite dev server proxies `/health` and `/api/*` to the backend, so the frontend
works with no CORS friction in development.

## 8. API documentation (Phase 1–2 scope)

| Method | Path | Status | Description |
|---|---|---|---|
| GET | `/health` | ✅ live | API + database component status |
| GET | `/` | ✅ live | Service info |
| GET | `/docs` | ✅ live | Interactive Swagger UI |
| POST | `/api/translate/text` | ✅ live | Hindi text → Santhali text (local IndicTrans2) |
| GET | `/api/models/status` | ✅ live | Model load/cache status (honest states) |
| POST | `/api/asr` | 🔜 Phase 5 | Hindi audio → Hindi text |
| POST | `/api/tts` | 🔜 Phase 6 | Santhali text → WAV audio |
| POST | `/api/translate/speech` | 🔜 Phase 7 | Full speech-to-speech pipeline |
| GET/POST | `/api/phrases` | 🔜 Phase 9 | Classroom phrase pack |
| GET/POST | `/api/lessons` | 🔜 Phase 9 | FLN lessons |
| POST | `/api/worksheets/generate` | 🔜 Phase 10 | Printable bilingual worksheet |
| GET | `/api/flashcards` | 🔜 Phase 10 | Flashcard decks |
| POST | `/api/sync` | 🔜 Phase 11 | ZIP/folder import-export |

## 9. AI model setup (one-time manual step)

- **MT:** AI4Bharat **IndicTrans2** `ai4bharat/indictrans2-indic-indic-dist-320M` (Indic-to-Indic, `hin_Deva → sat_Olck`), CPU-first, cached in `backend/model_cache/hf`

The Hugging Face repo is **gated**: create a free account, accept the model
conditions (instant), create a READ token and put it in `backend/.env` as
`HF_TOKEN=...`. The first translation then downloads ~1.3 GB **once**; after
that inference is **100% offline** — no cloud API, no per-request keys.

Detailed steps: [`backend/README.md` → "AI model setup"](backend/README.md).

- **ASR:** offline Hindi recognition (IndicConformer-class) — planned Phase 5
- **TTS:** offline Santhali synthesis with pre-recorded phrase fallback — planned Phase 6

The AI layer is pluggable: real model loaders, honest status reporting, and
clear errors when a model is missing. **No cloud API is used in the core
pipeline.** All AI output is labelled **"Requires native-speaker validation"**.

## 10. Offline mode

`OFFLINE_MODE=true` (default) in `backend/.env`. After the initial model/content
download, translation, lessons, phrases, worksheets and the database all work with
**zero internet**. Sync happens opportunistically at a connected BRC (Phase 11).

## 11. Testing

```powershell
# From the RootVerse root folder, with the backend venv active
python -m pytest tests -v
```

Expected (Phase 1): **3 passed** — health endpoint, root info, unknown-route 404.

## 12. GitHub (Windows / VS Code terminal)

Model weights and audio are git-ignored — never push multi-GB files.

```powershell
git init
git add .
git commit -m "Initial RootVerse SIH prototype"
git branch -M main
git remote add origin <repository-url>
git push -u origin main
```

## 13. Deployment notes

- **Mode 1 — Local Offline AI (the product):** runs on the teacher's Windows laptop. Full models, no internet.
- **Mode 2 — Web Demo (optional):** frontend on Vercel/Netlify + a lightweight Python host for the API with mock/limited models, because free hosting cannot hold multi-GB weights. Same API contract, clearly separated from Mode 1.

## 14. Known limitations (honest status)

- Santhali content in the prototype is **not yet linguistically verified** — placeholders are marked `REQUIRES_LANGUAGE_VALIDATION` until reviewed by a Santhali speaker.
- AI models (ASR/MT/TTS) are **not yet integrated** — the modular interfaces and status reporting land first, then real weights.
- No performance claims are made until latency is actually measured (target: total ≤ 3 s, displayed only after real measurement).
- FLN content is *designed to align with* NIPUN Bharat goals; **no official certification** is claimed.

## 15. Future scope

- Streaming ASR for lower latency · ONNX / quantised CPU inference
- More tribal languages beyond the Santhali prototype
- Teacher dashboard for lesson usage (kept simple, offline)

---

*RootVerse — built for SIH 2026. Offline-first, classroom-first, honest-by-default.*

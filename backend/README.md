# RootVerse Backend (FastAPI)

Offline-first API for the RootVerse classroom language bridge.
Phase 1 scope: application skeleton, configuration, SQLite wiring, health endpoint.

## Setup (Windows PowerShell)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
copy .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload
```

> If PowerShell blocks `activate`, run once in that window:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

## Endpoints (Phase 1–2)

| Method | Path | Description |
|---|---|---|
| GET | `/health` | API + database component status (`ok` / `degraded`) |
| GET | `/` | Service info |
| GET | `/docs` | Interactive Swagger UI |
| POST | `/api/translate/text` | Hindi text → Santali (Ol Chiki) via local IndicTrans2 |
| GET | `/api/models/status` | Honest AI model load status |

Later phases add: `/api/asr`, `/api/tts`, `/api/translate/speech`, `/api/phrases`,
`/api/lessons`, `/api/worksheets/generate`, `/api/flashcards`, `/api/sync`.

## AI model setup (ONE-TIME manual step)

The machine-translation model is **AI4Bharat IndicTrans2**
(`ai4bharat/indictrans2-indic-indic-dist-320M`, open weights, local CPU inference,
no cloud API). Hugging Face gates the repo behind a free account + one-click
conditions acceptance (access is instant and automatic):

1. Create a free account at <https://huggingface.co> (no payment).
2. Open <https://huggingface.co/ai4bharat/indictrans2-indic-indic-dist-320M>
   and click **Agree/accept access** (automatic approval).
3. Create a **READ** token at <https://huggingface.co/settings/tokens>.
4. Put it in `backend/.env`: `HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx`
5. Start the backend. The first translation downloads ~1.3 GB into
   `backend/model_cache/hf` (needs internet once). After that, inference is
   **100% offline** - delete the token if you want; it is only used for download.

Sanity check (from `backend/`, venv active):

```powershell
python scripts/translate_demo.py
```

> All translations are AI-generated: label them **"Requires native-speaker
> validation"** until reviewed by a Santali speaker.

## Project layout

```
app/
├── main.py        FastAPI app: CORS, lifespan (create tables + seed + model preload)
├── config.py      Settings from .env (pydantic-settings)
├── database.py    SQLAlchemy engine/session (SQLite), get_db dependency
├── routers/       health.py, translation.py
├── schemas/       Pydantic models (health, translation)
├── models/        ORM tables: classroom_phrases, fln_lessons,
│                  translation_history, model_metadata
├── services/      seed_service.py (safe seed data)
├── ai/            model_manager.py + translation_service.py (IndicTrans2)
├── utils/         Logging + helpers
└── static/        Static assets
scripts/           translate_demo.py (real local inference sanity check)
model_cache/       Downloaded AI weights (git-ignored, ~1.3 GB after setup)
generated_files/   Generated audio/worksheets (git-ignored)
```

## Troubleshooting (Windows)

| Problem | Fix |
|---|---|
| `python` not found | Install Python 3.11 from python.org, tick "Add to PATH", reopen terminal. Try `py -3.11` instead of `python`. |
| `.venv\Scripts\activate` blocked | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` then retry. |
| Port 8000 busy | `netstat -ano \| findstr :8000` then `taskkill /PID <pid> /F`, or run on another port: `uvicorn app.main:app --reload --port 8001`. |
| DB file location | Relative SQLite paths resolve from the folder you run uvicorn in — always start from `backend/`. |

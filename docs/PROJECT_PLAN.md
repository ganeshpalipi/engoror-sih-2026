# RootVerse — Build Plan (12 Phases)

Status legend: ✅ done · 🔜 planned

| Phase | Scope | Deliverables | Status |
|---|---|---|---|
| 1 | Skeleton | Folder structure, FastAPI skeleton, Vite React skeleton, SQLite config, `.env.example`, `.gitignore`, README, `GET /health` | ✅ |
| 2 | Health check live | Backend boots, `/health` returns API + DB status, Swagger UI works | ✅ |
| 3 | SQLite connected | ORM models (classroom_phrases, fln_lessons, translation_history, model_metadata) + safe seed data (Santali fields = REQUIRES_LANGUAGE_VALIDATION) | ✅ |
| 4 | Translation | Hindi → Santhali MT service (IndicTrans2 `hin_Deva→sat_Olck`, CPU, load-once, offline-first) + `POST /api/translate/text` + `GET /api/models/status` + Text Translation UI. *One-time gated HF download needs a free HF_TOKEN (see backend README).* | ✅ |
| 5 | ASR | Offline Hindi ASR service (WAV in, CPU, model status) | 🔜 |
| 6 | TTS | Offline Santhali TTS service (WAV out, pluggable, pre-recorded fallback) | 🔜 |
| 7 | Pipeline | Full speech-to-speech endpoint `/api/translate/speech` + latency tracking | 🔜 |
| 8 | Frontend wiring | Live Translation / History / Settings pages connected | 🔜 |
| 9 | Content | Classroom phrase pack + FLN lessons (seeded, audio paths) | 🔜 |
| 10 | Materials | Worksheet generator (PDF) + flashcards | 🔜 |
| 11 | Offline sync | ZIP import/export sync module (BRC-ready) + Offline Content page | 🔜 |
| 12 | Hardening | Full test suite, latency measurement, ONNX/quantisation prep, RAM profiling | 🔜 |

> The SIH "Phase 2" build delivered plan rows 3 + 4 (database foundation AND the
> first real AI feature) in one step, per the team's phase instructions.

## Verification after each phase

Every phase is verified **before** the next one starts:

- Backend: `python -m pytest tests -v` (from the `RootVerse/` folder)
- Manual: open `http://127.0.0.1:8000/docs` and exercise the new endpoints
- Frontend: `npm run build` must succeed; pages render at `http://localhost:5173`

## Non-goals (SIH scope discipline)

No social media, payments, leaderboards, gamification, complex analytics,
chatbots, or monetisation. The core priority is the speech-to-speech classroom
bridge, then FLN content, then offline storage and sync.

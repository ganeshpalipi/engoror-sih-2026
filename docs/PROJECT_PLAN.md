# RootVerse — Build Plan (12 Phases)

Status legend: ✅ done · 🔜 planned

| Phase | Scope | Deliverables | Status |
|---|---|---|---|
| 1 | Skeleton | Folder structure, FastAPI skeleton, Vite React skeleton, SQLite config, `.env.example`, `.gitignore`, README, `GET /health` | ✅ |
| 2 | Health check live | Backend boots, `/health` returns API + DB status, Swagger UI works | ✅ |
| 3 | SQLite connected | ORM models (classroom_phrases, fln_lessons, translation_history, model_metadata) + safe seed data (Santali fields = REQUIRES_LANGUAGE_VALIDATION) | ✅ |
| 4 | Translation | Hindi → Santhali MT service (IndicTrans2 `hin_Deva→sat_Olck`, CPU, load-once, offline-first) + `POST /api/translate/text` + `GET /api/models/status` + Text Translation UI. *One-time gated HF download needs a free HF_TOKEN (see backend README).* | ✅ |
| 5 | ASR | **Offline Hindi ASR delivered in the user's "Phase 3" build**: faster-whisper (`Systran/faster-whisper-small`, INT8 CPU, one-time public download into `backend/model_cache/asr`) + `POST /api/asr/transcribe` + `POST /api/classroom/speech-translate` (reuses the Phase 2 MT service) + Live Translation mic UI + `asr_transcriptions` table + `scripts/asr_demo.py` / `scripts/download_asr_model.py` | ✅ |
| 6 | TTS | **Offline Santali TTS delivered in the user's "Phase 4" build**: the only verifiable open-source Santali voice (`Ashraf01k/vernacular-pedagogy-santhali`, Piper-format VITS, MIT, ~60 MB, direct Ol Chiki input, `facebook/mms-tts-sat` does not exist) running on CPU via onnxruntime + `POST /api/tts/synthesize` + `GET /api/tts/audio/{file}` (whitelist) + `GET /api/tts/status` + speech-translate extended with TTS (additive `audio_available`/`audio_url`/`tts_*` fields) + Live Translation "Student Audio" section + TTS status surfaces + `scripts/tts_demo.py` / `scripts/download_tts_model.py` + separate `model_cache/tts` | ✅ |
| 7 | Pipeline | Full speech-to-speech endpoint `/api/translate/speech` (formal endpoint; the working pipeline already runs end-to-end via `POST /api/classroom/speech-translate`) + latency tracking | 🔜 |
| 8 | Frontend wiring | Live Translation / History / Settings pages connected | 🔜 |
| 9 | Content | **Delivered in the user's "Phase 5" build**: 18-lesson FLN bank (10 literacy + 8 numeracy categories, Hindi source text; legacy 4 seed rows upgraded in place) + 13-phrase classroom pack (8 seed + 5 new) + flashcards table (40 cards, 6 topics, local SVG/emoji visuals only) + `GET /api/fln/lessons`, `GET /api/fln/lessons/{id}`, `POST /api/fln/lessons/{id}/translate`, `POST /api/fln/lessons/{id}/audio`, `GET /api/phrases`, `POST /api/phrases/{id}/translate`, `POST /api/phrases/{id}/audio`, `GET /api/flashcards`, `GET /api/flashcards/topics`, `POST /api/flashcards/{id}/translate`, `POST /api/flashcards/{id}/audio` + on-demand Santali generation through the EXISTING IndicTrans2 service (validation_status AI_GENERATED + notice) + audio through the EXISTING TTS service (cached per row) + `scripts/prepare_content.py` (bulk offline translation) + FLN Lessons / Phrase Pack / Flashcards pages | ✅ |
| 10 | Materials | **Delivered in the user's "Phase 5" build**: offline bilingual worksheet generator (6 types: A match, B fill-blank, C count-objects, D MCQ, E picture→word, F Hindi→Santali practice; deterministic per grade/skill/topic/seed) + self-contained printable HTML (embedded Ol Chiki font as base64; browser Print → PDF, no extra dependency) + `POST /api/worksheets/generate`, `GET /api/worksheets/meta`, `GET /api/worksheets/file/{name}` (whitelist) + Worksheets page (form/preview/print/download) + Flashcards page | ✅ |
| 11 | Offline sync | ZIP import/export sync module (BRC-ready) + Offline Content page | 🔜 |
| 12 | Hardening | Full test suite, latency measurement, ONNX/quantisation prep, RAM profiling | 🔜 |

> The SIH "Phase 2" build delivered plan rows 3 + 4 (database foundation AND the
> first real AI feature) in one step, per the team's phase instructions.
> The SIH "Phase 3"/"Phase 4" builds delivered plan rows 5 and 6, completing the
> full 7-step classroom pipeline: Hindi speech → ASR → MT → Santali text → TTS → audio.
> The SIH "Phase 5" build delivered plan rows 9 + 10 (classroom content + materials),
> all powered by the existing offline ASR/MT/TTS services - no new AI engines.

## Verification after each phase

Every phase is verified **before** the next one starts:

- Backend: `python -m pytest tests -v` (from the `RootVerse/` folder)
- Manual: open `http://127.0.0.1:8000/docs` and exercise the new endpoints
- Frontend: `npm run build` must succeed; pages render at `http://localhost:5173`

## Non-goals (SIH scope discipline)

No social media, payments, leaderboards, gamification, complex analytics,
chatbots, or monetisation. The core priority is the speech-to-speech classroom
bridge, then FLN content, then offline storage and sync.

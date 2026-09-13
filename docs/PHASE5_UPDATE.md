# RootVerse — Phase 5 Update (FLN Classroom Content)

**Incremental update over Phase 1–4. Nothing from earlier phases was rebuilt or replaced.**

Phase 5 adds offline Foundational Literacy & Numeracy classroom content to the existing
offline pipeline:

```
Hindi Speech → Offline ASR → Hindi Text → Offline MT → Santali (Ol Chiki)
             → Offline TTS → Student Audio        ← Phases 3+4 (unchanged)

NEW in Phase 5 (built on the same services):
  • FLN lesson bank (18 lessons)      • Classroom phrase pack (13 phrases)
  • Bilingual worksheet generator     • Visual flashcards (40 cards, local assets)
```

No cloud APIs, no LLM APIs, no online image generation. After the existing one-time
model downloads, everything — including Santali text generation, audio and worksheets —
runs with Wi-Fi OFF.

---

## 1. What was added (files)

### Backend — new
| File | Purpose |
|---|---|
| `app/models/flashcard.py` | `flashcards` table (topic, hindi/english word, local visual, Santali, audio) |
| `app/services/content_data.py` | The Hindi SOURCE content pack: 18 lessons, 5 phrase additions, 40 flashcards, worksheet topics. **No Santali text is written by hand anywhere** |
| `app/services/content_seed.py` | Idempotent seeding + `ALTER TABLE` upgrade of an existing Phase 1–4 database (`fln_lessons.category` / `.skill`) |
| `app/services/content_service.py` | Translate-on-demand + audio generation **reusing** `translation_service` and `tts_service`; WAV caching per row |
| `app/services/content_serializers.py` | Row → API schemas (+ 404 helpers) |
| `app/services/worksheet_service.py` | Deterministic 6-type worksheet generator + self-contained printable HTML (Ol Chiki font embedded as base64) |
| `app/schemas/content.py` | Lesson / phrase / flashcard / audio response schemas |
| `app/schemas/worksheet.py` | Worksheet request/response schemas |
| `app/routers/fln.py` | `GET /api/fln/lessons`, `GET /api/fln/lessons/{id}`, `POST .../translate`, `POST .../audio` |
| `app/routers/phrases.py` | `GET /api/phrases`, `POST /api/phrases/{id}/translate`, `POST /api/phrases/{id}/audio` |
| `app/routers/flashcards.py` | `GET /api/flashcards`, `GET /api/flashcards/topics`, `POST .../translate`, `POST .../audio` |
| `app/routers/worksheets.py` | `GET /api/worksheets/meta`, `POST /api/worksheets/generate`, `GET /api/worksheets/file/{name}` (whitelist) |
| `app/static/fonts/NotoSansOlChiki-*.woff2` | Self-hosted Ol Chiki font (embedded into worksheet HTML; worksheets stay offline-renderable) |
| `scripts/prepare_content.py` | One command: upgrade schema → seed → translate the whole content pack offline |
| `tests/test_content_api.py` | 19 tests: lessons / phrases / flashcards APIs, mocked MT+TTS, honest errors |
| `tests/test_worksheet_service.py` | 13 tests: generator, determinism, Hindi-only fallback, whitelist serving, legacy-DB upgrade |

### Backend — modified (additive only)
| File | Change |
|---|---|
| `app/models/fln_lesson.py` | + `category`, `skill` columns (existing DBs upgraded via ALTER TABLE, never rebuilt) |
| `app/models/__init__.py` | Registers the Flashcard model |
| `app/main.py` | Lifespan calls `ensure_phase5_schema` + `seed_phase5_content`; includes the 4 new routers |
| `tests/test_database.py` | Updated seed expectations (18 lessons / 13 phrases / 40 flashcards) + idempotency test. Phase 1–4 tests otherwise untouched |

### Frontend — new
| Path | Purpose |
|---|---|
| `public/fonts/NotoSansOlChiki-*.woff2` | Ol Chiki font for the whole SPA (self-hosted, offline) |
| `public/flashcards/*.svg` | 8 hand-drawn local illustrations: book, apple, tree, sun, circle, triangle, cat, dog (no copyrighted material, nothing fetched at runtime) |

### Frontend — modified
| File | Change |
|---|---|
| `src/pages/Lessons.jsx` | Placeholder → working page: skill/topic filters, lesson detail, Generate Santali, Play Audio |
| `src/pages/Phrases.jsx` | Placeholder → working page: category filter, per-phrase Santali + audio |
| `src/pages/Worksheets.jsx` | Placeholder → working page: form (class/skill/topic/count), generate, preview, print, download |
| `src/pages/Flashcards.jsx` | Placeholder → working page: topic chips, visual grid, per-card Santali + audio |
| `src/pages/Home.jsx` | Roadmap statuses corrected (Phases 1–5 shown honestly) |
| `src/components/Layout.jsx` | Sidebar footer → "Phase 5: FLN classroom content live" |
| `src/index.css` | Phase 5 styles (chips, cards, flashcards, worksheet form/iframe) + Ol Chiki `@font-face` |

### Documentation
- `docs/PHASE5_UPDATE.md` (this file)
- `README.md`, `backend/README.md`, `docs/PROJECT_PLAN.md` updated

### Dependencies
**None added.** Phase 5 uses only the existing pinned stack (FastAPI, SQLAlchemy,
pydantic, onnxruntime, huggingface_hub 0.36.2 …). `torch==2.5.1`,
`transformers==4.46.3`, `huggingface_hub==0.36.2` are untouched. Even the worksheet
PDF path is dependency-free (browser Print → PDF). `requirements.txt` is unchanged.

---

## 2. Database changes

| Table | Change |
|---|---|
| `fln_lessons` | + `category` (topic slug), + `skill` columns. Existing rows are **upgraded in place** (legacy 4 lessons get categories; nothing deleted) |
| `flashcards` | NEW (40 seeded rows) |
| `classroom_phrases` | 5 rows added (existing 8 untouched) |

All changes are applied automatically at server startup (idempotent; safe on your
existing `rootverse.db`).

## 3. Content honesty model (important)

- The seed contains **Hindi source content only**. No Santali is invented by hand.
- Every Santali column starts as `REQUIRES_LANGUAGE_VALIDATION`.
- Translation happens on demand through the **existing Phase 2 IndicTrans2 service**
  (per item via UI buttons, or in bulk via `scripts\prepare_content.py`).
- Translated rows become `validation_status = AI_GENERATED` and every surface
  (lesson page, phrase page, flashcards, worksheets, audio buttons) shows
  **"AI-generated — Requires native-speaker validation"**.
- NIPUN Bharat wording used everywhere: *"Designed around foundational literacy and
  numeracy skills relevant to NIPUN Bharat goals."* — no certification is claimed.
- If the MT model is unavailable, worksheets are still generated (Hindi-only) with
  `santali_available: false` + an on-sheet notice. Nothing is ever faked.

---

## 4. How to apply and verify (Windows PowerShell)

```powershell
# 0) From the RootVerse folder, with the venv active
cd C:\Users\GANESH\Downloads\rootverse\RootVerse
.\.venv\Scripts\Activate.ps1

# 1) Tests (no models needed - AI calls are mocked)
python -m pytest tests -v
# Expected: 84 passed, 1 skipped  (skip = real-ASR test; real-TTS tests run when the voice is cached)

# 2) Start the backend (from the backend folder)
cd backend
uvicorn app.main:app --reload
# Startup automatically: creates flashcards, adds category/skill columns to fln_lessons,
# seeds the Phase 5 content (watch for: "Phase 5 content seeding: {...}")

# 3) One-time content preparation (offline if the MT model is already cached)
python scripts\prepare_content.py
# Translates all 18 lessons + 13 phrases + 40 flashcards via the existing service.
# Internet is NOT needed when backend\model_cache\hf already has IndicTrans2.

# 4) Frontend (second terminal, from the frontend folder)
cd ..\frontend
npm run dev
```

Then open http://localhost:5173 and check:

| Page | Verify |
|---|---|
| **FLN Lessons** | 18 lessons; filter Literacy/Numeracy + topic chips; open a lesson → Hindi text + Santali (or "Generate Santali Translation"); ▶ Play Santali Audio |
| **Phrase Pack** | 13 phrases; category chips; Generate Santali → ▶ Play Santali Audio |
| **Worksheets** | Class 1/2/3 · Literacy/Numeracy · topic · 5/10 questions → Generate → Preview/Print/Download (worksheet includes a teacher answer key) |
| **Flashcards** | 40 cards, topic chips; local SVG/emoji visuals; Hindi + Santali words; 🔊 audio |
| **Model Status** | translation / ASR / TTS statuses unchanged from Phase 4 |

### Wi-Fi OFF verification (after `prepare_content.py` finished once)

```powershell
# Turn Wi-Fi OFF, then:
uvicorn app.main:app --reload      # backend starts fine
# FLN Lessons  → open a lesson → Hindi + Santali visible
# Phrase Pack  → Play Santali Audio → audio plays
# Worksheets   → generate a bilingual worksheet → preview renders (incl. Ol Chiki font)
# Flashcards   → visuals + Santali + audio all local
```

The worksheet HTML embeds the Ol Chiki font (base64), so the script renders even
without any network or locally installed Ol Chiki font.

---

## 5. Worksheet types

| Letter | Type | Built from |
|---|---|---|
| A | Match the word | Hindi ↔ Santali pairs (flashcards / lesson words) |
| B | Fill in the blank | Number sequences (numeracy) or missing word in the lesson sentence + word bank |
| C | Count the objects | Local emoji groups → numeral |
| D | Choose the correct answer | Arithmetic, bigger/smaller, next number, shape names, emoji patterns, picture MCQ |
| E | Picture → word | Emoji/SVG visual → write the Hindi word (Santali shown when available) |
| F | Hindi → Santali vocabulary practice | Word tables + Santali word bank |

Deterministic: same (grade, skill, topic, count, seed) → identical sheet; the API
accepts an optional `seed` for exact regeneration.

## 6. Test results (this build)

```
84 passed, 1 skipped   (was 50 passed, 3 skipped after Phase 4)
```
- The 2 real-TTS tests ran against the real Santali voice during verification.
- The 1 skip is the real-ASR test (runs once `scripts\download_asr_model.py` has been executed).
- All Phase 1–4 tests still pass unchanged.

## 7. Known limitations

- All Santali text/audio is AI-generated and **requires native-speaker validation**
  (marked everywhere; nothing is presented as verified).
- Worksheet "match"/"vocab" types need Santali translations (auto-generated via the
  existing service); without the MT model those types are skipped and the sheet
  becomes Hindi-only with a notice.
- Worksheet PDF is produced via the browser's Print → Save as PDF (chosen deliberately:
  an fpdf2 path would need bundled Indic fonts + complex-text shaping dependencies and
  risks broken Devanagari/Ol Chiki output; the browser shapes both scripts correctly
  with zero extra dependencies).
- Audio caching reuses the Phase 4 TTS file retention (50 newest WAVs); expired files
  regenerate automatically on demand.
- Phase 5 does not modify ASR/MT/TTS performance code (per instructions).

**STOP after Phase 5 — no further phase has been started.**

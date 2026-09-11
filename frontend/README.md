# RootVerse Frontend (Vite + React)

React SPA for the RootVerse classroom language bridge. Phase 1 ships the full
navigation skeleton (12 pages) with a live backend-status home page.

## Setup (Windows PowerShell)

```powershell
cd frontend
npm install
copy .env.example .env   # optional in development
npm run dev
```

Open: http://localhost:5173

## How the API connection works

- In development, `vite.config.js` proxies `/health` and `/api/*` to the FastAPI
  backend at `http://127.0.0.1:8000` — no CORS setup needed.
- All HTTP calls live in `src/services/api.js`, which converts failures into
  human-friendly messages (e.g. "Cannot reach the RootVerse backend...").
- For a deployed frontend (Mode 2 web demo), set `VITE_API_BASE_URL` in `.env`.

## Pages

| Route | Page | Functional in |
|---|---|---|
| `/` | Home (pipeline + backend status) | Phase 1 ✅ |
| `/live-translation` | Live Translation | Phases 5–8 |
| `/text-translation` | Text Translation | Phase 4 |
| `/lessons` | FLN Lessons | Phase 9 |
| `/phrases` | Classroom Phrase Pack | Phase 9 |
| `/worksheets` | Worksheet Generator | Phase 10 |
| `/flashcards` | Flashcards | Phase 10 |
| `/history` | Translation History | Phase 8 |
| `/offline-content` | Offline Content | Phase 11 |
| `/sync` | Sync (BRC) | Phase 11 |
| `/settings` | Settings | Phase 8 |
| `/model-status` | Model Status | Phase 4+ |

## Fonts

Development uses Google Fonts (Noto Sans Devanagari + Noto Sans Ol Chiki).
Before offline deployment, self-host the fonts in `src/assets/fonts` so the
app never needs the internet (tracked in the Phase 11 checklist).

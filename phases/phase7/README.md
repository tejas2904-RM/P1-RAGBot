# Phase 7 — Frontend Deployment (Vercel)

Deploy the Phase 5 static chat UI on [Vercel](https://vercel.com). The UI calls the **Phase 6 Render** API via `API_BASE_URL`.

## Architecture

```
Browser → Vercel (static UI) → API_BASE_URL → Render (Phase 6 FastAPI)
```

No API keys on Vercel — only the public Render backend URL.

## What runs

| Module | Purpose |
|--------|---------|
| `vercel.json` (repo root) | Static build, output dir, SPA rewrites |
| `phases/phase7/inject_config.mjs` | Vercel build — writes `config.js` from `API_BASE_URL` |
| `phases/phase7/build.py` | Validate frontend bundle + write `config.js` (Python) |
| `phases/phase7/run.py` | Local preview server after build |
| `phases/phase5/frontend/` | HTML/CSS/JS source |

## Local preview

Point at your Render API (or leave empty for same-origin Phase 5):

```powershell
$env:API_BASE_URL="https://m2-ragbot-api.onrender.com"
python -m phases.phase7.run
# http://127.0.0.1:4173/
```

Build only:

```bash
python -m phases.phase7.build
# or: node phases/phase7/inject_config.mjs > phases/phase5/frontend/config.js
```

## Deploy on Vercel

1. Deploy **Phase 6 on Render first** and copy the API URL.
2. [vercel.com/new](https://vercel.com/new) → import your repo (e.g. `P1-RAGBot`).
3. **Framework Preset:** Other — root `vercel.json` handles the static build.
4. **Environment variable** (required):

| Name | Value |
|------|--------|
| `API_BASE_URL` | `https://m2-ragbot-api.onrender.com` |

No trailing slash. Do **not** set `GROQ_API_KEY` or `OPENAI_API_KEY` on Vercel.

5. Deploy and open your Vercel URL.
6. On **Render**, set `API_CORS_ORIGINS` to your Vercel URL and redeploy the API.

## Smoke test

1. Vercel URL loads dark chat UI + disclaimer.
2. `GET /config.js` shows correct `API_BASE_URL` (no API keys).
3. Factual question → answer + Groww source link.
4. Advisory question → refusal, no external link.

## Tests

```bash
pytest tests/phase7 -v
```

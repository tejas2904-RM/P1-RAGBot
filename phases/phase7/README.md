# Phase 7 — Frontend Deployment (Vercel)

Deploy the Phase 5 static chat UI on [Vercel](https://vercel.com). The UI calls the **Phase 6 Render** API via `API_BASE_URL`.

## Architecture

```
Browser → Vercel (static UI) → API_BASE_URL → Render (Phase 6 FastAPI)
```

No API keys on Vercel — only the public Render backend URL.

## Deploy on Vercel

1. Deploy **Phase 6 on Render first** and copy the API URL.
2. [vercel.com/new](https://vercel.com/new) → import **M2-RAGBOT**.
3. **Framework Preset:** Other (static — root `vercel.json` handles build).
4. **Environment variable** (required):

| Name | Value |
|------|--------|
| `API_BASE_URL` | `https://m2-ragbot-api.onrender.com` |

No trailing slash. Do **not** set `GROQ_API_KEY` on Vercel.

5. Deploy. Open your Vercel URL.

6. On **Render**, set `API_CORS_ORIGINS` to your Vercel URL and redeploy the API.

## Files

| File | Purpose |
|------|---------|
| `vercel.json` | Static build + SPA rewrites (repo root) |
| `phases/phase7/inject_config.mjs` | Build-time `config.js` from `API_BASE_URL` |
| `phases/phase5/frontend/` | HTML/CSS/JS source |

## Local frontend against remote API

```powershell
$env:API_BASE_URL="https://m2-ragbot-api.onrender.com"
node phases/phase7/inject_config.mjs > phases/phase5/frontend/config.js
```

## Smoke test

1. Vercel URL loads dark chat UI + disclaimer.
2. `GET /config.js` shows correct `API_BASE_URL`.
3. Factual question → answer + Groww source link.
4. Advisory question → refusal, no external link.

## Tests

```bash
pytest tests/phase7 -v
```

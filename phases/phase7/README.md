# Phase 7 — Frontend Deployment (Vercel)

Deploy the Phase 5 static chat UI to [Vercel](https://vercel.com) and point it at your Phase 6 FastAPI backend.

## Architecture

```
Browser (Vercel CDN)  →  config.js (API_BASE_URL)  →  Phase 6 FastAPI API
  phases/phase5/frontend/          POST /api/v1/chat
                                   GET  /api/v1/meta
                                   GET  /health
```

The frontend is static HTML/CSS/JS. No API keys in the browser — only the public backend URL.

## Deploy to Vercel

1. Import [tejas2904-RM/M2-RAGBOT](https://github.com/tejas2904-RM/M2-RAGBOT) on [vercel.com/new](https://vercel.com/new).
2. **Framework Preset:** Other (static)
3. Leave **Root Directory** empty — root `vercel.json` sets:
   - `outputDirectory`: `phases/phase5/frontend`
   - `buildCommand`: injects `config.js` from env
4. **Environment variables** (Project → Settings → Environment Variables):

| Variable | Example | Required |
|----------|---------|----------|
| `API_BASE_URL` | `https://your-api.onrender.com` | Yes |

No trailing slash. This is the public URL of `phases/phase6/api_server.py` (Render, Railway, Fly.io, etc.).

5. Deploy. Note your URL: `https://m2-ragbot.vercel.app` (or custom domain).

## Backend CORS

Allow your Vercel origin on the API server:

```env
API_CORS_ORIGINS=https://m2-ragbot.vercel.app,http://127.0.0.1:8000
```

FastAPI also allows `https://*.vercel.app` via regex automatically.

## Local development

**Same server (Phase 5):** `config.js` uses empty `API_BASE_URL` → same-origin requests.

```bash
python -m phases.phase5.run
# http://127.0.0.1:8000/
```

**Frontend only against remote API:**

```bash
# Windows PowerShell
$env:API_BASE_URL="https://your-api.onrender.com"
python phases/phase7/inject_config.py > phases/phase5/frontend/config.js
# Serve frontend with any static server, or use Phase 5 for /config.js route
```

See `phases/phase5/frontend/config.example.js` for the shape of `window.__ENV__`.

## Build script

```bash
API_BASE_URL=https://your-api.example.com python phases/phase7/inject_config.py
```

Writes:

```javascript
window.__ENV__ = {"API_BASE_URL": "https://your-api.example.com"};
```

## Files

| File | Purpose |
|------|---------|
| `vercel.json` | Vercel build + SPA rewrites |
| `phases/phase7/inject_config.py` | Build-time config generator |
| `phases/phase5/frontend/config.js` | Runtime API base (generated on Vercel) |
| `phases/phase5/frontend/config.example.js` | Example for manual setup |

## Smoke test (production)

1. Open Vercel URL — dark chat UI loads, disclaimer visible.
2. DevTools → Network: `GET /config.js` contains your `API_BASE_URL`.
3. `GET {API_BASE_URL}/health` returns `index_ready: true`.
4. Ask: *What is the expense ratio of HDFC Mid Cap Fund?* → answer + Groww source link.
5. Ask: *Should I invest in HDFC Mid Cap?* → refusal, no external link.

## Tests

```bash
pytest tests/phase7 -v
```

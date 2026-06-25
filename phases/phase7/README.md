# Phase 7 — Frontend Deployment (Vercel)

Deploy the chat UI and API on [Vercel](https://vercel.com) via FastAPI (`pyproject.toml` entrypoint).

## Recommended: unified FastAPI on Vercel

Vercel detects Python/FastAPI in this repo. Use the ASGI entrypoint in `pyproject.toml`:

```toml
[tool.vercel]
entrypoint = "phases.phase6.api_server:app"
```

This serves **both** the Phase 5 UI (`/`) and API (`/api/v1/chat`, `/health`) from one deployment. Leave `API_BASE_URL` **unset** — the frontend uses same-origin requests.

### Deploy steps

1. Import [tejas2904-RM/M2-RAGBOT](https://github.com/tejas2904-RM/M2-RAGBOT) on [vercel.com/new](https://vercel.com/new).
2. **Framework Preset:** FastAPI (or Other — `pyproject.toml` defines the entrypoint).
3. **Environment variables** (Project → Settings → Environment Variables):

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Yes | LLM answers |
| `OPENAI_API_KEY` | Yes* | Embeddings (`EMBEDDING_PROVIDER=openai`) |
| `GENERATOR_PROVIDER` | No | Default `groq` |
| `EMBEDDING_PROVIDER` | No | Default `openai` |

\* Or set `EMBEDDING_PROVIDER=deterministic` for tests (not recommended in production).

4. Deploy. Open your Vercel URL — chat UI and API share the same origin.

On cold start, the app rebuilds the vector index in `/tmp` from `corpus/processed/embedded_chunks.json` (bundled in the repo).

---

## Alternative: static frontend + external API

If the API runs elsewhere (Render, Railway, Streamlit sidecar), set:

| Variable | Example |
|----------|---------|
| `API_BASE_URL` | `https://your-api.onrender.com` |

The build writes `config.js` so the static UI calls that host. Use this only if you split frontend/API across two deployments.

## Architecture (unified)

```
Browser → Vercel (FastAPI) → Phase 6 bootstrap → Phase 4 pipeline → vector index
              /                  /api/v1/chat
              /static/…
```

## Architecture (split frontend + API)

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

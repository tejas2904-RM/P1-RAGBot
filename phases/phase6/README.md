# Phase 6 — Backend Deployment (Render)

Deploy the FastAPI REST API on [Render](https://render.com). This backend powers the Phase 7 Vercel frontend.

## What runs

| Module | Purpose |
|--------|---------|
| `phases/phase6/api_server.py` | ASGI entry — bootstrap + Phase 5 FastAPI routes |
| `phases/phase6/bootstrap.py` | Env load, vector index warmup from `corpus/processed/` |
| `phases/phase6/build.py` | Render build step — validates embedded corpus |
| `phases/phase6/config.py` | Render service name and env var constants |
| `render.yaml` (repo root) | Render Blueprint for one-click deploy |

Endpoints: `/health`, `/api/v1/meta`, `/api/v1/chat`, `/api/v1/disclaimer`

## Local run

```bash
pip install -r requirements.txt
python -m phases.phase6.run
# http://127.0.0.1:8000/health
```

## Deploy on Render

1. Push `main` to [tejas2904-RM/M2-RAGBOT](https://github.com/tejas2904-RM/M2-RAGBOT).
2. [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint**.
3. Connect the repo — Render reads `render.yaml` and creates **`m2-ragbot-api`**.
4. Set environment variables when prompted:

| Variable | Required |
|----------|----------|
| `GROQ_API_KEY` | Yes |
| `OPENAI_API_KEY` | Yes* |
| `API_CORS_ORIGINS` | Yes (after Vercel deploy — your `https://*.vercel.app` URL) |

\* Or `EMBEDDING_PROVIDER=deterministic` for offline tests only.

5. Deploy. Copy the URL, e.g. `https://m2-ragbot-api.onrender.com`.
6. Test: `GET /health` → `"index_ready": true`.

Use this URL as **`API_BASE_URL`** in Phase 7 (Vercel).

## Manual Render setup

- **Runtime:** Python 3.13
- **Build:** `pip install -r requirements.txt && python -m phases.phase6.build`
- **Start:** `python -m uvicorn phases.phase6.api_server:app --host 0.0.0.0 --port $PORT`
- **Health check path:** `/health`

## Tests

```bash
pytest tests/phase6 -v
```

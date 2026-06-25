# Phase 6 — Backend Deployment (Streamlit Community Cloud)

Host the RAG backend on [Streamlit Community Cloud](https://streamlit.io/cloud) with optional headless FastAPI for the Vercel frontend (Phase 7).

## What runs where

| Entry | Purpose |
|-------|---------|
| `phases/phase6/streamlit_app.py` | Streamlit Cloud UI — chat, health, disclaimer |
| `phases/phase6/api_server.py` | Headless FastAPI (same routes as Phase 5) for Vercel / Render / Railway |

Both reuse `phases.phase5.service` and `phases.phase4.pipeline.handle_query` — no duplicated RAG logic.

## Local run

```bash
pip install -r requirements.txt

# Streamlit UI (http://127.0.0.1:8501)
python -m phases.phase6.run streamlit

# Headless API (http://127.0.0.1:8000)
python -m phases.phase6.run api
```

### Local Streamlit secrets

```bash
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
# Edit .streamlit\secrets.toml with your keys (never commit secrets.toml)
```

Or use `.env` in the project root (loaded before Streamlit secrets).

## Streamlit Community Cloud deploy

1. Push `main` to [tejas2904-RM/M2-RAGBOT](https://github.com/tejas2904-RM/M2-RAGBOT).
2. [Streamlit Cloud](https://share.streamlit.io/) → **New app** → select repo, branch `main`.
3. **Main file path:** `phases/phase6/streamlit_app.py`
4. **App settings → Secrets** — paste TOML (same shape as `.streamlit/secrets.toml.example`):

```toml
GROQ_API_KEY = "gsk_..."
OPENAI_API_KEY = "sk-..."
EMBEDDING_PROVIDER = "openai"
GENERATOR_PROVIDER = "groq"
```

5. Deploy. On first boot the app rebuilds the vector index from `corpus/processed/embedded_chunks.json` if `data/vector_store/` is absent.

## Headless API deploy (for Phase 7 Vercel)

Deploy `phases/phase6/api_server.py` on Render, Railway, or Fly.io:

```bash
python -m phases.phase6.run api
# or: uvicorn phases.phase6.api_server:app --host 0.0.0.0 --port $PORT
```

Set environment variables:

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | LLM generation |
| `OPENAI_API_KEY` | Embeddings (if `EMBEDDING_PROVIDER=openai`) |
| `API_CORS_ORIGINS` | Vercel URL(s), comma-separated |
| `PORT` | Cloud host port (usually injected) |

## Index bootstrap

On startup, Phase 6:

1. Loads `.env` and Streamlit secrets into `os.environ`
2. Checks vector index health (`≥ 50` chunks)
3. If missing, upserts from `corpus/processed/embedded_chunks.json`
4. If that file is missing, runs the full Phase 2 pipeline

Commit `corpus/processed/` to the repo. The GitHub Actions reindex workflow keeps corpus fresh; after deploy, unchanged hashes skip re-embed locally.

## Tests

```bash
pytest tests/phase6 -v
```

## Security

- Never commit `.env`, `.streamlit/secrets.toml`, or API keys
- Streamlit Cloud secrets are injected at runtime only
- No PII fields in the UI; query text is not logged in Phase 6

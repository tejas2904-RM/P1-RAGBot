# Phase 5 — FAQ Assistant (API + UI)

FastAPI backend and minimal HTML/JS frontend for the HDFC mutual fund FAQ assistant.

## Run

```bash
pip install -r requirements.txt
python -m phases.phase5.run
```

Open **http://127.0.0.1:8000/** for the chat UI.

API docs: http://127.0.0.1:8000/docs

## Frontend (`frontend/`)

| File | Role |
|------|------|
| `index.html` | UI shell — disclaimer banner, welcome, examples, chat form |
| `static/css/styles.css` | Layout and styling |
| `static/js/app.js` | Loads `/api/v1/meta`, wires example buttons, posts to `/api/v1/chat` |

Requirements met:
- Persistent disclaimer (header + footer)
- Welcome message from API
- Exactly 3 clickable example questions
- Single free-text query input (no PII fields)
- Factual answers show body, source link, and last-updated footer

## API

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/` | Chat UI |
| `GET` | `/health` | Index readiness |
| `GET` | `/api/v1/meta` | Bootstrap metadata |
| `POST` | `/api/v1/chat` | Q&A |

## Environment

| Variable | Purpose |
|----------|---------|
| `API_CORS_ORIGINS` | Extra allowed origins (same-host UI needs no CORS) |
| `GROQ_API_KEY` | Groq LLM (optional) |
| `OPENAI_API_KEY` | Embeddings for retrieval |

## Tests

```bash
pytest tests/phase5 -v
```

# Mutual Fund FAQ Assistant (RAG Chatbot)

Facts-only FAQ assistant for five HDFC mutual fund schemes, using pinned Groww scheme pages as the sole data source.

## Project structure

```
RAG-Chatbot/
├── Docs/                    # Problem statement, architecture, edge cases
├── corpus/                  # Shared corpus artifacts (output of Phase 1+)
│   ├── urls.json
│   ├── metadata/
│   └── raw/
├── phases/
│   ├── phase1/              # Corpus definition & source curation ✅
│   ├── phase2/              # Ingestion & vector indexing (2.1–2.8 ✅)
│   ├── phase3/              # RAG core ✅
│   ├── phase4/              # Refusal & classification ✅
│   ├── phase5/              # API + UI ✅
│   ├── phase6/              # Render backend deploy ✅
│   └── phase7/              # Vercel frontend deploy ✅
└── tests/
    └── phase1/
```

Each implementation phase lives in its own folder under `phases/`. Shared data artifacts are stored under `corpus/`.

## Setup

```bash
pip install -r requirements.txt
copy .env.example .env   # Windows — then edit .env with your API keys
```

Set keys in `.env`:

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Groq LLM for Phase 3 answers |
| `OPENAI_API_KEY` | OpenAI embeddings for Phase 2 indexing |

For offline tests, use `EMBEDDING_PROVIDER=deterministic` and `GENERATOR_PROVIDER=template` in `.env`.

## Phase 1 — Run corpus curation

```bash
python -m phases.phase1.run
```

This validates `corpus/urls.json`, writes `scheme_registry.json`, fetches all five Groww pages, and updates `source_registry.json` with content hashes.

## Phase 3 — Ask a factual question

```bash
python -m phases.phase3.run "What is the expense ratio of HDFC Mid Cap Fund?"
```

Requires a populated vector index (`data/vector_store/` from Phase 2.7).

## Phase 4 — Classified assistant (recommended)

```bash
python -m phases.phase4.run "What is the expense ratio of HDFC Mid Cap Fund?"
python -m phases.phase4.run "Should I invest in HDFC Mid Cap?"
```

Routes factual queries to RAG; refuses advisory, comparative, performance, PII, and out-of-scope queries with fixed link-free messages.

## Phase 5 — Web UI + API

```bash
python -m phases.phase5.run
```

Open **http://127.0.0.1:8000/** for the chat UI (disclaimer, welcome, 3 example questions, Q&A).

## Phase 6 — Render backend

```bash
python -m phases.phase6.run
```

Deploy via `render.yaml` Blueprint on [Render](https://render.com). See `phases/phase6/README.md`.

## Phase 7 — Vercel frontend

```bash
python -m phases.phase7.run
```

Set `API_BASE_URL` to your Render API for cross-origin preview. Deploy on [Vercel](https://vercel.com) — see `phases/phase7/README.md`.

## Tests

```bash
pytest tests/phase1 -v
pytest tests/phase2 -v
pytest tests/phase3 -v
pytest tests/phase4 -v
pytest tests/phase5 -v
pytest tests/phase6 -v
pytest tests/phase7 -v
```

## Pinned schemes (HDFC Mutual Fund)

| Scheme | Groww URL |
|--------|-----------|
| HDFC Mid Cap Fund | [link](https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth) |
| HDFC Equity Fund | [link](https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth) |
| HDFC Focused Fund | [link](https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth) |
| HDFC ELSS Tax Saver Fund | [link](https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth) |
| HDFC Large Cap Fund | [link](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth) |

**Disclaimer:** Facts-only. No investment advice.

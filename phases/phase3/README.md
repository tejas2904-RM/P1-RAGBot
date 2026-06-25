# Phase 3 — RAG Core (Retrieval + Generation)

Metadata-first retrieval with vector fallback; template or Groq generation.

## Strategy

1. **Resolve** `scheme_id` (`SchemeResolver`) and `field`(s) (`field_resolver`)
2. **Retrieve** with Chroma metadata filters (`top_k=1` when both known)
3. **Generate** answer body (template offline, **Groq** in production)
4. **Format** with single Groww citation + footer; validate ≤3 sentences

See `Docs/PhaseWiseArchitecture.md` § Phase 3.

## CLI

```bash
# Requires indexed corpus (Phase 2.7)
python -m phases.phase3.run "What is the expense ratio of HDFC Mid Cap Fund?"

# JSON output
python -m phases.phase3.run "Minimum SIP for HDFC Large Cap Fund?" --json

# Tests (deterministic embeddings + template generator)
pytest tests/phase3 -v
```

## Environment

Copy `.env.example` to `.env` in the project root and set your keys. The app loads `.env` automatically via `python-dotenv`.

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Groq API key for LLM generation |
| `GENERATOR_PROVIDER` | `template`, `groq`, or `auto` (default) |
| `GENERATOR_MODEL` | Groq model (default `llama-3.3-70b-versatile`) |
| `OPENAI_API_KEY` | OpenAI API key for embeddings (`text-embedding-3-small`) |
| `EMBEDDING_PROVIDER` | `openai`, `deterministic` (tests/offline) |
| `EMBEDDING_MODEL` | Embedding model (default `text-embedding-3-small`) |

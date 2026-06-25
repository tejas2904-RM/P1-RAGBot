# Phase 4 — Refusal Handling & Query Classification

Rule-based classifier routes queries to fixed refusals or the Phase 3 RAG pipeline.

## Flow

1. **Classify** query (`query_classifier.py`)
2. **Refuse** with fixed text (no URLs) for advisory, comparative, performance, PII, out-of-scope
3. **RAG** for factual in-corpus queries (`phases.phase3.pipeline.answer_query`)

## CLI

```bash
python -m phases.phase4.run "Should I invest in HDFC Mid Cap?"
python -m phases.phase4.run "What is the expense ratio of HDFC Mid Cap Fund?"
python -m phases.phase4.run "What is the expense ratio of HDFC Mid Cap Fund?" --json

pytest tests/phase4 -v
```

## Refusal templates

All refusals are link-free (no AMFI/SEBI/Groww URLs). See `config.py` and `Docs/PhaseWiseArchitecture.md` § Phase 4.

## Modules

| Module | Role |
|--------|------|
| `query_classifier.py` | Rule-based routing |
| `refusal_handler.py` | Advisory / comparative / PII |
| `performance_handler.py` | Returns / performance |
| `handlers.py` | Category → fixed message |
| `pipeline.py` | `handle_query()` orchestrator |
| `run.py` | CLI |

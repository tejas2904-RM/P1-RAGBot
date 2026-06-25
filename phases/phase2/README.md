# Phase 2 — Document Ingestion & Vector Indexing

Subphases are implemented incrementally under `phases/phase2/`.

| Subphase | Status | Module |
|----------|--------|--------|
| **2.1** Groww selectors & field map | ✅ Done | `groww_selectors.py` |
| **2.2** HTML / JSON parsing | ✅ Done | `parser.py` |
| **2.3** Value normalization | ✅ Done | `normalizer.py` |
| **2.4** Fact statement synthesis | ✅ Done | `fact_builder.py` |
| **2.5** Chunking & metadata | ✅ Done | `chunker.py` |
| **2.6** Embedding pipeline | ✅ Done | `embedder.py` |
| **2.7** Vector index upsert | ✅ Done | `indexer.py`, `run.py` |
| **2.8** Re-index job + scheduler | ✅ Done | `reindex_job.py`, `.github/workflows/reindex-corpus.yml` |

## Phase 2.2 — Parser

```bash
python -c "from phases.phase2.parser import parse_scheme_snapshot; p=parse_scheme_snapshot('hdfc-mid-cap'); print(p.fields['expense_ratio'])"
```

## Phase 2.3 — Normalizer

```bash
pytest tests/phase2/test_normalizer.py -v
```

## Phase 2.6 — Embedder

Default model: `text-embedding-3-small` (OpenAI). Set `EMBEDDING_API_KEY` or `OPENAI_API_KEY`.

```bash
# Production (OpenAI)
python -c "from phases.phase2.embedder import embed_chunks_from_corpus, save_embedded_chunks_json; save_embedded_chunks_json(embed_chunks_from_corpus())"

# Offline / tests (deterministic vectors, no API key)
set EMBEDDING_PROVIDER=deterministic
python -c "from phases.phase2.embedder import DeterministicEmbeddingBackend, embed_chunks_from_corpus, save_embedded_chunks_json; save_embedded_chunks_json(embed_chunks_from_corpus(backend=DeterministicEmbeddingBackend()))"

pytest tests/phase2/test_embedder.py -v
```

Output: `corpus/processed/embedded_chunks.json`

## Phase 2.7 — Vector index

Uses local Chroma DB at `data/vector_store/`.

```bash
# Full pipeline (facts -> chunks -> embed -> index)
python -m phases.phase2.run --embedding-provider deterministic

# Index only (requires embedded_chunks.json)
python -c "from phases.phase2.indexer import upsert_index_from_corpus; upsert_index_from_corpus()"

# Check index health
python -m phases.phase2.run --stats-only

pytest tests/phase2/test_indexer.py -v
```

pytest tests/phase2/test_indexer.py -v
```

## Phase 2.8 — Re-index job & GitHub Actions scheduler

Hash-diff selective refresh: only schemes whose Phase 1 `content_hash` changed are re-parsed, re-embedded, and upserted.

```bash
# After fetching latest HTML (Phase 1)
python -m phases.phase1.run
python -m phases.phase2.reindex_job

# Force one scheme
python -m phases.phase2.reindex_job --scheme hdfc-mid-cap --json

# Scheduled CI: .github/workflows/reindex-corpus.yml (daily 09:15 IST / 03:45 UTC + workflow_dispatch)
pytest tests/phase2/test_reindex_job.py -v
```

## Phase 2.5 — Chunker

```bash
python -c "from phases.phase2.chunker import build_chunks_from_corpus, save_chunks_json; save_chunks_json(build_chunks_from_corpus())"
pytest tests/phase2/test_chunker.py -v
```

Output: `corpus/processed/chunks.json` (56 chunks, 1:1 with facts)

## Phase 2.4 — Fact builder

```bash
python -c "from phases.phase2.fact_builder import build_all_facts, save_facts_json; save_facts_json(build_all_facts())"
pytest tests/phase2/test_fact_builder.py -v
```

Output: `corpus/processed/facts.json`

## Tests

```bash
pytest tests/phase2 -v
```

See `Docs/PhaseWiseArchitecture.md` § Phase 2.

# Phase 1 — Corpus Definition & Source Curation

Establishes the bounded knowledge base from **five pinned HDFC scheme pages on Groww**.

## Deliverables

| Artifact | Path |
|----------|------|
| Canonical URLs | `corpus/urls.json` |
| Scheme registry (with aliases) | `corpus/metadata/scheme_registry.json` |
| Source registry (fetch status + hash) | `corpus/metadata/source_registry.json` |
| Raw HTML snapshots | `corpus/raw/*.html` |

## Modules

| Module | Purpose |
|--------|---------|
| `config.py` | `ALLOWED_URLS` allowlist and scheme aliases |
| `validator.py` | Validates `urls.json` against allowlist |
| `registry.py` | Load/save JSON registries |
| `fetcher.py` | Allowlist-enforced HTTP fetch + `content_hash` |
| `scheme_resolver.py` | Map query text → `scheme_id` |
| `run.py` | CLI entry point |

## Usage

From project root:

```bash
pip install -r requirements.txt

# Validate config and fetch all 5 Groww pages
python -m phases.phase1.run

# Validate only (no network)
python -m phases.phase1.run --no-fetch
```

## Exit criteria

- Exactly 5 URLs from `ALLOWED_URLS` in `urls.json`
- Categories: mid-cap, flexi-cap, focused, elss, large-cap
- All fetches store raw HTML + `source_registry.json` entries
- No URL outside the allowlist is ever fetched

See `Docs/PhaseWiseArchitecture.md` and `Docs/PhaseEdgeCases.md` for full specification.

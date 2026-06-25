"""Phase 2 CLI — chain ingestion subphases 2.2 through 2.7."""

from __future__ import annotations

import argparse
import sys

from phases.phase2.chunker import build_chunks_from_corpus, save_chunks_json
from phases.phase2.embedder import (
    DeterministicEmbeddingBackend,
    embed_chunks_from_corpus,
    get_embedding_backend,
    save_embedded_chunks_json,
)
from phases.phase2.fact_builder import build_all_facts, save_facts_json
from phases.phase2.indexer import get_index_stats, upsert_index
from phases.phase1.validator import ValidationError


def run(
    *,
    rebuild_facts: bool = False,
    embedding_provider: str | None = None,
) -> int:
    """Run Phase 2 pipeline: facts -> chunks -> embeddings -> vector index."""
    import os

    if embedding_provider:
        os.environ["EMBEDDING_PROVIDER"] = embedding_provider

    backend = (
        DeterministicEmbeddingBackend()
        if os.getenv("EMBEDDING_PROVIDER", "openai").lower() == "deterministic"
        else get_embedding_backend()
    )

    print("Phase 2.4 — Building facts...")
    facts = build_all_facts()
    facts_path = save_facts_json(facts)
    print(f"  Wrote {len(facts)} facts -> {facts_path}")

    print("Phase 2.5 — Building chunks...")
    chunks = build_chunks_from_corpus()
    chunks_path = save_chunks_json(chunks)
    print(f"  Wrote {len(chunks)} chunks -> {chunks_path}")

    print("Phase 2.6 — Embedding chunks...")
    embedded = embed_chunks_from_corpus(backend=backend)
    embedded_path = save_embedded_chunks_json(embedded)
    print(f"  Wrote {len(embedded)} embedded chunks -> {embedded_path}")

    print("Phase 2.7 — Upserting vector index...")
    stats = upsert_index(embedded)
    print(
        f"  Index ready={stats.ready}; chunks={stats.chunk_count}; "
        f"model={stats.embedding_model}; path={stats.index_path}"
    )

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 — Ingestion pipeline (2.4–2.7)")
    parser.add_argument(
        "--rebuild-facts",
        action="store_true",
        help="Rebuild facts from raw HTML snapshots (default behavior)",
    )
    parser.add_argument(
        "--embedding-provider",
        choices=["openai", "deterministic"],
        help="Embedding backend (default: openai, or EMBEDDING_PROVIDER env)",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Print vector index stats and exit",
    )
    args = parser.parse_args()

    if args.stats_only:
        stats = get_index_stats()
        print(stats.to_dict())
        raise SystemExit(0 if stats.ready else 1)

    try:
        code = run(rebuild_facts=args.rebuild_facts, embedding_provider=args.embedding_provider)
    except ValidationError as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        code = 1

    raise SystemExit(code)


if __name__ == "__main__":
    main()

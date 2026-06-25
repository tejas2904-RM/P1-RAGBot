"""Phase 2.8 — Hash-diff selective re-parse, re-embed, and vector index refresh."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from phases import paths
from phases.phase1.registry import load_source_registry
from phases.phase1.validator import ValidationError
from phases.phase2.chunker import (
    build_chunks,
    load_chunks_json,
    load_facts_json,
    save_chunks_json,
    validate_chunks,
)
from phases.phase2.embedder import (
    EmbeddingBackend,
    embed_chunks,
    get_embedding_backend,
    load_embedded_chunks_json,
    save_embedded_chunks_json,
    validate_embeddings,
)
from phases.phase2.fact_builder import (
    build_facts_for_scheme,
    save_facts_json,
    validate_facts,
)
from phases.phase2.indexer import (
    delete_scheme_from_index,
    get_index_stats,
    load_index_registry,
    upsert_index,
)
from phases.phase2.models import EmbeddedChunk, FactRecord, ReindexReport

logger = logging.getLogger(__name__)


def get_current_source_hashes() -> dict[str, str]:
    """Return content_hash per scheme from Phase 1 source_registry.json."""
    hashes: dict[str, str] = {}
    for record in load_source_registry():
        if record.status == "ok" and record.content_hash:
            hashes[record.scheme_id] = record.content_hash
    return hashes


def get_indexed_hashes(registry_path: Path | None = None) -> dict[str, str]:
    """Return last-indexed content_hash per scheme from index_registry.json."""
    registry = load_index_registry(registry_path)
    if not registry:
        return {}
    raw = registry.get("scheme_content_hashes", {})
    return {str(scheme_id): str(content_hash) for scheme_id, content_hash in raw.items()}


def detect_changed_schemes(
    *,
    source_hashes: dict[str, str] | None = None,
    indexed_hashes: dict[str, str] | None = None,
) -> tuple[list[str], list[str]]:
    """Compare source vs indexed hashes. Returns (changed, unchanged) scheme ids."""
    source = source_hashes if source_hashes is not None else get_current_source_hashes()
    indexed = indexed_hashes if indexed_hashes is not None else get_indexed_hashes()

    changed: list[str] = []
    unchanged: list[str] = []
    for scheme_id, content_hash in sorted(source.items()):
        if indexed.get(scheme_id) != content_hash:
            changed.append(scheme_id)
        else:
            unchanged.append(scheme_id)
    return changed, unchanged


def _load_facts_or_empty(facts_path: Path | None = None) -> list[FactRecord]:
    path = facts_path or paths.FACTS_FILE
    if not path.exists():
        return []
    return load_facts_json(path)


def _load_chunks_or_empty(chunks_path: Path | None = None):
    path = chunks_path or paths.CHUNKS_FILE
    if not path.exists():
        return []
    return load_chunks_json(path)


def _load_embedded_or_empty(embedded_path: Path | None = None) -> list[EmbeddedChunk]:
    path = embedded_path or paths.EMBEDDED_CHUNKS_FILE
    if not path.exists():
        return []
    return load_embedded_chunks_json(path)


def _remove_scheme_records(
    scheme_id: str,
    *,
    facts: list[FactRecord],
    chunks: list,
    embedded: list[EmbeddedChunk],
) -> tuple[list[FactRecord], list, list[EmbeddedChunk]]:
    facts = [item for item in facts if item.scheme_id != scheme_id]
    chunks = [item for item in chunks if item.scheme_id != scheme_id]
    embedded = [item for item in embedded if item.chunk.scheme_id != scheme_id]
    return facts, chunks, embedded


def _build_scheme_content_hashes(embedded: list[EmbeddedChunk]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for item in embedded:
        if item.chunk.content_hash:
            hashes[item.chunk.scheme_id] = item.chunk.content_hash
    return hashes


def reindex_schemes(
    scheme_ids: list[str],
    *,
    backend: EmbeddingBackend | None = None,
    index_path: Path | None = None,
    facts_path: Path | None = None,
    chunks_path: Path | None = None,
    embedded_path: Path | None = None,
) -> ReindexReport:
    """Re-parse, re-embed, and upsert only the given scheme ids."""
    if not scheme_ids:
        stats = get_index_stats(index_path=index_path, min_chunk_count=0)
        facts = _load_facts_or_empty(facts_path)
        chunks = _load_chunks_or_empty(chunks_path)
        return ReindexReport(
            updated=False,
            changed_schemes=(),
            skipped_schemes=tuple(sorted(get_current_source_hashes().keys())),
            facts_count=len(facts),
            chunks_count=len(chunks),
            index_chunk_count=stats.chunk_count,
            index_ready=stats.ready,
        )

    embedder = backend or get_embedding_backend()
    facts = _load_facts_or_empty(facts_path)
    chunks = _load_chunks_or_empty(chunks_path)
    embedded = _load_embedded_or_empty(embedded_path)
    upserted: list[EmbeddedChunk] = []

    for scheme_id in scheme_ids:
        logger.info("Re-indexing scheme '%s'", scheme_id)
        delete_scheme_from_index(scheme_id, index_path=index_path)
        facts, chunks, embedded = _remove_scheme_records(
            scheme_id,
            facts=facts,
            chunks=chunks,
            embedded=embedded,
        )

        new_facts = build_facts_for_scheme(scheme_id)
        new_chunks = build_chunks(new_facts)
        new_embedded = embed_chunks(new_chunks, backend=embedder)

        facts.extend(new_facts)
        chunks.extend(new_chunks)
        embedded.extend(new_embedded)
        upserted.extend(new_embedded)

    validate_facts(facts)
    validate_chunks(chunks)
    validate_embeddings(embedded)

    save_facts_json(facts, facts_path)
    save_chunks_json(chunks, chunks_path)
    save_embedded_chunks_json(embedded, embedded_path)

    scheme_hashes = _build_scheme_content_hashes(embedded)
    stats = upsert_index(
        upserted,
        index_path=index_path,
        scheme_content_hashes=scheme_hashes,
    )

    source_hashes = get_current_source_hashes()
    skipped = [scheme_id for scheme_id in source_hashes if scheme_id not in scheme_ids]

    return ReindexReport(
        updated=True,
        changed_schemes=tuple(scheme_ids),
        skipped_schemes=tuple(sorted(skipped)),
        facts_count=len(facts),
        chunks_count=len(chunks),
        index_chunk_count=stats.chunk_count,
        index_ready=stats.ready,
    )


def reindex_if_changed(
    *,
    backend: EmbeddingBackend | None = None,
    index_path: Path | None = None,
    facts_path: Path | None = None,
    chunks_path: Path | None = None,
    embedded_path: Path | None = None,
    force_all_if_index_not_ready: bool = True,
) -> ReindexReport:
    """Re-index only schemes whose Phase 1 content_hash differs from the last index."""
    source_hashes = get_current_source_hashes()
    if not source_hashes:
        raise ValidationError("No successful source records with content_hash found")

    changed, unchanged = detect_changed_schemes(source_hashes=source_hashes)
    index_stats = get_index_stats(index_path=index_path, min_chunk_count=0)

    if force_all_if_index_not_ready and not index_stats.ready:
        logger.info("Index not ready; re-indexing all schemes with source hashes")
        changed = sorted(source_hashes.keys())
        unchanged = []

    if not changed:
        logger.info("No scheme content_hash changes detected; skipping re-index")
        facts = _load_facts_or_empty(facts_path)
        chunks = _load_chunks_or_empty(chunks_path)
        return ReindexReport(
            updated=False,
            changed_schemes=(),
            skipped_schemes=tuple(sorted(unchanged)),
            facts_count=len(facts),
            chunks_count=len(chunks),
            index_chunk_count=index_stats.chunk_count,
            index_ready=index_stats.ready,
        )

    return reindex_schemes(
        changed,
        backend=backend,
        index_path=index_path,
        facts_path=facts_path,
        chunks_path=chunks_path,
        embedded_path=embedded_path,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2.8 — Selective corpus re-index job")
    parser.add_argument(
        "--scheme",
        action="append",
        dest="schemes",
        metavar="SCHEME_ID",
        help="Force re-index for specific scheme id (may be repeated)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print ReindexReport as JSON",
    )
    args = parser.parse_args()

    try:
        if args.schemes:
            report = reindex_schemes(args.schemes)
        else:
            report = reindex_if_changed()
    except ValidationError as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(
            f"updated={report.updated}; changed={list(report.changed_schemes)}; "
            f"skipped={list(report.skipped_schemes)}; facts={report.facts_count}; "
            f"chunks={report.chunks_count}; index_chunks={report.index_chunk_count}; "
            f"index_ready={report.index_ready}"
        )

    raise SystemExit(0)


if __name__ == "__main__":
    main()

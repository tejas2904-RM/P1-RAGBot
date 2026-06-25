"""Tests for Phase 2.8 — selective re-index job."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from phases import paths
from phases.phase1.registry import load_source_registry
from phases.phase2.embedder import DeterministicEmbeddingBackend
from phases.phase2.indexer import get_index_stats, load_index_registry, upsert_index_from_corpus
from phases.phase2.reindex_job import (
    detect_changed_schemes,
    get_current_source_hashes,
    get_indexed_hashes,
    reindex_if_changed,
    reindex_schemes,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = PROJECT_ROOT / "corpus"
PROCESSED_DIR = CORPUS_DIR / "processed"


@pytest.fixture
def corpus_copy(tmp_path):
    """Copy processed corpus artifacts into an isolated workspace."""
    workspace = tmp_path / "workspace"
    processed = workspace / "corpus" / "processed"
    metadata = workspace / "corpus" / "metadata"
    processed.mkdir(parents=True)
    metadata.mkdir(parents=True)

    for name in ("facts.json", "chunks.json", "embedded_chunks.json"):
        src = PROCESSED_DIR / name
        if src.exists():
            shutil.copy(src, processed / name)

    source_registry = CORPUS_DIR / "metadata" / "source_registry.json"
    if source_registry.exists():
        shutil.copy(source_registry, metadata / "source_registry.json")

    scheme_registry = CORPUS_DIR / "metadata" / "scheme_registry.json"
    if scheme_registry.exists():
        shutil.copy(scheme_registry, metadata / "scheme_registry.json")

    index_registry = CORPUS_DIR / "metadata" / "index_registry.json"
    if index_registry.exists():
        shutil.copy(index_registry, metadata / "index_registry.json")

    return workspace


@pytest.fixture
def isolated_paths(corpus_copy, tmp_path, monkeypatch):
    workspace = corpus_copy
    vector_store = tmp_path / "vector_store"
    vector_store.mkdir()

    facts_path = workspace / "corpus" / "processed" / "facts.json"
    chunks_path = workspace / "corpus" / "processed" / "chunks.json"
    embedded_path = workspace / "corpus" / "processed" / "embedded_chunks.json"
    index_registry_path = workspace / "corpus" / "metadata" / "index_registry.json"
    source_registry_path = workspace / "corpus" / "metadata" / "source_registry.json"

    monkeypatch.setattr(paths, "FACTS_FILE", facts_path)
    monkeypatch.setattr(paths, "CHUNKS_FILE", chunks_path)
    monkeypatch.setattr(paths, "EMBEDDED_CHUNKS_FILE", embedded_path)
    monkeypatch.setattr(paths, "INDEX_REGISTRY_FILE", index_registry_path)
    monkeypatch.setattr(paths, "SOURCE_REGISTRY_FILE", source_registry_path)
    monkeypatch.setattr(paths, "SCHEME_REGISTRY_FILE", workspace / "corpus" / "metadata" / "scheme_registry.json")
    monkeypatch.setattr(paths, "VECTOR_STORE_DIR", vector_store)

    if embedded_path.exists():
        upsert_index_from_corpus(embedded_path, index_path=vector_store)

    return {
        "facts_path": facts_path,
        "chunks_path": chunks_path,
        "embedded_path": embedded_path,
        "index_registry_path": index_registry_path,
        "source_registry_path": source_registry_path,
        "vector_store": vector_store,
    }


@pytest.fixture
def deterministic_backend() -> DeterministicEmbeddingBackend:
    return DeterministicEmbeddingBackend()


def test_detect_changed_schemes_when_hashes_match(isolated_paths) -> None:
    source = get_current_source_hashes()
    changed, unchanged = detect_changed_schemes(source_hashes=source, indexed_hashes=source)
    assert changed == []
    assert sorted(unchanged) == sorted(source.keys())


def test_detect_changed_schemes_when_hash_differs(isolated_paths) -> None:
    source = get_current_source_hashes()
    indexed = dict(source)
    first_scheme = next(iter(indexed))
    indexed[first_scheme] = "sha256:deadbeef"

    changed, unchanged = detect_changed_schemes(source_hashes=source, indexed_hashes=indexed)
    assert changed == [first_scheme]
    assert first_scheme not in unchanged


def test_reindex_if_changed_skips_unchanged(isolated_paths, deterministic_backend) -> None:
    report = reindex_if_changed(
        backend=deterministic_backend,
        index_path=isolated_paths["vector_store"],
        facts_path=isolated_paths["facts_path"],
        chunks_path=isolated_paths["chunks_path"],
        embedded_path=isolated_paths["embedded_path"],
    )
    assert report.updated is False
    assert report.changed_schemes == ()
    assert report.facts_count == 56
    assert report.chunks_count == 56
    assert report.index_chunk_count == 56
    assert report.index_ready is True


def test_reindex_if_changed_updates_changed_scheme(isolated_paths, deterministic_backend) -> None:
    source = get_current_source_hashes()
    target_scheme = "hdfc-mid-cap"
    indexed = dict(source)
    indexed[target_scheme] = "sha256:stale-hash"

    registry = load_index_registry(isolated_paths["index_registry_path"])
    assert registry is not None
    registry["scheme_content_hashes"] = indexed
    isolated_paths["index_registry_path"].write_text(
        json.dumps(registry, indent=2) + "\n",
        encoding="utf-8",
    )

    report = reindex_if_changed(
        backend=deterministic_backend,
        index_path=isolated_paths["vector_store"],
        facts_path=isolated_paths["facts_path"],
        chunks_path=isolated_paths["chunks_path"],
        embedded_path=isolated_paths["embedded_path"],
    )

    assert report.updated is True
    assert report.changed_schemes == (target_scheme,)
    assert report.facts_count == 56
    assert report.chunks_count == 56
    assert report.index_chunk_count == 56
    assert report.index_ready is True

    updated_registry = load_index_registry(isolated_paths["index_registry_path"])
    assert updated_registry is not None
    assert updated_registry["scheme_content_hashes"][target_scheme] == source[target_scheme]


def test_reindex_schemes_force_single_scheme(isolated_paths, deterministic_backend) -> None:
    report = reindex_schemes(
        ["hdfc-equity"],
        backend=deterministic_backend,
        index_path=isolated_paths["vector_store"],
        facts_path=isolated_paths["facts_path"],
        chunks_path=isolated_paths["chunks_path"],
        embedded_path=isolated_paths["embedded_path"],
    )

    assert report.updated is True
    assert report.changed_schemes == ("hdfc-equity",)
    assert report.facts_count == 56
    assert get_index_stats(index_path=isolated_paths["vector_store"]).chunk_count == 56


def test_index_registry_hashes_align_with_source_after_reindex(
    isolated_paths,
    deterministic_backend,
) -> None:
    source = get_current_source_hashes()
    indexed = {scheme_id: "sha256:stale" for scheme_id in source}
    registry = load_index_registry(isolated_paths["index_registry_path"])
    registry["scheme_content_hashes"] = indexed
    isolated_paths["index_registry_path"].write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    reindex_if_changed(
        backend=deterministic_backend,
        index_path=isolated_paths["vector_store"],
        facts_path=isolated_paths["facts_path"],
        chunks_path=isolated_paths["chunks_path"],
        embedded_path=isolated_paths["embedded_path"],
    )

    assert get_indexed_hashes(isolated_paths["index_registry_path"]) == source


@pytest.mark.skipif(not PROCESSED_DIR.exists(), reason="corpus processed artifacts missing")
def test_source_registry_available_for_hash_diff() -> None:
    records = load_source_registry()
    ok_records = [record for record in records if record.status == "ok" and record.content_hash]
    assert len(ok_records) == 5

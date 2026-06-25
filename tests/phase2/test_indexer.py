"""Tests for Phase 2.7 — vector index upsert and search."""

from __future__ import annotations

from pathlib import Path

import pytest

from phases.phase1.config import ALLOWED_URLS
from phases.phase1.validator import ValidationError
from phases.phase2.embedder import DeterministicEmbeddingBackend, embed_chunks_from_corpus
from phases.phase2.indexer import (
    get_index_stats,
    similarity_search,
    upsert_index,
    upsert_index_from_corpus,
)
from phases.phase2.models import EmbeddedChunk

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_FILE = PROJECT_ROOT / "corpus" / "processed" / "chunks.json"
EMBEDDED_FILE = PROJECT_ROOT / "corpus" / "processed" / "embedded_chunks.json"


@pytest.fixture
def deterministic_backend() -> DeterministicEmbeddingBackend:
    return DeterministicEmbeddingBackend()


@pytest.fixture
def embedded_chunks(deterministic_backend) -> list[EmbeddedChunk]:
    if not CHUNKS_FILE.exists():
        pytest.skip("chunks.json missing")
    return embed_chunks_from_corpus(backend=deterministic_backend)


@pytest.fixture
def index_path(tmp_path) -> Path:
    return tmp_path / "vector_store"


def test_upsert_index_stores_all_chunks(embedded_chunks, index_path) -> None:
    stats = upsert_index(embedded_chunks, index_path=index_path, min_chunk_count=50)
    assert stats.chunk_count == len(embedded_chunks)
    assert stats.ready is True
    assert stats.embedding_dim == 1536


def test_get_index_stats_before_and_after(embedded_chunks, index_path) -> None:
    empty = get_index_stats(index_path=index_path, min_chunk_count=0)
    assert empty.chunk_count == 0
    assert empty.ready is False

    upsert_index(embedded_chunks, index_path=index_path, min_chunk_count=50)
    stats = get_index_stats(index_path=index_path)
    assert stats.chunk_count == 56
    assert stats.ready is True


def test_metadata_filter_scheme_and_field(embedded_chunks, index_path, deterministic_backend) -> None:
    upsert_index(embedded_chunks, index_path=index_path, min_chunk_count=50)
    target = next(item for item in embedded_chunks if item.chunk.scheme_id == "hdfc-mid-cap" and item.chunk.field == "expense_ratio")

    results = similarity_search(
        target.chunk.text,
        top_k=3,
        scheme_id="hdfc-mid-cap",
        field="expense_ratio",
        index_path=index_path,
        backend=deterministic_backend,
    )
    assert results
    assert results[0].chunk_id == target.chunk.chunk_id
    assert results[0].field == "expense_ratio"
    assert results[0].source_url in ALLOWED_URLS


@pytest.mark.parametrize(
    "scheme_id,field",
    [
        ("hdfc-mid-cap", "expense_ratio"),
        ("hdfc-mid-cap", "exit_load"),
        ("hdfc-large-cap", "minimum_sip"),
        ("hdfc-elss", "lock_in_period"),
        ("hdfc-equity", "riskometer"),
        ("hdfc-focused", "benchmark"),
    ],
)
def test_exit_criteria_sample_queries(
    embedded_chunks,
    index_path,
    deterministic_backend,
    scheme_id: str,
    field: str,
) -> None:
    upsert_index(embedded_chunks, index_path=index_path, min_chunk_count=50)
    target = next(item for item in embedded_chunks if item.chunk.scheme_id == scheme_id and item.chunk.field == field)

    results = similarity_search(
        target.chunk.text,
        top_k=1,
        scheme_id=scheme_id,
        field=field,
        index_path=index_path,
        backend=deterministic_backend,
    )
    assert len(results) == 1
    assert results[0].chunk_id == target.chunk.chunk_id
    assert results[0].source_url == target.chunk.source_url


def test_lock_in_only_for_elss_in_index(embedded_chunks, index_path) -> None:
    upsert_index(embedded_chunks, index_path=index_path, min_chunk_count=50)
    stats = get_index_stats(index_path=index_path)
    assert stats.chunk_count == 56


def test_upsert_rejects_below_minimum(embedded_chunks, index_path) -> None:
    with pytest.raises(ValidationError, match="below minimum"):
        upsert_index(embedded_chunks[:10], index_path=index_path, min_chunk_count=50)


@pytest.mark.skipif(not EMBEDDED_FILE.exists(), reason="embedded_chunks.json missing")
def test_upsert_index_from_corpus_file(index_path) -> None:
    stats = upsert_index_from_corpus(index_path=index_path)
    assert stats.chunk_count >= 50
    assert stats.ready is True

"""Tests for Phase 2.6 — embedding pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from phases import paths
from phases.phase1.validator import ValidationError
from phases.phase2.chunker import load_chunks_json
from phases.phase2.embedder import (
    DEFAULT_EMBEDDING_MODEL,
    DeterministicEmbeddingBackend,
    OpenAIEmbeddingBackend,
    embed_chunks,
    embed_chunks_from_corpus,
    load_embedded_chunks_json,
    save_embedded_chunks_json,
    validate_embeddings,
)
from phases.phase2.models import ChunkDocument, EmbeddedChunk

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_FILE = PROJECT_ROOT / "corpus" / "processed" / "chunks.json"


@pytest.fixture
def sample_chunks() -> list[ChunkDocument]:
    if CHUNKS_FILE.exists():
        return load_chunks_json()[:3]
    return [
        ChunkDocument(
            chunk_id="test-1",
            text="The expense ratio of HDFC Mid Cap Fund - Direct Growth is 0.75%.",
            source_url="https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
            source="groww.in",
            scheme_id="hdfc-mid-cap",
            scheme_name="HDFC Mid Cap Fund - Direct Growth",
            scheme_category="mid-cap",
            amc="HDFC Mutual Fund",
            field="expense_ratio",
            value=0.75,
            unit="%",
            display_value="0.75%",
            last_updated="2026-06-24",
            content_hash="sha256:abc",
        )
    ]


@pytest.fixture
def deterministic_backend() -> DeterministicEmbeddingBackend:
    return DeterministicEmbeddingBackend(dim=1536)


def test_embed_chunks_returns_one_per_input(sample_chunks, deterministic_backend) -> None:
    embedded = embed_chunks(sample_chunks, backend=deterministic_backend, model="text-embedding-3-small")
    assert len(embedded) == len(sample_chunks)


def test_embedding_dimension_consistent(sample_chunks, deterministic_backend) -> None:
    embedded = embed_chunks(sample_chunks, backend=deterministic_backend, model="text-embedding-3-small")
    validate_embeddings(embedded)
    assert all(item.embedding_dim == 1536 for item in embedded)
    assert all(len(item.embedding) == 1536 for item in embedded)


def test_embeddings_use_chunk_text(sample_chunks, deterministic_backend) -> None:
    embedded = embed_chunks(sample_chunks, backend=deterministic_backend, model="text-embedding-3-small")
    for item in embedded:
        assert item.chunk.text
        assert item.embedding_model == "text-embedding-3-small"


def test_deterministic_backend_stable(deterministic_backend) -> None:
    vectors_a = deterministic_backend.embed_texts(["hello"], model="text-embedding-3-small")
    vectors_b = deterministic_backend.embed_texts(["hello"], model="text-embedding-3-small")
    assert vectors_a == vectors_b


def test_validate_embeddings_rejects_mismatched_dims(sample_chunks, deterministic_backend) -> None:
    embedded = embed_chunks(sample_chunks[:1], backend=deterministic_backend, model="text-embedding-3-small")
    bad = EmbeddedChunk(
        chunk=embedded[0].chunk,
        embedding=embedded[0].embedding[:100],
        embedding_model="text-embedding-3-small",
        embedding_dim=1536,
    )
    with pytest.raises(ValidationError, match="Embedding length mismatch"):
        validate_embeddings([bad])


def test_save_and_load_embedded_chunks_json(sample_chunks, deterministic_backend, tmp_path) -> None:
    embedded = embed_chunks(sample_chunks, backend=deterministic_backend, model="text-embedding-3-small")
    out = save_embedded_chunks_json(embedded, tmp_path / "embedded_chunks.json")
    loaded = load_embedded_chunks_json(out)
    assert len(loaded) == len(embedded)
    assert loaded[0].chunk.chunk_id == embedded[0].chunk.chunk_id
    assert loaded[0].embedding == embedded[0].embedding


@patch("phases.phase2.embedder.OpenAIEmbeddingBackend._get_client")
def test_openai_backend_batch_embed(mock_get_client, sample_chunks) -> None:
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.embeddings.create.return_value = MagicMock(
        data=[
            MagicMock(embedding=[0.1, 0.2, 0.3]),
            MagicMock(embedding=[0.4, 0.5, 0.6]),
            MagicMock(embedding=[0.7, 0.8, 0.9]),
        ][: len(sample_chunks)]
    )

    backend = OpenAIEmbeddingBackend(api_key="test-key")
    vectors = backend.embed_texts([c.text for c in sample_chunks], model=DEFAULT_EMBEDDING_MODEL)
    assert len(vectors) == len(sample_chunks)
    mock_client.embeddings.create.assert_called_once()


@pytest.mark.skipif(not CHUNKS_FILE.exists(), reason="chunks.json missing")
def test_embed_chunks_from_corpus_integration() -> None:
    embedded = embed_chunks_from_corpus(backend=DeterministicEmbeddingBackend())
    assert len(embedded) == 56
    validate_embeddings(embedded)


@pytest.mark.skipif(not CHUNKS_FILE.exists(), reason="chunks.json missing")
def test_write_corpus_embedded_chunks_json() -> None:
    embedded = embed_chunks_from_corpus(backend=DeterministicEmbeddingBackend())
    path = save_embedded_chunks_json(embedded)
    assert path == paths.EMBEDDED_CHUNKS_FILE
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["count"] == 56
    assert data["embedding_dim"] == 1536

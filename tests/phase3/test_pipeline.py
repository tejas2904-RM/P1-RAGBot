"""Tests for Phase 3 — retrieval and end-to-end RAG pipeline."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from phases import paths
from phases.phase1.config import ALLOWED_URLS
from phases.phase2.embedder import DeterministicEmbeddingBackend, embed_chunks_from_corpus
from phases.phase2.indexer import upsert_index_from_corpus
from phases.phase3.generator import TemplateAnswerGenerator
from phases.phase3.models import RetrievalMode
from phases.phase3.pipeline import answer_query
from phases.phase3.response_formatter import count_sentences, extract_source_url
from phases.phase3.retriever import retrieve

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "corpus" / "processed"
EMBEDDED_FILE = PROCESSED_DIR / "embedded_chunks.json"


@pytest.fixture
def rag_index(tmp_path, monkeypatch):
    if not EMBEDDED_FILE.exists():
        pytest.skip("embedded_chunks.json missing")

    workspace = tmp_path / "workspace"
    processed = workspace / "corpus" / "processed"
    metadata = workspace / "corpus" / "metadata"
    processed.mkdir(parents=True)
    metadata.mkdir(parents=True)

    for name in ("facts.json", "chunks.json", "embedded_chunks.json"):
        shutil.copy(PROCESSED_DIR / name, processed / name)

    for name in ("scheme_registry.json", "source_registry.json", "index_registry.json"):
        src = PROJECT_ROOT / "corpus" / "metadata" / name
        if src.exists():
            shutil.copy(src, metadata / name)

    vector_store = tmp_path / "vector_store"
    embedded_path = processed / "embedded_chunks.json"

    monkeypatch.setattr(paths, "FACTS_FILE", processed / "facts.json")
    monkeypatch.setattr(paths, "CHUNKS_FILE", processed / "chunks.json")
    monkeypatch.setattr(paths, "EMBEDDED_CHUNKS_FILE", embedded_path)
    monkeypatch.setattr(paths, "INDEX_REGISTRY_FILE", metadata / "index_registry.json")
    monkeypatch.setattr(paths, "SOURCE_REGISTRY_FILE", metadata / "source_registry.json")
    monkeypatch.setattr(paths, "SCHEME_REGISTRY_FILE", metadata / "scheme_registry.json")
    monkeypatch.setattr(paths, "VECTOR_STORE_DIR", vector_store)

    upsert_index_from_corpus(embedded_path, index_path=vector_store)
    backend = DeterministicEmbeddingBackend()

    return {
        "backend": backend,
        "index_path": vector_store,
        "generator": TemplateAnswerGenerator(),
    }


@pytest.mark.parametrize(
    "query,expected_scheme,expected_field,expected_url",
    [
        (
            "What is the expense ratio of HDFC Mid Cap Fund?",
            "hdfc-mid-cap",
            "expense_ratio",
            ALLOWED_URLS[0],
        ),
        (
            "Exit load on HDFC Focused Fund?",
            "hdfc-focused",
            "exit_load",
            ALLOWED_URLS[2],
        ),
        (
            "Minimum SIP for HDFC Large Cap Fund?",
            "hdfc-large-cap",
            "minimum_sip",
            ALLOWED_URLS[4],
        ),
        (
            "ELSS lock-in for HDFC ELSS Tax Saver?",
            "hdfc-elss",
            "lock_in_period",
            ALLOWED_URLS[3],
        ),
        (
            "Benchmark of HDFC Equity Fund?",
            "hdfc-equity",
            "benchmark",
            ALLOWED_URLS[1],
        ),
    ],
)
def test_e2e_factual_queries(
    rag_index,
    query: str,
    expected_scheme: str,
    expected_field: str,
    expected_url: str,
) -> None:
    response = answer_query(
        query,
        backend=rag_index["backend"],
        generator=rag_index["generator"],
        index_path=rag_index["index_path"],
    )
    assert response.success is True
    assert response.scheme_id == expected_scheme
    assert expected_field in response.fields
    assert response.source_url == expected_url
    assert extract_source_url(response.answer) == expected_url
    assert count_sentences(response.answer.split("Source:")[0]) <= 3
    assert "Last updated from sources:" in response.answer


def test_retriever_exact_mode(rag_index) -> None:
    query = "What is the expense ratio of HDFC Mid Cap Fund?"
    result = retrieve(
        query,
        backend=rag_index["backend"],
        index_path=rag_index["index_path"],
    )
    assert result.mode == RetrievalMode.EXACT
    assert result.scheme_id == "hdfc-mid-cap"
    assert result.fields == ("expense_ratio",)
    assert len(result.chunks) == 1
    assert result.chunks[0].field == "expense_ratio"


def test_compound_query_same_scheme(rag_index) -> None:
    query = "Expense ratio and exit load of HDFC Mid Cap Fund"
    response = answer_query(
        query,
        backend=rag_index["backend"],
        generator=rag_index["generator"],
        index_path=rag_index["index_path"],
    )
    assert response.success is True
    assert response.scheme_id == "hdfc-mid-cap"
    assert "expense_ratio" in response.fields
    assert "exit_load" in response.fields
    assert response.source_url == ALLOWED_URLS[0]


def test_insufficient_context_for_unrelated_query(rag_index) -> None:
    response = answer_query(
        "What is the weather in Mumbai?",
        backend=rag_index["backend"],
        generator=rag_index["generator"],
        index_path=rag_index["index_path"],
    )
    assert response.success is False
    assert response.source_url is None
    assert "http" not in response.answer

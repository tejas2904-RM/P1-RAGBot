"""Tests for Phase 4 — end-to-end classified assistant pipeline."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest

from phases import paths
from phases.phase1.config import ALLOWED_URLS
from phases.phase2.embedder import DeterministicEmbeddingBackend
from phases.phase2.indexer import upsert_index_from_corpus
from phases.phase3.generator import TemplateAnswerGenerator
from phases.phase3.response_formatter import count_sentences, extract_source_url
from phases.phase4.models import QueryCategory
from phases.phase4.pipeline import handle_query

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "corpus" / "processed"
EMBEDDED_FILE = PROCESSED_DIR / "embedded_chunks.json"
_URL_RE = re.compile(r"https?://", re.IGNORECASE)


@pytest.fixture
def assistant_index(tmp_path, monkeypatch):
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
    monkeypatch.setattr(paths, "EMBEDDED_CHUNKS_FILE", embedded_path)
    monkeypatch.setattr(paths, "FACTS_FILE", processed / "facts.json")
    monkeypatch.setattr(paths, "CHUNKS_FILE", processed / "chunks.json")
    monkeypatch.setattr(paths, "INDEX_REGISTRY_FILE", metadata / "index_registry.json")
    monkeypatch.setattr(paths, "SOURCE_REGISTRY_FILE", metadata / "source_registry.json")
    monkeypatch.setattr(paths, "SCHEME_REGISTRY_FILE", metadata / "scheme_registry.json")
    monkeypatch.setattr(paths, "VECTOR_STORE_DIR", vector_store)

    upsert_index_from_corpus(embedded_path, index_path=vector_store)
    return {
        "backend": DeterministicEmbeddingBackend(),
        "generator": TemplateAnswerGenerator(),
        "index_path": vector_store,
    }


@pytest.mark.parametrize(
    "query,expected_url",
    [
        ("What is the expense ratio of HDFC Mid Cap Fund?", ALLOWED_URLS[0]),
        ("Exit load on HDFC Focused Fund?", ALLOWED_URLS[2]),
        ("Minimum SIP for HDFC Large Cap Fund?", ALLOWED_URLS[4]),
        ("ELSS lock-in for HDFC ELSS Tax Saver?", ALLOWED_URLS[3]),
        ("Benchmark of HDFC Equity Fund?", ALLOWED_URLS[1]),
    ],
)
def test_e2e_factual_routes_to_rag(assistant_index, query: str, expected_url: str) -> None:
    response = handle_query(
        query,
        backend=assistant_index["backend"],
        generator=assistant_index["generator"],
        index_path=assistant_index["index_path"],
    )
    assert response.refused is False
    assert response.category == QueryCategory.FACTUAL
    assert response.success is True
    assert response.source_url == expected_url
    assert extract_source_url(response.answer) == expected_url
    assert count_sentences(response.answer.split("Source:")[0]) <= 3


@pytest.mark.parametrize(
    "query,expected_category",
    [
        ("Should I invest in HDFC Mid Cap?", QueryCategory.ADVISORY),
        ("Mid Cap vs Large Cap — which is better?", QueryCategory.COMPARATIVE),
        ("What was the 1-year return of HDFC Mid Cap?", QueryCategory.PERFORMANCE),
        ("Tell me about SBI Bluechip Fund", QueryCategory.OUT_OF_SCOPE),
        ("My PAN is ABCDE1234F, check my balance", QueryCategory.PII),
        ("Expense ratio and should I buy Mid Cap?", QueryCategory.ADVISORY),
    ],
)
def test_e2e_refusals_have_no_urls(assistant_index, query: str, expected_category: QueryCategory) -> None:
    response = handle_query(
        query,
        backend=assistant_index["backend"],
        generator=assistant_index["generator"],
        index_path=assistant_index["index_path"],
    )
    assert response.refused is True
    assert response.category == expected_category
    assert response.source_url is None
    assert not _URL_RE.search(response.answer)


def test_e2e_empty_query(assistant_index) -> None:
    response = handle_query(
        "",
        backend=assistant_index["backend"],
        generator=assistant_index["generator"],
        index_path=assistant_index["index_path"],
    )
    assert response.category == QueryCategory.EMPTY
    assert response.refused is True
    assert not _URL_RE.search(response.answer)

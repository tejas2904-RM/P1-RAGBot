"""Tests for Phase 5 — FastAPI backend."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from phases import paths
from phases.phase1.config import ALLOWED_URLS
from phases.phase2.indexer import upsert_index_from_corpus
from phases.phase5.app import app
from phases.phase5.config import DISCLAIMER, EXAMPLE_QUESTIONS

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "corpus" / "processed"
EMBEDDED_FILE = PROCESSED_DIR / "embedded_chunks.json"
_URL_RE = re.compile(r"https?://", re.IGNORECASE)


@pytest.fixture
def api_client(tmp_path, monkeypatch):
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
    monkeypatch.setenv("EMBEDDING_PROVIDER", "deterministic")
    monkeypatch.setenv("GENERATOR_PROVIDER", "template")
    with TestClient(app) as client:
        yield client


def test_health_endpoint(api_client) -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["index_ready"] is True
    assert payload["index_chunk_count"] >= 50
    assert payload["status"] == "ok"
    assert payload["generator"] == "TemplateAnswerGenerator"
    assert payload["llm_enabled"] is False


def test_meta_endpoint(api_client) -> None:
    response = api_client.get("/api/v1/meta")
    assert response.status_code == 200
    payload = response.json()
    assert payload["disclaimer"] == DISCLAIMER
    assert len(payload["example_questions"]) == 3
    assert payload["example_questions"][0]["text"] == EXAMPLE_QUESTIONS[0]
    assert "HDFC" in payload["welcome_message"]


def test_disclaimer_endpoint(api_client) -> None:
    response = api_client.get("/api/v1/disclaimer")
    assert response.status_code == 200
    assert response.json()["disclaimer"] == DISCLAIMER


def test_chat_factual_query(api_client) -> None:
    response = api_client.post(
        "/api/v1/chat",
        json={"query": "What is the expense ratio of HDFC Mid Cap Fund?"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["refused"] is False
    assert payload["success"] is True
    assert payload["used_llm"] is False
    assert payload["category"] == "factual"
    assert payload["source_url"] == ALLOWED_URLS[0]
    assert payload["answer_body"]
    assert "Source:" in payload["answer"]
    assert payload["last_updated"]


def test_chat_refusal_query(api_client) -> None:
    response = api_client.post(
        "/api/v1/chat",
        json={"query": "Should I invest in HDFC Mid Cap?"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["refused"] is True
    assert payload["category"] == "advisory"
    assert payload["source_url"] is None
    assert not _URL_RE.search(payload["answer"])


def test_chat_rejects_empty_query(api_client) -> None:
    response = api_client.post("/api/v1/chat", json={"query": ""})
    assert response.status_code == 422


def test_example_questions_route_to_factual_answers(api_client) -> None:
    for example in EXAMPLE_QUESTIONS:
        response = api_client.post("/api/v1/chat", json={"query": example})
        assert response.status_code == 200
        payload = response.json()
        assert payload["refused"] is False, example
        assert payload["success"] is True, example


def test_serves_frontend_index(api_client) -> None:
    response = api_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Mutual Fund FAQ Assistant" in response.text


def test_serves_frontend_static_assets(api_client) -> None:
    css = api_client.get("/static/css/styles.css")
    js = api_client.get("/static/js/app.js")
    assert css.status_code == 200
    assert js.status_code == 200
    assert "disclaimer" in css.text.lower()
    assert "/api/v1/chat" in js.text

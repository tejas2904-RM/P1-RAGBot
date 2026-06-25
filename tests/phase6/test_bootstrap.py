"""Tests for Phase 6 — deployment bootstrap."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from phases import paths
from phases.phase2.indexer import upsert_index_from_corpus
from phases.phase6.bootstrap import apply_secrets, ensure_index_ready

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = PROJECT_ROOT / "corpus" / "processed"
EMBEDDED_FILE = PROCESSED_DIR / "embedded_chunks.json"


@pytest.fixture
def isolated_index(tmp_path, monkeypatch):
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
    monkeypatch.setattr(paths, "VECTOR_STORE_DIR", vector_store)
    monkeypatch.setenv("EMBEDDING_PROVIDER", "deterministic")
    monkeypatch.setenv("GENERATOR_PROVIDER", "template")

    upsert_index_from_corpus(embedded_path, index_path=vector_store)
    return vector_store


def test_apply_secrets_sets_env(monkeypatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    apply_secrets({"GROQ_API_KEY": "test-key", "GENERATOR_PROVIDER": "groq"})
    import os

    assert os.environ["GROQ_API_KEY"] == "test-key"
    assert os.environ["GENERATOR_PROVIDER"] == "groq"


def test_apply_secrets_does_not_overwrite_with_empty(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "existing")
    monkeypatch.setattr("phases.phase6.bootstrap.load_env", lambda: None)
    monkeypatch.setattr("phases.phase6.bootstrap.load_streamlit_secrets", lambda: {})
    apply_secrets({"GROQ_API_KEY": "", "OPENAI_API_KEY": "sk-test"})
    import os

    assert os.environ["GROQ_API_KEY"] == "existing"
    assert os.environ["OPENAI_API_KEY"] == "sk-test"


def test_ensure_index_ready_builds_from_embedded(isolated_index) -> None:
    stats = ensure_index_ready()
    assert stats.ready is True
    assert stats.chunk_count >= paths.MIN_INDEX_CHUNK_COUNT


def test_ensure_index_ready_skips_when_ready(isolated_index) -> None:
    first = ensure_index_ready()
    second = ensure_index_ready()
    assert first.chunk_count == second.chunk_count


def test_api_server_exports_fastapi_app(isolated_index, monkeypatch) -> None:
    import importlib

    monkeypatch.setenv("GENERATOR_PROVIDER", "template")
    import phases.phase6.api_server as api_server

    importlib.reload(api_server)
    assert api_server.app is not None
    assert any(getattr(route, "path", "") == "/health" for route in api_server.app.routes)

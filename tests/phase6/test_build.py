"""Tests for Phase 6 — Render build script."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from phases import paths
from phases.phase6.build import main as run_build

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_build_succeeds_with_embedded_corpus() -> None:
    assert run_build() == 0


def test_build_cli() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "phases.phase6.build"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        check=False,
    )
    assert result.returncode == 0
    assert "OK: embedded corpus ready" in result.stdout


def test_ensure_embedded_corpus_from_chunks(tmp_path, monkeypatch) -> None:
    chunks_src = PROJECT_ROOT / "corpus" / "processed" / "chunks.json"
    if not chunks_src.exists():
        pytest.skip("chunks.json missing")

    processed = tmp_path / "corpus" / "processed"
    processed.mkdir(parents=True)
    embedded_path = processed / "embedded_chunks.json"
    chunks_path = processed / "chunks.json"

    shutil.copy(chunks_src, chunks_path)
    monkeypatch.setattr(paths, "CHUNKS_FILE", chunks_path)
    monkeypatch.setattr(paths, "EMBEDDED_CHUNKS_FILE", embedded_path)
    monkeypatch.setenv("EMBEDDING_PROVIDER", "deterministic")

    from phases.phase6.bootstrap import ensure_embedded_corpus

    ensure_embedded_corpus()
    assert embedded_path.exists()
    data = json.loads(embedded_path.read_text(encoding="utf-8"))
    assert data["count"] >= paths.MIN_INDEX_CHUNK_COUNT

"""Tests for Phase 2.5 — chunking and metadata attachment."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from phases import paths
from phases.phase1.config import ALLOWED_URLS
from phases.phase1.validator import ValidationError
from phases.phase2.chunker import (
    build_chunks,
    build_chunks_from_corpus,
    load_facts_json,
    save_chunks_json,
    validate_chunks,
)
from phases.phase2.fact_builder import build_all_facts, save_facts_json, validate_facts
from phases.phase2.groww_selectors import BLOCKED_FIELDS
from phases.phase2.models import ChunkDocument, FactRecord

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FACTS_FILE = PROJECT_ROOT / "corpus" / "processed" / "facts.json"


@pytest.fixture
def facts_from_corpus() -> list[FactRecord]:
    if not FACTS_FILE.exists():
        facts = build_all_facts()
        save_facts_json(facts)
    return load_facts_json()


def test_load_facts_json(facts_from_corpus: list[FactRecord]) -> None:
    assert len(facts_from_corpus) == 56


def test_build_chunks_one_to_one(facts_from_corpus: list[FactRecord]) -> None:
    chunks = build_chunks(facts_from_corpus)
    assert len(chunks) == len(facts_from_corpus)
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)


def test_chunk_metadata_from_fact(facts_from_corpus: list[FactRecord]) -> None:
    chunks = build_chunks(facts_from_corpus)
    fact = facts_from_corpus[0]
    chunk = chunks[0]
    assert chunk.scheme_id == fact.scheme_id
    assert chunk.text == fact.text
    assert chunk.display_value == fact.display_value
    assert chunk.source_url == fact.source_url
    assert chunk.content_hash == fact.content_hash


def test_validate_chunks_passes(facts_from_corpus: list[FactRecord]) -> None:
    chunks = build_chunks(facts_from_corpus)
    validate_chunks(chunks)


def test_all_source_urls_allowlisted(facts_from_corpus: list[FactRecord]) -> None:
    chunks = build_chunks(facts_from_corpus)
    for chunk in chunks:
        assert chunk.source_url in ALLOWED_URLS


def test_lock_in_only_for_elss(facts_from_corpus: list[FactRecord]) -> None:
    chunks = build_chunks(facts_from_corpus)
    lock_in = [c for c in chunks if c.field == "lock_in_period"]
    assert len(lock_in) == 1
    assert lock_in[0].scheme_id == "hdfc-elss"


def test_per_scheme_chunk_counts(facts_from_corpus: list[FactRecord]) -> None:
    chunks = build_chunks(facts_from_corpus)
    counts = Counter(chunk.scheme_id for chunk in chunks)
    assert counts["hdfc-elss"] == 12
    assert counts["hdfc-mid-cap"] == 11
    assert counts["hdfc-equity"] == 11


def test_no_blocked_fields_in_chunks(facts_from_corpus: list[FactRecord]) -> None:
    chunks = build_chunks(facts_from_corpus)
    for chunk in chunks:
        assert chunk.field not in BLOCKED_FIELDS


def test_build_chunks_rejects_duplicate_facts() -> None:
    fact = FactRecord(
        scheme_id="hdfc-mid-cap",
        scheme_name="HDFC Mid Cap Fund - Direct Growth",
        scheme_category="mid-cap",
        amc="HDFC Mutual Fund",
        source_url=ALLOWED_URLS[0],
        source="groww.in",
        field="expense_ratio",
        value=0.75,
        unit="%",
        display_value="0.75%",
        text="The expense ratio of HDFC Mid Cap Fund - Direct Growth is 0.75%.",
        last_updated="2026-06-24",
        content_hash="sha256:abc",
    )
    with pytest.raises(ValidationError, match="Duplicate fact"):
        build_chunks([fact, fact])


def test_save_chunks_json(tmp_path: Path, facts_from_corpus: list[FactRecord]) -> None:
    chunks = build_chunks(facts_from_corpus)
    out = save_chunks_json(chunks, tmp_path / "chunks.json")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["count"] == 56
    assert len(data["chunks"]) == 56
    assert data["chunks"][0]["chunk_id"]


@pytest.mark.skipif(not FACTS_FILE.exists(), reason="facts.json missing")
def test_build_chunks_from_corpus_integration() -> None:
    chunks = build_chunks_from_corpus()
    assert len(chunks) == 56
    validate_chunks(chunks)


@pytest.mark.skipif(not FACTS_FILE.exists(), reason="facts.json missing")
def test_write_corpus_processed_chunks_json() -> None:
    chunks = build_chunks_from_corpus()
    path = save_chunks_json(chunks)
    assert path == paths.CHUNKS_FILE
    assert path.exists()

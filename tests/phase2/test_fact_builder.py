"""Tests for Phase 2.4 — fact statement synthesis."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from phases import paths
from phases.phase1.config import ALLOWED_URLS
from phases.phase1.registry import load_scheme_registry
from phases.phase2.fact_builder import (
    build_all_facts,
    build_facts,
    build_facts_for_scheme,
    save_facts_json,
    validate_facts,
)
from phases.phase2.groww_selectors import BLOCKED_FIELDS
from phases.phase2.models import NormalizationStatus, NormalizedField
from phases.phase2.normalizer import normalize_parsed_scheme
from phases.phase2.parser import parse_scheme_snapshot

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "corpus" / "raw"


@pytest.fixture
def mid_cap_scheme():
    registry = load_scheme_registry()
    return next(s for s in registry.schemes if s.id == "hdfc-mid-cap")


@pytest.fixture
def mid_cap_normalized():
    parsed = parse_scheme_snapshot("hdfc-mid-cap")
    return normalize_parsed_scheme(parsed)


def test_build_facts_one_per_included_field(mid_cap_scheme, mid_cap_normalized) -> None:
    facts = build_facts(mid_cap_scheme, mid_cap_normalized, amc="HDFC Mutual Fund")
    fields = {fact.field for fact in facts}
    expected = {
        field_id
        for field_id, norm in mid_cap_normalized.items()
        if norm.status in {NormalizationStatus.OK, NormalizationStatus.NONE, NormalizationStatus.ZERO}
    }
    assert fields == expected
    assert len(facts) == len(expected)


def test_fact_source_url_from_scheme_registry(mid_cap_scheme, mid_cap_normalized) -> None:
    facts = build_facts(mid_cap_scheme, mid_cap_normalized, amc="HDFC Mutual Fund")
    for fact in facts:
        assert fact.source_url == mid_cap_scheme.url
        assert fact.source_url in ALLOWED_URLS


def test_expense_ratio_fact_text(mid_cap_scheme, mid_cap_normalized) -> None:
    facts = build_facts(mid_cap_scheme, mid_cap_normalized, amc="HDFC Mutual Fund")
    expense = next(f for f in facts if f.field == "expense_ratio")
    assert expense.text.startswith("The expense ratio of HDFC Mid Cap Fund")
    assert expense.text.endswith(".")
    assert "%" in expense.display_value
    assert expense.unit == "%"


def test_blocked_fields_never_in_facts(mid_cap_scheme, mid_cap_normalized) -> None:
    polluted = dict(mid_cap_normalized)
    polluted["return_1y"] = NormalizedField(
        field_id="return_1y",
        status=NormalizationStatus.OK,
        value=10.0,
        display_value="10%",
    )
    facts = build_facts(mid_cap_scheme, polluted, amc="HDFC Mutual Fund")
    assert "return_1y" not in {f.field for f in facts}


@pytest.mark.skipif(not (RAW_DIR / "hdfc-mid-cap.html").exists(), reason="snapshot missing")
def test_build_facts_for_scheme_integration() -> None:
    facts = build_facts_for_scheme("hdfc-mid-cap")
    validate_facts(facts)
    assert any(f.field == "benchmark" for f in facts)


@pytest.mark.skipif(not RAW_DIR.exists(), reason="corpus/raw missing")
def test_build_all_facts_for_five_schemes() -> None:
    facts = build_all_facts()
    validate_facts(facts)
    scheme_ids = {fact.scheme_id for fact in facts}
    assert len(scheme_ids) == 5
    for fact in facts:
        assert fact.field not in BLOCKED_FIELDS


def test_save_facts_json(tmp_path, mid_cap_scheme, mid_cap_normalized) -> None:
    facts = build_facts(mid_cap_scheme, mid_cap_normalized, amc="HDFC Mutual Fund")
    out = save_facts_json(facts, tmp_path / "facts.json")
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["count"] == len(facts)
    assert len(data["facts"]) == len(facts)


@pytest.mark.skipif(not RAW_DIR.exists(), reason="corpus/raw missing")
def test_write_corpus_processed_facts_json() -> None:
    facts = build_all_facts()
    path = save_facts_json(facts)
    assert path == paths.FACTS_FILE
    assert path.exists()

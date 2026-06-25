"""Tests for Phase 2.2 — HTML / JSON parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from phases.phase2.groww_selectors import BLOCKED_FIELDS, TARGET_FIELDS
from phases.phase2.models import ExtractionStatus
from phases.phase2.parser import parse_all_scheme_snapshots, parse_scheme_html, parse_scheme_snapshot

FIXTURES = Path(__file__).parent / "fixtures"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "corpus" / "raw"


@pytest.fixture
def minimal_html() -> str:
    return (FIXTURES / "minimal_groww_page.html").read_text(encoding="utf-8")


def test_parse_minimal_fixture(minimal_html: str) -> None:
    parsed = parse_scheme_html(minimal_html, "hdfc-mid-cap", scheme_category="mid-cap")
    assert parsed.scheme_id == "hdfc-mid-cap"
    assert parsed.fields["expense_ratio"].status == ExtractionStatus.FOUND
    assert parsed.fields["expense_ratio"].raw_value == "0.75"
    assert parsed.fields["minimum_sip"].status == ExtractionStatus.FOUND
    assert parsed.fields["minimum_lumpsum"].status == ExtractionStatus.FOUND
    assert parsed.fields["benchmark"].status == ExtractionStatus.FOUND


def test_lock_in_skipped_for_non_elss(minimal_html: str) -> None:
    parsed = parse_scheme_html(minimal_html, "hdfc-mid-cap", scheme_category="mid-cap")
    assert parsed.fields["lock_in_period"].status == ExtractionStatus.SKIPPED


@pytest.mark.skipif(not RAW_DIR.exists(), reason="corpus/raw snapshots not present")
def test_parse_all_five_scheme_snapshots() -> None:
    results = parse_all_scheme_snapshots()
    assert len(results) == 5
    for parsed in results:
        assert parsed.scheme_id
        assert len(parsed.fields) == len(TARGET_FIELDS)


@pytest.mark.skipif(not (RAW_DIR / "hdfc-mid-cap.html").exists(), reason="snapshot missing")
def test_mid_cap_core_fields_found_from_corpus() -> None:
    parsed = parse_scheme_snapshot("hdfc-mid-cap")
    for field_id in ("expense_ratio", "exit_load", "minimum_sip", "riskometer", "benchmark", "nav", "aum"):
        assert parsed.fields[field_id].status == ExtractionStatus.FOUND, field_id
    assert parsed.fields["minimum_lumpsum"].status == ExtractionStatus.FOUND
    assert parsed.fields["lock_in_period"].status == ExtractionStatus.SKIPPED


@pytest.mark.skipif(not (RAW_DIR / "hdfc-elss.html").exists(), reason="snapshot missing")
def test_elss_lock_in_found() -> None:
    parsed = parse_scheme_snapshot("hdfc-elss")
    assert parsed.fields["lock_in_period"].status == ExtractionStatus.FOUND
    assert parsed.fields["lock_in_period"].raw_value == "3 years"


def test_no_blocked_fields_in_target_definitions() -> None:
    assert not set(TARGET_FIELDS) & BLOCKED_FIELDS


@pytest.mark.skipif(not (RAW_DIR / "hdfc-mid-cap.html").exists(), reason="snapshot missing")
def test_parser_does_not_extract_blocked_performance_fields() -> None:
    parsed = parse_scheme_snapshot("hdfc-mid-cap")
    for blocked_id in BLOCKED_FIELDS:
        assert blocked_id not in parsed.fields

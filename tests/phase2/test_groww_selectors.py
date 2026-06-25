"""Tests for Phase 2.1 — Groww selectors and field map."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from phases.phase2.groww_selectors import (
    BLOCKED_FIELDS,
    BLOCKED_JSON_PATHS,
    TARGET_FIELDS,
    get_field_definition,
    get_field_definitions,
    get_json_paths_for_field,
    is_blocked_field,
    is_blocked_json_key,
    is_target_field,
    resolve_json_path,
    validate_field_map,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mf_data() -> dict:
    return json.loads((FIXTURES / "mf_server_side_data_snippet.json").read_text(encoding="utf-8"))


def test_validate_field_map_passes() -> None:
    validate_field_map()


def test_target_fields_cover_phase1_data_points() -> None:
    required = {
        "expense_ratio",
        "exit_load",
        "minimum_sip",
        "minimum_lumpsum",
        "lock_in_period",
        "riskometer",
        "benchmark",
        "fund_category",
        "fund_house_amc",
        "nav",
        "aum",
    }
    assert required.issubset(set(TARGET_FIELDS))


def test_target_and_blocked_fields_are_disjoint() -> None:
    assert set(TARGET_FIELDS).isdisjoint(BLOCKED_FIELDS)


def test_each_target_field_has_json_or_dom_spec() -> None:
    for field in get_field_definitions():
        assert field.json_paths is not None or field.dom is not None


def test_blocked_performance_fields_listed() -> None:
    assert "return_1y" in BLOCKED_FIELDS
    assert "cagr" in BLOCKED_FIELDS
    assert "groww_rating" in BLOCKED_FIELDS
    assert "peer_comparison" in BLOCKED_FIELDS


def test_blocked_json_keys_include_return_stats() -> None:
    assert is_blocked_json_key("return_stats")
    assert is_blocked_json_key("simple_return")
    assert is_blocked_json_key("groww_rating")
    assert "return_stats" in BLOCKED_JSON_PATHS


def test_is_target_and_blocked_helpers() -> None:
    assert is_target_field("expense_ratio")
    assert not is_target_field("return_1y")
    assert is_blocked_field("return_1y")
    assert not is_blocked_field("expense_ratio")


@pytest.mark.parametrize(
    "field_id,path,expected",
    [
        ("expense_ratio", "expense_ratio", "0.75"),
        ("minimum_sip", "min_sip_investment", 100),
        ("benchmark", "benchmark_name", "NIFTY Midcap 150 Total Return Index"),
        ("fund_house_amc", "amc", "HDFC"),
        ("nav", "nav", 227.898),
        ("aum", "aum", 97350.4842),
    ],
)
def test_resolve_json_path_on_fixture(mf_data: dict, field_id: str, path: str, expected: object) -> None:
    assert path in get_json_paths_for_field(field_id)
    assert resolve_json_path(mf_data, path) == expected


def test_riskometer_fallback_path(mf_data: dict) -> None:
    paths = get_json_paths_for_field("riskometer")
    assert resolve_json_path(mf_data, paths[0]) == "Moderately High"
    assert resolve_json_path(mf_data, paths[1]) == "Very High"


def test_blocked_json_values_not_in_target_paths(mf_data: dict) -> None:
    for blocked_key in ("groww_rating", "simple_return"):
        assert is_blocked_json_key(blocked_key)
        assert blocked_key not in TARGET_FIELDS


def test_lock_in_applicable_only_to_elss() -> None:
    field = get_field_definition("lock_in_period")
    assert field is not None
    assert field.applicable_categories == frozenset({"elss"})
    assert field.applies_to_category("elss")
    assert not field.applies_to_category("mid-cap")


def test_fixture_html_contains_next_data_script() -> None:
    html = (FIXTURES / "minimal_groww_page.html").read_text(encoding="utf-8")
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    assert match is not None
    data = json.loads(match.group(1))
    mf = data["props"]["pageProps"]["mfServerSideData"]
    assert resolve_json_path(mf, "expense_ratio") == "0.75"


def test_dom_regex_patterns_defined_for_sip_and_lumpsum() -> None:
    sip = get_field_definition("minimum_sip")
    lumpsum = get_field_definition("minimum_lumpsum")
    assert sip is not None and sip.dom is not None
    assert lumpsum is not None and lumpsum.dom is not None
    assert sip.dom.regex_patterns
    assert lumpsum.dom.regex_patterns

    html = (FIXTURES / "minimal_groww_page.html").read_text(encoding="utf-8")
    sip_match = re.search(sip.dom.regex_patterns[0], html, re.IGNORECASE)
    lumpsum_match = re.search(lumpsum.dom.regex_patterns[0], html, re.IGNORECASE)
    assert sip_match is not None
    assert lumpsum_match is not None
    assert sip_match.group(1) == "100"
    assert lumpsum_match.group(1) == "100"

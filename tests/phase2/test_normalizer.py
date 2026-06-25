"""Tests for Phase 2.3 — value normalization."""

from __future__ import annotations

import pytest

from phases.phase2.models import NormalizationStatus
from phases.phase2.normalizer import normalize_field, normalize_parsed_scheme
from phases.phase2.parser import parse_scheme_html

FIXTURE_HTML = """
<html><body>
<script id="__NEXT_DATA__" type="application/json">
{"props":{"pageProps":{"mfServerSideData":{"expense_ratio":"0.75","exit_load":"Nil","min_sip_investment":100,"nav":227.898,"nav_date":"24-Jun-2026"}}}}
</script>
Minimum Lumpsum Investment is ₹1,000.
</body></html>
"""


def test_normalize_percentage_with_and_without_symbol() -> None:
    result = normalize_field("expense_ratio", "0.74%")
    assert result.status == NormalizationStatus.OK
    assert result.value == 0.74
    assert result.unit == "%"
    assert result.display_value == "0.74%"

    bare = normalize_field("expense_ratio", "0.75")
    assert bare.status == NormalizationStatus.OK
    assert bare.value == 0.75
    assert bare.display_value == "0.75%"


def test_normalize_currency_with_rupee_and_commas() -> None:
    result = normalize_field("minimum_sip", "₹1,000")
    assert result.status == NormalizationStatus.OK
    assert result.value == 1000.0
    assert result.unit == "INR"

    plain = normalize_field("minimum_sip", "100")
    assert plain.status == NormalizationStatus.OK
    assert plain.value == 100.0


def test_normalize_nil_and_na_as_none() -> None:
    for raw in ("Nil", "NA", "N/A", "—"):
        result = normalize_field("exit_load", raw)
        assert result.status == NormalizationStatus.NONE
        assert result.value is None


def test_normalize_zero_percent() -> None:
    result = normalize_field("expense_ratio", "0%")
    assert result.status == NormalizationStatus.ZERO
    assert result.value == 0.0


def test_normalize_date_to_iso() -> None:
    result = normalize_field("nav_date", "24-Jun-2026")
    assert result.status == NormalizationStatus.OK
    assert result.value == "2026-06-24"
    assert result.display_value == "24-Jun-2026"


def test_normalize_number_fields() -> None:
    nav = normalize_field("nav", "227.898")
    assert nav.status == NormalizationStatus.OK
    assert nav.value == 227.898

    aum = normalize_field("aum", "97350.4842")
    assert aum.status == NormalizationStatus.OK
    assert aum.value == 97350.4842


def test_normalize_lock_in_not_applicable_for_mid_cap() -> None:
    result = normalize_field("lock_in_period", "3 years", scheme_category="mid-cap")
    assert result.status == NormalizationStatus.NOT_APPLICABLE


def test_normalize_lock_in_ok_for_elss() -> None:
    result = normalize_field("lock_in_period", "3 years", scheme_category="elss")
    assert result.status == NormalizationStatus.OK
    assert result.value == "3 years"


def test_unparseable_returns_status_without_raising() -> None:
    result = normalize_field("expense_ratio", "not-a-number")
    assert result.status == NormalizationStatus.UNPARSEABLE

    empty = normalize_field("minimum_sip", None)
    assert empty.status == NormalizationStatus.UNPARSEABLE


def test_normalize_parsed_scheme_integration() -> None:
    parsed = parse_scheme_html(FIXTURE_HTML, "hdfc-mid-cap", scheme_category="mid-cap")
    normalized = normalize_parsed_scheme(parsed)

    assert normalized["expense_ratio"].status == NormalizationStatus.OK
    assert normalized["exit_load"].status == NormalizationStatus.NONE
    assert normalized["minimum_sip"].value == 100.0
    assert normalized["nav_date"].value == "2026-06-24"
    assert normalized["lock_in_period"].status == NormalizationStatus.NOT_APPLICABLE

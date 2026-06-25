"""Tests for Phase 3 — field intent resolution."""

from __future__ import annotations

from phases.phase3.field_resolver import resolve_fields, resolve_primary_field


def test_resolve_expense_ratio() -> None:
    assert resolve_primary_field("What is the expense ratio of HDFC Mid Cap Fund?") == "expense_ratio"


def test_resolve_exit_load() -> None:
    assert resolve_primary_field("Exit load on HDFC Focused Fund?") == "exit_load"


def test_resolve_minimum_sip() -> None:
    assert resolve_primary_field("Minimum SIP for HDFC Large Cap Fund?") == "minimum_sip"


def test_resolve_lock_in() -> None:
    assert resolve_primary_field("ELSS lock-in for HDFC ELSS Tax Saver?") == "lock_in_period"


def test_resolve_benchmark() -> None:
    assert resolve_primary_field("Benchmark of HDFC Equity Fund?") == "benchmark"


def test_resolve_multiple_fields() -> None:
    fields = resolve_fields("Expense ratio and exit load of HDFC Mid Cap Fund")
    assert "expense_ratio" in fields
    assert "exit_load" in fields


def test_generic_minimum_investment_returns_both_amount_fields() -> None:
    fields = resolve_fields("What is the minimum investment for HDFC Mid Cap?")
    assert fields == ("minimum_sip", "minimum_lumpsum")

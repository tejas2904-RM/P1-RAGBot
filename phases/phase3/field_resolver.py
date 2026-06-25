"""Resolve factual field intent from user queries."""

from __future__ import annotations

import re

# Order matters: more specific phrases before generic ones.
FIELD_INTENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("minimum_sip", ("minimum sip", "min sip", "sip minimum", "minimum monthly sip", "sip amount")),
    (
        "minimum_lumpsum",
        ("minimum lumpsum", "min lumpsum", "lumpsum minimum", "one-time investment", "one time investment"),
    ),
    ("lock_in_period", ("lock-in period", "lock in period", "lock-in", "lock in", "lockin")),
    ("expense_ratio", ("expense ratio", "expense-ratio", " ter", "annual fee", "management fee")),
    ("exit_load", ("exit load", "redemption charge", "redemption fee")),
    ("riskometer", ("riskometer", "risk rating", "risk classification", "risk level")),
    ("benchmark", ("benchmark", "benchmark index", "tracks index", "index tracked")),
    ("fund_category", ("fund category", "fund type", "category of", "what category", "which category")),
    ("fund_house_amc", ("fund house", "amc", "asset management company", "which amc")),
    ("nav_date", ("nav date", "nav as of", "nav as-of")),
    ("nav", (" nav", "net asset value")),
    ("aum", ("aum", "assets under management", "fund size")),
)

_GENERIC_MIN_INVESTMENT_PHRASES = ("minimum investment", "minimum amount", "min investment")


def _normalize(query: str) -> str:
    lowered = query.lower().strip()
    lowered = re.sub(r"[^\w\s%-]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return f" {lowered} "


def resolve_fields(query: str) -> tuple[str, ...]:
    """Return canonical field ids mentioned in the query (may be multiple)."""
    normalized = _normalize(query)
    matched: list[str] = []

    for field_id, phrases in FIELD_INTENT_RULES:
        if any(phrase in normalized for phrase in phrases):
            if field_id not in matched:
                matched.append(field_id)

    if not matched and any(phrase in normalized for phrase in _GENERIC_MIN_INVESTMENT_PHRASES):
        return ("minimum_sip", "minimum_lumpsum")

    return tuple(matched)


def resolve_primary_field(query: str) -> str | None:
    """Return the first resolved field, if any."""
    fields = resolve_fields(query)
    return fields[0] if fields else None

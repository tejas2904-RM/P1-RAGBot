"""Map classification categories to fixed refusal responses."""

from __future__ import annotations

from phases.phase4.config import (
    EMPTY_QUERY_MESSAGE,
    GREETING_MESSAGE,
    OUT_OF_SCOPE_REFUSAL,
)
from phases.phase4.models import QueryCategory
from phases.phase4.performance_handler import performance_refusal
from phases.phase4.refusal_handler import advisory_refusal, comparative_refusal, pii_refusal


def refusal_for_category(category: QueryCategory) -> str:
    """Return the fixed response text for a non-factual category."""
    if category == QueryCategory.PERFORMANCE:
        return performance_refusal()
    if category in {QueryCategory.ADVISORY, QueryCategory.COMPARATIVE, QueryCategory.PII}:
        if category == QueryCategory.COMPARATIVE:
            return comparative_refusal()
        if category == QueryCategory.PII:
            return pii_refusal()
        return advisory_refusal()
    if category == QueryCategory.OUT_OF_SCOPE:
        return OUT_OF_SCOPE_REFUSAL
    if category == QueryCategory.EMPTY:
        return EMPTY_QUERY_MESSAGE
    if category == QueryCategory.GREETING:
        return GREETING_MESSAGE
    return OUT_OF_SCOPE_REFUSAL


def assert_refusal_has_no_urls(answer: str) -> None:
    """Guardrail: refusal templates must never contain http(s) links."""
    lowered = answer.lower()
    if "http://" in lowered or "https://" in lowered:
        raise ValueError("Refusal response must not contain URLs")

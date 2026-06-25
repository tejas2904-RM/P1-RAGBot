"""Rule-based query classifier — routes to RAG or fixed refusals."""

from __future__ import annotations

import re

from phases.phase1.registry import load_scheme_registry
from phases.phase1.scheme_resolver import SchemeResolver, _normalize
from phases.phase3.field_resolver import resolve_fields
from phases.phase4.config import MAX_QUERY_CHARS
from phases.phase4.models import ClassificationResult, QueryCategory

_PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
_AADHAAR_PATTERN = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
_OTP_PATTERN = re.compile(r"\botp\b", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE_PATTERN = re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b")

_PII_KEYWORDS: tuple[str, ...] = (
    "pan number",
    "aadhaar",
    "aadhar",
    "account number",
    "account balance",
    "my balance",
    "my portfolio",
    "check my",
)

_PERFORMANCE_PATTERNS: tuple[str, ...] = (
    "return",
    "returns",
    "cagr",
    "outperform",
    "underperform",
    "profit",
    "gains",
    "gain ",
    "lost money",
    "performance",
    "nav history",
    "historical nav",
    "calculate my",
    "how much will i make",
    "how much money",
    "1-year",
    "1 year",
    "3-year",
    "5-year",
    "annualized",
    "yield",
    "xirr",
    "sip returns",
)

_ADVISORY_PATTERNS: tuple[str, ...] = (
    "should i invest",
    "should i buy",
    "should i sell",
    "should i purchase",
    "worth investing",
    "worth buying",
    "good fund",
    "good investment",
    "safe fund",
    "recommend",
    "recommendation",
    "advice",
    "invest in this",
    "buy this fund",
    "sell this fund",
    "is it worth",
    "would you suggest",
)

_COMPARATIVE_PATTERNS: tuple[str, ...] = (
    " which is better",
    " which fund is better",
    "which is best",
    "which fund is best",
    " vs ",
    " versus ",
    "compare ",
    "comparison",
    "better than",
    " or large cap",
    " or mid cap",
    " or elss",
)

_OTHER_AMC_MARKERS: tuple[str, ...] = (
    "sbi ",
    " sbi",
    "icici",
    "axis mutual",
    "axis fund",
    "nippon",
    "parag parikh",
    "uti mutual",
    "kotak mutual",
    "mirae asset",
    "tata mutual",
    "dsp mutual",
    "franklin templeton",
    "bluechip fund",
    "blue chip fund",
)

_BROAD_TOPIC_PATTERNS: tuple[str, ...] = (
    "tell me about mutual fund",
    "what are mutual fund",
    "how do mutual fund",
    "explain mutual fund",
)

_GREETING_PATTERNS: tuple[str, ...] = (
    "hi",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "thanks",
    "thank you",
)


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


def _mentions_other_amc(text: str) -> bool:
    return _contains_any(text, _OTHER_AMC_MARKERS)


def _is_greeting_only(text: str) -> bool:
    stripped = text.strip(" .!?")
    return stripped in _GREETING_PATTERNS


def _has_pii(query: str, normalized: str) -> bool:
    if _PAN_PATTERN.search(query):
        return True
    if _AADHAAR_PATTERN.search(query):
        return True
    if _OTP_PATTERN.search(normalized):
        return True
    if _EMAIL_PATTERN.search(query):
        return True
    if _PHONE_PATTERN.search(query):
        return True
    return _contains_any(normalized, _PII_KEYWORDS)


def _has_performance_intent(normalized: str) -> bool:
    return _contains_any(normalized, _PERFORMANCE_PATTERNS)


def _has_advisory_intent(normalized: str) -> bool:
    return _contains_any(normalized, _ADVISORY_PATTERNS)


def _has_comparative_intent(normalized: str) -> bool:
    if _contains_any(normalized, _COMPARATIVE_PATTERNS):
        return True
    if " vs " in normalized or " versus " in normalized:
        return True
    if re.search(r"\bwhich\b.+\b(better|best)\b", normalized):
        return True
    return False


def _is_out_of_scope(query: str, normalized: str, resolver: SchemeResolver) -> bool:
    if _mentions_other_amc(normalized):
        return True

    if _contains_any(normalized, _BROAD_TOPIC_PATTERNS) and resolver.resolve(query) is None:
        return True

    # Non-HDFC fund mention with fund language but no corpus scheme.
    if resolver.resolve(query) is None and "fund" in normalized:
        if "hdfc" not in normalized and any(
            token in normalized for token in ("mutual fund", "scheme", "elss", "large cap", "mid cap")
        ):
            return True

    return False


def classify_query(query: str) -> ClassificationResult:
    """Classify a user query using rule-based patterns (hybrid MVP — rules first)."""
    cleaned = query.strip()
    if not cleaned:
        return ClassificationResult(QueryCategory.EMPTY, "empty query")

    if len(cleaned) > MAX_QUERY_CHARS:
        cleaned = cleaned[:MAX_QUERY_CHARS]

    normalized = f" {_normalize(cleaned)} "
    if _is_greeting_only(_normalize(cleaned)):
        return ClassificationResult(QueryCategory.GREETING, "greeting only")

    if _has_pii(cleaned, normalized):
        return ClassificationResult(QueryCategory.PII, "pii detected")

    if _has_performance_intent(normalized):
        return ClassificationResult(QueryCategory.PERFORMANCE, "performance or returns intent")

    if _has_advisory_intent(normalized):
        return ClassificationResult(QueryCategory.ADVISORY, "advisory intent")

    if _has_comparative_intent(normalized):
        return ClassificationResult(QueryCategory.COMPARATIVE, "comparative intent")

    registry = load_scheme_registry()
    resolver = SchemeResolver(registry)
    if _is_out_of_scope(cleaned, normalized, resolver):
        return ClassificationResult(QueryCategory.OUT_OF_SCOPE, "unlisted scheme or broad topic")

    return ClassificationResult(QueryCategory.FACTUAL, "factual query")

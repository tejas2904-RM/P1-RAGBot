"""Phase 4 configuration — fixed refusal templates (no external links)."""

from __future__ import annotations

ADVISORY_COMPARATIVE_REFUSAL = """I can only answer factual questions about the five HDFC mutual fund schemes available in this assistant. I cannot provide investment advice, recommendations, or fund comparisons.

Facts-only. No investment advice."""

PERFORMANCE_REFUSAL = """I do not provide performance data, return calculations, or projections. I can answer factual questions such as expense ratio, exit load, minimum SIP, lock-in period, riskometer classification, or benchmark index.

Facts-only. No investment advice."""

OUT_OF_SCOPE_REFUSAL = """This assistant only covers five HDFC mutual fund schemes (Mid Cap, Equity, Focused, ELSS Tax Saver, Large Cap — Direct Growth). I don't have information about other funds or topics.

Facts-only. No investment advice."""

EMPTY_QUERY_MESSAGE = (
    "Please enter a factual question about one of the five HDFC mutual fund schemes "
    "(for example expense ratio, exit load, minimum SIP, lock-in, riskometer, or benchmark)."
)

GREETING_MESSAGE = (
    "Hello. I can answer factual questions about the five HDFC mutual fund schemes in this "
    "assistant. Try asking about expense ratio, exit load, minimum SIP, lock-in, riskometer, or benchmark."
)

MAX_QUERY_CHARS = 500

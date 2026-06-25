"""Phase 5 API configuration — bootstrap content for the UI."""

from __future__ import annotations

APP_TITLE = "Mutual Fund FAQ Assistant"
DISCLAIMER = "Facts-only. No investment advice."

WELCOME_MESSAGE = (
    "Ask factual questions about five HDFC mutual fund schemes (Direct Growth) "
    "sourced from Groww. I can help with expense ratio, exit load, minimum SIP, "
    "lock-in period, riskometer, benchmark, and similar objective details. "
    "I cannot provide investment advice, comparisons, or performance projections."
)

EXAMPLE_QUESTIONS: tuple[str, ...] = (
    "What is the expense ratio of HDFC Mid Cap Fund?",
    "What is the lock-in period of HDFC ELSS Tax Saver Fund?",
    "What is the benchmark index of HDFC Large Cap Fund?",
)

MAX_REQUEST_BODY_BYTES = 8_192
DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8000

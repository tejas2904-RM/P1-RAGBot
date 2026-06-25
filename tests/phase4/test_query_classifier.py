"""Tests for Phase 4 — query classifier."""

from __future__ import annotations

import pytest

from phases.phase4.models import QueryCategory
from phases.phase4.query_classifier import classify_query

FACTUAL_QUERIES = [
    "What is the expense ratio of HDFC Mid Cap Fund?",
    "Exit load on HDFC Focused Fund?",
    "Minimum SIP for HDFC Large Cap Fund?",
    "ELSS lock-in for HDFC ELSS Tax Saver?",
    "Benchmark of HDFC Equity Fund?",
    "What is the expense ratio?",
    "HDFC Mid Cap ka expense ratio kya hai?",
]

REFUSAL_QUERIES: list[tuple[str, QueryCategory]] = [
    ("Should I invest in HDFC Mid Cap?", QueryCategory.ADVISORY),
    ("Mid Cap vs Large Cap — which is better?", QueryCategory.COMPARATIVE),
    ("What was the 1-year return of HDFC Mid Cap?", QueryCategory.PERFORMANCE),
    ("Tell me about SBI Bluechip Fund", QueryCategory.OUT_OF_SCOPE),
    ("My PAN is ABCDE1234F, check my balance", QueryCategory.PII),
    ("Expense ratio and should I buy Mid Cap?", QueryCategory.ADVISORY),
    ("Will HDFC Equity Fund outperform the market?", QueryCategory.PERFORMANCE),
    ("Which fund is better for tax saving?", QueryCategory.COMPARATIVE),
    ("What is my account balance?", QueryCategory.PII),
    ("Tell me about mutual funds in general", QueryCategory.OUT_OF_SCOPE),
]


@pytest.mark.parametrize("query", FACTUAL_QUERIES)
def test_factual_queries_classified_correctly(query: str) -> None:
    result = classify_query(query)
    assert result.category == QueryCategory.FACTUAL, f"{query!r} -> {result.category}"


@pytest.mark.parametrize("query,expected", REFUSAL_QUERIES)
def test_refusal_queries_classified_correctly(query: str, expected: QueryCategory) -> None:
    result = classify_query(query)
    assert result.category == expected, f"{query!r} -> {result.category} ({result.reason})"


def test_empty_query() -> None:
    assert classify_query("").category == QueryCategory.EMPTY
    assert classify_query("   ").category == QueryCategory.EMPTY


def test_greeting_only() -> None:
    assert classify_query("Hello").category == QueryCategory.GREETING
    assert classify_query("Thanks").category == QueryCategory.GREETING


def test_greeting_with_question_is_factual() -> None:
    result = classify_query("Hi, what is the expense ratio of HDFC Mid Cap Fund?")
    assert result.category == QueryCategory.FACTUAL


def test_classifier_accuracy_on_labeled_set() -> None:
    labeled = [(q, QueryCategory.FACTUAL) for q in FACTUAL_QUERIES] + REFUSAL_QUERIES
    correct = sum(1 for query, expected in labeled if classify_query(query).category == expected)
    accuracy = correct / len(labeled)
    assert accuracy >= 0.95, f"accuracy {accuracy:.1%} below 95%"

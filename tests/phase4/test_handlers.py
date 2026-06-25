"""Tests for Phase 4 — refusal templates and handlers."""

from __future__ import annotations

import re

import pytest

from phases.phase4.config import (
    ADVISORY_COMPARATIVE_REFUSAL,
    OUT_OF_SCOPE_REFUSAL,
    PERFORMANCE_REFUSAL,
)
from phases.phase4.handlers import assert_refusal_has_no_urls, refusal_for_category
from phases.phase4.models import QueryCategory
from phases.phase4.performance_handler import performance_refusal
from phases.phase4.refusal_handler import advisory_refusal

_URL_RE = re.compile(r"https?://", re.IGNORECASE)


@pytest.mark.parametrize(
    "text",
    [
        ADVISORY_COMPARATIVE_REFUSAL,
        PERFORMANCE_REFUSAL,
        OUT_OF_SCOPE_REFUSAL,
        advisory_refusal(),
        performance_refusal(),
    ],
)
def test_refusal_templates_contain_no_urls(text: str) -> None:
    assert not _URL_RE.search(text)
    assert_refusal_has_no_urls(text)


def test_refusal_templates_include_disclaimer() -> None:
    assert "Facts-only. No investment advice." in advisory_refusal()
    assert "Facts-only. No investment advice." in performance_refusal()
    assert "Facts-only. No investment advice." in OUT_OF_SCOPE_REFUSAL


@pytest.mark.parametrize(
    "category",
    [
        QueryCategory.ADVISORY,
        QueryCategory.COMPARATIVE,
        QueryCategory.PERFORMANCE,
        QueryCategory.PII,
        QueryCategory.OUT_OF_SCOPE,
    ],
)
def test_refusal_for_category_has_no_urls(category: QueryCategory) -> None:
    answer = refusal_for_category(category)
    assert_refusal_has_no_urls(answer)

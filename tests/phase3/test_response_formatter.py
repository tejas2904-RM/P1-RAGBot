"""Tests for Phase 3 — response formatting and validation."""

from __future__ import annotations

import pytest

from phases.phase1.config import ALLOWED_URLS
from phases.phase1.validator import ValidationError
from phases.phase2.models import SearchResult
from phases.phase3.response_formatter import (
    count_sentences,
    extract_source_url,
    format_response,
    validate_formatted_response,
)

MID_CAP_URL = ALLOWED_URLS[0]


def _search_result(**overrides) -> SearchResult:
    metadata = {
        "scheme_name": "HDFC Mid Cap Fund - Direct Growth",
        "display_value": "0.75%",
        "value": "0.75",
        "last_updated": "2026-06-24",
    }
    metadata.update(overrides.get("metadata", {}))
    return SearchResult(
        chunk_id=overrides.get("chunk_id", "chunk-1"),
        text=overrides.get("text", "The expense ratio of HDFC Mid Cap Fund - Direct Growth is 0.75%."),
        source_url=overrides.get("source_url", MID_CAP_URL),
        scheme_id=overrides.get("scheme_id", "hdfc-mid-cap"),
        field=overrides.get("field", "expense_ratio"),
        score=overrides.get("score", 0.99),
        metadata=metadata,
    )


def test_format_response_template() -> None:
    formatted = format_response(
        "The expense ratio of HDFC Mid Cap Fund - Direct Growth is 0.75%.",
        source_url=MID_CAP_URL,
        last_updated="2026-06-24",
    )
    assert "Source: " + MID_CAP_URL in formatted
    assert "Last updated from sources: 2026-06-24" in formatted
    assert count_sentences(formatted.split("Source:")[0]) == 1


def test_validate_formatted_response_accepts_valid_answer() -> None:
    chunk = _search_result()
    formatted = format_response(
        chunk.text,
        source_url=chunk.source_url,
        last_updated="2026-06-24",
    )
    validate_formatted_response(formatted, chunks=[chunk])


def test_validate_rejects_multiple_urls() -> None:
    chunk = _search_result()
    formatted = (
        f"{chunk.text}\n\nSource: {chunk.source_url}\n\n"
        f"Also see {ALLOWED_URLS[1]}\n\nLast updated from sources: 2026-06-24"
    )
    with pytest.raises(ValidationError, match="exactly one"):
        validate_formatted_response(formatted, chunks=[chunk])


def test_validate_rejects_disallowed_url() -> None:
    chunk = _search_result()
    formatted = format_response(
        chunk.text,
        source_url="https://example.com/fund",
        last_updated="2026-06-24",
    )
    with pytest.raises(ValidationError, match="ALLOWED_URLS"):
        validate_formatted_response(formatted, chunks=[chunk])


def test_extract_source_url() -> None:
    formatted = format_response("Answer.", source_url=MID_CAP_URL, last_updated="2026-06-24")
    assert extract_source_url(formatted) == MID_CAP_URL

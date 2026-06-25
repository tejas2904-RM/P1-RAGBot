"""Validate and format Phase 3 responses."""

from __future__ import annotations

import re

from phases.phase1.config import ALLOWED_URLS
from phases.phase1.validator import ValidationError
from phases.phase2.models import SearchResult
from phases.phase3.config import ADVISORY_PHRASES, INSUFFICIENT_CONTEXT_MESSAGE, MAX_ANSWER_SENTENCES

_URL_PATTERN = re.compile(r"https?://[^\s]+")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def split_answer_body(formatted_answer: str) -> str:
    """Return the answer body before the Source footer."""
    parts = formatted_answer.split("\n\nSource:", 1)
    return parts[0].strip()


def count_sentences(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0
    return len([part for part in _SENTENCE_SPLIT.split(stripped) if part.strip()])


def extract_source_url(formatted_answer: str) -> str | None:
    match = re.search(r"Source:\s*(https?://\S+)", formatted_answer)
    if not match:
        return None
    return match.group(1).rstrip(".")


def extract_last_updated(formatted_answer: str) -> str | None:
    match = re.search(r"Last updated from sources:\s*(\S+)", formatted_answer)
    if not match:
        return None
    return match.group(1).strip()


def format_response(answer_body: str, *, source_url: str, last_updated: str) -> str:
    """Apply the canonical response template."""
    body = answer_body.strip()
    if body and not body.endswith((".", "!", "?")):
        body += "."
    return f"{body}\n\nSource: {source_url}\n\nLast updated from sources: {last_updated}"


def _chunk_values(chunks: list[SearchResult]) -> set[str]:
    values: set[str] = set()
    for item in chunks:
        metadata = item.metadata
        display_value = metadata.get("display_value")
        if display_value:
            values.add(str(display_value).strip().lower())
        raw_value = metadata.get("value")
        if raw_value is not None:
            values.add(str(raw_value).strip().lower())
        if item.text:
            values.add(item.text.strip().lower())
    return values


def validate_answer_body(answer_body: str, *, chunks: list[SearchResult]) -> None:
    """Ensure generated body is safe and grounded in retrieved chunks."""
    normalized = answer_body.strip()
    if not normalized or normalized == "INSUFFICIENT_CONTEXT":
        raise ValidationError("Insufficient context for a factual answer")

    lowered = normalized.lower()
    for phrase in ADVISORY_PHRASES:
        if phrase in lowered:
            raise ValidationError(f"Advisory language detected: {phrase}")

    if count_sentences(normalized) > MAX_ANSWER_SENTENCES:
        raise ValidationError(f"Answer exceeds {MAX_ANSWER_SENTENCES} sentences")

    if _URL_PATTERN.search(normalized):
        raise ValidationError("Answer body must not contain URLs")

    allowed_values = _chunk_values(chunks)
    if allowed_values and not any(value in lowered for value in allowed_values if len(value) >= 3):
        raise ValidationError("Answer body is not grounded in retrieved chunk values")


def validate_formatted_response(formatted_answer: str, *, chunks: list[SearchResult]) -> None:
    """Validate full response including citation and footer."""
    body = split_answer_body(formatted_answer)
    validate_answer_body(body, chunks=chunks)

    urls = _URL_PATTERN.findall(formatted_answer)
    if len(urls) != 1:
        raise ValidationError("Response must contain exactly one source URL")

    source_url = extract_source_url(formatted_answer)
    if source_url not in ALLOWED_URLS:
        raise ValidationError(f"Source URL not in ALLOWED_URLS: {source_url}")

    expected_urls = {item.source_url for item in chunks}
    if source_url not in expected_urls:
        raise ValidationError("Source URL does not match retrieved chunk metadata")

    if not extract_last_updated(formatted_answer):
        raise ValidationError("Missing last updated footer")


def build_insufficient_response() -> str:
    return INSUFFICIENT_CONTEXT_MESSAGE

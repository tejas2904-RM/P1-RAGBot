"""Tests for Phase 3 — Groq answer generator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from phases.phase3.generator import GroqAnswerGenerator


def _chunk():
    from phases.phase1.config import ALLOWED_URLS
    from phases.phase2.models import SearchResult

    return SearchResult(
        chunk_id="chunk-1",
        text="The expense ratio of HDFC Mid Cap Fund - Direct Growth is 0.75%.",
        source_url=ALLOWED_URLS[0],
        scheme_id="hdfc-mid-cap",
        field="expense_ratio",
        score=1.0,
        metadata={
            "scheme_name": "HDFC Mid Cap Fund - Direct Growth",
            "display_value": "0.75%",
            "last_updated": "2026-06-24",
        },
    )


@patch("phases.phase3.generator.GroqAnswerGenerator._get_client")
def test_groq_generator_returns_model_content(mock_get_client) -> None:
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="The expense ratio is 0.75%."))]
    mock_client.chat.completions.create.return_value = mock_response
    mock_get_client.return_value = mock_client

    generator = GroqAnswerGenerator(api_key="test-groq-key", model="llama-3.3-70b-versatile")
    result = generator.generate("expense ratio?", [_chunk()])

    assert result == "The expense ratio is 0.75%."
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "llama-3.3-70b-versatile"
    assert call_kwargs["temperature"] == 0.0

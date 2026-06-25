"""Service layer — wraps Phase 4 pipeline for the HTTP API."""

from __future__ import annotations

import logging
import os

from phases.phase2.indexer import get_index_stats
from phases.phase3.generator import get_generator_name, is_llm_enabled
from phases.phase3.response_formatter import split_answer_body
from phases.phase4.pipeline import handle_query
from phases.phase5.config import DISCLAIMER, EXAMPLE_QUESTIONS, WELCOME_MESSAGE, APP_TITLE
from phases.phase5.models import BootstrapResponse, ChatResponse, ExampleQuestion, HealthResponse

logger = logging.getLogger(__name__)


def get_health() -> HealthResponse:
    stats = get_index_stats(min_chunk_count=0)
    status = "ok" if stats.ready else "degraded"
    return HealthResponse(
        status=status,
        index_ready=stats.ready,
        index_chunk_count=stats.chunk_count,
        embedding_model=stats.embedding_model if stats.embedding_model else None,
        generator=get_generator_name(),
        llm_enabled=is_llm_enabled(),
        groq_configured=bool(os.getenv("GROQ_API_KEY") or os.getenv("GENERATOR_API_KEY")),
    )


def get_bootstrap() -> BootstrapResponse:
    return BootstrapResponse(
        title=APP_TITLE,
        disclaimer=DISCLAIMER,
        welcome_message=WELCOME_MESSAGE,
        example_questions=[ExampleQuestion(text=item) for item in EXAMPLE_QUESTIONS],
    )


def ask_question(query: str) -> ChatResponse:
    """Run the classified assistant pipeline and shape the API response."""
    result = handle_query(query)
    answer_body: str | None = None
    if result.source_url and "Source:" in result.answer:
        answer_body = split_answer_body(result.answer)
    elif not result.refused:
        answer_body = result.answer.strip() or None

    logger.info(
        "chat query handled category=%s refused=%s success=%s used_llm=%s",
        result.category.value,
        result.refused,
        result.success,
        result.used_llm,
    )

    return ChatResponse(
        query=result.query,
        answer=result.answer,
        answer_body=answer_body,
        source_url=result.source_url,
        last_updated=result.last_updated,
        category=result.category.value,
        refused=result.refused,
        success=result.success,
        used_llm=result.used_llm,
        scheme_id=result.scheme_id,
        fields=list(result.fields),
    )

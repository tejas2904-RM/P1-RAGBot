"""Phase 4 orchestrator — classify, refuse, or delegate to Phase 3 RAG."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from phases.phase2.embedder import EmbeddingBackend
from phases.phase3.generator import AnswerGenerator
from phases.phase3.pipeline import answer_query
from phases.phase4.handlers import assert_refusal_has_no_urls, refusal_for_category
from phases.phase4.models import AssistantResponse, QueryCategory
from phases.phase4.query_classifier import classify_query

logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(r"https?://", re.IGNORECASE)


def _refusal_response(query: str, category: QueryCategory) -> AssistantResponse:
    answer = refusal_for_category(category)
    assert_refusal_has_no_urls(answer)
    return AssistantResponse(
        query=query,
        answer=answer,
        category=category,
        refused=True,
        success=False,
    )


def handle_query(
    query: str,
    *,
    backend: EmbeddingBackend | None = None,
    generator: AnswerGenerator | None = None,
    index_path: Path | None = None,
) -> AssistantResponse:
    """Classify the query, refuse unsafe inputs, or run the Phase 3 RAG pipeline."""
    classification = classify_query(query)
    logger.info("Query classified as %s (%s)", classification.category.value, classification.reason)

    if classification.category != QueryCategory.FACTUAL:
        return _refusal_response(query, classification.category)

    rag = answer_query(
        query,
        backend=backend,
        generator=generator,
        index_path=index_path,
    )

    if _URL_PATTERN.search(rag.answer) and rag.source_url:
        return AssistantResponse(
            query=query,
            answer=rag.answer,
            category=QueryCategory.FACTUAL,
            refused=False,
            source_url=rag.source_url,
            last_updated=rag.last_updated,
            scheme_id=rag.scheme_id,
            fields=rag.fields,
            retrieval_mode=rag.retrieval_mode,
            used_llm=rag.used_llm,
            success=rag.success,
        )

    return AssistantResponse(
        query=query,
        answer=rag.answer,
        category=QueryCategory.FACTUAL,
        refused=False,
        source_url=rag.source_url,
        last_updated=rag.last_updated,
        scheme_id=rag.scheme_id,
        fields=rag.fields,
        retrieval_mode=rag.retrieval_mode,
        used_llm=rag.used_llm,
        success=rag.success,
    )

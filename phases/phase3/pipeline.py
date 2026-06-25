"""End-to-end Phase 3 RAG pipeline."""

from __future__ import annotations

import logging
from pathlib import Path

from phases.phase1.validator import ValidationError
from phases.phase2.embedder import EmbeddingBackend, get_embedding_backend
from phases.phase2.indexer import get_index_stats
from phases.phase2.models import SearchResult
from phases.phase3.config import INDEX_NOT_READY_MESSAGE, MAX_QUERY_CHARS
from phases.phase3.generator import AnswerGenerator, TemplateAnswerGenerator, get_answer_generator
from phases.phase3.models import RAGResponse, RetrievalMode
from phases.phase3.response_formatter import (
    build_insufficient_response,
    format_response,
    validate_formatted_response,
)
from phases.phase3.retriever import retrieve

logger = logging.getLogger(__name__)


def _primary_chunk(chunks: list[SearchResult]) -> SearchResult:
    return chunks[0]


def _footer_date(chunks: list[SearchResult]) -> str:
    dates = [str(item.metadata.get("last_updated", "")) for item in chunks if item.metadata.get("last_updated")]
    if not dates:
        return ""
    return max(dates)


def answer_query(
    query: str,
    *,
    backend: EmbeddingBackend | None = None,
    generator: AnswerGenerator | None = None,
    index_path: Path | None = None,
) -> RAGResponse:
    """Run retrieval, generation, formatting, and validation for a user query."""
    cleaned = query.strip()
    if not cleaned:
        return RAGResponse(
            query=query,
            answer=build_insufficient_response(),
            source_url=None,
            last_updated=None,
            scheme_id=None,
            fields=(),
            retrieval_mode=None,
            used_llm=False,
            success=False,
        )

    if len(cleaned) > MAX_QUERY_CHARS:
        cleaned = cleaned[:MAX_QUERY_CHARS]

    stats = get_index_stats(index_path=index_path, min_chunk_count=0)
    if not stats.ready:
        return RAGResponse(
            query=query,
            answer=INDEX_NOT_READY_MESSAGE,
            source_url=None,
            last_updated=None,
            scheme_id=None,
            fields=(),
            retrieval_mode=None,
            used_llm=False,
            success=False,
        )

    embedder = backend or get_embedding_backend()
    answer_gen = generator or get_answer_generator()
    used_llm = not isinstance(answer_gen, TemplateAnswerGenerator)

    retrieval = retrieve(cleaned, backend=embedder, index_path=index_path)
    if not retrieval.found:
        return RAGResponse(
            query=query,
            answer=build_insufficient_response(),
            source_url=None,
            last_updated=None,
            scheme_id=retrieval.scheme_id,
            fields=retrieval.fields,
            retrieval_mode=retrieval.mode,
            used_llm=False,
            success=False,
        )

    chunks = list(retrieval.chunks)
    top = _primary_chunk(chunks)
    body = answer_gen.generate(cleaned, chunks)

    if body.strip() == "INSUFFICIENT_CONTEXT":
        return RAGResponse(
            query=query,
            answer=build_insufficient_response(),
            source_url=None,
            last_updated=None,
            scheme_id=retrieval.scheme_id,
            fields=retrieval.fields,
            retrieval_mode=retrieval.mode,
            used_llm=used_llm,
            success=False,
        )

    try:
        formatted = format_response(
            body,
            source_url=top.source_url,
            last_updated=_footer_date(chunks),
        )
        validate_formatted_response(formatted, chunks=chunks)
    except ValidationError as exc:
        logger.warning("Response validation failed, using template fallback: %s", exc)
        fallback = TemplateAnswerGenerator().generate(cleaned, chunks)
        if fallback.strip() == "INSUFFICIENT_CONTEXT":
            return RAGResponse(
                query=query,
                answer=build_insufficient_response(),
                source_url=None,
                last_updated=None,
                scheme_id=retrieval.scheme_id,
                fields=retrieval.fields,
                retrieval_mode=retrieval.mode,
                used_llm=False,
                success=False,
            )
        formatted = format_response(
            fallback,
            source_url=top.source_url,
            last_updated=_footer_date(chunks),
        )
        validate_formatted_response(formatted, chunks=chunks)
        used_llm = False

    return RAGResponse(
        query=query,
        answer=formatted,
        source_url=top.source_url,
        last_updated=_footer_date(chunks),
        scheme_id=retrieval.scheme_id or top.scheme_id,
        fields=retrieval.fields or tuple(item.field for item in chunks),
        retrieval_mode=retrieval.mode,
        used_llm=used_llm,
        success=True,
    )

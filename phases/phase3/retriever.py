"""Metadata-first retrieval with vector search fallback."""

from __future__ import annotations

import logging
from pathlib import Path

from phases.phase1.registry import load_scheme_registry
from phases.phase1.scheme_resolver import SchemeResolver
from phases.phase2.embedder import EmbeddingBackend
from phases.phase2.indexer import fetch_chunks_by_metadata, similarity_search
from phases.phase2.models import SearchResult
from phases.phase3.config import (
    DEFAULT_MIN_SIMILARITY_SCORE,
    DEFAULT_TOP_K_FIELD,
    DEFAULT_TOP_K_GLOBAL,
    DEFAULT_TOP_K_SCHEME,
)
from phases.phase3.field_resolver import resolve_fields
from phases.phase3.models import RetrievalMode, RetrievalResult

logger = logging.getLogger(__name__)


def _dedupe_results(results: list[SearchResult]) -> list[SearchResult]:
    seen: set[str] = set()
    unique: list[SearchResult] = []
    for item in results:
        if item.chunk_id in seen:
            continue
        seen.add(item.chunk_id)
        unique.append(item)
    return unique


def _filter_by_score(results: list[SearchResult], min_score: float) -> list[SearchResult]:
    return [item for item in results if item.score >= min_score]


def _retrieve_exact(
    query: str,
    *,
    scheme_id: str,
    fields: tuple[str, ...],
    backend: EmbeddingBackend | None,
    index_path: Path | None,
    min_score: float,
) -> list[SearchResult]:
    del query, backend, min_score  # exact tier uses metadata lookup, not embeddings
    results: list[SearchResult] = []
    for field in fields:
        hits = fetch_chunks_by_metadata(
            scheme_id=scheme_id,
            field=field,
            index_path=index_path,
        )
        results.extend(hits)
    return _dedupe_results(results)


def _retrieve_scheme_filtered(
    query: str,
    *,
    scheme_id: str,
    backend: EmbeddingBackend | None,
    index_path: Path | None,
    min_score: float,
    top_k: int,
) -> list[SearchResult]:
    hits = similarity_search(
        query,
        top_k=top_k,
        scheme_id=scheme_id,
        index_path=index_path,
        backend=backend,
    )
    return _filter_by_score(_dedupe_results(hits), min_score)


def _retrieve_field_filtered(
    query: str,
    *,
    fields: tuple[str, ...],
    backend: EmbeddingBackend | None,
    index_path: Path | None,
    min_score: float,
    top_k: int,
) -> list[SearchResult]:
    results: list[SearchResult] = []
    for field in fields:
        hits = similarity_search(
            query,
            top_k=top_k,
            field=field,
            index_path=index_path,
            backend=backend,
        )
        results.extend(_filter_by_score(hits, min_score))
    results.sort(key=lambda item: item.score, reverse=True)
    return _dedupe_results(results)[:top_k]


def _retrieve_global(
    query: str,
    *,
    backend: EmbeddingBackend | None,
    index_path: Path | None,
    min_score: float,
    top_k: int,
) -> list[SearchResult]:
    hits = similarity_search(
        query,
        top_k=top_k,
        index_path=index_path,
        backend=backend,
    )
    return _filter_by_score(_dedupe_results(hits), min_score)


def retrieve(
    query: str,
    *,
    backend: EmbeddingBackend | None = None,
    index_path: Path | None = None,
    min_score: float = DEFAULT_MIN_SIMILARITY_SCORE,
    top_k_scheme: int = DEFAULT_TOP_K_SCHEME,
    top_k_field: int = DEFAULT_TOP_K_FIELD,
    top_k_global: int = DEFAULT_TOP_K_GLOBAL,
) -> RetrievalResult:
    """
    Tiered retrieval:
    1. scheme_id + field(s) -> metadata-filtered top_k=1 per field
    2. scheme_id only -> vector search within scheme
    3. field(s) only -> vector search within field(s)
    4. neither -> global vector search with score threshold
    """
    registry = load_scheme_registry()
    resolver = SchemeResolver(registry)
    scheme = resolver.resolve(query)
    scheme_id = scheme.id if scheme else None
    fields = resolve_fields(query)

    chunks: list[SearchResult] = []
    mode = RetrievalMode.GLOBAL_FALLBACK

    if scheme_id and fields:
        chunks = _retrieve_exact(
            query,
            scheme_id=scheme_id,
            fields=fields,
            backend=backend,
            index_path=index_path,
            min_score=min_score,
        )
        mode = RetrievalMode.EXACT
    elif scheme_id:
        chunks = _retrieve_scheme_filtered(
            query,
            scheme_id=scheme_id,
            backend=backend,
            index_path=index_path,
            min_score=min_score,
            top_k=top_k_scheme,
        )
        mode = RetrievalMode.SCHEME_FILTERED
    elif fields:
        chunks = _retrieve_field_filtered(
            query,
            fields=fields,
            backend=backend,
            index_path=index_path,
            min_score=min_score,
            top_k=top_k_field,
        )
        mode = RetrievalMode.FIELD_FILTERED
    else:
        chunks = _retrieve_global(
            query,
            backend=backend,
            index_path=index_path,
            min_score=min_score,
            top_k=top_k_global,
        )
        mode = RetrievalMode.GLOBAL_FALLBACK

    if scheme_id and chunks:
        chunks = [item for item in chunks if item.scheme_id == scheme_id]

    logger.info(
        "Retrieved %s chunk(s) mode=%s scheme=%s fields=%s",
        len(chunks),
        mode.value,
        scheme_id,
        fields,
    )

    return RetrievalResult(
        query=query,
        scheme_id=scheme_id,
        fields=fields,
        chunks=tuple(chunks),
        mode=mode,
    )

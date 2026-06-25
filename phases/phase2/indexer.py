"""Phase 2.7 — Persist embedded chunks in a local Chroma vector store."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phases import paths
from phases.phase1.config import ALLOWED_URLS
from phases.phase1.validator import ValidationError
from phases.phase2.embedder import (
    EmbeddingBackend,
    get_embedding_backend,
    get_embedding_model,
    load_embedded_chunks_json,
)
from phases.phase2.models import EmbeddedChunk, IndexStats, SearchResult

logger = logging.getLogger(__name__)


def _chunk_to_metadata(item: EmbeddedChunk) -> dict[str, str | int | float | bool]:
    chunk = item.chunk
    metadata: dict[str, str | int | float | bool] = {
        "source_url": chunk.source_url,
        "source": chunk.source,
        "scheme_id": chunk.scheme_id,
        "scheme_name": chunk.scheme_name,
        "scheme_category": chunk.scheme_category,
        "amc": chunk.amc,
        "field": chunk.field,
        "display_value": chunk.display_value or "",
        "last_updated": chunk.last_updated,
        "content_hash": chunk.content_hash or "",
        "embedding_model": item.embedding_model,
        "embedding_dim": item.embedding_dim,
    }
    if chunk.unit is not None:
        metadata["unit"] = chunk.unit
    if chunk.value is not None:
        metadata["value"] = str(chunk.value)
    return metadata


def _get_chroma_collection(
    *,
    collection_name: str = paths.DEFAULT_COLLECTION_NAME,
    index_path: Path | None = None,
):
    try:
        import chromadb
    except ImportError as exc:
        raise ImportError("chromadb package is required for vector indexing") from exc

    store_path = index_path or paths.VECTOR_STORE_DIR
    store_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(store_path))
    return client.get_or_create_collection(name=collection_name)


def load_index_registry(registry_path: Path | None = None) -> dict[str, Any] | None:
    """Load index registry written by Phase 2.7 / 2.8."""
    path = registry_path or paths.INDEX_REGISTRY_FILE
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def delete_scheme_from_index(
    scheme_id: str,
    *,
    collection_name: str = paths.DEFAULT_COLLECTION_NAME,
    index_path: Path | None = None,
) -> int:
    """Remove all vector chunks for a scheme from the Chroma collection."""
    stats = get_index_stats(collection_name=collection_name, index_path=index_path, min_chunk_count=0)
    if stats.chunk_count == 0:
        return 0

    collection = _get_chroma_collection(collection_name=collection_name, index_path=index_path)
    before = collection.count()
    collection.delete(where={"scheme_id": scheme_id})
    deleted = before - collection.count()
    logger.info("Deleted %s chunks for scheme '%s' from index", deleted, scheme_id)
    return deleted


def upsert_index(
    embedded_chunks: list[EmbeddedChunk],
    *,
    collection_name: str = paths.DEFAULT_COLLECTION_NAME,
    index_path: Path | None = None,
    min_chunk_count: int = paths.MIN_INDEX_CHUNK_COUNT,
    scheme_content_hashes: dict[str, str] | None = None,
) -> IndexStats:
    """Upsert embedded chunks into the local Chroma vector store."""
    if not embedded_chunks:
        raise ValidationError("Cannot upsert an empty embedding set")

    for item in embedded_chunks:
        if item.chunk.source_url not in ALLOWED_URLS:
            raise ValidationError(f"Chunk source_url not in ALLOWED_URLS: {item.chunk.source_url}")

    collection = _get_chroma_collection(collection_name=collection_name, index_path=index_path)

    ids = [item.chunk.chunk_id for item in embedded_chunks]
    embeddings = [list(item.embedding) for item in embedded_chunks]
    documents = [item.chunk.text for item in embedded_chunks]
    metadatas = [_chunk_to_metadata(item) for item in embedded_chunks]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    stats = get_index_stats(collection_name=collection_name, index_path=index_path)
    if stats.chunk_count < min_chunk_count:
        raise ValidationError(
            f"Index chunk count {stats.chunk_count} is below minimum {min_chunk_count}"
        )

    _write_index_registry(
        embedded_chunks,
        stats,
        scheme_content_hashes=scheme_content_hashes,
    )
    logger.info(
        "Upserted %s chunks into collection '%s' at %s",
        stats.chunk_count,
        stats.collection_name,
        stats.index_path,
    )
    return stats


def get_index_stats(
    *,
    collection_name: str = paths.DEFAULT_COLLECTION_NAME,
    index_path: Path | None = None,
    min_chunk_count: int = paths.MIN_INDEX_CHUNK_COUNT,
) -> IndexStats:
    """Return vector store statistics for Phase 3 preflight."""
    store_path = index_path or paths.VECTOR_STORE_DIR
    if not store_path.exists():
        return IndexStats(
            chunk_count=0,
            embedding_model=get_embedding_model(),
            embedding_dim=0,
            collection_name=collection_name,
            index_path=str(store_path),
            ready=False,
        )

    collection = _get_chroma_collection(collection_name=collection_name, index_path=index_path)
    count = collection.count()
    sample_meta: dict[str, Any] = {}
    if count > 0:
        sample = collection.get(limit=1, include=["metadatas"])
        if sample.get("metadatas"):
            sample_meta = sample["metadatas"][0]

    return IndexStats(
        chunk_count=count,
        embedding_model=str(sample_meta.get("embedding_model", get_embedding_model())),
        embedding_dim=int(sample_meta.get("embedding_dim", 0) or 0),
        collection_name=collection_name,
        index_path=str(store_path),
        ready=count >= min_chunk_count,
    )


def similarity_search(
    query: str,
    *,
    top_k: int = 5,
    scheme_id: str | None = None,
    field: str | None = None,
    collection_name: str = paths.DEFAULT_COLLECTION_NAME,
    index_path: Path | None = None,
    backend: EmbeddingBackend | None = None,
) -> list[SearchResult]:
    """Query the vector index with optional scheme_id / field metadata filters."""
    stats = get_index_stats(collection_name=collection_name, index_path=index_path, min_chunk_count=0)
    if stats.chunk_count == 0:
        return []

    embedder = backend or get_embedding_backend()
    query_vector = embedder.embed_texts([query], model=stats.embedding_model)[0]

    where = _build_where_filter(scheme_id=scheme_id, field=field)
    collection = _get_chroma_collection(collection_name=collection_name, index_path=index_path)

    kwargs: dict[str, Any] = {
        "query_embeddings": [query_vector],
        "n_results": min(top_k, stats.chunk_count),
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    response = collection.query(**kwargs)
    return _parse_search_results(response)


def fetch_chunks_by_metadata(
    *,
    scheme_id: str | None = None,
    field: str | None = None,
    collection_name: str = paths.DEFAULT_COLLECTION_NAME,
    index_path: Path | None = None,
) -> list[SearchResult]:
    """Direct metadata lookup — used for exact tier retrieval (no embedding score)."""
    stats = get_index_stats(collection_name=collection_name, index_path=index_path, min_chunk_count=0)
    if stats.chunk_count == 0:
        return []

    where = _build_where_filter(scheme_id=scheme_id, field=field)
    if where is None:
        return []

    collection = _get_chroma_collection(collection_name=collection_name, index_path=index_path)
    response = collection.get(where=where, include=["documents", "metadatas"])
    ids = response.get("ids", [])
    documents = response.get("documents", [])
    metadatas = response.get("metadatas", [])

    results: list[SearchResult] = []
    for chunk_id, text, metadata in zip(ids, documents, metadatas, strict=True):
        results.append(
            SearchResult(
                chunk_id=chunk_id,
                text=text or "",
                source_url=str(metadata.get("source_url", "")),
                scheme_id=str(metadata.get("scheme_id", "")),
                field=str(metadata.get("field", "")),
                score=1.0,
                metadata=metadata,
            )
        )
    return results


def _build_where_filter(
    *,
    scheme_id: str | None,
    field: str | None,
) -> dict[str, Any] | None:
    clauses: list[dict[str, Any]] = []
    if scheme_id:
        clauses.append({"scheme_id": scheme_id})
    if field:
        clauses.append({"field": field})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _parse_search_results(response: dict[str, Any]) -> list[SearchResult]:
    ids = response.get("ids", [[]])[0]
    documents = response.get("documents", [[]])[0]
    metadatas = response.get("metadatas", [[]])[0]
    distances = response.get("distances", [[]])[0]

    results: list[SearchResult] = []
    for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances, strict=True):
        # Chroma returns lower distance for closer vectors.
        score = 1.0 / (1.0 + float(distance))
        results.append(
            SearchResult(
                chunk_id=chunk_id,
                text=text,
                source_url=str(metadata.get("source_url", "")),
                scheme_id=str(metadata.get("scheme_id", "")),
                field=str(metadata.get("field", "")),
                score=score,
                metadata=metadata,
            )
        )
    return results


def _write_index_registry(
    embedded_chunks: list[EmbeddedChunk],
    stats: IndexStats,
    *,
    scheme_content_hashes: dict[str, str] | None = None,
) -> None:
    """Record index build metadata for Phase 2.8 re-index tracking."""
    paths.METADATA_DIR.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, str] = dict(scheme_content_hashes or {})
    if not hashes:
        for item in embedded_chunks:
            if item.chunk.content_hash:
                hashes[item.chunk.scheme_id] = item.chunk.content_hash

    payload = {
        "last_indexed_at": datetime.now(timezone.utc).isoformat(),
        "chunk_count": stats.chunk_count,
        "embedding_model": stats.embedding_model,
        "embedding_dim": stats.embedding_dim,
        "collection_name": stats.collection_name,
        "index_path": stats.index_path,
        "scheme_content_hashes": hashes,
    }
    paths.INDEX_REGISTRY_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def upsert_index_from_corpus(
    embedded_path: Path | None = None,
    *,
    index_path: Path | None = None,
    collection_name: str = paths.DEFAULT_COLLECTION_NAME,
) -> IndexStats:
    """Load embedded_chunks.json and upsert into the vector store."""
    embedded = load_embedded_chunks_json(embedded_path)
    return upsert_index(embedded, collection_name=collection_name, index_path=index_path)

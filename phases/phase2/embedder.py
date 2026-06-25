"""Phase 2.6 — Generate embedding vectors for chunk texts."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phases import paths
from phases.phase1.validator import ValidationError
from phases.phase2.chunker import load_chunks_json, validate_chunks
from phases.phase2.models import ChunkDocument, EmbeddedChunk

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_BATCH_SIZE = 32
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BASE_SECONDS = 1.0

OPENAI_EMBEDDING_DIM = 1536


class EmbeddingBackend(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str], *, model: str) -> list[list[float]]:
        raise NotImplementedError


class OpenAIEmbeddingBackend(EmbeddingBackend):
    """OpenAI embeddings API with retry/backoff on rate limits."""

    def __init__(self, api_key: str | None = None, max_retries: int = DEFAULT_MAX_RETRIES) -> None:
        self._api_key = api_key
        self._max_retries = max_retries
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ImportError("openai package is required for OpenAIEmbeddingBackend") from exc
            api_key = self._api_key or os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("EMBEDDING_API_KEY or OPENAI_API_KEY must be set for OpenAI embeddings")
            self._client = OpenAI(api_key=api_key)
        return self._client

    def embed_texts(self, texts: list[str], *, model: str) -> list[list[float]]:
        if not texts:
            return []

        client = self._get_client()
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = client.embeddings.create(input=texts, model=model)
                return [list(item.embedding) for item in response.data]
            except Exception as exc:
                last_error = exc
                retryable = _is_retryable_embedding_error(exc)
                if not retryable or attempt >= self._max_retries:
                    logger.error("Embedding request failed after %s attempts: %s", attempt + 1, exc)
                    raise
                sleep_seconds = DEFAULT_RETRY_BASE_SECONDS * (2**attempt)
                logger.warning(
                    "Embedding rate limit or transient error (attempt %s/%s); retrying in %ss: %s",
                    attempt + 1,
                    self._max_retries + 1,
                    sleep_seconds,
                    exc,
                )
                time.sleep(sleep_seconds)

        raise RuntimeError("Embedding failed") from last_error


class DeterministicEmbeddingBackend(EmbeddingBackend):
    """Deterministic local vectors for tests and offline development."""

    def __init__(self, dim: int = OPENAI_EMBEDDING_DIM) -> None:
        self._dim = dim

    def embed_texts(self, texts: list[str], *, model: str) -> list[list[float]]:
        return [_hash_to_vector(text, self._dim) for text in texts]


def _is_retryable_embedding_error(exc: Exception) -> bool:
    name = type(exc).__name__
    if name in {"RateLimitError", "APIConnectionError", "InternalServerError"}:
        return True
    message = str(exc).lower()
    return "rate limit" in message or "timeout" in message or "503" in message


def _hash_to_vector(text: str, dim: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < dim:
        for byte in digest:
            values.append((byte / 127.5) - 1.0)
            if len(values) >= dim:
                break
        digest = hashlib.sha256(digest).digest()
    return values[:dim]


def get_embedding_model() -> str:
    return os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)


def get_embedding_backend() -> EmbeddingBackend:
    provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()
    if provider == "deterministic":
        return DeterministicEmbeddingBackend()
    has_openai_key = bool(os.getenv("EMBEDDING_API_KEY") or os.getenv("OPENAI_API_KEY"))
    if provider == "openai" and not has_openai_key:
        logger.warning("EMBEDDING_PROVIDER=openai but no API key; using deterministic embeddings")
        return DeterministicEmbeddingBackend()
    return OpenAIEmbeddingBackend()


def embed_chunks(
    chunks: list[ChunkDocument],
    *,
    model: str | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    backend: EmbeddingBackend | None = None,
) -> list[EmbeddedChunk]:
    """Batch-embed chunk text fields. Fails if any chunk cannot be embedded."""
    if not chunks:
        return []

    model_name = model or get_embedding_model()
    embedder = backend or get_embedding_backend()
    embedded: list[EmbeddedChunk] = []

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        texts = [chunk.text for chunk in batch]
        try:
            vectors = embedder.embed_texts(texts, model=model_name)
        except Exception as exc:
            logger.error(
                "Failed to embed batch starting at index %s (chunks %s-%s): %s",
                start,
                start,
                start + len(batch) - 1,
                exc,
            )
            raise

        if len(vectors) != len(batch):
            raise ValidationError(
                f"Embedding count mismatch: expected {len(batch)} vectors, got {len(vectors)}"
            )

        for chunk, vector in zip(batch, vectors, strict=True):
            if not vector:
                raise ValidationError(f"Empty embedding for chunk {chunk.chunk_id} ({chunk.field})")
            embedded.append(
                EmbeddedChunk(
                    chunk=chunk,
                    embedding=tuple(float(v) for v in vector),
                    embedding_model=model_name,
                    embedding_dim=len(vector),
                )
            )

    validate_embeddings(embedded)
    return embedded


def validate_embeddings(embedded: list[EmbeddedChunk]) -> None:
    """Ensure every chunk has a vector of consistent dimension."""
    if not embedded:
        return

    expected_dim = embedded[0].embedding_dim
    seen_ids: set[str] = set()

    for item in embedded:
        if item.chunk.chunk_id in seen_ids:
            raise ValidationError(f"Duplicate embedded chunk_id: {item.chunk.chunk_id}")
        seen_ids.add(item.chunk.chunk_id)

        if item.embedding_dim != expected_dim:
            raise ValidationError(
                f"Inconsistent embedding dimension for {item.chunk.chunk_id}: "
                f"expected {expected_dim}, got {item.embedding_dim}"
            )
        if len(item.embedding) != expected_dim:
            raise ValidationError(f"Embedding length mismatch for {item.chunk.chunk_id}")
        if not item.embedding_model:
            raise ValidationError(f"Missing embedding_model for {item.chunk.chunk_id}")


def save_embedded_chunks_json(
    embedded: list[EmbeddedChunk],
    output_path: Path | None = None,
) -> Path:
    """Persist embedded chunks to corpus/processed/embedded_chunks.json."""
    path = output_path or paths.EMBEDDED_CHUNKS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "embedding_model": embedded[0].embedding_model if embedded else get_embedding_model(),
        "embedding_dim": embedded[0].embedding_dim if embedded else None,
        "count": len(embedded),
        "chunks": [item.to_dict() for item in embedded],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_embedded_chunks_json(embedded_path: Path | None = None) -> list[EmbeddedChunk]:
    """Read embedded chunks from corpus/processed/embedded_chunks.json."""
    path = embedded_path or paths.EMBEDDED_CHUNKS_FILE
    if not path.exists():
        raise FileNotFoundError(f"Embedded chunks file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return [EmbeddedChunk.from_dict(dict(item)) for item in data.get("chunks", [])]


def embed_chunks_from_corpus(
    chunks_path: Path | None = None,
    *,
    backend: EmbeddingBackend | None = None,
) -> list[EmbeddedChunk]:
    """Load chunks.json, validate, embed, and validate embeddings."""
    chunks = load_chunks_json(chunks_path)
    validate_chunks(chunks)
    embedded = embed_chunks(chunks, backend=backend)
    return embedded

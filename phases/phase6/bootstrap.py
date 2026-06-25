"""Phase 6 startup — secrets, env, and vector index readiness."""

from __future__ import annotations

import logging
import os
from typing import Any

from phases import paths
from phases.env import load_env
from phases.phase2.indexer import get_index_stats, upsert_index_from_corpus
from phases.phase2.models import IndexStats

logger = logging.getLogger(__name__)

SECRET_KEYS: tuple[str, ...] = (
    "GROQ_API_KEY",
    "GENERATOR_API_KEY",
    "OPENAI_API_KEY",
    "EMBEDDING_API_KEY",
    "GENERATOR_PROVIDER",
    "EMBEDDING_PROVIDER",
    "GENERATOR_MODEL",
    "EMBEDDING_MODEL",
    "API_CORS_ORIGINS",
)


def _flatten_secrets(raw: Any, prefix: str = "") -> dict[str, str]:
    """Flatten Streamlit/nested secret mappings into env key -> value."""
    flat: dict[str, str] = {}
    if raw is None:
        return flat
    if isinstance(raw, dict):
        for key, value in raw.items():
            full_key = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, dict):
                flat.update(_flatten_secrets(value, full_key))
            elif value is not None and str(value).strip():
                flat[str(key)] = str(value)
        return flat
    return flat


def load_streamlit_secrets() -> dict[str, str]:
    """Read secrets from Streamlit when available (Cloud or local secrets.toml)."""
    try:
        import streamlit as st

        return _flatten_secrets(dict(st.secrets))
    except Exception:
        return {}


def apply_secrets(extra: dict[str, str] | None = None) -> None:
    """Load .env, then Streamlit secrets, then optional overrides into os.environ."""
    load_env()
    merged = load_streamlit_secrets()
    if extra:
        merged.update({key: value for key, value in extra.items() if value and str(value).strip()})
    for key in SECRET_KEYS:
        value = merged.get(key)
        if value and str(value).strip():
            os.environ[key] = str(value)


def ensure_index_ready(*, force_rebuild: bool = False) -> IndexStats:
    """Ensure vector index meets minimum chunk count; rebuild from corpus if needed."""
    stats = get_index_stats(min_chunk_count=0)
    if (
        not force_rebuild
        and stats.ready
        and stats.chunk_count >= paths.MIN_INDEX_CHUNK_COUNT
    ):
        return stats

    if paths.EMBEDDED_CHUNKS_FILE.exists():
        logger.info("Building vector index from embedded_chunks.json")
        stats = upsert_index_from_corpus()
    else:
        logger.info("embedded_chunks.json missing; running Phase 2 pipeline")
        from phases.phase2.run import run

        run()
        stats = get_index_stats(min_chunk_count=0)

    if not stats.ready or stats.chunk_count < paths.MIN_INDEX_CHUNK_COUNT:
        raise RuntimeError(
            f"Vector index not ready after bootstrap (chunks={stats.chunk_count}, "
            f"required>={paths.MIN_INDEX_CHUNK_COUNT})"
        )
    return stats


def init_backend(*, force_rebuild: bool = False) -> IndexStats:
    """Apply secrets and ensure index readiness (single entry for apps)."""
    apply_secrets()
    return ensure_index_ready(force_rebuild=force_rebuild)

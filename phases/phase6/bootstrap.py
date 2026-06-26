"""Phase 6 startup — env and vector index readiness for Render."""

from __future__ import annotations

import logging
import os

from phases import paths
from phases.env import load_env
from phases.phase2.indexer import get_index_stats, upsert_index_from_corpus
from phases.phase2.models import IndexStats

logger = logging.getLogger(__name__)


def apply_secrets(extra: dict[str, str] | None = None) -> None:
    """Load .env and optional overrides into os.environ."""
    load_env()
    if extra:
        for key, value in extra.items():
            if value and str(value).strip():
                os.environ[key] = str(value)


def configure_runtime_paths() -> None:
    """Use writable /tmp for ephemeral hosts (serverless). Render uses project disk."""
    if not os.getenv("VERCEL"):
        return
    from pathlib import Path

    tmp_root = Path("/tmp/ragbot")
    tmp_store = tmp_root / "vector_store"
    tmp_store.mkdir(parents=True, exist_ok=True)
    paths.DATA_DIR = tmp_root
    paths.VECTOR_STORE_DIR = tmp_store
    logger.info("Ephemeral runtime: vector store path=%s", tmp_store)


def ensure_embedded_corpus() -> None:
    """Ensure embedded_chunks.json exists; embed from chunks.json when possible."""
    if paths.EMBEDDED_CHUNKS_FILE.exists():
        return

    if not paths.CHUNKS_FILE.exists():
        raise FileNotFoundError(
            f"Missing {paths.EMBEDDED_CHUNKS_FILE} and {paths.CHUNKS_FILE}. "
            "Commit corpus artifacts or run the Phase 2 pipeline."
        )

    logger.info("embedded_chunks.json missing — embedding from chunks.json")
    from phases.phase2.embedder import embed_chunks_from_corpus, save_embedded_chunks_json

    embedded = embed_chunks_from_corpus()
    save_embedded_chunks_json(embedded)


def ensure_index_ready(*, force_rebuild: bool = False) -> IndexStats:
    """Ensure vector index meets minimum chunk count; rebuild from corpus if needed."""
    ensure_embedded_corpus()
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
    """Apply secrets and ensure index readiness (Render entry)."""
    configure_runtime_paths()
    apply_secrets()
    return ensure_index_ready(force_rebuild=force_rebuild)

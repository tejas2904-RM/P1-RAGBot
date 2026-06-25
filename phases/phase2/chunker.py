"""Phase 2.5 — Package fact records into index-ready chunk documents."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phases import paths
from phases.phase1.config import ALLOWED_URLS
from phases.phase1.validator import ValidationError
from phases.phase2.fact_builder import validate_facts
from phases.phase2.groww_selectors import is_blocked_field
from phases.phase2.models import ChunkDocument, FactRecord

_REQUIRED_CHUNK_FIELDS = (
    "chunk_id",
    "text",
    "display_value",
    "field",
    "scheme_id",
    "last_updated",
    "content_hash",
    "source_url",
)


def load_facts_json(facts_path: Path | None = None) -> list[FactRecord]:
    """Read fact records from corpus/processed/facts.json."""
    path = facts_path or paths.FACTS_FILE
    if not path.exists():
        raise FileNotFoundError(f"Facts file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return [FactRecord.from_dict(item) for item in data.get("facts", [])]


def build_chunks(facts: list[FactRecord]) -> list[ChunkDocument]:
    """Convert fact records to chunk documents (1:1) with UUID chunk_ids."""
    seen: set[tuple[str, str]] = set()
    chunks: list[ChunkDocument] = []

    for fact in facts:
        key = (fact.scheme_id, fact.field)
        if key in seen:
            raise ValidationError(f"Duplicate fact for scheme/field: {key}")
        seen.add(key)
        chunk_id = str(uuid.uuid4())
        chunks.append(ChunkDocument.from_fact(fact, chunk_id))

    return chunks


def validate_chunks(chunks: list[ChunkDocument]) -> None:
    """Ensure all chunks meet Phase 2.5 constraints."""
    allowed = set(ALLOWED_URLS)
    seen_keys: set[tuple[str, str]] = set()
    seen_ids: set[str] = set()

    for chunk in chunks:
        if chunk.source_url not in allowed:
            raise ValidationError(f"Chunk source_url not in ALLOWED_URLS: {chunk.source_url}")
        if is_blocked_field(chunk.field):
            raise ValidationError(f"Blocked field present in chunks: {chunk.field}")
        if chunk.field == "lock_in_period" and chunk.scheme_id != "hdfc-elss":
            raise ValidationError(
                f"lock_in_period chunk must only exist for hdfc-elss, found: {chunk.scheme_id}"
            )

        for required in _REQUIRED_CHUNK_FIELDS:
            value = getattr(chunk, required, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValidationError(f"Chunk missing required field {required}: {chunk.scheme_id}/{chunk.field}")

        if not chunk.text.strip():
            raise ValidationError(f"Chunk text must not be empty: {chunk.scheme_id}/{chunk.field}")

        if chunk.chunk_id in seen_ids:
            raise ValidationError(f"Duplicate chunk_id: {chunk.chunk_id}")
        seen_ids.add(chunk.chunk_id)

        key = (chunk.scheme_id, chunk.field)
        if key in seen_keys:
            raise ValidationError(f"Duplicate chunk for scheme/field: {key}")
        seen_keys.add(key)


def save_chunks_json(
    chunks: list[ChunkDocument],
    output_path: Path | None = None,
) -> Path:
    """Persist chunk documents to corpus/processed/chunks.json."""
    path = output_path or paths.CHUNKS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(chunks),
        "chunks": [chunk.to_dict() for chunk in chunks],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def build_chunks_from_corpus(facts_path: Path | None = None) -> list[ChunkDocument]:
    """Load facts.json, validate, chunk, and validate chunks."""
    facts = load_facts_json(facts_path)
    validate_facts(facts)
    chunks = build_chunks(facts)
    validate_chunks(chunks)
    return chunks


def load_chunks_json(chunks_path: Path | None = None) -> list[ChunkDocument]:
    """Read chunk documents from corpus/processed/chunks.json."""
    path = chunks_path or paths.CHUNKS_FILE
    if not path.exists():
        raise FileNotFoundError(f"Chunks file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return [ChunkDocument.from_dict(item) for item in data.get("chunks", [])]

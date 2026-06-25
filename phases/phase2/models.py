"""Shared data models for Phase 2 ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class ExtractionStatus(str, Enum):
    FOUND = "found"
    MISSING = "missing"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class ExtractionSource(str, Enum):
    JSON = "json"
    DOM = "dom"


@dataclass(frozen=True)
class FieldExtraction:
    field_id: str
    status: ExtractionStatus
    raw_value: str | None = None
    source: ExtractionSource | None = None


@dataclass
class ParsedScheme:
    scheme_id: str
    scheme_category: str
    fields: dict[str, FieldExtraction] = field(default_factory=dict)

    def get_raw(self, field_id: str) -> str | None:
        extraction = self.fields.get(field_id)
        if extraction is None or extraction.status != ExtractionStatus.FOUND:
            return None
        return extraction.raw_value


class NormalizationStatus(str, Enum):
    OK = "ok"
    NONE = "none"
    ZERO = "zero"
    NOT_APPLICABLE = "not_applicable"
    UNPARSEABLE = "unparseable"


@dataclass(frozen=True)
class NormalizedField:
    field_id: str
    status: NormalizationStatus
    value: Any = None
    unit: str | None = None
    display_value: str | None = None
    raw_value: str | None = None


@dataclass(frozen=True)
class FactRecord:
    scheme_id: str
    scheme_name: str
    scheme_category: str
    amc: str
    source_url: str
    source: str
    field: str
    value: Any
    unit: str | None
    display_value: str | None
    text: str
    last_updated: str
    content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "scheme_name": self.scheme_name,
            "scheme_category": self.scheme_category,
            "amc": self.amc,
            "source_url": self.source_url,
            "source": self.source,
            "field": self.field,
            "value": self.value,
            "unit": self.unit,
            "display_value": self.display_value,
            "text": self.text,
            "last_updated": self.last_updated,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FactRecord:
        return cls(
            scheme_id=data["scheme_id"],
            scheme_name=data["scheme_name"],
            scheme_category=data["scheme_category"],
            amc=data["amc"],
            source_url=data["source_url"],
            source=data["source"],
            field=data["field"],
            value=data["value"],
            unit=data.get("unit"),
            display_value=data.get("display_value"),
            text=data["text"],
            last_updated=data["last_updated"],
            content_hash=data.get("content_hash"),
        )


@dataclass(frozen=True)
class ChunkDocument:
    chunk_id: str
    text: str
    source_url: str
    source: str
    scheme_id: str
    scheme_name: str
    scheme_category: str
    amc: str
    field: str
    value: Any
    unit: str | None
    display_value: str | None
    last_updated: str
    content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_url": self.source_url,
            "source": self.source,
            "scheme_id": self.scheme_id,
            "scheme_name": self.scheme_name,
            "scheme_category": self.scheme_category,
            "amc": self.amc,
            "field": self.field,
            "value": self.value,
            "unit": self.unit,
            "display_value": self.display_value,
            "last_updated": self.last_updated,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_fact(cls, fact: FactRecord, chunk_id: str) -> ChunkDocument:
        return cls(
            chunk_id=chunk_id,
            text=fact.text,
            source_url=fact.source_url,
            source=fact.source,
            scheme_id=fact.scheme_id,
            scheme_name=fact.scheme_name,
            scheme_category=fact.scheme_category,
            amc=fact.amc,
            field=fact.field,
            value=fact.value,
            unit=fact.unit,
            display_value=fact.display_value,
            last_updated=fact.last_updated,
            content_hash=fact.content_hash,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChunkDocument:
        return cls(
            chunk_id=data["chunk_id"],
            text=data["text"],
            source_url=data["source_url"],
            source=data["source"],
            scheme_id=data["scheme_id"],
            scheme_name=data["scheme_name"],
            scheme_category=data["scheme_category"],
            amc=data["amc"],
            field=data["field"],
            value=data["value"],
            unit=data.get("unit"),
            display_value=data.get("display_value"),
            last_updated=data["last_updated"],
            content_hash=data.get("content_hash"),
        )


@dataclass(frozen=True)
class EmbeddedChunk:
    chunk: ChunkDocument
    embedding: tuple[float, ...]
    embedding_model: str
    embedding_dim: int

    def to_dict(self) -> dict[str, Any]:
        payload = self.chunk.to_dict()
        payload["embedding"] = list(self.embedding)
        payload["embedding_model"] = self.embedding_model
        payload["embedding_dim"] = self.embedding_dim
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmbeddedChunk:
        item = dict(data)
        embedding = item.pop("embedding")
        embedding_model = item.pop("embedding_model")
        embedding_dim = int(item.pop("embedding_dim"))
        chunk = ChunkDocument.from_dict(item)
        vector = tuple(float(v) for v in embedding)
        return cls(
            chunk=chunk,
            embedding=vector,
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
        )


@dataclass(frozen=True)
class IndexStats:
    chunk_count: int
    embedding_model: str
    embedding_dim: int
    collection_name: str
    index_path: str
    ready: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_count": self.chunk_count,
            "embedding_model": self.embedding_model,
            "embedding_dim": self.embedding_dim,
            "collection_name": self.collection_name,
            "index_path": self.index_path,
            "ready": self.ready,
        }


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    text: str
    source_url: str
    scheme_id: str
    field: str
    score: float
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ReindexReport:
    updated: bool
    changed_schemes: tuple[str, ...]
    skipped_schemes: tuple[str, ...]
    facts_count: int
    chunks_count: int
    index_chunk_count: int
    index_ready: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "updated": self.updated,
            "changed_schemes": list(self.changed_schemes),
            "skipped_schemes": list(self.skipped_schemes),
            "facts_count": self.facts_count,
            "chunks_count": self.chunks_count,
            "index_chunk_count": self.index_chunk_count,
            "index_ready": self.index_ready,
        }

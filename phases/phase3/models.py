"""Data models for Phase 3 RAG pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from phases.phase2.models import SearchResult


class RetrievalMode(str, Enum):
    EXACT = "exact"
    SCHEME_FILTERED = "scheme_filtered"
    FIELD_FILTERED = "field_filtered"
    GLOBAL_FALLBACK = "global_fallback"


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    scheme_id: str | None
    fields: tuple[str, ...]
    chunks: tuple[SearchResult, ...]
    mode: RetrievalMode

    @property
    def found(self) -> bool:
        return bool(self.chunks)


@dataclass(frozen=True)
class RAGResponse:
    query: str
    answer: str
    source_url: str | None
    last_updated: str | None
    scheme_id: str | None
    fields: tuple[str, ...]
    retrieval_mode: RetrievalMode | None
    used_llm: bool
    success: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "source_url": self.source_url,
            "last_updated": self.last_updated,
            "scheme_id": self.scheme_id,
            "fields": list(self.fields),
            "retrieval_mode": self.retrieval_mode.value if self.retrieval_mode else None,
            "used_llm": self.used_llm,
            "success": self.success,
        }

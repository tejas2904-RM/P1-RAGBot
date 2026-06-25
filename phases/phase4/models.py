"""Data models for Phase 4 classification and responses."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from phases.phase3.models import RetrievalMode


class QueryCategory(str, Enum):
    FACTUAL = "factual"
    ADVISORY = "advisory"
    COMPARATIVE = "comparative"
    PERFORMANCE = "performance"
    PII = "pii"
    OUT_OF_SCOPE = "out_of_scope"
    EMPTY = "empty"
    GREETING = "greeting"


@dataclass(frozen=True)
class ClassificationResult:
    category: QueryCategory
    reason: str

    def is_refusal(self) -> bool:
        return self.category != QueryCategory.FACTUAL


@dataclass(frozen=True)
class AssistantResponse:
    query: str
    answer: str
    category: QueryCategory
    refused: bool
    source_url: str | None = None
    last_updated: str | None = None
    scheme_id: str | None = None
    fields: tuple[str, ...] = ()
    retrieval_mode: RetrievalMode | None = None
    used_llm: bool = False
    success: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "category": self.category.value,
            "refused": self.refused,
            "source_url": self.source_url,
            "last_updated": self.last_updated,
            "scheme_id": self.scheme_id,
            "fields": list(self.fields),
            "retrieval_mode": self.retrieval_mode.value if self.retrieval_mode else None,
            "used_llm": self.used_llm,
            "success": self.success,
        }

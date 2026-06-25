"""Data models for Phase 1 corpus artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Scheme:
    id: str
    scheme_name: str
    category: str
    plan: str
    option: str
    url: str
    aliases: list[str] = field(default_factory=list)

    def to_registry_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "scheme_name": self.scheme_name,
            "category": self.category,
            "plan": self.plan,
            "option": self.option,
            "url": self.url,
            "aliases": self.aliases,
        }


@dataclass(frozen=True)
class UrlsConfig:
    amc: str
    source: str
    schemes: list[Scheme]


@dataclass
class SourceRecord:
    scheme_id: str
    url: str
    status: str
    last_fetched: str | None = None
    content_hash: str | None = None
    http_status: int | None = None
    error: str | None = None
    raw_snapshot: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scheme_id": self.scheme_id,
            "url": self.url,
            "status": self.status,
            "last_fetched": self.last_fetched,
            "content_hash": self.content_hash,
            "http_status": self.http_status,
            "error": self.error,
            "raw_snapshot": self.raw_snapshot,
        }

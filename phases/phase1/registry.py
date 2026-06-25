"""Load and persist corpus registry files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from phases import paths
from phases.phase1.config import AMC_NAME, SCHEME_ALIASES, SOURCE_NAME
from phases.phase1.models import Scheme, SourceRecord, UrlsConfig


def load_urls_config(urls_path: Path | None = None) -> UrlsConfig:
    path = urls_path or paths.URLS_FILE
    data = json.loads(path.read_text(encoding="utf-8"))
    schemes = [
        Scheme(
            id=item["id"],
            scheme_name=item["scheme_name"],
            category=item["category"],
            plan=item["plan"],
            option=item["option"],
            url=item["url"],
            aliases=SCHEME_ALIASES.get(item["id"], []),
        )
        for item in data["schemes"]
    ]
    return UrlsConfig(amc=data.get("amc", AMC_NAME), source=data.get("source", SOURCE_NAME), schemes=schemes)


def save_scheme_registry(config: UrlsConfig, output_path: Path | None = None) -> Path:
    path = output_path or paths.SCHEME_REGISTRY_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "amc": config.amc,
        "source": config.source,
        "schemes": [scheme.to_registry_dict() for scheme in config.schemes],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_scheme_registry(registry_path: Path | None = None) -> UrlsConfig:
    path = registry_path or paths.SCHEME_REGISTRY_FILE
    data = json.loads(path.read_text(encoding="utf-8"))
    schemes = [
        Scheme(
            id=item["id"],
            scheme_name=item["scheme_name"],
            category=item["category"],
            plan=item["plan"],
            option=item["option"],
            url=item["url"],
            aliases=item.get("aliases", SCHEME_ALIASES.get(item["id"], [])),
        )
        for item in data["schemes"]
    ]
    return UrlsConfig(amc=data.get("amc", AMC_NAME), source=data.get("source", SOURCE_NAME), schemes=schemes)


def load_source_registry(registry_path: Path | None = None) -> list[SourceRecord]:
    path = registry_path or paths.SOURCE_REGISTRY_FILE
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        SourceRecord(
            scheme_id=item["scheme_id"],
            url=item["url"],
            status=item["status"],
            last_fetched=item.get("last_fetched"),
            content_hash=item.get("content_hash"),
            http_status=item.get("http_status"),
            error=item.get("error"),
            raw_snapshot=item.get("raw_snapshot"),
        )
        for item in data.get("sources", [])
    ]


def save_source_registry(records: list[SourceRecord], output_path: Path | None = None) -> Path:
    path = output_path or paths.SOURCE_REGISTRY_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"sources": [record.to_dict() for record in records]}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path

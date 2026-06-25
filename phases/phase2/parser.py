"""Phase 2.2 — Parse Groww scheme HTML into raw field extractions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from phases import paths
from phases.phase1.config import RAW_SNAPSHOT_FILES
from phases.phase1.registry import load_scheme_registry
from phases.phase2.groww_selectors import (
    NEXT_DATA_ROOT_PATH,
    NEXT_DATA_SCRIPT_ID,
    FieldDefinition,
    get_field_definitions,
    is_blocked_field,
    resolve_json_path,
)
from phases.phase2.models import ExtractionSource, ExtractionStatus, FieldExtraction, ParsedScheme


def _extract_next_data_json(html: str) -> dict[str, Any] | None:
    match = re.search(
        rf'<script id="{re.escape(NEXT_DATA_SCRIPT_ID)}"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _get_mf_server_side_data(next_data: dict[str, Any]) -> dict[str, Any] | None:
    current: Any = next_data
    for key in NEXT_DATA_ROOT_PATH:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current if isinstance(current, dict) else None


def _value_to_raw_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return _format_lock_in_dict(value) or json.dumps(value, ensure_ascii=False)
    text = str(value).strip()
    return text or None


def _format_lock_in_dict(lock_in: dict[str, Any]) -> str | None:
    years = lock_in.get("years")
    months = lock_in.get("months")
    days = lock_in.get("days")
    if not any(v not in (None, 0) for v in (years, months, days)):
        return None
    parts: list[str] = []
    if years:
        parts.append(f"{years} year" if years == 1 else f"{years} years")
    if months:
        parts.append(f"{months} month" if months == 1 else f"{months} months")
    if days:
        parts.append(f"{days} day" if days == 1 else f"{days} days")
    return " ".join(parts) if parts else None


def _extract_fund_category(mf_data: dict[str, Any]) -> str | None:
    sub_category = mf_data.get("sub_category")
    category = mf_data.get("category")
    if sub_category and category and str(sub_category) != str(category):
        return f"{category} / {sub_category}"
    if sub_category:
        return str(sub_category)
    if category:
        return str(category)
    return None


def _extract_from_json(field: FieldDefinition, mf_data: dict[str, Any]) -> str | None:
    if field.field_id == "fund_category":
        return _extract_fund_category(mf_data)

    if field.field_id == "lock_in_period":
        lock_in = mf_data.get("lock_in")
        if isinstance(lock_in, dict):
            return _format_lock_in_dict(lock_in)
        return _value_to_raw_string(lock_in)

    if field.json_paths is None:
        return None

    for path in field.json_paths.paths:
        if path.startswith("return_stats"):
            value = resolve_json_path(mf_data, path)
        else:
            top_key = path.split(".")[0]
            if top_key in mf_data:
                value = resolve_json_path(mf_data, path)
            else:
                value = None
        raw = _value_to_raw_string(value)
        if raw is not None:
            return raw
    return None


def _visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def _extract_from_dom(field: FieldDefinition, html: str, soup: BeautifulSoup | None = None) -> str | None:
    if field.dom is None:
        return None

    if soup is None:
        soup = BeautifulSoup(html, "html.parser")

    for selector in field.dom.css_selectors:
        element = soup.select_one(selector)
        if element:
            text = element.get_text(strip=True)
            if text:
                return text

    text_blob = _visible_text(html)
    for pattern in field.dom.regex_patterns:
        match = re.search(pattern, text_blob, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    for label in field.dom.labels:
        pattern = re.compile(rf"{re.escape(label)}\s*[:\-]?\s*([^\n.]+)", re.IGNORECASE)
        for node in soup.find_all(string=True):
            text = str(node).strip()
            if not text:
                continue
            match = pattern.search(text)
            if match:
                return match.group(1).strip()

    return None


def _extract_field(
    field: FieldDefinition,
    *,
    scheme_category: str,
    mf_data: dict[str, Any] | None,
    html: str,
    soup: BeautifulSoup | None,
) -> FieldExtraction:
    if is_blocked_field(field.field_id):
        return FieldExtraction(field_id=field.field_id, status=ExtractionStatus.BLOCKED)

    if field.applicable_categories is not None and not field.applies_to_category(scheme_category):
        return FieldExtraction(field_id=field.field_id, status=ExtractionStatus.SKIPPED)

    raw_value: str | None = None
    source: ExtractionSource | None = None

    if mf_data is not None:
        raw_value = _extract_from_json(field, mf_data)
        if raw_value is not None:
            source = ExtractionSource.JSON

    if raw_value is None:
        raw_value = _extract_from_dom(field, html, soup)
        if raw_value is not None:
            source = ExtractionSource.DOM

    if raw_value is None:
        return FieldExtraction(field_id=field.field_id, status=ExtractionStatus.MISSING)

    return FieldExtraction(
        field_id=field.field_id,
        status=ExtractionStatus.FOUND,
        raw_value=raw_value,
        source=source,
    )


def parse_scheme_html(html: str, scheme_id: str, *, scheme_category: str | None = None) -> ParsedScheme:
    """Parse a Groww scheme page HTML snapshot into raw field extractions."""
    if scheme_category is None:
        registry = load_scheme_registry()
        scheme = next((s for s in registry.schemes if s.id == scheme_id), None)
        if scheme is None:
            raise ValueError(f"Unknown scheme_id: {scheme_id}")
        scheme_category = scheme.category

    next_data = _extract_next_data_json(html)
    mf_data = _get_mf_server_side_data(next_data) if next_data else None
    soup = BeautifulSoup(html, "html.parser")

    fields: dict[str, FieldExtraction] = {}
    for field_def in get_field_definitions():
        fields[field_def.field_id] = _extract_field(
            field_def,
            scheme_category=scheme_category,
            mf_data=mf_data,
            html=html,
            soup=soup,
        )

    return ParsedScheme(scheme_id=scheme_id, scheme_category=scheme_category, fields=fields)


def parse_scheme_snapshot(
    scheme_id: str,
    *,
    raw_dir: Path | None = None,
    scheme_category: str | None = None,
) -> ParsedScheme:
    """Read corpus/raw/{scheme_id}.html and parse it."""
    filename = RAW_SNAPSHOT_FILES.get(scheme_id)
    if filename is None:
        raise ValueError(f"No raw snapshot mapping for scheme_id: {scheme_id}")
    snapshot_path = (raw_dir or paths.RAW_DIR) / filename
    if not snapshot_path.exists():
        raise FileNotFoundError(f"Raw snapshot not found: {snapshot_path}")
    html = snapshot_path.read_text(encoding="utf-8")
    return parse_scheme_html(html, scheme_id, scheme_category=scheme_category)


def parse_all_scheme_snapshots(*, raw_dir: Path | None = None) -> list[ParsedScheme]:
    """Parse all schemes listed in the scheme registry."""
    registry = load_scheme_registry()
    results: list[ParsedScheme] = []
    for scheme in registry.schemes:
        results.append(parse_scheme_snapshot(scheme.id, raw_dir=raw_dir, scheme_category=scheme.category))
    return results

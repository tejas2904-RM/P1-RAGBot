"""Phase 2.4 — Build natural-language fact statements from normalized fields."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phases import paths
from phases.phase1.config import ALLOWED_URLS, SOURCE_NAME
from phases.phase1.models import Scheme
from phases.phase1.registry import load_scheme_registry, load_source_registry
from phases.phase1.validator import ValidationError, validate_url_allowlist
from phases.phase2.groww_selectors import get_field_definition, is_blocked_field
from phases.phase2.models import FactRecord, NormalizationStatus, NormalizedField
from phases.phase2.normalizer import normalize_parsed_scheme
from phases.phase2.parser import parse_scheme_snapshot

_INCLUDED_STATUSES = frozenset(
    {
        NormalizationStatus.OK,
        NormalizationStatus.NONE,
        NormalizationStatus.ZERO,
    }
)

_SENTENCE_BUILDERS: dict[str, str] = {
    "expense_ratio": "The expense ratio of {scheme_name} is {value}.",
    "exit_load": "The exit load of {scheme_name} is {value}.",
    "minimum_sip": "The minimum SIP amount for {scheme_name} is {value}.",
    "minimum_lumpsum": "The minimum lumpsum investment for {scheme_name} is {value}.",
    "lock_in_period": "The lock-in period for {scheme_name} is {value}.",
    "riskometer": "The riskometer classification of {scheme_name} is {value}.",
    "benchmark": "The benchmark index of {scheme_name} is {value}.",
    "fund_category": "The fund category of {scheme_name} is {value}.",
    "fund_house_amc": "The fund house (AMC) for {scheme_name} is {display_amc}.",
    "nav": "The NAV of {scheme_name} is {value}.",
    "nav_date": "The NAV as-of date for {scheme_name} is {value}.",
    "aum": "The AUM of {scheme_name} is {value} crore.",
}


def _format_display_value(field_id: str, normalized: NormalizedField, *, amc: str) -> str:
    if normalized.display_value:
        return normalized.display_value
    if normalized.status == NormalizationStatus.NONE:
        return "Nil"
    if normalized.value is None:
        return "Not available"
    if field_id == "fund_house_amc":
        return amc
    return str(normalized.value)


def _build_sentence(
    field_id: str,
    scheme_name: str,
    display_value: str,
    *,
    amc: str,
) -> str:
    template = _SENTENCE_BUILDERS.get(field_id)
    if template is None:
        field_def = get_field_definition(field_id)
        label = field_def.display_name if field_def else field_id
        return f"The {label.lower()} of {scheme_name} is {display_value}."
    return template.format(
        scheme_name=scheme_name,
        value=display_value,
        display_amc=display_value,
    )


def _resolve_last_updated(
    normalized_fields: dict[str, NormalizedField],
    *,
    fallback: str | None,
) -> str:
    nav_date = normalized_fields.get("nav_date")
    if nav_date and nav_date.status == NormalizationStatus.OK and nav_date.value:
        return str(nav_date.value)
    if fallback:
        return fallback[:10] if len(fallback) >= 10 else fallback
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _resolve_content_hash(scheme_id: str) -> str | None:
    for record in load_source_registry():
        if record.scheme_id == scheme_id:
            return record.content_hash
    return None


def _resolve_source_fetched_date(scheme_id: str) -> str | None:
    for record in load_source_registry():
        if record.scheme_id == scheme_id and record.last_fetched:
            return record.last_fetched
    return None


def build_facts(
    scheme: Scheme,
    normalized_fields: dict[str, NormalizedField],
    *,
    amc: str | None = None,
    content_hash: str | None = None,
    last_updated: str | None = None,
) -> list[FactRecord]:
    """Convert normalized fields into one fact record per includable field."""
    amc_name = amc or load_scheme_registry().amc
    validate_url_allowlist(scheme.url, context=f"scheme {scheme.id}")

    if content_hash is None:
        content_hash = _resolve_content_hash(scheme.id)
    if last_updated is None:
        last_updated = _resolve_last_updated(
            normalized_fields,
            fallback=_resolve_source_fetched_date(scheme.id),
        )

    facts: list[FactRecord] = []
    for field_id, normalized in normalized_fields.items():
        if is_blocked_field(field_id):
            continue
        if normalized.status not in _INCLUDED_STATUSES:
            continue

        display_value = _format_display_value(field_id, normalized, amc=amc_name)
        text = _build_sentence(field_id, scheme.scheme_name, display_value, amc=amc_name)

        facts.append(
            FactRecord(
                scheme_id=scheme.id,
                scheme_name=scheme.scheme_name,
                scheme_category=scheme.category,
                amc=amc_name,
                source_url=scheme.url,
                source=SOURCE_NAME,
                field=field_id,
                value=normalized.value,
                unit=normalized.unit,
                display_value=display_value,
                text=text,
                last_updated=last_updated,
                content_hash=content_hash,
            )
        )

    return facts


def build_facts_for_scheme(scheme_id: str) -> list[FactRecord]:
    """Parse, normalize, and build facts for a single scheme snapshot."""
    registry = load_scheme_registry()
    scheme = next((item for item in registry.schemes if item.id == scheme_id), None)
    if scheme is None:
        raise ValueError(f"Unknown scheme_id: {scheme_id}")

    parsed = parse_scheme_snapshot(scheme_id, scheme_category=scheme.category)
    normalized = normalize_parsed_scheme(parsed)
    return build_facts(scheme, normalized, amc=registry.amc)


def build_all_facts() -> list[FactRecord]:
    """Build fact records for all schemes in the registry."""
    registry = load_scheme_registry()
    all_facts: list[FactRecord] = []
    for scheme in registry.schemes:
        all_facts.extend(build_facts_for_scheme(scheme.id))
    return all_facts


def save_facts_json(
    facts: list[FactRecord],
    output_path: Path | None = None,
) -> Path:
    """Persist fact records to corpus/processed/facts.json."""
    path = output_path or paths.FACTS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(facts),
        "facts": [fact.to_dict() for fact in facts],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def validate_facts(facts: list[FactRecord]) -> None:
    """Ensure all fact records meet Phase 2.4 constraints."""
    allowed = set(ALLOWED_URLS)
    seen: set[tuple[str, str]] = set()

    for fact in facts:
        if fact.source_url not in allowed:
            raise ValidationError(f"Fact source_url not in ALLOWED_URLS: {fact.source_url}")
        if is_blocked_field(fact.field):
            raise ValidationError(f"Blocked field present in facts: {fact.field}")
        if not fact.text.endswith("."):
            raise ValidationError(f"Fact text must end with a period: {fact.field}")
        key = (fact.scheme_id, fact.field)
        if key in seen:
            raise ValidationError(f"Duplicate fact for scheme/field: {key}")
        seen.add(key)

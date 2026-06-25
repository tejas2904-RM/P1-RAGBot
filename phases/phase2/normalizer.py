"""Phase 2.3 — Normalize raw extracted field values into typed values."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from phases.phase2.groww_selectors import FieldValueType, get_field_definition
from phases.phase2.models import NormalizationStatus, NormalizedField, ParsedScheme

_NIL_VALUES = frozenset({"nil", "na", "n/a", "none", "-", "—", ""})
_ZERO_PERCENT = frozenset({"0%", "0.0%", "0.00%"})

_CURRENCY_PATTERN = re.compile(r"^[₹]?\s*([\d,]+(?:\.\d+)?)\s*$")
_PERCENT_PATTERN = re.compile(r"^([\d.]+)\s*%?\s*$")
_DATE_PATTERNS = (
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%Y-%m-%d",
    "%d/%m/%Y",
)


def _is_nil(raw: str) -> bool:
    return raw.strip().lower() in _NIL_VALUES


def _parse_percentage(field_id: str, raw: str) -> NormalizedField | None:
    cleaned = raw.strip()
    if _is_nil(cleaned):
        return None
    if cleaned in _ZERO_PERCENT:
        return NormalizedField(
            field_id=field_id,
            status=NormalizationStatus.ZERO,
            value=0.0,
            unit="%",
            display_value="0%",
            raw_value=raw,
        )
    match = _PERCENT_PATTERN.match(cleaned)
    if not match:
        return None
    value = float(match.group(1))
    display = cleaned if "%" in cleaned else f"{match.group(1)}%"
    return NormalizedField(
        field_id=field_id,
        status=NormalizationStatus.OK,
        value=value,
        unit="%",
        display_value=display,
        raw_value=raw,
    )


def _parse_currency(field_id: str, raw: str) -> NormalizedField | None:
    cleaned = raw.strip()
    if _is_nil(cleaned):
        return None
    match = _CURRENCY_PATTERN.match(cleaned)
    if not match:
        amount_match = re.search(r"₹\s*([\d,]+(?:\.\d+)?)", cleaned)
        if amount_match:
            amount = float(amount_match.group(1).replace(",", ""))
        else:
            digits = re.sub(r"[^\d.]", "", cleaned)
            if not digits:
                return None
            try:
                amount = float(digits)
            except ValueError:
                return None
    else:
        amount = float(match.group(1).replace(",", ""))
    display = cleaned if "₹" in cleaned else f"₹{int(amount) if amount.is_integer() else amount}"
    return NormalizedField(
        field_id=field_id,
        status=NormalizationStatus.OK,
        value=amount,
        unit="INR",
        display_value=display,
        raw_value=raw,
    )


def _parse_date(field_id: str, raw: str) -> NormalizedField | None:
    cleaned = raw.strip()
    if _is_nil(cleaned):
        return None
    for pattern in _DATE_PATTERNS:
        try:
            parsed = datetime.strptime(cleaned, pattern)
            iso = parsed.strftime("%Y-%m-%d")
            return NormalizedField(
                field_id=field_id,
                status=NormalizationStatus.OK,
                value=iso,
                unit=None,
                display_value=cleaned,
                raw_value=raw,
            )
        except ValueError:
            continue
    return None


def _parse_number(field_id: str, raw: str) -> NormalizedField | None:
    cleaned = raw.strip().replace(",", "")
    if _is_nil(cleaned):
        return None
    try:
        value = float(cleaned)
    except ValueError:
        return None
    display = raw.strip()
    return NormalizedField(
        field_id=field_id,
        status=NormalizationStatus.OK,
        value=value,
        unit=None,
        display_value=display,
        raw_value=raw,
    )


def _parse_text(field_id: str, raw: str) -> NormalizedField:
    cleaned = raw.strip()
    if _is_nil(cleaned):
        return NormalizedField(
            field_id=field_id,
            status=NormalizationStatus.NONE,
            value=None,
            unit=None,
            display_value="Nil",
            raw_value=raw,
        )
    if cleaned in _ZERO_PERCENT:
        return NormalizedField(
            field_id=field_id,
            status=NormalizationStatus.ZERO,
            value=0.0,
            unit="%",
            display_value=cleaned,
            raw_value=raw,
        )
    return NormalizedField(
        field_id=field_id,
        status=NormalizationStatus.OK,
        value=cleaned,
        unit=None,
        display_value=cleaned,
        raw_value=raw,
    )


def _parse_composite(field_id: str, raw: str) -> NormalizedField:
    cleaned = raw.strip()
    if _is_nil(cleaned):
        return NormalizedField(
            field_id=field_id,
            status=NormalizationStatus.NONE,
            value=None,
            unit=None,
            display_value="Not applicable",
            raw_value=raw,
        )
    return NormalizedField(
        field_id=field_id,
        status=NormalizationStatus.OK,
        value=cleaned,
        unit=None,
        display_value=cleaned,
        raw_value=raw,
    )


def normalize_field(
    field_id: str,
    raw_value: str | None,
    *,
    scheme_category: str | None = None,
) -> NormalizedField:
    """Normalize a single raw field value. Never raises on bad input."""
    field_def = get_field_definition(field_id)
    if field_def is None:
        return NormalizedField(
            field_id=field_id,
            status=NormalizationStatus.UNPARSEABLE,
            raw_value=raw_value,
        )

    if field_id == "lock_in_period" and scheme_category is not None and scheme_category != "elss":
        return NormalizedField(
            field_id=field_id,
            status=NormalizationStatus.NOT_APPLICABLE,
            value=None,
            unit=None,
            display_value="Not applicable",
            raw_value=raw_value,
        )

    if raw_value is None or not str(raw_value).strip():
        return NormalizedField(
            field_id=field_id,
            status=NormalizationStatus.UNPARSEABLE,
            raw_value=raw_value,
        )

    raw = str(raw_value).strip()
    value_type = field_def.value_type
    result: NormalizedField | None = None

    if value_type == FieldValueType.PERCENTAGE:
        result = _parse_percentage(field_id, raw)
        if result:
            return result
    elif value_type == FieldValueType.CURRENCY:
        result = _parse_currency(field_id, raw)
        if result:
            return result
    elif value_type == FieldValueType.DATE:
        result = _parse_date(field_id, raw)
        if result:
            return result
    elif value_type == FieldValueType.NUMBER:
        result = _parse_number(field_id, raw)
        if result:
            return result
    elif value_type == FieldValueType.COMPOSITE:
        return _parse_composite(field_id, raw)
    elif value_type == FieldValueType.TEXT:
        return _parse_text(field_id, raw)

    return NormalizedField(
        field_id=field_id,
        status=NormalizationStatus.UNPARSEABLE,
        raw_value=raw,
    )


def normalize_parsed_scheme(parsed: ParsedScheme) -> dict[str, NormalizedField]:
    """Normalize all found fields in a ParsedScheme."""
    from phases.phase2.models import ExtractionStatus

    normalized: dict[str, NormalizedField] = {}
    for field_id, extraction in parsed.fields.items():
        if extraction.status == ExtractionStatus.SKIPPED:
            normalized[field_id] = NormalizedField(
                field_id=field_id,
                status=NormalizationStatus.NOT_APPLICABLE,
                raw_value=None,
                display_value="Not applicable",
            )
            continue
        if extraction.status != ExtractionStatus.FOUND:
            continue
        normalized[field_id] = normalize_field(
            field_id,
            extraction.raw_value,
            scheme_category=parsed.scheme_category,
        )
    return normalized

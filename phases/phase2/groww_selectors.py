"""
Groww scheme page field map — Phase 2.1.

Central configuration for extractable target fields, blocked performance fields,
JSON paths (__NEXT_DATA__), and DOM fallback selectors/labels.

JSON paths are relative to: props.pageProps.mfServerSideData
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class FieldValueType(str, Enum):
    PERCENTAGE = "percentage"
    CURRENCY = "currency"
    TEXT = "text"
    NUMBER = "number"
    COMPOSITE = "composite"
    DATE = "date"


@dataclass(frozen=True)
class JsonPathSpec:
    """One or more dot-paths under mfServerSideData (first non-null wins)."""

    paths: tuple[str, ...]
    notes: str = ""


@dataclass(frozen=True)
class DomSelectorSpec:
    """DOM fallback selectors when JSON extraction misses a field."""

    labels: tuple[str, ...] = ()
    css_selectors: tuple[str, ...] = ()
    regex_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class FieldDefinition:
    field_id: str
    display_name: str
    description: str
    value_type: FieldValueType
    json_paths: JsonPathSpec | None = None
    dom: DomSelectorSpec | None = None
    # None = all schemes; otherwise only listed scheme categories (from registry).
    applicable_categories: frozenset[str] | None = None

    def applies_to_category(self, category: str) -> bool:
        if self.applicable_categories is None:
            return True
        return category in self.applicable_categories


# Root key for __NEXT_DATA__ extraction (Phase 2.2).
NEXT_DATA_ROOT_PATH: tuple[str, ...] = ("props", "pageProps", "mfServerSideData")
NEXT_DATA_SCRIPT_ID = "__NEXT_DATA__"


# --- Blocked fields: must NEVER be extracted or indexed (Phase 2.4 second guard) ---

BLOCKED_JSON_PREFIXES: tuple[str, ...] = (
    "return_stats",
    "simple_return",
    "sip_return",
    "peerComparison",
    "historic_fund_expense",
    "historic_exit_loads",
    "groww_rating",
    "crisil_rating",
    "analysis",
)

BLOCKED_JSON_PATHS: frozenset[str] = frozenset(
    {
        # Returns / CAGR
        "return_stats",
        "simple_return",
        "sip_return",
        "peerComparison",
        "historic_fund_expense",
        "historic_exit_loads",
        # Ratings / rankings
        "groww_rating",
        "crisil_rating",
        "analysis",
        # Holdings with ratings (peer-style data)
        "holdings",
    }
)

BLOCKED_FIELD_IDS: frozenset[str] = frozenset(
    {
        "return_1y",
        "return_3y",
        "return_5y",
        "return_10y",
        "return_since_launch",
        "cagr",
        "sip_returns",
        "trailing_returns",
        "groww_rating",
        "crisil_rating",
        "peer_comparison",
        "fund_performance",
        "mean_return",
        "category_return",
        "index_return",
    }
)

BLOCKED_DOM_LABELS: frozenset[str] = frozenset(
    {
        "1Y Return",
        "3Y Return",
        "5Y Return",
        "10Y Return",
        "Returns",
        "CAGR",
        "Fund performance",
        "Groww rating",
        "Category rank",
        "Peer comparison",
    }
)

BLOCKED_REGEX_PATTERNS: tuple[str, ...] = (
    r"return\s*\d+y",
    r"\d+\s*year\s*return",
    r"cagr",
    r"rating",
    r"outperform",
)


# --- Target fields: canonical extractable facts ---

_FIELD_DEFINITIONS: tuple[FieldDefinition, ...] = (
    FieldDefinition(
        field_id="expense_ratio",
        display_name="Expense ratio",
        description="Annual fund management fee as a percentage of AUM.",
        value_type=FieldValueType.PERCENTAGE,
        json_paths=JsonPathSpec(paths=("expense_ratio",)),
        dom=DomSelectorSpec(
            labels=("Expense ratio", "Expense Ratio"),
            regex_patterns=(r"expense ratio[^.]*?([\d.]+%?)", r"Expense ratio is\s*([\d.]+%?)"),
        ),
    ),
    FieldDefinition(
        field_id="exit_load",
        display_name="Exit load",
        description="Fee charged on redemption within a specified period.",
        value_type=FieldValueType.TEXT,
        json_paths=JsonPathSpec(paths=("exit_load",)),
        dom=DomSelectorSpec(
            labels=("Exit load", "Exit Load"),
            regex_patterns=(
                r"Exit load of\s*([^.]+)\.",
                r"Exit load[:\s]+([^.]+)",
            ),
        ),
    ),
    FieldDefinition(
        field_id="minimum_sip",
        display_name="Minimum SIP",
        description="Minimum systematic investment plan amount.",
        value_type=FieldValueType.CURRENCY,
        json_paths=JsonPathSpec(paths=("min_sip_investment",)),
        dom=DomSelectorSpec(
            labels=("Min. SIP amount", "Minimum SIP", "Min SIP"),
            regex_patterns=(
                r"Minimum SIP Investment is set to\s*₹?\s*([\d,]+)",
                r"Min\.?\s*SIP[^₹]*₹\s*([\d,]+)",
            ),
        ),
    ),
    FieldDefinition(
        field_id="minimum_lumpsum",
        display_name="Minimum lumpsum",
        description="Minimum one-time investment amount.",
        value_type=FieldValueType.CURRENCY,
        json_paths=JsonPathSpec(
            paths=("min_lumpsum_investment",),
            notes="Often null in JSON; DOM/regex fallback required.",
        ),
        dom=DomSelectorSpec(
            labels=("Min. lumpsum", "Minimum Lumpsum", "Min Lumpsum"),
            regex_patterns=(
                r"Minimum Lumpsum Investment is\s*₹?\s*([\d,]+)",
                r"Min\.?\s*Lumpsum[^₹]*₹\s*([\d,]+)",
            ),
        ),
    ),
    FieldDefinition(
        field_id="lock_in_period",
        display_name="Lock-in period",
        description="Mandatory holding period (ELSS tax-saving schemes).",
        value_type=FieldValueType.COMPOSITE,
        json_paths=JsonPathSpec(
            paths=("lock_in",),
            notes="Object with years/months/days; ELSS typically years=3.",
        ),
        dom=DomSelectorSpec(
            labels=("Lock-in", "Lock in", "Lock-in period"),
            regex_patterns=(r"lock[- ]?in[^.]*?(\d+\s*(?:year|month|day)s?)",),
        ),
        applicable_categories=frozenset({"elss"}),
    ),
    FieldDefinition(
        field_id="riskometer",
        display_name="Riskometer",
        description="SEBI riskometer classification for the scheme.",
        value_type=FieldValueType.TEXT,
        json_paths=JsonPathSpec(
            paths=("nfo_risk", "return_stats.0.risk"),
            notes="Prefer nfo_risk; return_stats[0].risk as fallback.",
        ),
        dom=DomSelectorSpec(
            labels=("Risk", "Riskometer", "Risk level"),
            regex_patterns=(
                r"is rated\s+([^.\n]+?)\s+risk",
                r"Riskometer[:\s]+([^.\n]+)",
            ),
        ),
    ),
    FieldDefinition(
        field_id="benchmark",
        display_name="Benchmark index",
        description="Index used to measure scheme performance.",
        value_type=FieldValueType.TEXT,
        json_paths=JsonPathSpec(paths=("benchmark_name", "benchmark")),
        dom=DomSelectorSpec(
            labels=("Fund benchmark", "Benchmark"),
            css_selectors=(
                "div.investmentObjective_benchmarkRow__tpudX span.bodyLargeHeavy",
            ),
        ),
    ),
    FieldDefinition(
        field_id="fund_category",
        display_name="Fund category",
        description="Scheme category and sub-category (e.g. Equity / Mid Cap).",
        value_type=FieldValueType.COMPOSITE,
        json_paths=JsonPathSpec(
            paths=("sub_category", "category"),
            notes="Combine category + sub_category when both present.",
        ),
        dom=DomSelectorSpec(labels=("Category", "Fund category", "Sub category")),
    ),
    FieldDefinition(
        field_id="fund_house_amc",
        display_name="Fund house (AMC)",
        description="Asset management company managing the scheme.",
        value_type=FieldValueType.TEXT,
        json_paths=JsonPathSpec(paths=("amc", "amc_info.amc")),
        dom=DomSelectorSpec(labels=("Fund house", "AMC", "Managed by")),
    ),
    FieldDefinition(
        field_id="nav",
        display_name="NAV",
        description="Net asset value snapshot (not for return calculations).",
        value_type=FieldValueType.NUMBER,
        json_paths=JsonPathSpec(paths=("nav",), notes="Pair with nav_date for snapshot."),
        dom=DomSelectorSpec(labels=("NAV", "Net Asset Value")),
    ),
    FieldDefinition(
        field_id="nav_date",
        display_name="NAV date",
        description="As-of date for the NAV snapshot.",
        value_type=FieldValueType.DATE,
        json_paths=JsonPathSpec(paths=("nav_date",)),
        dom=DomSelectorSpec(labels=("NAV date", "As on")),
    ),
    FieldDefinition(
        field_id="aum",
        display_name="AUM",
        description="Assets under management snapshot in crores (Groww source units).",
        value_type=FieldValueType.NUMBER,
        json_paths=JsonPathSpec(paths=("aum",)),
        dom=DomSelectorSpec(labels=("Fund size", "AUM", "Assets under management")),
    ),
)

TARGET_FIELDS: tuple[str, ...] = tuple(field.field_id for field in _FIELD_DEFINITIONS)

BLOCKED_FIELDS: frozenset[str] = BLOCKED_FIELD_IDS


def get_field_definitions() -> tuple[FieldDefinition, ...]:
    return _FIELD_DEFINITIONS


def get_field_definition(field_id: str) -> FieldDefinition | None:
    for field in _FIELD_DEFINITIONS:
        if field.field_id == field_id:
            return field
    return None


def is_target_field(field_id: str) -> bool:
    return field_id in TARGET_FIELDS


def is_blocked_field(field_id: str) -> bool:
    return field_id in BLOCKED_FIELDS


def is_blocked_json_key(key: str) -> bool:
    if key in BLOCKED_JSON_PATHS:
        return True
    return any(key.startswith(prefix) for prefix in BLOCKED_JSON_PREFIXES)


def resolve_json_path(data: dict[str, Any], path: str) -> Any:
    """Resolve a dot-path with optional list index (e.g. return_stats.0.risk)."""
    current: Any = data
    for segment in path.split("."):
        if current is None:
            return None
        if segment.isdigit():
            index = int(segment)
            if not isinstance(current, list) or index >= len(current):
                return None
            current = current[index]
            continue
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def get_json_paths_for_field(field_id: str) -> tuple[str, ...]:
    field = get_field_definition(field_id)
    if field is None or field.json_paths is None:
        return ()
    return field.json_paths.paths


def validate_field_map() -> None:
    """Raise ValueError if the field map is incomplete or inconsistent."""
    if not TARGET_FIELDS:
        raise ValueError("TARGET_FIELDS must not be empty")

    if overlap := set(TARGET_FIELDS) & set(BLOCKED_FIELDS):
        raise ValueError(f"Fields cannot be both target and blocked: {sorted(overlap)}")

    required_from_phase1 = {
        "expense_ratio",
        "exit_load",
        "minimum_sip",
        "minimum_lumpsum",
        "lock_in_period",
        "riskometer",
        "benchmark",
        "fund_category",
        "fund_house_amc",
        "nav",
        "aum",
    }
    missing = required_from_phase1 - set(TARGET_FIELDS)
    if missing:
        raise ValueError(f"Field map missing Phase 1 target data points: {sorted(missing)}")

    for field in _FIELD_DEFINITIONS:
        if field.json_paths is None and field.dom is None:
            raise ValueError(f"Field {field.field_id} has no JSON path or DOM fallback")

    if not BLOCKED_FIELDS:
        raise ValueError("BLOCKED_FIELDS must not be empty")

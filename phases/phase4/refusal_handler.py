"""Fixed refusal messages for advisory, comparative, and PII queries."""

from __future__ import annotations

from phases.phase4.config import ADVISORY_COMPARATIVE_REFUSAL


def advisory_refusal() -> str:
    return ADVISORY_COMPARATIVE_REFUSAL


def comparative_refusal() -> str:
    return ADVISORY_COMPARATIVE_REFUSAL


def pii_refusal() -> str:
    return ADVISORY_COMPARATIVE_REFUSAL

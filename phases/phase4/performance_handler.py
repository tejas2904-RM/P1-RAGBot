"""Fixed refusal messages for performance and return queries."""

from __future__ import annotations

from phases.phase4.config import PERFORMANCE_REFUSAL


def performance_refusal() -> str:
    return PERFORMANCE_REFUSAL

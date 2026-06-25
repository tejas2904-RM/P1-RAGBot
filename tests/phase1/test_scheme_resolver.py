"""Tests for scheme name and alias resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from phases.phase1.registry import load_urls_config
from phases.phase1.scheme_resolver import SchemeResolver


@pytest.fixture
def resolver() -> SchemeResolver:
    urls_path = Path(__file__).resolve().parents[2] / "corpus" / "urls.json"
    return SchemeResolver(load_urls_config(urls_path))


def test_resolve_canonical_name(resolver: SchemeResolver) -> None:
    scheme = resolver.resolve("What is the expense ratio of HDFC Mid Cap Fund?")
    assert scheme is not None
    assert scheme.id == "hdfc-mid-cap"


def test_resolve_alias_midcap(resolver: SchemeResolver) -> None:
    scheme = resolver.resolve("midcap fund expense ratio")
    assert scheme is not None
    assert scheme.id == "hdfc-mid-cap"


def test_resolve_elss_alias(resolver: SchemeResolver) -> None:
    scheme = resolver.resolve("ELSS lock-in period")
    assert scheme is not None
    assert scheme.id == "hdfc-elss"


def test_unlisted_scheme_returns_none(resolver: SchemeResolver) -> None:
    assert resolver.resolve("SBI Bluechip Fund expense ratio") is None

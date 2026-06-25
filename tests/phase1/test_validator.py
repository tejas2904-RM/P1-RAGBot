"""Tests for corpus validation and allowlist enforcement."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from phases.phase1.config import ALLOWED_URLS
from phases.phase1.models import UrlsConfig
from phases.phase1.registry import load_urls_config, save_scheme_registry
from phases.phase1.validator import (
    ValidationError,
    validate_scheme_registry_matches_urls,
    validate_url_allowlist,
    validate_urls_config,
)


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def urls_config(project_root: Path) -> UrlsConfig:
    return load_urls_config(project_root / "corpus" / "urls.json")


def test_urls_json_has_exactly_five_allowlisted_urls(urls_config: UrlsConfig) -> None:
    validate_urls_config(urls_config)
    assert len(urls_config.schemes) == 5
    assert {scheme.url for scheme in urls_config.schemes} == set(ALLOWED_URLS)


def test_scheme_registry_matches_urls(urls_config: UrlsConfig, tmp_path: Path) -> None:
    registry_path = save_scheme_registry(urls_config, tmp_path / "scheme_registry.json")
    registry = load_urls_config(registry_path)
    validate_scheme_registry_matches_urls(urls_config, registry)


def test_rejects_sixth_url(tmp_path: Path) -> None:
    payload = json.loads((Path(__file__).parents[2] / "corpus" / "urls.json").read_text(encoding="utf-8"))
    payload["schemes"].append(
        {
            "id": "extra",
            "scheme_name": "Extra Fund",
            "category": "other",
            "plan": "Direct",
            "option": "Growth",
            "url": "https://groww.in/mutual-funds/extra-fund",
        }
    )
    bad_path = tmp_path / "urls.json"
    bad_path.write_text(json.dumps(payload), encoding="utf-8")

    config = load_urls_config(bad_path)
    with pytest.raises(ValidationError, match="Expected exactly"):
        validate_urls_config(config)


def test_rejects_non_allowlisted_url() -> None:
    with pytest.raises(ValidationError, match="not in ALLOWED_URLS"):
        validate_url_allowlist("https://amfiindia.com/some-page")

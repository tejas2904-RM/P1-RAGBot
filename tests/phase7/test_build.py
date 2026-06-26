"""Tests for Phase 7 — Vercel build script."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from phases.phase7.build import build_frontend, main as run_build, validate_frontend_bundle
from phases.phase7.config import CONFIG_JS_PATH, FRONTEND_DIR

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_validate_frontend_bundle_passes() -> None:
    validate_frontend_bundle()


def test_build_frontend_writes_config(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.js"
    monkeypatch.setattr("phases.phase7.build.CONFIG_JS_PATH", config_path)

    content = build_frontend(api_base_url="https://api.render.test")
    assert config_path.exists()
    assert content == config_path.read_text(encoding="utf-8")
    payload = json.loads(content.split("=", 1)[1].strip().rstrip(";"))
    assert payload == {"API_BASE_URL": "https://api.render.test"}


def test_build_cli() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "phases.phase7.build"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        check=False,
    )
    assert result.returncode == 0
    assert "OK: frontend bundle ready" in result.stdout
    assert CONFIG_JS_PATH.exists()


def test_build_main_returns_zero() -> None:
    assert run_build() == 0


def test_build_fails_when_index_missing(tmp_path, monkeypatch) -> None:
    fake_frontend = tmp_path / "frontend"
    monkeypatch.setattr(
        "phases.phase7.config.REQUIRED_FRONTEND_FILES",
        (fake_frontend / "index.html",),
    )
    monkeypatch.setattr("phases.phase7.build.REQUIRED_FRONTEND_FILES", (fake_frontend / "index.html",))

    with pytest.raises(FileNotFoundError, match="Missing frontend files"):
        validate_frontend_bundle()

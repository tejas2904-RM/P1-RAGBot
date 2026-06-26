"""Tests for Phase 7 — Vercel frontend deployment."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from phases.phase7.inject_config import build_config_js

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_build_config_js_empty_base() -> None:
    js = build_config_js(api_base_url="")
    assert "window.__ENV__" in js
    assert json.loads(js.split("=", 1)[1].strip().rstrip(";")) == {"API_BASE_URL": ""}


def test_build_config_js_strips_trailing_slash() -> None:
    js = build_config_js(api_base_url="https://api.example.com/")
    payload = json.loads(js.split("=", 1)[1].strip().rstrip(";"))
    assert payload["API_BASE_URL"] == "https://api.example.com"


def test_inject_config_cli() -> None:
    import os

    env = {**os.environ, "API_BASE_URL": "https://backend.test"}
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "phases" / "phase7" / "inject_config.py")],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )
    payload = json.loads(result.stdout.split("=", 1)[1].strip().rstrip(";"))
    assert payload["API_BASE_URL"] == "https://backend.test"


def test_vercel_json_static_frontend() -> None:
    vercel_path = PROJECT_ROOT / "vercel.json"
    assert vercel_path.exists()
    content = vercel_path.read_text(encoding="utf-8")
    assert "phases/phase5/frontend" in content
    assert "inject_config.mjs" in content
    assert "outputDirectory" in content


def test_pyproject_has_no_vercel_entrypoint() -> None:
    content = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.vercel]" not in content


def test_render_blueprint_build_step() -> None:
    render_path = PROJECT_ROOT / "render.yaml"
    assert render_path.exists()
    content = render_path.read_text(encoding="utf-8")
    assert "phases.phase6.build" in content
    assert "phases.phase6.api_server:app" in content

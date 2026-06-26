"""Tests for Phase 7 — static frontend bundle layout."""

from __future__ import annotations

import re
from pathlib import Path

from phases.phase5.config import DISCLAIMER
from phases.phase7.config import FRONTEND_DIR

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INDEX_HTML = FRONTEND_DIR / "index.html"
APP_JS = FRONTEND_DIR / "static" / "js" / "app.js"
STYLES_CSS = FRONTEND_DIR / "static" / "css" / "styles.css"


def test_frontend_required_files_exist() -> None:
    assert INDEX_HTML.exists()
    assert APP_JS.exists()
    assert STYLES_CSS.exists()


def test_index_loads_config_before_app_js() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    config_pos = html.index('src="/config.js"')
    app_pos = html.index('src="/static/js/app.js"')
    assert config_pos < app_pos


def test_index_has_disclaimer_elements() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'id="disclaimer-banner"' in html
    assert 'id="footer-disclaimer"' in html
    assert DISCLAIMER in html


def test_app_js_uses_configurable_api_base() -> None:
    js = APP_JS.read_text(encoding="utf-8")
    assert "window.__ENV__" in js
    assert "function getApiBase()" in js
    assert "function apiUrl(path)" in js
    assert 'apiUrl("/api/v1/chat")' in js
    assert 'apiUrl("/api/v1/meta")' in js
    assert "127.0.0.1:8000" not in js


def test_app_js_handles_vercel_missing_backend() -> None:
    js = APP_JS.read_text(encoding="utf-8")
    assert "vercel.app" in js
    assert "API_BASE_URL is not configured" in js


def test_styles_dark_theme() -> None:
    css = STYLES_CSS.read_text(encoding="utf-8")
    assert "#0a0e17" in css or "0a0e17" in css.lower()


def test_config_example_has_no_secrets() -> None:
    example = (FRONTEND_DIR / "config.example.js").read_text(encoding="utf-8")
    assert "API_BASE_URL" in example
    assert not re.search(r"GROQ|OPENAI|sk-", example, re.IGNORECASE)

"""Phase 7 — Vercel deployment constants."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "phases" / "phase5" / "frontend"
CONFIG_JS_PATH = FRONTEND_DIR / "config.js"
CONFIG_EXAMPLE_PATH = FRONTEND_DIR / "config.example.js"
VERCEL_JSON_PATH = PROJECT_ROOT / "vercel.json"
INJECT_CONFIG_MJS = PROJECT_ROOT / "phases" / "phase7" / "inject_config.mjs"

API_BASE_URL_ENV = "API_BASE_URL"
DEFAULT_PREVIEW_PORT = 4173

REQUIRED_FRONTEND_FILES: tuple[Path, ...] = (
    FRONTEND_DIR / "index.html",
    FRONTEND_DIR / "static" / "js" / "app.js",
    FRONTEND_DIR / "static" / "css" / "styles.css",
)

ALLOWED_CONFIG_KEYS: frozenset[str] = frozenset({"API_BASE_URL"})

"""Write frontend config.js from API_BASE_URL (Vercel build step)."""

from __future__ import annotations

import json
import os
import sys

from phases.phase7.config import ALLOWED_CONFIG_KEYS, API_BASE_URL_ENV


def build_config_js(*, api_base_url: str | None = None) -> str:
    """Return JavaScript that sets window.__ENV__ for the static frontend."""
    api_base = (
        api_base_url if api_base_url is not None else os.environ.get(API_BASE_URL_ENV, "")
    ).strip()
    api_base = api_base.rstrip("/")
    payload = {"API_BASE_URL": api_base}
    if set(payload) - ALLOWED_CONFIG_KEYS:
        raise ValueError("config.js must not expose secret keys")
    return f"window.__ENV__ = {json.dumps(payload)};\n"


def main() -> None:
    if os.getenv("VERCEL") and not os.environ.get(API_BASE_URL_ENV, "").strip():
        print(
            "ERROR: API_BASE_URL must be set in Vercel environment variables.\n"
            "Use your Phase 6 Render API URL, e.g. https://m2-ragbot-api.onrender.com",
            file=sys.stderr,
        )
        raise SystemExit(1)
    sys.stdout.write(build_config_js())


if __name__ == "__main__":
    main()

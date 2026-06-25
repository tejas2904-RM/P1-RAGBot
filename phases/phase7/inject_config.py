"""Write frontend config.js from API_BASE_URL (Vercel build step)."""

from __future__ import annotations

import json
import os
import sys


def build_config_js(*, api_base_url: str | None = None) -> str:
    """Return JavaScript that sets window.__ENV__ for the static frontend."""
    api_base = (api_base_url if api_base_url is not None else os.environ.get("API_BASE_URL", "")).strip()
    api_base = api_base.rstrip("/")
    payload = {"API_BASE_URL": api_base}
    return f"window.__ENV__ = {json.dumps(payload)};\n"


def main() -> None:
    sys.stdout.write(build_config_js())


if __name__ == "__main__":
    main()

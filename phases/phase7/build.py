"""Phase 7 Vercel build — validate frontend bundle and write config.js."""

from __future__ import annotations

import sys

from phases.phase7.config import CONFIG_JS_PATH, REQUIRED_FRONTEND_FILES
from phases.phase7.inject_config import build_config_js


def validate_frontend_bundle() -> None:
    """Ensure the static frontend assets required for Vercel deploy exist."""
    from phases.phase7.config import PROJECT_ROOT

    missing = []
    for path in REQUIRED_FRONTEND_FILES:
        if path.exists():
            continue
        try:
            missing.append(str(path.relative_to(PROJECT_ROOT)))
        except ValueError:
            missing.append(str(path))
    if missing:
        raise FileNotFoundError(
            "Missing frontend files required for Phase 7 deploy: " + ", ".join(missing)
        )


def build_frontend(*, api_base_url: str | None = None) -> str:
    """Validate bundle and write config.js; return generated JavaScript."""
    validate_frontend_bundle()
    content = build_config_js(api_base_url=api_base_url)
    CONFIG_JS_PATH.write_text(content, encoding="utf-8")
    return content


def main() -> int:
    try:
        build_frontend()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"OK: frontend bundle ready; wrote {CONFIG_JS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Phase 6 CLI — run the Render API backend locally."""

from __future__ import annotations

import argparse

from phases.phase5.config import DEFAULT_API_HOST, DEFAULT_API_PORT


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 6 — Render FAQ API server")
    parser.add_argument("--host", default=DEFAULT_API_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_API_PORT)
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development)")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit("uvicorn is required: pip install uvicorn") from exc

    uvicorn.run(
        "phases.phase6.api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

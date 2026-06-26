"""Phase 7 CLI — build config.js and preview the static frontend locally."""

from __future__ import annotations

import argparse
import http.server
import socketserver
import webbrowser
from functools import partial

from phases.phase7.build import build_frontend
from phases.phase7.config import DEFAULT_PREVIEW_PORT, FRONTEND_DIR


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 7 — build Vercel frontend config and preview locally"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PREVIEW_PORT,
        help=f"Preview server port (default: {DEFAULT_PREVIEW_PORT})",
    )
    parser.add_argument(
        "--api-base-url",
        default=None,
        help="Render API URL for config.js (default: API_BASE_URL env or same-origin)",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Serve existing frontend without regenerating config.js",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the browser automatically",
    )
    args = parser.parse_args()

    if not args.skip_build:
        build_frontend(api_base_url=args.api_base_url)

    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(FRONTEND_DIR))
    url = f"http://127.0.0.1:{args.port}/"

    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"Serving Phase 7 frontend at {url}")
        print("Press Ctrl+C to stop.")
        if not args.no_open:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()

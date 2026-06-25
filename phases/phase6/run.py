"""Phase 6 CLI — run Streamlit UI or headless FastAPI server."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 6 — deployment runners")
    sub = parser.add_subparsers(dest="command", required=True)

    streamlit_cmd = sub.add_parser("streamlit", help="Run Streamlit Community Cloud entry locally")
    streamlit_cmd.add_argument("--port", type=int, default=8501)

    sub.add_parser("api", help="Run headless FastAPI server (for Vercel / cloud API)")

    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]

    if args.command == "streamlit":
        app_path = Path(__file__).resolve().parent / "streamlit_app.py"
        raise SystemExit(
            subprocess.call(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    str(app_path),
                    "--server.port",
                    str(args.port),
                    "--server.headless",
                    "true",
                ],
                cwd=root,
            )
        )

    if args.command == "api":
        from phases.phase6.api_server import main as run_api

        run_api()


if __name__ == "__main__":
    main()

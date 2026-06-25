"""Phase 6 — FastAPI entrypoint for headless API deploy (Vercel / Render / Railway)."""

from __future__ import annotations

import logging
import os

from phases.phase6.bootstrap import init_backend

logger = logging.getLogger(__name__)

# Bootstrap before importing the FastAPI app (env + vector index).
init_backend()

from phases.phase5.app import app  # noqa: E402  — import after bootstrap

__all__ = ["app"]


def main() -> None:
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    logger.info("Starting Phase 6 API server on %s:%s", host, port)
    uvicorn.run("phases.phase6.api_server:app", host=host, port=port)


if __name__ == "__main__":
    main()

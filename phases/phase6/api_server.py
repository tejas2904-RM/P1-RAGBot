"""Phase 6 — FastAPI backend for Render deployment."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

if os.getenv("PHASE6_SKIP_BOOTSTRAP") != "1":
    from phases.phase6.bootstrap import init_backend

    init_backend()

from phases.phase5.app import app  # noqa: E402

__all__ = ["app"]


def main() -> None:
    import uvicorn

    from phases.phase6.config import RENDER_SERVICE_NAME

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    logger.info("Starting %s (Phase 6 Render API) on %s:%s", RENDER_SERVICE_NAME, host, port)
    uvicorn.run("phases.phase6.api_server:app", host=host, port=port)


if __name__ == "__main__":
    main()

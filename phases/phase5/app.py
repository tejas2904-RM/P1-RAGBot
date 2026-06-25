"""FastAPI application for the Phase 5 FAQ assistant backend."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from phases.phase5.config import APP_TITLE, DISCLAIMER
from phases.phase5.models import BootstrapResponse, ChatRequest, ChatResponse, HealthResponse
from phases.phase5.service import ask_question, get_bootstrap, get_health

logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"

app = FastAPI(
    title=APP_TITLE,
    description="Facts-only HDFC mutual fund FAQ API (Groww-sourced corpus).",
    version="1.0.0",
)

_cors_origins = os.getenv(
    "API_CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://127.0.0.1:8000,http://localhost:8000",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _cors_origins.split(",") if origin.strip()],
    allow_origin_regex=r"https://[\w.-]+\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness and vector index readiness."""
    return get_health()


@app.get("/api/v1/meta", response_model=BootstrapResponse, tags=["bootstrap"])
def meta() -> BootstrapResponse:
    """Welcome copy, disclaimer, and example questions for the UI shell."""
    return get_bootstrap()


@app.post("/api/v1/chat", response_model=ChatResponse, tags=["chat"])
def chat(request: ChatRequest) -> ChatResponse:
    """Ask a factual question or receive a fixed refusal response."""
    try:
        return ask_question(request.query)
    except Exception as exc:
        logger.exception("chat request failed")
        raise HTTPException(status_code=500, detail="Unable to process the question.") from exc


@app.get("/api/v1/disclaimer", tags=["bootstrap"])
def disclaimer() -> dict[str, str]:
    """Reusable disclaimer snippet for UI banners and docs."""
    return {"disclaimer": DISCLAIMER}


@app.get("/config.js", include_in_schema=False, response_model=None)
def serve_config() -> FileResponse | Response:
    """Runtime API base URL config for Vercel / static frontend."""
    config_path = FRONTEND_DIR / "config.js"
    if config_path.exists():
        return FileResponse(config_path, media_type="application/javascript")
    from phases.phase7.inject_config import build_config_js

    return Response(content=build_config_js(), media_type="application/javascript")


@app.get("/", include_in_schema=False)
def serve_index() -> FileResponse:
    """Serve the Phase 5 chat UI."""
    return FileResponse(FRONTEND_DIR / "index.html")


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def log_startup_config() -> None:
    from phases.env import load_env

    load_env()
    health = get_health()
    logger.info(
        "Startup: generator=%s llm_enabled=%s groq_configured=%s index_ready=%s",
        health.generator,
        health.llm_enabled,
        health.groq_configured,
        health.index_ready,
    )

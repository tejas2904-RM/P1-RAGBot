"""Phase 6 — Render deployment constants."""

from __future__ import annotations

RENDER_SERVICE_NAME = "m2-ragbot-api"
HEALTH_CHECK_PATH = "/health"

REQUIRED_ENV_VARS: tuple[str, ...] = (
    "GROQ_API_KEY",
    "OPENAI_API_KEY",
)

OPTIONAL_ENV_VARS: tuple[str, ...] = (
    "API_CORS_ORIGINS",
    "GENERATOR_PROVIDER",
    "GENERATOR_MODEL",
    "EMBEDDING_PROVIDER",
    "EMBEDDING_MODEL",
    "PORT",
    "API_HOST",
)

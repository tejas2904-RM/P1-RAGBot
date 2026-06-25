"""Load environment variables from the project root .env file."""

from __future__ import annotations

from pathlib import Path


def load_env() -> None:
    """Load .env from the repository root if python-dotenv is installed."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_path, override=True)

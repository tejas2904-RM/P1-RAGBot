"""Phase 3 configuration constants."""

from __future__ import annotations

# Retrieval
DEFAULT_TOP_K_SCHEME = 3
DEFAULT_TOP_K_FIELD = 3
DEFAULT_TOP_K_GLOBAL = 5
DEFAULT_MIN_SIMILARITY_SCORE = 0.25

# Generation (Groq LLM)
DEFAULT_LLM_MODEL = "llama-3.3-70b-versatile"
DEFAULT_LLM_TEMPERATURE = 0.0
MAX_QUERY_CHARS = 500
MAX_ANSWER_SENTENCES = 3

INSUFFICIENT_CONTEXT_MESSAGE = (
    "I could not find enough information in the available sources to answer that question "
    "accurately. Please ask about one of the five HDFC mutual fund schemes covered by this "
    "assistant (for example expense ratio, exit load, minimum SIP, lock-in, riskometer, or benchmark)."
)

INDEX_NOT_READY_MESSAGE = (
    "The knowledge index is not ready yet. Please run the Phase 2 indexing pipeline before "
    "asking factual questions."
)

ADVISORY_PHRASES: tuple[str, ...] = (
    "you should",
    "you should consider",
    "i recommend",
    "i would recommend",
    "worth buying",
    "worth investing",
    "good investment",
    "better choice",
)

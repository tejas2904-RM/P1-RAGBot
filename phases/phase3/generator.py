"""Generate answer bodies from retrieved chunks."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod

from phases.phase2.models import SearchResult
from phases.phase3.config import DEFAULT_LLM_MODEL, DEFAULT_LLM_TEMPERATURE
from phases.phase3.prompt_builder import build_messages

logger = logging.getLogger(__name__)


class AnswerGenerator(ABC):
    @abstractmethod
    def generate(self, query: str, chunks: list[SearchResult]) -> str:
        raise NotImplementedError


class TemplateAnswerGenerator(AnswerGenerator):
    """Deterministic answer body from retrieved chunk text (tests and offline)."""

    def generate(self, query: str, chunks: list[SearchResult]) -> str:
        if not chunks:
            return "INSUFFICIENT_CONTEXT"

        scheme_ids = {item.scheme_id for item in chunks}
        source_urls = {item.source_url for item in chunks}
        if len(scheme_ids) > 1 or len(source_urls) > 1:
            return "INSUFFICIENT_CONTEXT"

        sentences = [item.text.strip() for item in chunks if item.text.strip()]
        body = " ".join(sentences)
        if len(sentences) > 3:
            body = " ".join(sentences[:3])
        if body and not body.endswith("."):
            body += "."
        return body


class GroqAnswerGenerator(AnswerGenerator):
    """Groq LLM answer generation with temperature near zero."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float = DEFAULT_LLM_TEMPERATURE,
    ) -> None:
        self._api_key = api_key
        self._model = model or os.getenv("GENERATOR_MODEL", DEFAULT_LLM_MODEL)
        self._temperature = temperature
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from groq import Groq
            except ImportError as exc:
                raise ImportError("groq package is required for GroqAnswerGenerator") from exc
            api_key = self._api_key or os.getenv("GROQ_API_KEY") or os.getenv("GENERATOR_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY or GENERATOR_API_KEY must be set for Groq generation")
            self._client = Groq(api_key=api_key)
        return self._client

    def generate(self, query: str, chunks: list[SearchResult]) -> str:
        if not chunks:
            return "INSUFFICIENT_CONTEXT"

        client = self._get_client()
        messages = build_messages(query, chunks)
        response = client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            messages=messages,
        )
        logger.info("Groq completion model=%s query_len=%s chunks=%s", self._model, len(query), len(chunks))
        content = (response.choices[0].message.content or "").strip()
        if not content:
            return "INSUFFICIENT_CONTEXT"
        return content


def get_answer_generator() -> AnswerGenerator:
    provider = os.getenv("GENERATOR_PROVIDER", "auto").lower()
    has_groq_key = bool(os.getenv("GROQ_API_KEY") or os.getenv("GENERATOR_API_KEY"))

    if provider == "template":
        return TemplateAnswerGenerator()
    if provider == "groq":
        if has_groq_key:
            return GroqAnswerGenerator()
        logger.warning("GENERATOR_PROVIDER=groq but no API key; using template generator")
        return TemplateAnswerGenerator()
    if has_groq_key:
        return GroqAnswerGenerator()
    return TemplateAnswerGenerator()


def get_generator_name() -> str:
    """Return active generator class name for diagnostics."""
    return type(get_answer_generator()).__name__


def is_llm_enabled() -> bool:
    """True when Groq generator is active (not template fallback)."""
    return not isinstance(get_answer_generator(), TemplateAnswerGenerator)

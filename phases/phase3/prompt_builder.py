"""Build constrained prompts for the Phase 3 generator."""

from __future__ import annotations

from phases.phase2.models import SearchResult

SYSTEM_PROMPT = """You are a facts-only mutual fund FAQ assistant for five HDFC schemes on Groww.

Rules:
1. Answer ONLY using the provided context chunks. Do not invent numbers or facts.
2. Use at most 3 sentences in the answer body (before the Source line).
3. Do not include URLs in the answer body — citation is added separately.
4. Do not provide investment advice, opinions, recommendations, or fund comparisons.
5. Do not discuss returns, CAGR, performance, or predictions.
6. If the context is insufficient, reply with exactly: INSUFFICIENT_CONTEXT
"""


def _format_chunk(item: SearchResult, index: int) -> str:
    metadata = item.metadata
    display_value = metadata.get("display_value", "")
    return (
        f"Chunk {index}:\n"
        f"- scheme_id: {item.scheme_id}\n"
        f"- scheme_name: {metadata.get('scheme_name', '')}\n"
        f"- field: {item.field}\n"
        f"- fact: {item.text}\n"
        f"- display_value: {display_value}\n"
        f"- last_updated: {metadata.get('last_updated', '')}\n"
        f"- source_url: {item.source_url}"
    )


def build_messages(query: str, chunks: list[SearchResult]) -> list[dict[str, str]]:
    """Return chat messages for the Groq chat-completions generator."""
    context = "\n\n".join(_format_chunk(item, index + 1) for index, item in enumerate(chunks))
    user_prompt = (
        f"User question:\n{query}\n\n"
        f"Retrieved context:\n{context}\n\n"
        "Write only the answer body (max 3 sentences). Do not include Source or footer lines."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

"""Pydantic schemas for the Phase 5 HTTP API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    index_ready: bool
    index_chunk_count: int
    embedding_model: str | None = None
    generator: str | None = None
    llm_enabled: bool = False
    groq_configured: bool = False


class ExampleQuestion(BaseModel):
    text: str


class BootstrapResponse(BaseModel):
    title: str
    disclaimer: str
    welcome_message: str
    example_questions: list[ExampleQuestion]


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)


class ChatResponse(BaseModel):
    query: str
    answer: str
    answer_body: str | None = None
    source_url: str | None = None
    last_updated: str | None = None
    category: str
    refused: bool
    success: bool
    used_llm: bool = False
    scheme_id: str | None = None
    fields: list[str] = Field(default_factory=list)

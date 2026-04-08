from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class Citation(BaseModel):
    title: str
    doc_type: str
    source_url: str
    section_title: str | None = None
    excerpt: str = Field(..., description="Short excerpt from retrieved chunk")


class CTA(BaseModel):
    type: str
    label: str
    payload: dict[str, Any] | None = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: UUID | None = None
    vehicle_model: str | None = None


class ChatResponse(BaseModel):
    intent: str
    answer: str
    citations: list[Citation]
    confidence: str = "medium"
    cta: CTA | None = None
    needs_handoff: bool = False
    disclaimer: str | None = None
    session_id: UUID | None = None


class FeedbackRequest(BaseModel):
    chat_id: UUID | None = None
    rating: int | None = Field(None, ge=1, le=5)
    comment: str | None = Field(None, max_length=2000)


class HealthResponse(BaseModel):
    status: str
    database: str

"""Pydantic models for Chat API (FANG v2)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ChatQueryRequest(BaseModel):
    jobAppId: int
    hrId: int
    prompt: str
    conversationId: uuid.UUID | None = None
    modelMode: str  # 1 of 7: gemini-flash, gpt-mini, ... auto-lite, auto-pro


class SummarizeRequest(BaseModel):
    """Body is empty — conversationId comes from path."""

    pass


class BranchNewRequest(BaseModel):
    """Body is empty — conversationId comes from path."""

    pass


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ContextWarning(BaseModel):
    type: str = "budget_near_limit"
    usedPercent: int
    options: list[str] = Field(
        default_factory=lambda: [
            "summarize_and_continue",
            "new_conversation_with_summary",
        ]
    )


class ChatQueryResponse(BaseModel):
    conversationId: uuid.UUID
    messageId: int
    response: str
    model: str | None = None
    modelMode: str
    fallbackPath: str | None = None
    latencyMs: int
    topK: int
    contextWarning: ContextWarning | None = None


class ConversationSummary(BaseModel):
    conversationId: uuid.UUID
    jobAppId: int
    hrId: int
    createdAt: str
    lastMessageAt: str
    messageCount: int


class ChatMessage(BaseModel):
    messageId: int
    role: str
    content: str
    model: str | None = None
    createdAt: str


class SummarizeResponse(BaseModel):
    status: str = "done"
    summarizedMessageCount: int


class BranchNewResponse(BaseModel):
    newConversationId: uuid.UUID
    summaryMessageId: int

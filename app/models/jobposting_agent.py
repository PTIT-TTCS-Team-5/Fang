"""Pydantic models for JobPosting Agent API (FANG C3)."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class JobPostingAgentQueryRequest(BaseModel):
    jobPostId: int
    hrId: int
    prompt: str
    conversationId: uuid.UUID | None = None


class RenameConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


# ---------------------------------------------------------------------------
# Helper models
# ---------------------------------------------------------------------------


class ToolCallDetail(BaseModel):
    step: int
    toolName: str
    args: dict[str, Any]
    resultSummary: str
    resultPreview: dict[str, Any] | None = None
    status: str
    latencyMs: int | None = None
    errorMsg: str | None = None
    toolCallId: str | None = None


class WorkingSetInfo(BaseModel):
    jobAppIds: list[int]
    label: str | None = None
    activeFilters: dict[str, Any] | None = None


class AgentWarning(BaseModel):
    type: str
    message: str
    suggestion: str | None = None


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class JobPostingAgentQueryResponse(BaseModel):
    conversationId: uuid.UUID
    messageId: int
    response: str
    model: str
    stepsUsed: int
    toolCalls: list[ToolCallDetail]
    sourceJobAppIds: list[int]
    workingSet: WorkingSetInfo | None = None
    latencyMs: int
    warnings: list[AgentWarning] = Field(default_factory=list)


class JobPostingConversationSummary(BaseModel):
    conversationId: uuid.UUID
    jobPostId: int
    hrId: int
    title: str
    createdAt: str
    lastMessageAt: str
    messageCount: int
    isArchived: bool = False


class JobPostingChatMessage(BaseModel):
    messageId: int
    role: str
    content: str
    toolName: str | None = None
    toolCallId: str | None = None
    model: str | None = None
    latencyMs: int | None = None
    createdAt: str


class RenameConversationResponse(BaseModel):
    conversationId: uuid.UUID
    title: str
    updatedAt: str

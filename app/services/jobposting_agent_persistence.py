"""JobPosting Agent persistence — CRUD cho AIJOBPOSTINGCHATCONVERSATION, AIJOBPOSTINGCHATMESSAGE, AIJOBPOSTINGCHATSTATE, AIJOBPOSTINGTOOLCALLLOG."""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.core.database import acquire_conn
from app.core.logging import logger

# ---------------------------------------------------------------------------
# Conversation CRUD
# ---------------------------------------------------------------------------


async def create_conversation(
    job_post_id: int, hr_id: int, title: str | None = None
) -> uuid.UUID:
    """Tạo hội thoại mới, khởi tạo state rỗng, trả về conversationId."""
    title_val = title if title is not None else "Cuộc trò chuyện mới"
    query_conv = """
        INSERT INTO AIJOBPOSTINGCHATCONVERSATION (jobPostId, hrId, title)
        VALUES ($1, $2, $3)
        RETURNING conversationId;
    """
    query_state = """
        INSERT INTO AIJOBPOSTINGCHATSTATE (conversationId, stateJson)
        VALUES ($1, '{}'::jsonb);
    """
    async with acquire_conn() as conn:
        async with conn.transaction():
            conv_id = await conn.fetchval(query_conv, job_post_id, hr_id, title_val)
            await conn.execute(query_state, conv_id)
            logger.info(
                "Created new JobPosting conversation & state",
                extra={
                    "conversationId": str(conv_id),
                    "jobPostId": job_post_id,
                    "hrId": hr_id,
                    "title": title_val,
                },
            )
            return conv_id


async def get_conversation(conversation_id: uuid.UUID) -> dict[str, Any] | None:
    """Load conversation metadata."""
    query = """
        SELECT conversationId, jobPostId, hrId, title, createdAt, lastMessageAt, isArchived
        FROM AIJOBPOSTINGCHATCONVERSATION
        WHERE conversationId = $1;
    """
    async with acquire_conn() as conn:
        row = await conn.fetchrow(query, conversation_id)
        return dict(row) if row else None


async def list_conversations(hr_id: int, job_post_id: int) -> list[dict[str, Any]]:
    """Danh sách conversation chưa lưu trữ của HR cho 1 JobPosting, kèm messageCount."""
    query = """
        SELECT
            c.conversationId,
            c.jobPostId,
            c.hrId,
            c.title,
            c.createdAt,
            c.lastMessageAt,
            c.isArchived,
            COALESCE(cnt.n, 0) AS messageCount
        FROM AIJOBPOSTINGCHATCONVERSATION c
        LEFT JOIN (
            SELECT conversationId, COUNT(*) AS n
            FROM AIJOBPOSTINGCHATMESSAGE
            WHERE role IN ('user', 'assistant')
            GROUP BY conversationId
        ) cnt ON cnt.conversationId = c.conversationId
        WHERE c.hrId = $1 AND c.jobPostId = $2 AND c.isArchived = FALSE
        ORDER BY c.lastMessageAt DESC;
    """
    async with acquire_conn() as conn:
        rows = await conn.fetch(query, hr_id, job_post_id)
        return [dict(r) for r in rows]


async def rename_conversation(conversation_id: uuid.UUID, title: str) -> None:
    """Đổi tên cuộc trò chuyện và touch lastMessageAt."""
    query = """
        UPDATE AIJOBPOSTINGCHATCONVERSATION
        SET title = $2, lastMessageAt = CURRENT_TIMESTAMP
        WHERE conversationId = $1;
    """
    async with acquire_conn() as conn:
        await conn.execute(query, conversation_id, title)
        logger.info(
            "Renamed conversation",
            extra={"conversationId": str(conversation_id), "title": title},
        )


async def archive_conversation(conversation_id: uuid.UUID) -> None:
    """Lưu trữ (soft delete) cuộc trò chuyện."""
    query = """
        UPDATE AIJOBPOSTINGCHATCONVERSATION
        SET isArchived = TRUE
        WHERE conversationId = $1;
    """
    async with acquire_conn() as conn:
        await conn.execute(query, conversation_id)
        logger.info(
            "Archived conversation", extra={"conversationId": str(conversation_id)}
        )


async def touch_conversation(conversation_id: uuid.UUID) -> None:
    """Cập nhật lastMessageAt."""
    query = """
        UPDATE AIJOBPOSTINGCHATCONVERSATION
        SET lastMessageAt = CURRENT_TIMESTAMP
        WHERE conversationId = $1;
    """
    async with acquire_conn() as conn:
        await conn.execute(query, conversation_id)


# ---------------------------------------------------------------------------
# Message CRUD
# ---------------------------------------------------------------------------


async def insert_message(
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    *,
    tool_name: str | None = None,
    tool_call_id: str | None = None,
    model: str | None = None,
    model_mode: str | None = None,
    latency_ms: int | None = None,
    summarized: bool = False,
) -> int:
    """Thêm message mới vào hội thoại, touch conversation, trả về messageId."""
    query = """
        INSERT INTO AIJOBPOSTINGCHATMESSAGE
            (conversationId, role, content, toolName, toolCallId, model, modelMode, latencyMs, summarized)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING messageId;
    """
    async with acquire_conn() as conn:
        msg_id = await conn.fetchval(
            query,
            conversation_id,
            role,
            content,
            tool_name,
            tool_call_id,
            model,
            model_mode,
            latency_ms,
            summarized,
        )
        await touch_conversation(conversation_id)
        return msg_id


async def get_messages(
    conversation_id: uuid.UUID,
    *,
    include_system: bool = False,
    include_tool: bool = True,
) -> list[dict[str, Any]]:
    """Load messages theo bộ lọc. Ẩn system và/hoặc tool messages nếu được yêu cầu."""
    clauses = ["conversationId = $1"]
    if not include_system:
        clauses.append("role != 'system'")
    if not include_tool:
        clauses.append("role NOT IN ('tool_call', 'tool_result')")

    query = f"""
        SELECT messageId, conversationId, role, content, toolName, toolCallId, model, modelMode, latencyMs, summarized, createdAt
        FROM AIJOBPOSTINGCHATMESSAGE
        WHERE {" AND ".join(clauses)}
        ORDER BY createdAt ASC;
    """
    async with acquire_conn() as conn:
        rows = await conn.fetch(query, conversation_id)
        return [dict(r) for r in rows]


async def get_full_history(conversation_id: uuid.UUID) -> list[dict[str, Any]]:
    """Load toàn bộ messages bao gồm cả system/tool."""
    query = """
        SELECT messageId, conversationId, role, content, toolName, toolCallId, model, modelMode, latencyMs, summarized, createdAt
        FROM AIJOBPOSTINGCHATMESSAGE
        WHERE conversationId = $1
        ORDER BY createdAt ASC;
    """
    async with acquire_conn() as conn:
        rows = await conn.fetch(query, conversation_id)
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# State Management
# ---------------------------------------------------------------------------


async def get_state(conversation_id: uuid.UUID) -> dict[str, Any] | None:
    """Load state Json của cuộc hội thoại."""
    query = """
        SELECT stateJson
        FROM AIJOBPOSTINGCHATSTATE
        WHERE conversationId = $1;
    """
    async with acquire_conn() as conn:
        val = await conn.fetchval(query, conversation_id)
        if val is None:
            return None
        if isinstance(val, str):
            return json.loads(val)
        return val


async def save_state(conversation_id: uuid.UUID, state_json: dict[str, Any]) -> None:
    """UPSERT stateJson cho cuộc hội thoại.

    Note: pass the dict directly — asyncpg's built-in JSONB codec calls
    json.dumps() internally. Pre-serialising with json.dumps() would cause
    double-encoding (the string is stored as a JSON string, not a JSON object).
    """
    query = """
        INSERT INTO AIJOBPOSTINGCHATSTATE (conversationId, stateJson, updatedAt)
        VALUES ($1, $2, CURRENT_TIMESTAMP)
        ON CONFLICT (conversationId) DO UPDATE
        SET stateJson = EXCLUDED.stateJson, updatedAt = CURRENT_TIMESTAMP;
    """
    async with acquire_conn() as conn:
        await conn.execute(query, conversation_id, state_json)


# ---------------------------------------------------------------------------
# Tool Call Logging
# ---------------------------------------------------------------------------


async def insert_tool_call_log(
    conversation_id: uuid.UUID,
    message_id: int | None,
    job_post_id: int,
    hr_id: int,
    tool_name: str,
    tool_input: dict[str, Any] | None,
    tool_output_meta: dict[str, Any] | None,
    status: str = "success",
    latency_ms: int | None = None,
    error_msg: str | None = None,
    tool_id: int | None = None,
) -> int:
    """Ghi log gọi tool vào bảng AIJOBPOSTINGTOOLCALLLOG."""
    # Pass dicts directly — asyncpg JSONB codec handles serialisation.
    # Pre-serialising with json.dumps() would cause double-encoding.
    tool_input_val = tool_input
    tool_output_meta_val = tool_output_meta

    if tool_id is None:
        query_tool = "SELECT toolId FROM AIJOBPOSTINGTOOL WHERE toolName = $1;"
        async with acquire_conn() as conn:
            tool_id = await conn.fetchval(query_tool, tool_name)

    query = """
        INSERT INTO AIJOBPOSTINGTOOLCALLLOG
            (conversationId, messageId, jobPostId, hrId, toolId, toolName, toolInput, toolOutputMeta, status, latencyMs, errorMsg)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING toolCallLogId;
    """
    async with acquire_conn() as conn:
        return await conn.fetchval(
            query,
            conversation_id,
            message_id,
            job_post_id,
            hr_id,
            tool_id,
            tool_name,
            tool_input_val,
            tool_output_meta_val,
            status,
            latency_ms,
            error_msg,
        )

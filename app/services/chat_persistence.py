"""Chat persistence — CRUD cho AICHATCONVERSATION và AICHATMESSAGE.

Cũng bao gồm ghi audit log vào AIQUERYLOG (backward-compatible)."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.database import acquire_conn
from app.core.logging import logger

# ---------------------------------------------------------------------------
# Conversation CRUD
# ---------------------------------------------------------------------------


async def create_conversation(job_app_id: int, hr_id: int) -> uuid.UUID:
    """Tạo hội thoại mới, trả về conversationId."""
    query = """
        INSERT INTO AICHATCONVERSATION (jobAppId, hrId)
        VALUES ($1, $2)
        RETURNING conversationId;
    """
    async with acquire_conn() as conn:
        conv_id = await conn.fetchval(query, job_app_id, hr_id)
        logger.info(
            "Created new conversation",
            extra={
                "conversationId": str(conv_id),
                "jobAppId": job_app_id,
                "hrId": hr_id,
            },
        )
        return conv_id


async def get_conversation(conversation_id: uuid.UUID) -> dict[str, Any] | None:
    """Load conversation metadata."""
    query = """
        SELECT conversationId, jobAppId, hrId, createdAt, lastMessageAt
        FROM AICHATCONVERSATION
        WHERE conversationId = $1;
    """
    async with acquire_conn() as conn:
        row = await conn.fetchrow(query, conversation_id)
        return dict(row) if row else None


async def list_conversations(hr_id: int, job_app_id: int) -> list[dict[str, Any]]:
    """Danh sách conversation của HR cho 1 ứng viên, kèm messageCount."""
    query = """
        SELECT
            c.conversationId,
            c.jobAppId,
            c.hrId,
            c.createdAt,
            c.lastMessageAt,
            COALESCE(cnt.n, 0) AS messageCount
        FROM AICHATCONVERSATION c
        LEFT JOIN (
            SELECT conversationId, COUNT(*) AS n
            FROM AICHATMESSAGE
            WHERE role != 'system'
            GROUP BY conversationId
        ) cnt ON cnt.conversationId = c.conversationId
        WHERE c.hrId = $1 AND c.jobAppId = $2
        ORDER BY c.lastMessageAt DESC;
    """
    async with acquire_conn() as conn:
        rows = await conn.fetch(query, hr_id, job_app_id)
        return [dict(r) for r in rows]


async def touch_conversation(conversation_id: uuid.UUID) -> None:
    """Cập nhật lastMessageAt."""
    query = """
        UPDATE AICHATCONVERSATION
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
    model: str | None = None,
    model_mode: str | None = None,
    top_k: int | None = None,
    latency_ms: int | None = None,
    fallback_path: str | None = None,
) -> int:
    """Thêm message mới, trả về messageId."""
    query = """
        INSERT INTO AICHATMESSAGE
            (conversationId, role, content, model, modelMode, topK, latencyMs, fallbackPath)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING messageId;
    """
    async with acquire_conn() as conn:
        msg_id = await conn.fetchval(
            query,
            conversation_id,
            role,
            content,
            model,
            model_mode,
            top_k,
            latency_ms,
            fallback_path,
        )
        await touch_conversation(conversation_id)
        return msg_id


async def get_messages(
    conversation_id: uuid.UUID,
    *,
    include_system: bool = False,
) -> list[dict[str, Any]]:
    """Load messages. Khi include_system=False (default), ẩn role='system'."""
    if include_system:
        where_clause = "WHERE conversationId = $1"
    else:
        where_clause = "WHERE conversationId = $1 AND role != 'system'"

    query = f"""
        SELECT messageId, role, content, model, createdAt
        FROM AICHATMESSAGE
        {where_clause}
        ORDER BY createdAt ASC;
    """
    async with acquire_conn() as conn:
        rows = await conn.fetch(query, conversation_id)
        return [dict(r) for r in rows]


async def get_full_history(conversation_id: uuid.UUID) -> list[dict[str, Any]]:
    """Load toàn bộ messages bao gồm cả system (cho token counting)."""
    query = """
        SELECT messageId, role, content, model, summarized, createdAt
        FROM AICHATMESSAGE
        WHERE conversationId = $1
        ORDER BY createdAt ASC;
    """
    async with acquire_conn() as conn:
        rows = await conn.fetch(query, conversation_id)
        return [dict(r) for r in rows]


async def mark_messages_summarized(
    conversation_id: uuid.UUID,
    up_to_message_id: int,
) -> int:
    """Đánh dấu messages cũ đã được include trong summary."""
    query = """
        UPDATE AICHATMESSAGE
        SET summarized = TRUE
        WHERE conversationId = $1
          AND messageId <= $2
          AND role != 'system'
          AND summarized = FALSE;
    """
    async with acquire_conn() as conn:
        result = await conn.execute(query, conversation_id, up_to_message_id)
        # asyncpg returns "UPDATE N"
        count = int(result.split()[-1]) if result else 0
        return count


# ---------------------------------------------------------------------------
# Audit log (AIQUERYLOG — backward-compatible)
# ---------------------------------------------------------------------------


async def insert_query_log(
    job_app_id: int,
    hr_id: int,
    prompt: str,
    response: str,
    top_k: int,
    latency_ms: int,
    *,
    model: str | None = None,
    model_mode: str | None = None,
    fallback_path: str | None = None,
) -> int:
    """Ghi audit log vào AIQUERYLOG. Backward-compatible với v1."""
    query = """
        INSERT INTO AIQUERYLOG
            (jobAppId, hrId, prompt, response, topK, latencyMs, model, modelMode, fallbackPath)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING queryId;
    """
    async with acquire_conn() as conn:
        return await conn.fetchval(
            query,
            job_app_id,
            hr_id,
            prompt,
            response,
            top_k,
            latency_ms,
            model,
            model_mode,
            fallback_path,
        )

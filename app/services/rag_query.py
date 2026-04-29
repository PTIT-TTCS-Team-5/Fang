"""RAG Query Service — pipeline xử lý 1 prompt từ HR.

Ghép context đa nguồn (CV chunks + JobPosting + Candidate + ATS),
embed prompt, vector search, build messages, invoke generation,
persist results.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.config import settings
from app.core.database import acquire_conn
from app.core.logging import logger
from app.services.chat_persistence import (
    create_conversation,
    get_conversation,
    get_full_history,
    insert_message,
    insert_query_log,
)
from app.services.embedding import embed_chunks
from app.services.rag_model_adapters import get_model_budget
from app.services.rag_orchestrator import (
    invoke_generation,
)

# ---------------------------------------------------------------------------
# Token budget heuristic (reuse từ chunking.py)
# ---------------------------------------------------------------------------

CHARS_PER_TOKEN = 3.5


def _approx_tokens(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)


# ---------------------------------------------------------------------------
# Vector search
# ---------------------------------------------------------------------------


async def _vector_search(
    prompt_embedding: list[float],
    job_app_id: int,
    top_k: int,
) -> list[dict[str, Any]]:
    """Cosine distance search trên AIDOCUMENTCHUNK."""
    vec_type = settings.embedding_vector_type  # 'halfvec' or 'vector'
    query = f"""
        SELECT chunkId, content, metadata,
               embedding <=> $1::{vec_type} AS distance
        FROM AIDOCUMENTCHUNK
        WHERE jobAppId = $2
        ORDER BY embedding <=> $1::{vec_type}
        LIMIT $3;
    """
    vec_literal = "[" + ",".join(str(v) for v in prompt_embedding) + "]"
    async with acquire_conn() as conn:
        rows = await conn.fetch(query, vec_literal, job_app_id, top_k)
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Context đa nguồn
# ---------------------------------------------------------------------------


async def _fetch_job_posting(job_app_id: int) -> dict[str, Any] | None:
    """Lấy thông tin JobPosting liên quan đến application."""
    query = """
        SELECT jp.title, jp.description
        FROM JOBPOSTING jp
        INNER JOIN JOBAPPLICATION ja ON ja.jobPostId = jp.jobPostId
        WHERE ja.jobAppId = $1;
    """
    async with acquire_conn() as conn:
        row = await conn.fetchrow(query, job_app_id)
        return dict(row) if row else None


async def _fetch_candidate_profile(job_app_id: int) -> dict[str, Any] | None:
    """Lấy thông tin Candidate profile."""
    query = """
        SELECT u.fName || ' ' || u.lName AS fullname, u.email, u.phone, c.bio, c.expyears, p.provName AS location
        FROM CANDIDATE c
        INNER JOIN "user" u ON c.userId = u.userId
        LEFT JOIN PROVINCE p ON u.provId = p.provId
        INNER JOIN JOBAPPLICATION ja ON ja.candidateId = c.userId
        WHERE ja.jobAppId = $1;
    """
    async with acquire_conn() as conn:
        row = await conn.fetchrow(query, job_app_id)
        return dict(row) if row else None


async def _fetch_ats_history(job_app_id: int) -> list[dict[str, Any]]:
    """Lấy lịch sử ATS (interviews, offers, feedback) nếu có."""
    records: list[dict[str, Any]] = []

    interview_query = """
        SELECT i.startAt AS interviewdate, i."mode" AS interviewtype, f.cmt AS notes, f.score
        FROM INTERVIEW i
        LEFT JOIN INTERVIEWFEEDBACK f ON i.intervId = f.intervId
        WHERE i.jobAppId = $1
        ORDER BY i.startAt;
    """
    async with acquire_conn() as conn:
        rows = await conn.fetch(interview_query, job_app_id)
        for r in rows:
            records.append({"type": "interview", **dict(r)})

    return records


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------


def _build_system_prompt(
    chunks: list[dict[str, Any]],
    job_posting: dict[str, Any] | None,
    candidate: dict[str, Any] | None,
    ats_history: list[dict[str, Any]],
) -> str:
    """Ghép context đa nguồn thành system prompt."""
    parts: list[str] = []

    parts.append(
        "Bạn là trợ lý AI chuyên về đánh giá nhân sự (HR Co-pilot) của hệ thống miCareer.\n"
        "Nhiệm vụ: giúp HR đánh giá ứng viên khách quan và chuyên nghiệp."
    )

    # Job Posting
    if job_posting:
        jp_section = "\n[VỊ TRÍ TUYỂN DỤNG]"
        if job_posting.get("title"):
            jp_section += f"\nVị trí: {job_posting['title']}"
        if job_posting.get("description"):
            jp_section += f"\nMô tả: {job_posting['description']}"
        if job_posting.get("requirements"):
            jp_section += f"\nYêu cầu: {job_posting['requirements']}"
        parts.append(jp_section)

    # Candidate profile
    if candidate:
        c_section = "\n[HỒ SƠ ỨNG VIÊN]"
        if candidate.get("fullname"):
            c_section += f"\nHọ tên: {candidate['fullname']}"
        if candidate.get("expyears"):
            c_section += f"\nKinh nghiệm: {candidate['expyears']} năm"
        if candidate.get("location"):
            c_section += f"\nKhu vực: {candidate['location']}"
        if candidate.get("bio"):
            c_section += f"\nBio: {candidate['bio']}"
        parts.append(c_section)

    # CV Chunks
    if chunks:
        chunk_section = "\n[NỘI DUNG CV — Top K kết quả phù hợp nhất với câu hỏi]"
        for i, chunk in enumerate(chunks, 1):
            content = chunk.get("content", "")
            chunk_section += f"\n[Chunk {i}]: {content}"
        parts.append(chunk_section)

    # ATS History
    if ats_history:
        ats_section = "\n[LỊCH SỬ TUYỂN DỤNG]"
        for record in ats_history:
            rec_type = record.get("type", "unknown")
            if rec_type == "interview":
                date = record.get("interviewdate", "N/A")
                score = record.get("score", "N/A")
                notes = record.get("notes", "")
                ats_section += (
                    f"\n- Phỏng vấn {date} — Điểm: {score} — Nhận xét: {notes}"
                )
        parts.append(ats_section)

    # Instructions
    parts.append(
        "\n[HƯỚNG DẪN TRẢ LỜI]\n"
        "- Trả lời bằng Tiếng Việt. Thuật ngữ kỹ thuật giữ nguyên tiếng Anh.\n"
        "- Chỉ dựa vào thông tin được cung cấp ở trên. Không suy diễn ngoài dữ liệu.\n"
        "- Nếu không có đủ thông tin → nêu rõ điểm còn thiếu.\n"
        "- Trích dẫn nguồn dữ liệu khi có thể.\n"
        "- Format câu trả lời có cấu trúc (heading, bullet point) khi cần."
    )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Context window budget check
# ---------------------------------------------------------------------------


def _check_context_budget(
    history_messages: list[dict[str, Any]],
    model_mode: str,
) -> tuple[list[dict[str, str]], dict[str, Any] | None]:
    """Kiểm tra token budget cho history. Trả về:
    - messages đã build cho LLM
    - contextWarning dict nếu > threshold, None nếu OK
    """
    budget = get_model_budget(model_mode)
    threshold = settings.context_budget_warning_threshold

    llm_messages: list[dict[str, str]] = []
    total_tokens = 0

    for msg in history_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        tokens = _approx_tokens(content)
        total_tokens += tokens
        llm_messages.append({"role": role, "content": content})

    used_percent = int((total_tokens / budget) * 100) if budget > 0 else 0
    context_warning = None

    if used_percent >= int(threshold * 100):
        context_warning = {
            "type": "budget_near_limit",
            "usedPercent": used_percent,
            "options": [
                "summarize_and_continue",
                "new_conversation_with_summary",
            ],
        }
        logger.info(
            "Context budget warning triggered",
            extra={
                "usedPercent": used_percent,
                "totalTokens": total_tokens,
                "budget": budget,
                "modelMode": model_mode,
            },
        )

    return llm_messages, context_warning


# ---------------------------------------------------------------------------
# Public API — process_chat_query
# ---------------------------------------------------------------------------


async def process_chat_query(
    job_app_id: int,
    hr_id: int,
    prompt: str,
    conversation_id: uuid.UUID | None,
    model_mode: str,
) -> dict[str, Any]:
    """Pipeline xử lý 1 prompt. Trả về dict tương ứng ChatQueryResponse."""
    top_k = settings.rag_top_k_chunks

    # --- 1. Validate ingestion đã SUCCESS ---
    async with acquire_conn() as conn:
        row = await conn.fetchrow(
            """
            SELECT stat FROM AIINDEXJOB
            WHERE jobAppId = $1
            ORDER BY createdAt DESC LIMIT 1;
            """,
            job_app_id,
        )
    if not row or row["stat"] != "SUCCESS":
        current_status = row["stat"] if row else "NOT_FOUND"
        raise ValueError(
            f"Ingestion chưa hoàn thành cho jobAppId={job_app_id}. "
            f"Trạng thái hiện tại: {current_status}"
        )

    # --- 2. Load or create conversation ---
    if conversation_id:
        conv = await get_conversation(conversation_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found.")
    else:
        conversation_id = await create_conversation(job_app_id, hr_id)

    # --- 3. Persist user message ---
    user_msg_id = await insert_message(
        conversation_id, "user", prompt, model_mode=model_mode
    )

    # --- 4. Embed prompt ---
    prompt_vectors = await embed_chunks([prompt])
    prompt_embedding = prompt_vectors[0] if prompt_vectors else []

    # --- 5. Vector search ---
    chunks = await _vector_search(prompt_embedding, job_app_id, top_k)

    # --- 6. Fetch context đa nguồn ---
    job_posting = await _fetch_job_posting(job_app_id)
    candidate = await _fetch_candidate_profile(job_app_id)
    ats_history = await _fetch_ats_history(job_app_id)

    # --- 7. Build system prompt ---
    system_prompt = _build_system_prompt(chunks, job_posting, candidate, ats_history)

    # --- 8. Load history + check budget ---
    full_history = await get_full_history(conversation_id)
    history_for_budget = [m for m in full_history if m["messageid"] != user_msg_id]
    history_llm_messages, context_warning = _check_context_budget(
        history_for_budget, model_mode
    )

    # --- 9. Build LLM messages ---
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
    ]
    messages.extend(history_llm_messages)
    messages.append({"role": "user", "content": prompt})

    # --- 10. Invoke LLM ---
    trace = await invoke_generation(messages, model_mode)
    response_text = trace.response
    model_used = trace.model
    fallback_path = trace.fallback_path
    latency_ms = trace.latency_ms

    # --- 11. Persist assistant message + audit log ---
    assistant_msg_id = await insert_message(
        conversation_id,
        "assistant",
        response_text,
        model=model_used,
        model_mode=model_mode,
        top_k=top_k,
        latency_ms=latency_ms,
        fallback_path=fallback_path,
    )

    await insert_query_log(
        job_app_id=job_app_id,
        hr_id=hr_id,
        prompt=prompt,
        response=response_text,
        top_k=top_k,
        latency_ms=latency_ms,
        model=model_used,
        model_mode=model_mode,
        fallback_path=fallback_path,
    )

    # --- 12. Return result ---
    return {
        "conversationId": conversation_id,
        "messageId": assistant_msg_id,
        "response": response_text,
        "model": model_used,
        "modelMode": model_mode,
        "fallbackPath": fallback_path,
        "latencyMs": latency_ms,
        "topK": top_k,
        "contextWarning": context_warning,
    }

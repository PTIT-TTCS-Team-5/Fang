"""Chat API routes (FANG v2).

Endpoints:
- POST   /chat/query                            → RAG query
- GET    /chat/conversations                     → list conversations
- GET    /chat/conversations/{id}/messages        → message history
- POST   /chat/conversations/{id}/summarize       → tóm tắt & tiếp tục
- POST   /chat/conversations/{id}/branch-new      → hội thoại mới từ summary
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from app.core.logging import logger
from app.models.chat import (
    BranchNewResponse,
    ChatMessage,
    ChatQueryRequest,
    ChatQueryResponse,
    ContextWarning,
    ConversationSummary,
    SummarizeResponse,
)
from app.services.chat_persistence import (
    create_conversation,
    get_full_history,
    get_messages,
    insert_message,
    list_conversations,
    mark_messages_summarized,
)
from app.services.rag_model_adapters import VALID_MODEL_MODES
from app.services.rag_orchestrator import GenerationError, InvalidModelModeError
from app.services.rag_query import process_chat_query

router = APIRouter(prefix="/chat", tags=["Chat"])


# ---------------------------------------------------------------------------
# POST /chat/query
# ---------------------------------------------------------------------------


@router.post("/query", response_model=ChatQueryResponse)
async def chat_query(request: ChatQueryRequest):
    """Nhận prompt từ HR, FANG xử lý toàn bộ pipeline RAG."""
    if request.modelMode not in VALID_MODEL_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"modelMode='{request.modelMode}' không hợp lệ. "
                f"Hợp lệ: {sorted(VALID_MODEL_MODES)}"
            ),
        )

    try:
        result = await process_chat_query(
            job_app_id=request.jobAppId,
            hr_id=request.hrId,
            prompt=request.prompt,
            conversation_id=request.conversationId,
            model_mode=request.modelMode,
        )

        # Build response
        ctx_warning = None
        if result.get("contextWarning"):
            ctx_warning = ContextWarning(**result["contextWarning"])

        return ChatQueryResponse(
            conversationId=result["conversationId"],
            messageId=result["messageId"],
            response=result["response"],
            model=result.get("model"),
            modelMode=result["modelMode"],
            fallbackPath=result.get("fallbackPath"),
            latencyMs=result["latencyMs"],
            topK=result["topK"],
            contextWarning=ctx_warning,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except InvalidModelModeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except GenerationError as exc:
        logger.error("All generation tiers failed", extra={"error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Generation failed: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error in chat_query")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred.",
        ) from exc


# ---------------------------------------------------------------------------
# GET /chat/conversations?hrId=&jobAppId=
# ---------------------------------------------------------------------------


@router.get("/conversations", response_model=list[ConversationSummary])
async def get_conversations(hrId: int, jobAppId: int):
    """Danh sách conversation của HR cho 1 ứng viên."""
    rows = await list_conversations(hrId, jobAppId)
    return [
        ConversationSummary(
            conversationId=r["conversationid"],
            jobAppId=r["jobappid"],
            hrId=r["hrid"],
            createdAt=str(r["createdat"]),
            lastMessageAt=str(r["lastmessageat"]),
            messageCount=r["messagecount"],
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# GET /chat/conversations/{id}/messages
# ---------------------------------------------------------------------------


@router.get(
    "/conversations/{conversationId}/messages",
    response_model=list[ChatMessage],
)
async def get_conversation_messages(conversationId: uuid.UUID):
    """Lịch sử message (loại trừ role='system')."""
    rows = await get_messages(conversationId, include_system=False)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No messages found for conversation {conversationId}",
        )
    return [
        ChatMessage(
            messageId=r["messageid"],
            role=r["role"],
            content=r["content"],
            model=r.get("model"),
            createdAt=str(r["createdat"]),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# POST /chat/conversations/{id}/summarize
# ---------------------------------------------------------------------------


@router.post(
    "/conversations/{conversationId}/summarize",
    response_model=SummarizeResponse,
)
async def summarize_conversation(conversationId: uuid.UUID):
    """HR chọn 'Tóm tắt & tiếp tục'. Dùng LLM Lite tóm tắt phần cũ."""
    from app.services.rag_orchestrator import invoke_generation

    # Load full history
    history = await get_full_history(conversationId)
    if not history:
        raise HTTPException(status_code=404, detail="Conversation not found or empty.")

    # Filter unsummarized messages
    unsummarized = [
        m for m in history if not m.get("summarized") and m["role"] != "system"
    ]
    if len(unsummarized) < 4:
        raise HTTPException(
            status_code=400,
            detail="Not enough messages to summarize (minimum 4).",
        )

    # Build summarization prompt
    conversation_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in unsummarized
    )
    messages = [
        {
            "role": "system",
            "content": (
                "Tóm tắt cuộc hội thoại HR-AI dưới đây thành bản rút gọn, "
                "giữ lại các điểm quan trọng về ứng viên, đánh giá, và kết luận. "
                "Viết bằng Tiếng Việt, ngắn gọn, súc tích."
            ),
        },
        {"role": "user", "content": conversation_text},
    ]

    # Invoke Lite model cho tóm tắt (rẻ, nhanh)
    from app.core.config import settings

    summarization_model = settings.context_summarization_model
    trace = await invoke_generation(messages, summarization_model)

    # Persist summary as system message
    await insert_message(conversationId, "system", trace.response)

    # Mark old messages as summarized
    last_msg_id = unsummarized[-1]["messageid"]
    count = await mark_messages_summarized(conversationId, last_msg_id)

    logger.info(
        "Conversation summarized",
        extra={
            "conversationId": str(conversationId),
            "summarizedCount": count,
            "summaryModel": trace.model,
        },
    )

    return SummarizeResponse(status="done", summarizedMessageCount=count)


# ---------------------------------------------------------------------------
# POST /chat/conversations/{id}/branch-new
# ---------------------------------------------------------------------------


@router.post(
    "/conversations/{conversationId}/branch-new",
    response_model=BranchNewResponse,
)
async def branch_new_conversation(conversationId: uuid.UUID):
    """HR chọn 'Sang hội thoại mới' — tạo conversation mới kèm summary."""
    # Load old conversation metadata
    from app.services.chat_persistence import get_conversation
    from app.services.rag_orchestrator import invoke_generation

    old_conv = await get_conversation(conversationId)
    if not old_conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    # Load history và summarize
    history = await get_full_history(conversationId)
    unsummarized = [
        m for m in history if not m.get("summarized") and m["role"] != "system"
    ]

    if not unsummarized:
        raise HTTPException(status_code=400, detail="No messages to summarize.")

    conversation_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in unsummarized
    )
    messages = [
        {
            "role": "system",
            "content": (
                "Tóm tắt cuộc hội thoại HR-AI dưới đây thành bản rút gọn để mang sang "
                "hội thoại mới. Giữ lại các điểm quan trọng và ngữ cảnh chính. "
                "Viết bằng Tiếng Việt."
            ),
        },
        {"role": "user", "content": conversation_text},
    ]

    from app.core.config import settings

    summarization_model = settings.context_summarization_model
    trace = await invoke_generation(messages, summarization_model)

    # Create new conversation
    new_conv_id = await create_conversation(old_conv["jobappid"], old_conv["hrid"])

    # Inject summary as first system message
    summary_msg_id = await insert_message(
        new_conv_id,
        "system",
        f"[Tóm tắt từ hội thoại trước]\n{trace.response}",
    )

    logger.info(
        "Branched new conversation from old",
        extra={
            "oldConversationId": str(conversationId),
            "newConversationId": str(new_conv_id),
            "summaryModel": trace.model,
        },
    )

    return BranchNewResponse(
        newConversationId=new_conv_id,
        summaryMessageId=summary_msg_id,
    )

"""FastAPI routes for JobPosting Agent (FANG C3).

Endpoints:
- POST   /query                                       → Agent query turn
- GET    /conversations                               → List conversations for HR & Job
- GET    /conversations/{conversationId}/messages     → Message history
- PATCH  /conversations/{conversationId}              → Rename conversation
- DELETE /conversations/{conversationId}              → Archive conversation
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.core.logging import logger
from app.models.jobposting_agent import (
    JobPostingAgentQueryRequest,
    JobPostingAgentQueryResponse,
    JobPostingChatMessage,
    JobPostingConversationSummary,
    RenameConversationRequest,
    RenameConversationResponse,
)
from app.services.jobposting_agent_persistence import (
    archive_conversation,
    get_conversation,
    get_messages,
    list_conversations,
    rename_conversation,
)
from app.services.jobposting_agent_query import process_jobposting_agent_query

router = APIRouter()

# ---------------------------------------------------------------------------
# POST /query
# ---------------------------------------------------------------------------


@router.post(
    "/query",
    response_model=JobPostingAgentQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Gửi câu hỏi tới JobPosting Agent",
)
async def query_agent(request: JobPostingAgentQueryRequest):
    """Gửi tin nhắn của HR cho một tin tuyển dụng cụ thể để Agent xử lý."""
    try:
        response_data = await process_jobposting_agent_query(request)
        return response_data
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except BufferError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=str(exc),
        ) from exc
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ AI chưa sẵn sàng (Agent Runtime chưa được cài đặt).",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error in query_agent route")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi hệ thống không mong đợi.",
        ) from exc


# ---------------------------------------------------------------------------
# GET /conversations
# ---------------------------------------------------------------------------


@router.get(
    "/conversations",
    response_model=list[JobPostingConversationSummary],
    summary="Lấy danh sách các cuộc trò chuyện chưa lưu trữ",
)
async def get_conversations(
    jobPostId: int = Query(..., description="ID của tin tuyển dụng"),
    hrId: int = Query(..., description="ID của tài khoản HR"),
):
    """Trả về danh sách các cuộc hội thoại đang hoạt động (không bị archive) của HR với tin tuyển dụng này."""
    try:
        # Validate that the HR and JobPost ownership is valid (simplest check matches company validation if needed,
        # but list_conversations will return empty if mismatch or none found).
        rows = await list_conversations(hrId, jobPostId)
        return [
            JobPostingConversationSummary(
                conversationId=r["conversationid"],
                jobPostId=r["jobpostid"],
                hrId=r["hrid"],
                title=r["title"],
                createdAt=str(r["createdat"]),
                lastMessageAt=str(r["lastmessageat"]),
                messageCount=r["messagecount"],
                isArchived=r["isarchived"],
            )
            for r in rows
        ]
    except Exception as exc:
        logger.exception("Error listing conversations")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể tải danh sách cuộc trò chuyện.",
        ) from exc


# ---------------------------------------------------------------------------
# GET /conversations/{conversationId}/messages
# ---------------------------------------------------------------------------


@router.get(
    "/conversations/{conversationId}/messages",
    response_model=list[JobPostingChatMessage],
    summary="Lấy lịch sử tin nhắn của cuộc trò chuyện",
)
async def get_conversation_messages(
    conversationId: uuid.UUID,
    includeToolMessages: bool = Query(True, description="Bao gồm tin nhắn gọi tool"),
    includeSystem: bool = Query(False, description="Bao gồm tin nhắn hệ thống"),
):
    """Trả về toàn bộ tin nhắn thuộc hội thoại theo thứ tự thời gian tăng dần."""
    try:
        # Kiểm tra sự tồn tại của conversation trước
        conv = await get_conversation(conversationId)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cuộc trò chuyện không tồn tại.",
            )

        rows = await get_messages(
            conversationId,
            include_system=includeSystem,
            include_tool=includeToolMessages,
        )
        # Giống routes_chat, nếu không tìm thấy tin nhắn nào thì raise 404
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không có tin nhắn nào trong cuộc trò chuyện này.",
            )

        return [
            JobPostingChatMessage(
                messageId=r["messageid"],
                role=r["role"],
                content=r["content"],
                toolName=r.get("toolname"),
                toolCallId=r.get("toolcallid"),
                model=r.get("model"),
                latencyMs=r.get("latencyms"),
                createdAt=str(r["createdat"]),
            )
            for r in rows
        ]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error getting conversation messages")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể tải lịch sử tin nhắn.",
        ) from exc


# ---------------------------------------------------------------------------
# PATCH /conversations/{conversationId}
# ---------------------------------------------------------------------------


@router.patch(
    "/conversations/{conversationId}",
    response_model=RenameConversationResponse,
    summary="Đổi tên cuộc trò chuyện",
)
async def rename_chat_conversation(
    conversationId: uuid.UUID,
    payload: RenameConversationRequest,
    hrId: int | None = Query(None, description="Tùy chọn kiểm tra sở hữu của HR"),
):
    """Cập nhật tiêu đề cuộc trò chuyện (tối đa 200 ký tự và không để trống)."""
    try:
        conv = await get_conversation(conversationId)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cuộc trò chuyện không tồn tại.",
            )

        if hrId is not None and conv["hrid"] != hrId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không có quyền truy cập cuộc trò chuyện này.",
            )

        await rename_conversation(conversationId, payload.title)

        # Load lại để lấy thời gian cập nhật chính xác
        updated_conv = await get_conversation(conversationId)
        return RenameConversationResponse(
            conversationId=conversationId,
            title=payload.title,
            updatedAt=str(updated_conv["lastmessageat"]),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error renaming conversation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể đổi tên cuộc trò chuyện.",
        ) from exc


# ---------------------------------------------------------------------------
# DELETE /conversations/{conversationId}
# ---------------------------------------------------------------------------


@router.delete(
    "/conversations/{conversationId}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Lưu trữ cuộc trò chuyện",
)
async def delete_conversation(
    conversationId: uuid.UUID,
    hrId: int = Query(..., description="ID của tài khoản HR sở hữu cuộc hội thoại"),
):
    """Lưu trữ (soft-delete) một cuộc trò chuyện. Trả về 204 No Content."""
    try:
        conv = await get_conversation(conversationId)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cuộc trò chuyện không tồn tại.",
            )

        if conv["hrid"] != hrId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không có quyền truy cập cuộc trò chuyện này.",
            )

        await archive_conversation(conversationId)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error archiving conversation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể lưu trữ cuộc trò chuyện.",
        ) from exc

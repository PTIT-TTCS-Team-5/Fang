"""JobPosting Agent Query Orchestration Shell (FANG C3)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.core.database import acquire_conn
from app.models.jobposting_agent import (
    AgentWarning,
    JobPostingAgentQueryRequest,
    JobPostingAgentQueryResponse,
    ToolCallDetail,
    WorkingSetInfo,
)
from app.services.jobposting_agent_persistence import (
    create_conversation,
    get_conversation,
    get_full_history,
    get_state,
    insert_message,
    insert_tool_call_log,
    save_state,
)
from app.services.jobposting_agent_runtime import run_agent_turn


async def run_agent_turn_boundary(
    conversation_id: uuid.UUID,
    prompt: str,
    job_post_id: int,
    hr_id: int,
) -> dict[str, Any]:
    """Stable integration boundary for the concrete WS3 runtime."""
    state = await get_state(conversation_id)
    history = await get_full_history(conversation_id)
    return await run_agent_turn(
        conversation_id=conversation_id,
        job_post_id=job_post_id,
        hr_id=hr_id,
        prompt=prompt,
        state=state,
        history=history,
    )


async def process_jobposting_agent_query(
    request: JobPostingAgentQueryRequest,
) -> JobPostingAgentQueryResponse:
    """Điều phối toàn bộ luồng xử lý query của JobPosting Agent:

    1. Kiểm tra validation của prompt (độ dài, không rỗng).
    2. Xác thực jobPostId tồn tại.
    3. Xác thực hrId tồn tại và thuộc cùng Company sở hữu jobPostId.
    4. Khởi tạo hội thoại mới (nếu conversationId = None) hoặc tải hội thoại hiện tại.
    5. Lưu tin nhắn của user.
    6. Gọi runtime xử lý logic agent (Gemini native tool calling).
    7. Lưu tin nhắn của trợ lý, các thông tin gọi tool và cập nhật state mới nhất.
    """
    # 1. Validate prompt
    prompt_stripped = request.prompt.strip() if request.prompt else ""
    if not prompt_stripped:
        raise ValueError("Prompt không được để trống")
    if len(prompt_stripped) > 2000:
        raise ValueError("Prompt quá dài (tối đa 2000 ký tự)")

    # 2 & 3. Validate Job & HR Access
    async with acquire_conn() as conn:
        # Check HR exists
        hr_row = await conn.fetchrow(
            "SELECT compId FROM HR WHERE userId = $1;", request.hrId
        )
        if not hr_row:
            raise PermissionError("Tài khoản HR không tồn tại hoặc không hợp lệ")
        hr_comp_id = hr_row["compid"]

        # Check Job exists
        job_row = await conn.fetchrow(
            "SELECT compId FROM JOBPOSTING WHERE jobPostId = $1;", request.jobPostId
        )
        if not job_row:
            raise LookupError("Tin tuyển dụng không tồn tại")
        job_comp_id = job_row["compid"]

        # Company match check
        if job_comp_id != hr_comp_id:
            raise PermissionError("HR không có quyền truy cập vào tin tuyển dụng này")

    # 4. Load/Create Conversation
    conversation_id = request.conversationId
    if conversation_id is None:
        # Tự động tạo tiêu đề cuộc trò chuyện bằng cách cắt prompt đầu tiên
        title = prompt_stripped[:100] if len(prompt_stripped) > 100 else prompt_stripped
        conversation_id = await create_conversation(
            request.jobPostId, request.hrId, title
        )
    else:
        conv = await get_conversation(conversation_id)
        if not conv:
            raise LookupError("Cuộc trò chuyện không tồn tại")
        if conv["jobpostid"] != request.jobPostId or conv["hrid"] != request.hrId:
            raise PermissionError(
                "Cuộc trò chuyện không thuộc về tin tuyển dụng hoặc HR này"
            )
        if conv["isarchived"]:
            raise BufferError("Cuộc trò chuyện đã bị lưu trữ")

    # 5. Insert User Message
    await insert_message(conversation_id, "user", request.prompt)

    # 6. Call Runtime Turn
    # runtime_result phải trả về dạng:
    # {
    #     "response": str,
    #     "model": str,
    #     "steps_used": int,
    #     "tool_calls": list[dict],
    #     "source_job_app_ids": list[int],
    #     "working_set": dict | None,
    #     "latency_ms": int,
    #     "warnings": list[dict],
    #     "state": dict | None
    # }
    runtime_result = await run_agent_turn_boundary(
        conversation_id, request.prompt, request.jobPostId, request.hrId
    )

    # 7. Persist Assistant Response
    assistant_msg_id = await insert_message(
        conversation_id,
        "assistant",
        runtime_result["response"],
        model=runtime_result.get("model"),
        latency_ms=runtime_result.get("latency_ms"),
    )

    # Persist Tool messages & logs
    tool_calls_data = runtime_result.get("tool_calls", [])
    for tc in tool_calls_data:
        tc_name = tc.get("toolName")
        tc_args = tc.get("args") or {}
        tc_summary = tc.get("resultSummary") or ""
        tc_status = tc.get("status") or "success"
        tc_latency = tc.get("latencyMs")
        tc_error = tc.get("errorMsg")

        # Link tool call and result via a unique toolCallId
        tc_id = tc.get("toolCallId") or f"call_{uuid.uuid4().hex[:12]}"

        # Save tool_call message
        call_msg_id = await insert_message(
            conversation_id,
            "tool_call",
            json.dumps(tc_args),
            tool_name=tc_name,
            tool_call_id=tc_id,
        )

        # Save tool_result message
        result_meta = {"summary": tc_summary, "status": tc_status}
        if tc_error:
            result_meta["error"] = tc_error

        await insert_message(
            conversation_id,
            "tool_result",
            json.dumps(result_meta),
            tool_name=tc_name,
            tool_call_id=tc_id,
        )

        # Save tool call log to AIJOBPOSTINGTOOLCALLLOG
        await insert_tool_call_log(
            conversation_id=conversation_id,
            message_id=call_msg_id,
            job_post_id=request.jobPostId,
            hr_id=request.hrId,
            tool_name=tc_name,
            tool_input=tc_args,
            tool_output_meta={"summary": tc_summary},
            status=tc_status,
            latency_ms=tc_latency,
            error_msg=tc_error,
        )

    # Update Conversation State
    if "state" in runtime_result and runtime_result["state"] is not None:
        await save_state(conversation_id, runtime_result["state"])

    # Parse Warnings
    warnings = []
    for w in runtime_result.get("warnings", []):
        warnings.append(
            AgentWarning(
                type=w.get("type"),
                message=w.get("message"),
                suggestion=w.get("suggestion"),
            )
        )

    # Parse Working Set
    working_set = None
    ws_data = runtime_result.get("working_set")
    if ws_data:
        working_set = WorkingSetInfo(
            jobAppIds=ws_data.get("jobAppIds", []),
            label=ws_data.get("label"),
            activeFilters=ws_data.get("activeFilters"),
        )

    # Parse Tool Calls Details for Response
    tool_calls_details = []
    for tc in tool_calls_data:
        tool_calls_details.append(
            ToolCallDetail(
                step=tc.get("step", 1),
                toolName=tc.get("toolName"),
                args=tc.get("args") or {},
                resultSummary=tc.get("resultSummary") or "",
                status=tc.get("status") or "success",
                latencyMs=tc.get("latencyMs"),
                errorMsg=tc.get("errorMsg"),
                toolCallId=tc.get("toolCallId"),
            )
        )

    return JobPostingAgentQueryResponse(
        conversationId=conversation_id,
        messageId=assistant_msg_id,
        response=runtime_result["response"],
        model=runtime_result.get("model", "gemini-3.1-flash-lite"),
        stepsUsed=runtime_result.get("steps_used", 0),
        toolCalls=tool_calls_details,
        sourceJobAppIds=runtime_result.get("source_job_app_ids", []),
        workingSet=working_set,
        latencyMs=runtime_result.get("latency_ms", 0),
        warnings=warnings,
    )

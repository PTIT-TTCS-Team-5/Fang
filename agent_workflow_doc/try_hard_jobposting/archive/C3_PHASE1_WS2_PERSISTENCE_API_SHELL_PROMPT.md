# C3 Phase 1 WS2 Persistence/API Shell Prompt

Bạn là **WS2 Persistence/API Shell Implementation Agent** cho FANG JobPosting Agent C3.1.

Model khuyến nghị: **GPT-5.4/GPT-5.5 high** hoặc **Claude Sonnet 4.6**.  
Nếu dùng Gemini 3.5 Flash, chỉ dùng khi bạn giữ scope thật chặt và không tự thiết kế lại runtime. Reasoning khuyến nghị: **medium/high**.

## 0. Workspace / branch

Bạn nên chạy trong worktree riêng, ví dụ:

```powershell
git worktree add ..\Fang-c3-api -b codex/c3-api-persistence
cd ..\Fang-c3-api
```

Nếu user đã tạo worktree/branch khác, dùng đúng workspace hiện tại và ghi rõ branch trong report.

## 1. Truth sources

Đọc trước khi code:

1. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_OFFICIAL_IMPLEMENTATION_PLAN.md`
2. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_PHASE0_BASELINE_REPORT.md`
3. Khi cần chi tiết persistence/API:
   - `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSB_CONVERSATION_MEMORY_SCHEMA.md`
   - `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSD_API_UI_CONTRACT.md`

The official implementation plan wins over WS-D if they conflict. In particular: **do not expose `modelMode` to HR in the new JobPosting Agent request**.

## 2. Mission

Implement the **JobPosting Agent persistence/API shell**:

1. Pydantic models for JobPosting Agent API and state/tool metadata.
2. Dedicated persistence layer for `AIJOBPOSTING*` tables.
3. FastAPI routes under `/v2/agent/job-posting`.
4. Query endpoint shell that validates request, creates/loads conversation, persists user message, calls a runtime/query service boundary, and returns the response shape.
5. Conversation list/messages/rename/archive endpoints.
6. Focused unit tests with mocked DB/runtime where appropriate.
7. Implementation report.

This WS may use a **stubbed query/runtime boundary** until WS3 is merged. Do not implement Gemini native runtime or real tools here.

## 3. Hard boundaries

Allowed to create/modify:

1. `app/models/jobposting_agent.py`
2. `app/services/jobposting_agent_persistence.py`
3. `app/services/jobposting_agent_query.py` as shell/orchestration with runtime dependency that can be mocked
4. `app/api/routes_jobposting_agent.py`
5. `app/main.py`
6. `app/core/config.py` for JobPosting Agent config fields if not already present
7. `.env.example` if it exists
8. `tests/unit/unit_test_jobposting_agent_persistence.py`
9. `tests/unit/unit_test_routes_jobposting_agent.py`
10. Optional focused test files
11. Report file under `agent_workflow_doc/try_hard_jobposting/`

Do **not** modify:

1. `database/schema_ai_core.sql`
2. `database/schema_web_core.sql`
3. `app/api/routes_chat.py`
4. `app/models/chat.py`
5. `app/services/chat_persistence.py`
6. `app/services/rag_orchestrator.py`
7. `app/services/rag_model_adapters.py`
8. `app/services/nmaiex_candidate_enrichment.py`
9. `app/services/nmaiex_ranking_service.py`
10. `.understand-anything/*`

Do not implement read-only tools or Gemini runtime. Those belong to WS3.

## 4. Required implementation details

### 4.1 Models

Create `app/models/jobposting_agent.py`.

Required models:

1. `JobPostingAgentQueryRequest`
2. `JobPostingAgentQueryResponse`
3. `ToolCallDetail`
4. `WorkingSetInfo`
5. `AgentWarning`
6. `JobPostingConversationSummary`
7. `JobPostingChatMessage`
8. `RenameConversationRequest`
9. `RenameConversationResponse`

Important request rule:

```python
class JobPostingAgentQueryRequest(BaseModel):
    jobPostId: int
    hrId: int
    prompt: str
    conversationId: uuid.UUID | None = None
```

No `modelMode` field in this request.

### 4.2 Config

Add config fields to `app/core/config.py` if missing:

1. `jobposting_agent_enabled: bool = True`
2. `jobposting_agent_model: str = "agent-lite"`
3. `jobposting_agent_max_tool_steps: int = 8`
4. `jobposting_agent_max_full_cv_loads: int = 3`
5. `jobposting_agent_max_compare: int = 25`
6. `jobposting_agent_default_top_n: int = 10`
7. `jobposting_agent_hr_max_top_n: int = 25`
8. `jobposting_agent_max_turn_seconds: int = 60`
9. `jobposting_agent_temperature: float = 0.2`
10. `jobposting_agent_max_output_tokens: int = 4096`
11. `jobposting_agent_max_tool_result_chars: int = 12000`

Avoid conflicting with WS3. If config fields already exist, do not duplicate.

### 4.3 Persistence service

Create `app/services/jobposting_agent_persistence.py`, following the style of `app/services/chat_persistence.py`.

Required functions:

1. `create_conversation(job_post_id: int, hr_id: int, title: str | None = None) -> uuid.UUID`
2. `get_conversation(conversation_id: uuid.UUID) -> dict | None`
3. `list_conversations(hr_id: int, job_post_id: int) -> list[dict]`
4. `rename_conversation(conversation_id: uuid.UUID, title: str) -> None`
5. `archive_conversation(conversation_id: uuid.UUID) -> None`
6. `touch_conversation(conversation_id: uuid.UUID) -> None`
7. `insert_message(...) -> int`
8. `get_messages(conversation_id, include_system=False, include_tool=True) -> list[dict]`
9. `get_full_history(conversation_id) -> list[dict]`
10. `get_state(conversation_id) -> dict | None`
11. `save_state(conversation_id, state_json: dict) -> None`
12. `insert_tool_call_log(...) -> int`

Rules:

1. Use `AIJOBPOSTINGCHATCONVERSATION`, `AIJOBPOSTINGCHATMESSAGE`, `AIJOBPOSTINGCHATSTATE`, `AIJOBPOSTINGTOOLCALLLOG`.
2. `messageCount` for conversation list is computed, not stored.
3. Count only visible chat messages for `messageCount`: roles `user` and `assistant`.
4. List excludes `isArchived = TRUE`.
5. Tool messages are sanitized JSON summaries only.
6. Do not store full CV/email/phone raw content.

### 4.4 Query orchestration shell

Create or stub `app/services/jobposting_agent_query.py`.

It should define a stable service boundary for WS3, for example:

```python
async def process_jobposting_agent_query(request: JobPostingAgentQueryRequest) -> JobPostingAgentQueryResponse:
    ...
```

Minimum behavior:

1. Validate prompt is non-empty and not too long.
2. Validate jobPostId exists.
3. Validate HR exists/access as strongly as current schema allows.
4. If `conversationId` is absent, create conversation + state.
5. If `conversationId` is present, verify it belongs to same `jobPostId` + `hrId` and is not archived.
6. Insert user message.
7. Call a runtime boundary function that WS3 can replace/implement.
8. Insert assistant message.
9. Save/update state if returned.
10. Auto-title a new conversation from the first prompt by truncating, not by LLM.

If runtime is not implemented yet, use an internal placeholder that raises a clear `NotImplementedError` or returns a deterministic stub only in tests. Do not fake a production answer silently.

### 4.5 Routes

Create `app/api/routes_jobposting_agent.py`.

Register in `app/main.py`:

```python
from app.api.routes_jobposting_agent import router as jobposting_agent_router
app.include_router(jobposting_agent_router, prefix="/v2/agent/job-posting")
```

Required endpoints:

1. `POST /query`
2. `GET /conversations?jobPostId=...&hrId=...`
3. `GET /conversations/{conversationId}/messages?includeToolMessages=true&includeSystem=false`
4. `PATCH /conversations/{conversationId}`
5. `DELETE /conversations/{conversationId}?hrId=...`

Error mapping:

1. invalid prompt/title -> 400
2. no HR/job access -> 403
3. job/conversation not found -> 404
4. archived conversation -> 410
5. provider unavailable placeholder/runtime error -> 503 only when appropriate
6. unexpected -> 500

Do not alter existing `/v2/chat` route registration or behavior.

## 5. Tests to add/run

Use repo venv first:

```powershell
.\venv\Scripts\python.exe -m pytest tests/unit/unit_test_jobposting_agent_persistence.py tests/unit/unit_test_routes_jobposting_agent.py
.\venv\Scripts\python.exe -m compileall app
```

If venv fails for environment reasons, also try:

```powershell
python -m pytest tests/unit/unit_test_jobposting_agent_persistence.py tests/unit/unit_test_routes_jobposting_agent.py
python -m compileall app
```

Add focused tests for:

1. Request model has no `modelMode`.
2. Conversation create initializes state if function does so.
3. Conversation list filters by `jobPostId`, `hrId`, `isArchived = FALSE`.
4. `messageCount` counts only user/assistant.
5. `get_messages()` includes tool messages by default and hides system by default.
6. Rename rejects empty/too-long titles.
7. Archive sets `isArchived = TRUE`.
8. Query shell rejects mismatched conversation job/hr.
9. Route registration compiles and does not remove existing routers.

Use mocks for DB and runtime. Do not require a real Gemini call.

## 6. Report

Create:

`agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WS2_PERSISTENCE_API_REPORT.md`

Report sections:

1. Summary
2. Files changed
3. API/models implemented
4. Persistence functions implemented
5. Runtime/query boundary exposed for WS3
6. Tests run and results
7. Drift/conflicts found
8. Integration notes for WS1/WS3
9. Remaining risks

## 7. Stop conditions

Stop and report instead of improvising if:

1. Required AI tables are not in schema and you cannot safely code against planned names.
2. HR/job ownership rules are ambiguous enough that implementing access checks would be unsafe. In that case implement strongest available validation and document the gap.
3. Query shell would require real Gemini/runtime implementation.
4. Existing `/v2/chat` behavior would need to change.
5. Tests reveal unrelated existing failures.

## 8. Final response

After completion, respond briefly:

1. Report path.
2. Files changed.
3. Tests run.
4. Whether WS3 can proceed.
5. Any blockers.

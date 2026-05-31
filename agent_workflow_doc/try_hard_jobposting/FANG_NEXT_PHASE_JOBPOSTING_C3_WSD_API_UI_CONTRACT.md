# WS-D — Product, API, and UI Contract

## Discovery Report — Input cho Official Implementation Plan

> **Workstream:** WS-D  
> **Mã việc:** WS-D - Product, API, and UI Contract  
> **Ngày:** 2026-05-28  
> **Tác giả:** Tier 1 Discovery Architect  
> **Trạng thái:** Discovery hoàn tất — chờ synthesis

---

## 1. Executive Summary

WS-D chịu trách nhiệm thiết kế **lớp HTTP endpoint** và **contract giữa backend với frontend** cho JobPosting Agent C3. Report này xác định:

1. **Route namespace** mới cho agent, tách biệt hoàn toàn khỏi hệ thống chat hiện tại (`/v2/chat`).
2. **Request/Response schema** cho query endpoint và conversation management endpoints.
3. **Conversation CRUD API** hỗ trợ create, list, get history, rename, archive (soft-delete).
4. **Chat Pane UX contract** — fields cần hiển thị: response, tool calls, working set label, active filters, source job app IDs, warnings.
5. **Tool usage visibility** — cách frontend hiển thị tool progress và tool details.
6. **Streaming decision** — Phase 1 là request-response đồng bộ, không SSE/WebSocket.
7. **Smoke test flows** — 7 manual/Postman flows để validate end-to-end.

**Scope rõ ràng:** WS-D KHÔNG thiết kế agent runtime (WS-A), schema database (WS-B), hay tool implementations (WS-C). WS-D thiết kế lớp HTTP mỏng (thin HTTP layer) và contract giao tiếp với frontend.

**NMAIex normalization bug:** WS-D ghi nhận dependency — language filter UI features chỉ hoạt động chính xác khi WS-C đã fix normalization ở parse/enrichment stage. WS-D không cần thiết kế fix, nhưng API response phải có cơ chế báo warning nếu filter result không đáng tin cậy.

---

## 2. Current API/UI Reality Assumptions

### 2.1. Hiện trạng API (Code Reality)

| Khía cạnh | Hiện trạng | File nguồn |
|-----------|-----------|------------|
| Entry point | FastAPI app "FANG AI Core" v2.0.0 | `app/main.py` |
| Prefix chung | `/v2` | `app/main.py` |
| Chat routes | `/v2/chat/*` — 5 endpoints | `app/api/routes_chat.py` |
| Chat scope | `jobAppId`-scoped (bắt buộc) | `app/models/chat.py` |
| Conversation title | **Không có** — không có field `title` trong DB hoặc model | `schema_ai_core.sql`, `chat.py` |
| Conversation rename | **Không có** endpoint | `routes_chat.py` |
| Conversation delete | **Không có** endpoint hoặc soft-delete | `routes_chat.py` |
| Streaming | **Không có** — tất cả response là JSON đồng bộ | `rag_query.py` |
| Tool call visibility | **Không có** — không có structured tool metadata trong response | `chat.py` |
| Pagination | **Không có** — `list_conversations` và `get_messages` trả toàn bộ | `chat_persistence.py` |

### 2.2. Chat Endpoints Hiện Tại (để tham chiếu, KHÔNG reuse)

| Method | Path | Scope | Mô tả |
|--------|------|-------|--------|
| `POST` | `/v2/chat/query` | `jobAppId` | Main RAG query |
| `GET` | `/v2/chat/conversations` | `hrId` + `jobAppId` | List conversations |
| `GET` | `/v2/chat/conversations/{id}/messages` | `conversationId` | Message history |
| `POST` | `/v2/chat/conversations/{id}/summarize` | `conversationId` | Summarize & continue |
| `POST` | `/v2/chat/conversations/{id}/branch-new` | `conversationId` | Branch new from summary |

### 2.3. Current Chat Request/Response (để tham chiếu)

**ChatQueryRequest:**
```python
class ChatQueryRequest(BaseModel):
    jobAppId: int          # REQUIRED
    hrId: int              # REQUIRED
    prompt: str            # REQUIRED
    conversationId: UUID | None = None
    modelMode: str         # REQUIRED — 7 modes
```

**ChatQueryResponse:**
```python
class ChatQueryResponse(BaseModel):
    conversationId: UUID
    messageId: int
    response: str
    model: str | None = None
    modelMode: str
    fallbackPath: str | None = None
    latencyMs: int
    topK: int
    contextWarning: ContextWarning | None = None
```

### 2.4. Kết luận từ hiện trạng

1. JobPosting Agent cần **hoàn toàn tách biệt** khỏi `/v2/chat` — scope khác (`jobPostId` vs `jobAppId`), runtime khác (agent loop vs RAG pipeline), response format khác (có tool calls).
2. Có thể **tham khảo pattern** của chat hiện tại (route structure, Pydantic model style, persistence function style) nhưng **không reuse trực tiếp** vì semantic khác quá nhiều.
3. File mới: `app/api/routes_jobposting_agent.py` và `app/models/jobposting_agent.py` — đúng với đề xuất của WS-A.

---

## 3. Proposed Route Namespace

### 3.1. Phân tích các lựa chọn

| Lựa chọn | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| `/v2/job-posting-agent/*` | Rõ ràng, tự mô tả | Dài, có hyphen |
| `/v2/jobposting-agent/*` | Gọn hơn | Viết liền khó đọc |
| `/v2/job-postings/{id}/assistant/*` | RESTful, resource-nested | Quá dài, khó match với existing `/v2/nmaiex/` pattern |
| `/v2/agent/job-posting/*` | Agent-first namespace | Mở rộng tốt nếu có thêm agent khác |

### 3.2. Quyết định đề xuất: `/v2/agent/job-posting`

**Lý do:**

1. **Namespace rõ ràng cho agent domain** — tách biệt khỏi `/v2/chat` (RAG) và `/v2/nmaiex` (ranking/management).
2. **Mở rộng tốt** — nếu tương lai có thêm agent khác (ví dụ: candidate agent, interview agent), chỉ cần thêm `/v2/agent/candidate`, `/v2/agent/interview`.
3. **Không conflict** với bất kỳ prefix hiện tại nào.
4. **Đủ ngắn** cho Postman/curl.

> **⚠️ Lưu ý:** Đây là đề xuất — synthesis tier 1 và user có quyền chọn khác. Nếu user prefer `/v2/job-posting-agent`, cũng chấp nhận được.

### 3.3. Route Map Đầy Đủ

| # | Method | Path | Mô tả | Phase |
|---|--------|------|-------|-------|
| 1 | `POST` | `/v2/agent/job-posting/query` | Gửi message, agent xử lý, trả response | P1 |
| 2 | `GET` | `/v2/agent/job-posting/conversations` | List conversations cho HR + jobPost | P1 |
| 3 | `GET` | `/v2/agent/job-posting/conversations/{conversationId}/messages` | Lấy message history | P1 |
| 4 | `PATCH` | `/v2/agent/job-posting/conversations/{conversationId}` | Rename conversation (update title) | P1 |
| 5 | `DELETE` | `/v2/agent/job-posting/conversations/{conversationId}` | Archive conversation (soft-delete) | P1 |
| 6 | `POST` | `/v2/agent/job-posting/conversations/{conversationId}/summarize` | Summarize & continue | P2 |
| 7 | `POST` | `/v2/agent/job-posting/conversations/{conversationId}/branch-new` | Branch new from summary | P2 |

**Phase 1 MVP:** Endpoints 1–5.  
**Phase 2:** Endpoints 6–7 (summarize/branch — tương tự existing chat, nhưng chưa cần ngay vì agent loop chưa dùng full context window).

---

## 4. Request/Response Schemas

### 4.1. Query Endpoint — `POST /v2/agent/job-posting/query`

#### Request: `JobPostingAgentQueryRequest`

```python
class JobPostingAgentQueryRequest(BaseModel):
    jobPostId: int                      # REQUIRED — scope key
    hrId: int                           # REQUIRED — auth/ownership
    prompt: str                         # REQUIRED — HR message text
    conversationId: UUID | None = None  # Optional — omit to create new
    modelMode: str = "auto-agent"       # Optional — default "auto-agent"
```

**Thiết kế rationale:**

| Field | So với ChatQueryRequest | Lý do |
|-------|------------------------|-------|
| `jobPostId` | Thay `jobAppId` | Agent scope theo job posting, không phải job application |
| `hrId` | Giữ nguyên | Auth/ownership — HR phải đăng nhập |
| `prompt` | Giữ nguyên | Text message từ HR |
| `conversationId` | Giữ nguyên pattern | Omit = tạo mới, có = tiếp tục |
| `modelMode` | Default khác | Agent dùng model riêng (WS-A), default là `"auto-agent"` thay vì 7 modes cũ |

**`modelMode` cho agent:**

- WS-A quyết định agent dùng **Gemini only** (`gemini-3.1-flash-lite` default, upgrade path `gemini-3.5-flash`).
- Đề xuất `modelMode` cho agent: `"auto-agent"` (default, chọn model tối ưu) hoặc chỉ định cụ thể nếu cần.
- Synthesis cần confirm với WS-A chính xác các mode nào hợp lệ cho agent.

**Validation rules:**

| Validation | HTTP Response |
|------------|---------------|
| `jobPostId` không tồn tại trong `JOBPOSTING` | `404 Not Found` |
| `hrId` không tồn tại hoặc không có quyền | `403 Forbidden` |
| `conversationId` tồn tại nhưng thuộc `jobPostId` khác | `403 Forbidden` |
| `conversationId` tồn tại nhưng đã archive | `410 Gone` |
| `prompt` rỗng hoặc quá dài (>2000 chars) | `400 Bad Request` |
| `modelMode` không hợp lệ | `400 Bad Request` |

#### Response: `JobPostingAgentQueryResponse`

```python
class ToolCallDetail(BaseModel):
    """Chi tiết một tool call trong agent turn."""
    step: int                           # Bước thứ mấy trong agent loop (1-indexed)
    toolName: str                       # Tên tool (e.g. "get_job_candidate_ranking")
    args: dict                          # Input args (sanitized, no PII)
    resultSummary: str                  # Tóm tắt kết quả (e.g. "Trả về 10 ứng viên")
    status: str                         # "success" | "error" | "timeout"
    latencyMs: int | None = None        # Latency của tool call này
    errorMsg: str | None = None         # Error message nếu status != success

class WorkingSetInfo(BaseModel):
    """Thông tin working set hiện tại."""
    jobAppIds: list[int]                # List jobAppIds trong working set
    label: str | None = None            # Mô tả (e.g. "Top 10 Backend Developer")
    activeFilters: dict | None = None   # Filters đang áp dụng

class AgentWarning(BaseModel):
    """Warning từ agent (too-large, max steps, normalization)."""
    type: str                           # "too_large_set" | "max_steps_reached" | "data_quality"
    message: str                        # Human-readable warning
    suggestion: str | None = None       # Gợi ý hành động

class JobPostingAgentQueryResponse(BaseModel):
    conversationId: UUID                # Conversation (mới tạo hoặc existing)
    messageId: int                      # ID of assistant message
    response: str                       # Agent response text
    model: str                          # Model đã dùng (e.g. "gemini-3.1-flash-lite")
    stepsUsed: int                      # Số bước agent loop đã chạy
    toolCalls: list[ToolCallDetail]     # Chi tiết tool calls (có thể rỗng nếu agent trả lời trực tiếp)
    sourceJobAppIds: list[int]          # Job app IDs được reference trong response
    workingSet: WorkingSetInfo | None = None  # Working set sau turn này
    latencyMs: int                      # Total latency (end-to-end)
    warnings: list[AgentWarning] = []   # Warnings (nếu có)
```

**Thiết kế rationale:**

| Field | Có trong ChatQueryResponse? | Lý do thêm/bỏ |
|-------|----------------------------|----------------|
| `conversationId` | ✅ Giữ | Cùng pattern |
| `messageId` | ✅ Giữ | Cùng pattern |
| `response` | ✅ Giữ | Cùng pattern |
| `model` | ✅ Giữ | Cùng pattern |
| `modelMode` | ❌ Bỏ | Agent chỉ có 1 mode chính, không cần expose |
| `fallbackPath` | ❌ Bỏ | Agent dùng single provider, không fallback chain |
| `topK` | ❌ Bỏ | Agent không dùng vector search trực tiếp |
| `stepsUsed` | 🆕 Thêm | Agent loop có nhiều bước, UI có thể show |
| `toolCalls` | 🆕 Thêm | Core differentiator — agent has tools |
| `sourceJobAppIds` | 🆕 Thêm | Grounding — HR biết agent đang nói về ứng viên nào |
| `workingSet` | 🆕 Thêm | Memory state — HR biết đang làm việc với tập nào |
| `warnings` | 🆕 Thêm | Thay `contextWarning` — rộng hơn, hỗ trợ nhiều loại warning |
| `latencyMs` | ✅ Giữ | Performance monitoring |

### 4.2. Conversation List — `GET /v2/agent/job-posting/conversations`

#### Query Parameters

```
?jobPostId=123&hrId=456
```

Cả hai đều **REQUIRED**.

#### Response: `list[JobPostingConversationSummary]`

```python
class JobPostingConversationSummary(BaseModel):
    conversationId: UUID
    jobPostId: int
    hrId: int
    title: str                          # Conversation title (default hoặc renamed)
    createdAt: str                      # ISO 8601 timestamp
    lastMessageAt: str                  # ISO 8601 timestamp
    messageCount: int                   # Computed via COUNT query
    isArchived: bool = False            # Always false (archived conversations filtered out)
```

**Notes:**

- Default sort: `lastMessageAt DESC` (cuộc trò chuyện gần nhất lên trước).
- Chỉ trả conversations có `isArchived = FALSE`.
- `messageCount` tính bằng `LEFT JOIN COUNT` trên `AIJOBPOSTINGCHATMESSAGE` — **computed, không stored** (đúng pattern hiện tại trong `chat_persistence.py` → `list_conversations()`).

### 4.3. Message History — `GET /v2/agent/job-posting/conversations/{conversationId}/messages`

#### Query Parameters (Optional)

```
?includeToolMessages=true    # Default: true — include role=tool_call/tool_result
&includeSystem=false         # Default: false — exclude role=system
```

#### Response: `list[JobPostingChatMessage]`

```python
class JobPostingChatMessage(BaseModel):
    messageId: int
    role: str                           # "user" | "assistant" | "system" | "tool_call" | "tool_result"
    content: str                        # Text for user/assistant/system; JSON string for tool_call/tool_result
    toolName: str | None = None         # Populated for tool_call/tool_result roles
    toolCallId: str | None = None       # Links tool_call ↔ tool_result
    model: str | None = None            # Model used, null for user/system/tool
    latencyMs: int | None = None        # Latency, null for user/system
    createdAt: str                      # ISO 8601 timestamp
```

**Notes:**

- Default sort: `createdAt ASC` (chronological order).
- `content` cho `role=tool_call` chứa JSON params (sanitized, no PII).
- `content` cho `role=tool_result` chứa JSON summary (NOT full data).
- `system` messages mặc định ẩn — chỉ trả nếu `includeSystem=true`.

### 4.4. Rename Conversation — `PATCH /v2/agent/job-posting/conversations/{conversationId}`

#### Request Body

```python
class RenameConversationRequest(BaseModel):
    title: str     # New title, max 200 chars
```

#### Response

```python
class RenameConversationResponse(BaseModel):
    conversationId: UUID
    title: str
    updatedAt: str
```

**Validation:**
- `title` rỗng → `400 Bad Request`
- `title` dài hơn 200 chars → `400 Bad Request`
- `conversationId` không tồn tại → `404 Not Found`
- `conversationId` thuộc HR khác → `403 Forbidden`

### 4.5. Archive Conversation — `DELETE /v2/agent/job-posting/conversations/{conversationId}`

#### Query Parameters

```
?hrId=456    # REQUIRED — ownership check
```

#### Response

```
HTTP 204 No Content
```

**Behavior:**
- Set `isArchived = TRUE` trong `AIJOBPOSTINGCHATCONVERSATION`.
- **KHÔNG xóa data** — soft-delete.
- Conversation không còn xuất hiện trong list.
- Nếu query với `conversationId` đã archive → `410 Gone`.

---

## 5. Conversation Management API

### 5.1. Conversation Lifecycle

```
┌──────────────────────────────────────────────────────┐
│                  Conversation Lifecycle               │
│                                                      │
│  POST /query (no conversationId)                     │
│       │                                              │
│       ▼                                              │
│  ┌─────────┐   POST /query   ┌─────────┐            │
│  │ Created  │──────────────→ │ Active   │            │
│  │ (title:  │                │ (title:  │            │
│  │ default) │                │ auto or  │            │
│  └─────────┘                 │ renamed) │            │
│                              └────┬─────┘            │
│                                   │                  │
│                          DELETE /{id}                │
│                                   │                  │
│                                   ▼                  │
│                            ┌──────────┐              │
│                            │ Archived │              │
│                            │ (hidden) │              │
│                            └──────────┘              │
└──────────────────────────────────────────────────────┘
```

### 5.2. Title Auto-Generation

**Đề xuất:** Backend auto-generate sau message đầu tiên của user.

**Logic:**

1. Khi `POST /query` tạo conversation mới (không có `conversationId`):
   - Tạo conversation với `title = 'Cuộc trò chuyện mới'`.
   - Sau khi agent trả response thành công, update title = truncate `prompt` thành ~100 chars.
2. HR có thể rename bất cứ lúc nào qua `PATCH /{id}`.
3. **KHÔNG dùng LLM để generate title** — quá tốn và không cần thiết khi user prompt đã đủ mô tả.

**Lý do chọn backend thay vì agent:**
- Agent runtime (WS-A) nên focus vào tool calling và response, không nên thêm side-effect generate title.
- Backend truncate prompt đơn giản, deterministic, zero latency overhead.
- Consistent với pattern tương tự ở nhiều chat product (ChatGPT, Claude đều dùng first message as title).

### 5.3. Persistence Functions Cần Tạo

Tham chiếu `chat_persistence.py` pattern hiện tại, cần tạo file mới `app/services/jobposting_agent_persistence.py` với:

| Function | Signature | Mô tả |
|----------|-----------|-------|
| `create_conversation` | `(job_post_id: int, hr_id: int, title: str = None) → UUID` | INSERT + return UUID |
| `get_conversation` | `(conversation_id: UUID) → dict \| None` | Fetch metadata |
| `list_conversations` | `(hr_id: int, job_post_id: int) → list[dict]` | List active, ordered by lastMessageAt DESC, with messageCount |
| `rename_conversation` | `(conversation_id: UUID, title: str) → None` | UPDATE title |
| `archive_conversation` | `(conversation_id: UUID) → None` | UPDATE isArchived = TRUE |
| `touch_conversation` | `(conversation_id: UUID) → None` | UPDATE lastMessageAt |
| `insert_message` | `(conv_id, role, content, *, tool_name, tool_call_id, model, model_mode, latency_ms) → int` | INSERT message |
| `get_messages` | `(conv_id, *, include_system=False, include_tool=True) → list[dict]` | Get history filtered by role |
| `get_full_history` | `(conv_id) → list[dict]` | All messages for agent context |
| `save_state` | `(conv_id, state_json: dict) → None` | UPSERT state |
| `get_state` | `(conv_id) → dict \| None` | Get latest state |
| `insert_tool_call_log` | `(conv_id, msg_id, tool_name, tool_input, tool_output_meta, status, latency_ms, error_msg) → int` | Log to AIJOBPOSTINGTOOLCALLLOG |

---

## 6. Chat Pane UX Contract

### 6.1. Layout Overview

```
┌─────────────────────────────────────────────────────────────┐
│  JobPosting Detail Page                                     │
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────────────┐ │
│  │                      │  │  Agent Chat Pane              │ │
│  │   Job Posting Info   │  │                              │ │
│  │   (existing UI)      │  │  ┌──────────────────────┐   │ │
│  │                      │  │  │ Conversation List     │   │ │
│  │   - Title            │  │  │ (dropdown/sidebar)    │   │ │
│  │   - Description      │  │  └──────────────────────┘   │ │
│  │   - Requirements     │  │                              │ │
│  │   - Applications     │  │  ┌──────────────────────┐   │ │
│  │     list             │  │  │ Messages Area        │   │ │
│  │                      │  │  │                      │   │ │
│  │                      │  │  │  [User bubble]       │   │ │
│  │                      │  │  │  [Tool indicator]    │   │ │
│  │                      │  │  │  [Assistant bubble]  │   │ │
│  │                      │  │  │  [Working set badge] │   │ │
│  │                      │  │  │                      │   │ │
│  │                      │  │  └──────────────────────┘   │ │
│  │                      │  │                              │ │
│  │                      │  │  ┌──────────────────────┐   │ │
│  │                      │  │  │ Input area + Send    │   │ │
│  │                      │  │  └──────────────────────┘   │ │
│  └──────────────────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 6.2. UI Fields và Data Source

| UI Element | Data Source | Hiển thị khi nào |
|-----------|------------|-----------------|
| **Conversation title** | `JobPostingConversationSummary.title` | Luôn — header chat pane |
| **Conversation list** | `GET /conversations` response | Khi user mở dropdown/sidebar |
| **User message bubble** | `JobPostingChatMessage` (role=user) | Luôn |
| **Assistant message bubble** | `JobPostingChatMessage` (role=assistant) | Luôn |
| **Tool usage indicator** | `JobPostingAgentQueryResponse.toolCalls[]` | Trước assistant bubble nếu có tool calls |
| **Working set badge** | `JobPostingAgentQueryResponse.workingSet` | Sau assistant bubble nếu workingSet != null |
| **Active filters chips** | `workingSet.activeFilters` | Cùng working set badge |
| **Source references** | `sourceJobAppIds` | Trong/dưới assistant bubble — link đến ứng viên |
| **Warning banner** | `warnings[]` | Trên assistant bubble nếu có warnings |
| **Latency indicator** | `latencyMs` | Optional — footer hoặc tooltip |
| **Model indicator** | `model` | Optional — footer hoặc tooltip |
| **Steps indicator** | `stepsUsed` | Optional — tooltip trên tool usage |

### 6.3. Tool Usage Display Design

Khi agent query trả về `toolCalls` không rỗng, UI nên hiển thị **collapsible tool usage section** giữa user message và assistant response:

```
┌─────────────────────────────────────────┐
│  👤 HR: "Phân tích 10 ứng viên top"    │
├─────────────────────────────────────────┤
│  🔧 Agent đã sử dụng 2 công cụ         │  ← collapsible header
│  ┌─────────────────────────────────┐    │
│  │ ① Xếp hạng ứng viên           │    │  ← tool display name
│  │    Params: limit=10             │    │  ← sanitized args
│  │    Kết quả: 10/45 ứng viên     │    │  ← result summary
│  │    ⏱ 320ms ✅                   │    │  ← latency + status
│  ├─────────────────────────────────┤    │
│  │ ② Xem thông tin tin tuyển dụng │    │
│  │    ⏱ 45ms ✅                    │    │
│  └─────────────────────────────────┘    │
├─────────────────────────────────────────┤
│  🤖 Agent: "Dựa trên phân tích..."     │
│                                         │
│  📋 Working set: Top 10 Backend Dev     │
│  🔗 Ứng viên: #456, #789, #12, ...     │
└─────────────────────────────────────────┘
```

### 6.4. Tool Display Name Mapping

UI cần mapping `toolName` → Vietnamese display name. Đề xuất frontend hardcode hoặc backend cung cấp qua response:

| `toolName` | Display Name | Icon |
|-----------|-------------|------|
| `get_job_posting_context` | Xem thông tin tin tuyển dụng | 📋 |
| `get_job_candidate_ranking` | Xếp hạng ứng viên | 📊 |
| `search_job_applications_text` | Tìm kiếm ứng viên | 🔍 |
| `get_job_application_summary` | Tóm tắt ứng viên | 📝 |
| `get_job_application_full_cv` | Xem CV đầy đủ | 📄 |
| `get_candidate_ats_history` | Lịch sử tuyển dụng | 📅 |
| `count_job_applications` | Đếm ứng viên | 🔢 |

**Đề xuất:** Hardcode ở frontend cho Phase 1. Nếu Phase 2 thêm tools, xem xét dynamic tool catalog API (endpoint `/v2/agent/job-posting/tools` trả tool metadata).

### 6.5. Loading State

Vì Phase 1 không có streaming, agent turn có thể mất **tới 60 giây** (max latency từ WS-A). UI cần:

1. **Immediately** show user message bubble khi HR nhấn Send.
2. **Show loading indicator** — typing dots hoặc "Agent đang phân tích..." animation.
3. **Disable input** trong khi đang chờ response.
4. **Timeout handling** — nếu >60s không có response, show error message.
5. **No cancel button Phase 1** — backend không hỗ trợ cancel mid-turn.

### 6.6. Error State Display

| HTTP Status | UI Display |
|-------------|-----------|
| `200` + `warnings` | Show warning banner phía trên response |
| `400` | "Yêu cầu không hợp lệ" + error detail |
| `403` | "Bạn không có quyền truy cập" |
| `404` | "Tin tuyển dụng không tồn tại" |
| `410` | "Cuộc trò chuyện đã được lưu trữ" |
| `429` | "Hệ thống đang quá tải, vui lòng thử lại" |
| `503` | "Dịch vụ AI tạm thời không khả dụng" |
| `500` | "Lỗi hệ thống, vui lòng thử lại" |

---

## 7. Tool Usage Visibility

### 7.1. Two Layers of Tool Visibility

**Layer 1 — Query Response (real-time):**
- `toolCalls[]` trong `JobPostingAgentQueryResponse` — chi tiết tool calls của turn vừa xong.
- Frontend render ngay sau khi nhận response.

**Layer 2 — Message History (replay):**
- `role=tool_call` và `role=tool_result` messages trong `GET /conversations/{id}/messages`.
- Frontend render khi load conversation history (quay lại conversation cũ).

**Consistency:** Cả hai layer phải hiển thị cùng thông tin. Layer 1 là structured (parsed objects), Layer 2 là serialized (JSON strings trong `content`). Frontend parse JSON từ Layer 2 để render UI giống Layer 1.

### 7.2. Privacy Guardrails

Tuân theo WS-B privacy constraints:

| Data | Cho phép trong tool log? | Lý do |
|------|--------------------------|-------|
| `tool_name` | ✅ | Non-sensitive |
| `args` (params) | ✅ (sanitized) | Chỉ IDs và filter values |
| `result_summary` | ✅ | Count/summary only |
| Candidate name | ✅ | HR đã có quyền xem |
| Email/phone | ❌ | PII — không log |
| Full CV text | ❌ | Quá lớn + PII risk |
| Full ranking JSON | ❌ | Quá lớn — chỉ summary |

### 7.3. Phase 2 Consideration — Streaming Tool Progress

Phase 1 không có streaming, nhưng ghi nhận yêu cầu Phase 2:

- **SSE stream** cho từng step của agent loop — UI show real-time "đang gọi tool X...", "đang phân tích...", "đang trả lời...".
- Cần SSE event types: `tool_start`, `tool_complete`, `thinking`, `response_chunk`, `done`.
- WS-D không thiết kế chi tiết Phase 2 streaming — chỉ đảm bảo Phase 1 response format không block Phase 2 extension.

---

## 8. Smoke Test Flows

### 8.1. Flow 1 — Top 10 Ranking Analysis

```
Mục tiêu: HR hỏi agent phân tích top 10 ứng viên

1. POST /v2/agent/job-posting/query
   Body: { jobPostId: 123, hrId: 456, prompt: "Phân tích 10 ứng viên xếp hạng cao nhất" }

2. Expected response:
   - conversationId: <new UUID>
   - response: Phân tích chi tiết 10 ứng viên
   - toolCalls: [
       { toolName: "get_job_posting_context", status: "success" },
       { toolName: "get_job_candidate_ranking", args: { limit: 10 }, status: "success" }
     ]
   - sourceJobAppIds: [id1, id2, ..., id10]
   - workingSet: { jobAppIds: [...], label: "Top 10 ứng viên cho ...", activeFilters: null }
   - stepsUsed: 2 hoặc 3

3. Verify:
   - Response chứa tên/thông tin 10 ứng viên
   - sourceJobAppIds có đúng 10 items
   - workingSet.jobAppIds match sourceJobAppIds
   - toolCalls có get_job_candidate_ranking
   - latencyMs < 60000
```

### 8.2. Flow 2 — Refine với Language Filter

```
Mục tiêu: HR hỏi lọc từ working set theo ngôn ngữ

1. POST /v2/agent/job-posting/query
   Body: { jobPostId: 123, hrId: 456, conversationId: <from flow 1>, 
           prompt: "Trong 10 ứng viên này, ai có tiếng Anh hạng C trở lên?" }

2. Expected response:
   - conversationId: <same UUID>
   - response: Danh sách ứng viên đạt tiếng Anh hạng C+
   - workingSet: { jobAppIds: [filtered subset], activeFilters: { language: "English", proficiency: "ADVANCED" } }
   - warnings: [] (hoặc warning nếu normalization chưa fix)

3. Verify:
   - Agent nhớ working set từ turn trước
   - Response chỉ nói về ứng viên trong working set
   - activeFilters được set đúng
   - Nếu normalization chưa fix → warnings có type: "data_quality"
```

### 8.3. Flow 3 — Too-Large Set Rejection

```
Mục tiêu: HR hỏi so sánh tất cả ứng viên (quá lớn)

1. POST /v2/agent/job-posting/query
   Body: { jobPostId: 123, hrId: 456, conversationId: <from flow 1>,
           prompt: "So sánh chi tiết tất cả ứng viên cho vị trí này" }

2. Expected response:
   - response: Agent từ chối so sánh toàn bộ, đề xuất dùng top N hoặc filter
   - warnings: [{ type: "too_large_set", message: "Tập ứng viên quá lớn (>25) để so sánh chi tiết", 
                  suggestion: "Hãy dùng top N hoặc thêm bộ lọc" }]
   - toolCalls: [{ toolName: "count_job_applications", resultSummary: "Total: 150" }]

3. Verify:
   - Agent KHÔNG load full CV cho 150 ứng viên
   - Warning type là "too_large_set"
   - Agent gợi ý cách tiếp cận thay thế
```

### 8.4. Flow 4 — Rename Conversation

```
Mục tiêu: HR đổi tên conversation

1. PATCH /v2/agent/job-posting/conversations/<conversationId>
   Body: { title: "Phân tích Backend Developer Q3" }

2. Expected response:
   - HTTP 200
   - { conversationId: <UUID>, title: "Phân tích Backend Developer Q3", updatedAt: "..." }

3. GET /v2/agent/job-posting/conversations?jobPostId=123&hrId=456

4. Verify:
   - Conversation xuất hiện với title mới trong list
```

### 8.5. Flow 5 — New Conversation + Auto Title

```
Mục tiêu: Tạo conversation mới, verify auto-generated title

1. POST /v2/agent/job-posting/query
   Body: { jobPostId: 123, hrId: 456, prompt: "Ai là ứng viên có kinh nghiệm Java nhiều nhất?" }

2. GET /v2/agent/job-posting/conversations?jobPostId=123&hrId=456

3. Verify:
   - Conversation mới xuất hiện trong list
   - title = "Ai là ứng viên có kinh nghiệm Java nhiều nhất?" (truncated nếu >100 chars)
   - messageCount = 2 (1 user + 1 assistant, không tính system/tool)
```

### 8.6. Flow 6 — Archive Conversation

```
Mục tiêu: Archive conversation, verify không còn trong list

1. DELETE /v2/agent/job-posting/conversations/<conversationId>?hrId=456

2. Expected: HTTP 204

3. GET /v2/agent/job-posting/conversations?jobPostId=123&hrId=456

4. Verify:
   - Conversation KHÔNG còn trong list
   - POST /query với conversationId đã archive → HTTP 410 Gone
```

### 8.7. Flow 7 — Invalid Request Handling

```
Mục tiêu: Verify error responses

1. POST /query với jobPostId không tồn tại → 404
2. POST /query với prompt rỗng → 400
3. POST /query với conversationId thuộc HR khác → 403
4. PATCH /conversations/<id> với title rỗng → 400
5. DELETE /conversations/<id> với hrId sai → 403
```

---

## 9. Dependency on WS-A/B/C

### 9.1. Dependencies từ WS-A (Agent Runtime)

| Dependency | Chi tiết | Blocking? |
|-----------|---------|-----------|
| `AgentTurnResult` structure | WS-D response schema map từ `AgentTurnResult` fields | ✅ Blocking |
| Error categories | WS-D HTTP error codes dựa trên WS-A error types | ✅ Blocking |
| Max turn latency (60s) | WS-D UI loading state timeout | ⚠️ Soft — config value |
| Model mode valid values | WS-D request validation | ⚠️ Soft — có thể skip validation Phase 1 |
| No streaming Phase 1 | WS-D UI design is request-response | ✅ Confirmed |

**Input WS-D cần từ WS-A:**
- Confirm `AgentTurnResult` dataclass fields — WS-D đã base trên WS-A report nhưng cần confirm cuối cùng.
- Confirm error types và HTTP status mapping.

### 9.2. Dependencies từ WS-B (Conversation Memory Schema)

| Dependency | Chi tiết | Blocking? |
|-----------|---------|-----------|
| Table schema finalized | WS-D persistence functions match table columns | ✅ Blocking |
| `title` column confirmed | WS-D rename endpoint depends on this | ✅ Confirmed |
| `isArchived` column confirmed | WS-D archive endpoint depends on this | ✅ Confirmed |
| State JSON schema | WS-D `WorkingSetInfo` maps from `stateJson` | ✅ Confirmed |
| Message roles (5 values) | WS-D message history API handles all roles | ✅ Confirmed |
| Tool call log table | WS-D tool visibility depends on log structure | ✅ Confirmed |

**Input WS-D cần từ WS-B:**
- Confirm `messageCount` strategy (WS-D đề xuất: computed via COUNT, KHÔNG stored) — WS-B §10.1 Q5.
- Confirm title auto-gen responsibility (WS-D đề xuất: backend) — WS-B §10.1 Q3.

### 9.3. Dependencies từ WS-C (Tool Contract)

| Dependency | Chi tiết | Blocking? |
|-----------|---------|-----------|
| MVP tool list finalized | WS-D tool display name mapping | ⚠️ Soft — 7 tools confirmed |
| Tool input/output schemas | WS-D sanitized args display | ⚠️ Soft |
| `sourceJobAppIds` logic | WS-D response field | ⚠️ Soft — agent runtime extracts this |
| NMAIex normalization fix | Language filter accuracy trong UI | ✅ Blocking cho language filter feature |

**Input WS-D cần từ WS-C:**
- Confirm tool input/output schemas — cho sanitization rules.
- Confirm language filter feasibility timeline — nếu chưa fix thì WS-D cần add warning logic.

### 9.4. NMAIex Normalization Bug — Impact on WS-D

**WS-D không fix normalization bug.** WS-C là owner. Tuy nhiên WS-D phải:

1. **Design warning mechanism:** Khi language filter results có thể không chính xác do unnormalized data, response phải có `warnings[].type = "data_quality"`.
2. **UI phải handle warning:** Show warning banner khi `data_quality` warning present.
3. **Assumption:** WS-C sẽ fix normalization TRƯỚC khi language filter feature được release. Nếu không fix, language filter sẽ có disclaimer trong UI.

---

## 10. Open Questions for Synthesis

### 10.1. Câu hỏi cần user/synthesis quyết định

| # | Câu hỏi | Options | Đề xuất WS-D | Impact |
|---|---------|---------|---------------|--------|
| Q1 | Route namespace prefix? | `(a) /v2/agent/job-posting` `(b) /v2/job-posting-agent` `(c) /v2/job-postings/{id}/assistant` | (a) | Toàn bộ route paths |
| Q2 | `messageCount` — computed hay stored? | `(a) Computed via COUNT` `(b) Stored column + trigger` | (a) | Performance vs complexity |
| Q3 | Title auto-gen — backend hay agent? | `(a) Backend truncate prompt` `(b) Agent generate title` `(c) Cả hai (agent Phase 2)` | (a) | Latency, complexity |
| Q4 | Tool messages mặc định show hay ẩn trong history? | `(a) Show (includeToolMessages=true default)` `(b) Ẩn (includeToolMessages=false default)` | (a) | UX, data transfer |
| Q5 | `modelMode` trong request — cho phép HR chọn hay hardcode? | `(a) Optional field, default "auto-agent"` `(b) Không expose, backend quyết định` | (b) | Complexity vs flexibility |
| Q6 | Có cần endpoint riêng get state (`GET /conversations/{id}/state`)? | `(a) Có — endpoint riêng` `(b) Không — state trong query response đủ` | (b) | Number of endpoints |
| Q7 | Pagination cho conversation list và message history? | `(a) Phase 1 không cần (max ~50 conversations)` `(b) Phase 1 cần (limit/offset)` | (a) | Complexity |

### 10.2. Inputs cần từ các workstream khác

| Từ | Input cần | Blocking? |
|----|-----------|-----------|
| WS-A | Confirm `AgentTurnResult` final fields | ✅ |
| WS-A | Confirm error type → HTTP status mapping | ✅ |
| WS-A | Confirm `modelMode` valid values cho agent | ⚠️ |
| WS-B | Confirm `messageCount` strategy | ⚠️ |
| WS-B | Confirm title auto-gen responsibility | ⚠️ |
| WS-C | Confirm tool input/output schemas cho sanitization | ⚠️ |
| WS-C | Confirm normalization fix timeline | ⚠️ |

---

## 11. Acceptance Criteria

### 11.1. API Contract

- [ ] Route namespace được confirm và document.
- [ ] `JobPostingAgentQueryRequest` schema finalized — tất cả fields, types, validations.
- [ ] `JobPostingAgentQueryResponse` schema finalized — bao gồm `toolCalls[]`, `workingSet`, `warnings`.
- [ ] Conversation CRUD endpoints (list, get messages, rename, archive) finalized.
- [ ] HTTP error codes cho mọi error scenario documented.
- [ ] Request validation rules rõ ràng cho mỗi endpoint.

### 11.2. UI Contract

- [ ] Chat pane layout contract — fields, vị trí, conditional display rules.
- [ ] Tool usage display design — collapsible, display names, status indicators.
- [ ] Working set badge design — label, count, filter chips.
- [ ] Loading state design — Phase 1 request-response, max 60s.
- [ ] Error state display mapping — HTTP status → Vietnamese message.
- [ ] Conversation list — title, last message time, message count.

### 11.3. Smoke Tests

- [ ] 7 smoke test flows documented với expected request/response.
- [ ] Postman collection spec cho tất cả flows.
- [ ] Error handling flows covered.

### 11.4. Cross-Workstream

- [ ] Dependencies từ WS-A/B/C documented với blocking status.
- [ ] NMAIex normalization bug impact acknowledged với warning mechanism.
- [ ] WS-D không duplicate normalization logic.

### 11.5. Non-Goals (Phase 1)

- [ ] ❌ Streaming/SSE — Phase 2.
- [ ] ❌ Dynamic tool catalog API — Phase 2.
- [ ] ❌ Pagination — Phase 2 (nếu data volume tăng).
- [ ] ❌ Cancel mid-turn — Phase 2.
- [ ] ❌ Summarize/branch-new — Phase 2.

---

## 12. Recommended Decisions For Synthesis

| # | Decision | Recommendation | Confidence |
|---|----------|----------------|-----------|
| D1 | Route namespace | `/v2/agent/job-posting` | High — extensible, clear |
| D2 | Phase 1 endpoints | 5 endpoints: query, list, get messages, rename, archive | High |
| D3 | Request scope | `jobPostId` + `hrId` (thay vì `jobAppId`) | Confirmed — locked |
| D4 | Response includes tool calls | `toolCalls[]` structured array trong query response | High |
| D5 | Response includes working set | `workingSet` object với `jobAppIds`, `label`, `activeFilters` | High |
| D6 | No streaming Phase 1 | Request-response, UI loading state | Confirmed — locked |
| D7 | Soft-delete only | `isArchived` flag, không hard delete | High |
| D8 | Title auto-gen | Backend truncate first prompt, HR can rename | High |
| D9 | messageCount computed | LEFT JOIN COUNT, không stored column | High |
| D10 | Tool display hardcoded | Frontend hardcode 7 tool display names Phase 1 | Medium — extensible Phase 2 |
| D11 | No modelMode exposure | Backend picks model, HR không chọn | Medium — có thể thay đổi |
| D12 | No pagination Phase 1 | Đủ cho initial scale (<50 conversations) | Medium |

---

## 13. Risks If Ignored

| # | Risk | Impact | Mitigation |
|---|------|--------|-----------|
| R1 | NMAIex normalization không fix trước launch | Language filter trả kết quả sai → HR mất tin tưởng | WS-C phải fix; WS-D thêm warning mechanism |
| R2 | Agent turn >60s timeout | UI treo, HR tưởng app crash | Loading state + timeout handler + error message |
| R3 | No streaming → UX kém | HR chờ lâu không biết agent đang làm gì | Clear loading indicator + Phase 2 SSE plan |
| R4 | Tool display name không đồng bộ với WS-C | UI hiện sai tên tool | WS-C confirm tool list trước implementation |
| R5 | `sourceJobAppIds` mapping fail | Response không grounded — HR không biết agent nói về ai | WS-C + WS-A đảm bảo ranking trả `jobAppId` |
| R6 | No pagination → slow list load | Conversation list hoặc message history chậm khi data lớn | Phase 2 pagination; Phase 1 OK với expected volume |
| R7 | State JSON schema drift | UI hiển thị sai working set/filters | WS-B lock state schema trước implementation |

---

## 14. Inputs Needed From Other Workstreams

### Từ WS-A (Agent Runtime)

1. **`AgentTurnResult` dataclass** — fields chính xác, types, nullable rules.
2. **Error types** — danh sách error classes và recommended HTTP status code.
3. **`modelMode` valid values** — nếu expose cho API, cần biết valid options.
4. **Max turn latency config** — confirm `JOBPOSTING_AGENT_MAX_TURN_SECONDS = 60`.

### Từ WS-B (Conversation Memory Schema)

1. **Confirm `messageCount`** — computed via COUNT (WS-D đề xuất) hay stored column.
2. **Confirm title auto-gen** — backend responsibility (WS-D đề xuất) hay agent.
3. **State JSON schema** — final `stateJson` structure, đặc biệt `workingSetLabel` và `activeFilters`.
4. **Tool call log sanitization rules** — fields nào luôn null, fields nào optional.

### Từ WS-C (Tool Contract)

1. **Tool input schemas** — để biết fields nào safe to display.
2. **Tool output summary format** — `resultSummary` format cho mỗi tool.
3. **`sourceJobAppIds` extraction logic** — tool nào trả `jobAppId`, format nào.
4. **NMAIex normalization fix timeline** — có fix trước Phase 1 launch không.
5. **Language filter enum mapping** — "hạng C" → proficiency value nào.

---

## 15. Checklist For Official Implementation Plan

### Files cần tạo mới

- [ ] `app/api/routes_jobposting_agent.py` — HTTP endpoint layer (5 endpoints Phase 1)
- [ ] `app/models/jobposting_agent.py` — Request/Response Pydantic models
- [ ] `app/services/jobposting_agent_persistence.py` — Persistence functions cho conversations/messages/state
- [ ] `tests/unit/unit_test_routes_jobposting_agent.py` — API route tests
- [ ] `tests/unit/unit_test_jobposting_agent_persistence.py` — Persistence tests

### Files cần sửa

- [ ] `app/main.py` — Register router `routes_jobposting_agent` với prefix `/v2/agent/job-posting`

### Pydantic Models cần define

- [ ] `JobPostingAgentQueryRequest`
- [ ] `JobPostingAgentQueryResponse`
- [ ] `ToolCallDetail`
- [ ] `WorkingSetInfo`
- [ ] `AgentWarning`
- [ ] `JobPostingConversationSummary`
- [ ] `JobPostingChatMessage`
- [ ] `RenameConversationRequest`
- [ ] `RenameConversationResponse`

### Persistence Functions cần implement

- [ ] `create_conversation(job_post_id, hr_id, title)`
- [ ] `get_conversation(conversation_id)`
- [ ] `list_conversations(hr_id, job_post_id)`
- [ ] `rename_conversation(conversation_id, title)`
- [ ] `archive_conversation(conversation_id)`
- [ ] `touch_conversation(conversation_id)`
- [ ] `insert_message(conv_id, role, content, ...)`
- [ ] `get_messages(conv_id, include_system, include_tool)`
- [ ] `get_full_history(conv_id)`
- [ ] `save_state(conv_id, state_json)`
- [ ] `get_state(conv_id)`
- [ ] `insert_tool_call_log(conv_id, msg_id, ...)`

### API Tests cần viết

- [ ] Test query endpoint — happy path, new conversation
- [ ] Test query endpoint — continue conversation
- [ ] Test query endpoint — invalid jobPostId → 404
- [ ] Test query endpoint — invalid hrId → 403
- [ ] Test query endpoint — archived conversation → 410
- [ ] Test list conversations — filter by jobPostId + hrId
- [ ] Test get messages — include/exclude tool messages
- [ ] Test rename — happy path
- [ ] Test rename — invalid title → 400
- [ ] Test archive — happy path, verify list exclusion

### Smoke Test Postman Collection

- [ ] Flow 1: Top 10 ranking analysis
- [ ] Flow 2: Refine with language filter
- [ ] Flow 3: Too-large set rejection
- [ ] Flow 4: Rename conversation
- [ ] Flow 5: New conversation + auto title
- [ ] Flow 6: Archive conversation
- [ ] Flow 7: Invalid request handling

### Cross-Workstream Coordination

- [ ] Confirm `AgentTurnResult` fields với WS-A
- [ ] Confirm `messageCount` strategy với WS-B
- [ ] Confirm title auto-gen responsibility với WS-B
- [ ] Confirm tool schemas và display names với WS-C
- [ ] Document NMAIex normalization dependency và warning mechanism

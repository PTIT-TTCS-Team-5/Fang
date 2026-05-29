# WS-B — Dedicated Conversation Tables and Memory State

## Discovery Report — Input cho Official Implementation Plan

> **Workstream:** WS-B — Dedicated Conversation Tables and Memory State
> **Mục đích:** Phân tích persistence hiện tại, đề xuất schema cho JobPosting Agent conversation, memory state, tool-call logging, và conversation UX. Report này là input cho tier 1 synthesis, KHÔNG phải implementation plan chính thức.
> **Ngày:** 2026-05-28
> **Ràng buộc:** Không code, không sửa file runtime, không tạo migration.
> **Database engine:** PostgreSQL (pgvector, UUID, JSONB — xác nhận từ `schema_ai_core.sql`)

---

## 1. Executive Summary

JobPosting Agent C3.1 yêu cầu hệ thống persistence hoàn toàn mới, tách biệt khỏi JobApplication Chat hiện tại. Lý do cốt lõi: scope conversation khác nhau cơ bản — chat hiện tại scope theo `jobAppId` (một ứng viên, qua bảng `AICHATCONVERSATION`), còn JobPosting Agent scope theo `jobPostId` (một tin tuyển dụng, nhiều ứng viên).

Report này đề xuất **4 bảng chính** và **1 bảng tùy chọn**:

| Bảng | Vai trò | Bắt buộc? |
|---|---|---|
| `AIJOBPOSTINGCHATCONVERSATION` | Header conversation, scope `jobPostId` + `hrId` | ✅ Bắt buộc |
| `AIJOBPOSTINGCHATMESSAGE` | Lưu message lịch sử, hỗ trợ role `tool_call`/`tool_result` | ✅ Bắt buộc |
| `AIJOBPOSTINGCHATSTATE` | State JSON cho working set, filters, context multi-turn | ✅ Bắt buộc (Decision Lock) |
| `AIJOBPOSTINGTOOLCALLLOG` | Audit log tool call (không PII) | ✅ Khuyến nghị mạnh |
| `AIJOBPOSTINGTOOL` | Tool catalog — registry tool declarations, FK cho tool-call log | ⚠️ Planning Brief nghiêng về có, cần WS-A confirm |

**Nguyên tắc thiết kế:**
- Tách biệt hoàn toàn khỏi `AICHATCONVERSATION`/`AICHATMESSAGE`. Không thêm column vào bảng hiện tại.
- Soft-delete (archive), không hard-delete.
- Không cascade delete từ `JOBPOSTING`/`HR`.
- Không lưu PII trong tool call log.
- Không lưu full CV content trong message.
- State JSON minimal — chỉ chứa reference (IDs), không chứa data có thể re-fetch.
- Dùng PostgreSQL native types: `UUID`, `SERIAL`, `TIMESTAMP`, `JSONB`, `TEXT`.
- Theo đúng naming/pattern convention từ `schema_ai_core.sql`.

---

## 2. Current Persistence Reality

### 2.1 Bảng chat hiện có (schema_ai_core.sql)

**`AICHATCONVERSATION`** (Lines 88-96):

| Cột | Kiểu | Constraints |
|---|---|---|
| `conversationId` | `UUID` | PK, DEFAULT `gen_random_uuid()` |
| `jobAppId` | `INT NOT NULL` | FK → `JOBAPPLICATION(jobAppId)` |
| `hrId` | `INT NOT NULL` | FK → `HR(userId)` |
| `createdAt` | `TIMESTAMP NOT NULL` | DEFAULT `CURRENT_TIMESTAMP` |
| `lastMessageAt` | `TIMESTAMP NOT NULL` | DEFAULT `CURRENT_TIMESTAMP` |

- Index: `idx_conversation_hr_jobapp ON (hrId, jobAppId)` — composite B-tree

**`AICHATMESSAGE`** (Lines 101-114):

| Cột | Kiểu | Constraints |
|---|---|---|
| `messageId` | `SERIAL` | PK |
| `conversationId` | `UUID NOT NULL` | FK → `AICHATCONVERSATION(conversationId)` |
| `role` | `VARCHAR(20) NOT NULL` | `'user'`, `'assistant'`, `'system'` |
| `content` | `TEXT NOT NULL` | — |
| `model` | `VARCHAR(100)` | NULL cho user/system messages |
| `modelMode` | `VARCHAR(50)` | nullable |
| `topK` | `INT` | nullable |
| `latencyMs` | `INT` | nullable |
| `fallbackPath` | `TEXT` | nullable |
| `summarized` | `BOOLEAN NOT NULL` | DEFAULT `FALSE` |
| `createdAt` | `TIMESTAMP NOT NULL` | DEFAULT `CURRENT_TIMESTAMP` |

- Index: `idx_chatmessage_conversation ON (conversationId, createdAt)` — composite B-tree

**`AIQUERYLOG`** (Lines 70-84) — Legacy audit log, scope `jobAppId`:

| Cột chính | Kiểu |
|---|---|
| `queryId SERIAL PK` | — |
| `jobAppId INT NOT NULL` | FK → `JOBAPPLICATION` |
| `hrId INT NOT NULL` | FK → `HR` |
| `prompt TEXT`, `response TEXT`, `topK INT`, `latencyMs INT`, `model`, `modelMode`, `fallbackPath` | — |

### 2.2 Vì sao không thể tái sử dụng

| Khía cạnh | Chat hiện tại | JobPosting Agent cần |
|---|---|---|
| Scope | `jobAppId` (1 ứng viên) | `jobPostId` (1 job, N ứng viên) |
| PK conversation | `UUID` (gen_random_uuid) | Giữ UUID pattern — nhất quán |
| Roles | `user`, `assistant`, `system` | `user`, `assistant`, `system`, `tool_call`, `tool_result` |
| Working set / memory | Không có | Cần lưu `jobAppId[]` working set |
| State | Stateless mỗi turn (rebuild system prompt mỗi request) | Persistent state qua các turn |
| Tool logging | Không có (chỉ `AIQUERYLOG` cho RAG queries) | Cần audit log tool call riêng |
| Tool metadata trên message | Không có `toolName`/`toolCallId` | Cần `toolName`, `toolCallId` |
| Summarization | `summarized BOOLEAN` trên message | Cùng pattern, nhưng scope khác |
| Conversation title/rename | Không có column `title` | Cần title + rename support |

**Kết luận:** Retrofit `AICHATCONVERSATION`/`AICHATMESSAGE` sẽ gây:
1. Schema conflict (nullable `jobAppId` vs `jobPostId` — cả hai NOT NULL hiện tại)
2. Regression risk cho JobApplication Chat đang hoạt động
3. Mất rõ ràng scope (không biết conversation nào là loại gì)

> **Decision Lock** (từ Planning Brief §2): Dùng dedicated tables, KHÔNG reuse.

### 2.3 Code persistence hiện tại

**`chat_persistence.py`** — CRUD layer:
- `create_conversation(job_app_id, hr_id)` → INSERT, trả UUID
- `insert_message(conversation_id, role, content, *, model, model_mode, top_k, latency_ms, fallback_path)` → INSERT + `touch_conversation()`
- `get_messages(conversation_id, *, include_system=False)` → SELECT ORDER BY createdAt ASC
- `list_conversations(hr_id, job_app_id)` → LEFT JOIN message count
- `touch_conversation(conversation_id)` → UPDATE `lastMessageAt`
- `mark_messages_summarized(conversation_id, up_to_message_id)` → UPDATE `summarized=TRUE`

**`rag_query.py`** — Context construction:
- `_build_system_prompt()` → fetch job posting + candidate + CV chunks + ATS history mỗi request
- Token budget: `context_budget_lite = 180,000`, `context_budget_pro = 960,000`
- `ContextWarning` khi đạt 80% budget → options: `"summarize_and_continue"` hoặc `"new_conversation_with_summary"`

**`routes_chat.py`** — Summarization endpoints:
- `POST /chat/conversations/{id}/summarize` → summarize in-place
- `POST /chat/conversations/{id}/branch-new` → new conversation with summary

**Không có:** state management, working set, tool-call logging, tool metadata.

### 2.4 Pydantic models hiện tại (chat.py)

```python
class ChatQueryRequest(BaseModel):
    jobAppId: int
    hrId: int
    prompt: str
    conversationId: uuid.UUID | None = None
    modelMode: str  # 1 of 7 modes

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
```

**Quan sát:** Không có `toolName`, `toolCallId`, `stateJson`, `title`, `isArchived`. Models mới cho JobPosting Agent cần thiết kế riêng.

### 2.5 FK targets có sẵn (schema_web_core.sql)

| Bảng target | PK | Ghi chú |
|---|---|---|
| `JOBPOSTING` | `jobPostId SERIAL PK` | FK target cho conversation → `jobPostId` |
| `HR` | `userId INT PK` | FK target cho conversation → `hrId` |
| `JOBAPPLICATION` | `jobAppId SERIAL PK` | **Không FK trực tiếp** từ bảng mới, nhưng working set chứa `jobAppId` refs trong JSONB |

- `JOBAPPLICATION.jobPostId` → `JOBPOSTING(jobPostId)` — index có sẵn, dùng để validate working set membership

### 2.6 Ranking data liên quan

- `nmaiex_ranking_service.py`: `get_ranking(job_post_id, limit, filters)` trả về list candidates với `jobAppId` + score
- Ranking result structure: `{"jobPostId", "candidates": [{"jobAppId", "score", ...}], "totalCount", "returnedCount"}`
- Đây là nguồn working set chính cho agent state

### 2.7 Mapper service liên quan (nmaiex_mapper_service.py)

- `map_string_to_province_id(province_name) -> Optional[int]` — normalize tỉnh
- `normalize_proficiency(raw_proficiency) -> Optional[str]` — normalize trình độ ("A1", "A2", "B1", "B2", "C1", "C2")
- **Không có `normalize_language()`** — thiếu language name mapper → normalization bug WS-C phải fix
- Các giá trị normalized từ mapper này sẽ xuất hiện trong `stateJson.activeFilters`

---

## 3. Proposed Tables

> **Convention:** Tất cả DDL theo PostgreSQL syntax, matching pattern từ `schema_ai_core.sql`. Naming: `AIJOBPOSTING*` prefix, lowercase index prefix `idx_`.

### 3.1 `AIJOBPOSTINGCHATCONVERSATION`

Header conversation, scope theo `jobPostId` + `hrId`. Hỗ trợ title rename và soft-archive.

```sql
-- ========== JobPosting Agent Chat (C3) ==========

CREATE TABLE AIJOBPOSTINGCHATCONVERSATION (
    conversationId  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jobPostId       INT NOT NULL,
    hrId            INT NOT NULL,
    title           VARCHAR(200) NOT NULL DEFAULT 'Cuộc trò chuyện mới',
    createdAt       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lastMessageAt   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    isArchived      BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (jobPostId) REFERENCES JOBPOSTING(jobPostId),
    FOREIGN KEY (hrId) REFERENCES HR(userId)
);

CREATE INDEX IF NOT EXISTS idx_jpchat_conv_jobpost_hr
    ON AIJOBPOSTINGCHATCONVERSATION (jobPostId, hrId);
```

**Quyết định thiết kế:**

| Quyết định | Lý do |
|---|---|
| `UUID PK` với `gen_random_uuid()` | Nhất quán với `AICHATCONVERSATION`. UUID tốt cho distributed systems và frontend routing |
| Composite index `(jobPostId, hrId)` | Query phổ biến nhất: list conversations cho 1 HR trên 1 job posting |
| `title VARCHAR(200)` | **Mới so với chat cũ** — chat cũ không có title. Planning Brief yêu cầu conversation rename |
| `lastMessageAt` | Pattern từ `AICHATCONVERSATION`. Dùng cho ORDER BY khi list conversations |
| `isArchived BOOLEAN` | **Mới so với chat cũ** — chat cũ không có archive. Soft-delete pattern |
| Không cascade delete | Conversations persist cho audit khi job posting bị xóa |
| Không column `status`, `summaryVersion` | Deep Advisory đề xuất optional. Defer cho Phase 2+ để giữ schema minimal |

### 3.2 `AIJOBPOSTINGCHATMESSAGE`

Lưu toàn bộ message history, bao gồm tool call/result. Mở rộng schema so với `AICHATMESSAGE`.

```sql
CREATE TABLE AIJOBPOSTINGCHATMESSAGE (
    messageId       SERIAL PRIMARY KEY,
    conversationId  UUID NOT NULL,
    role            VARCHAR(20) NOT NULL,  -- 'user' | 'assistant' | 'system' | 'tool_call' | 'tool_result'
    content         TEXT NOT NULL,
    toolName        VARCHAR(100),          -- NOT NULL khi role = 'tool_call' hoặc 'tool_result'
    toolCallId      VARCHAR(100),          -- ID liên kết tool_call ↔ tool_result
    model           VARCHAR(100),          -- model used, null cho user/system/tool messages
    modelMode       VARCHAR(50),           -- nullable, nhất quán với AICHATMESSAGE
    latencyMs       INT,                   -- nullable, nhất quán với AICHATMESSAGE
    summarized      BOOLEAN NOT NULL DEFAULT FALSE,
    createdAt       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversationId) REFERENCES AIJOBPOSTINGCHATCONVERSATION(conversationId)
);

CREATE INDEX IF NOT EXISTS idx_jpchat_msg_conv_created
    ON AIJOBPOSTINGCHATMESSAGE (conversationId, createdAt);
```

**Quyết định thiết kế:**

| Quyết định | Lý do |
|---|---|
| `role VARCHAR(20)` | Nhất quán với `AICHATMESSAGE`. Giá trị hợp lệ: `user`, `assistant`, `system`, `tool_call`, `tool_result`. Enforcement ở application layer (Pydantic) |
| `toolName VARCHAR(100)` nullable | Chỉ populate khi role là `tool_call` hoặc `tool_result`. NULL cho user/assistant/system messages |
| `toolCallId VARCHAR(100)` nullable | ID do LLM provider generate (Google GenAI). Match `tool_call` → `tool_result` trong cùng agent loop turn. FANG fallback: generate UUID nếu provider không cung cấp |
| `model`, `modelMode`, `latencyMs` | Giữ nhất quán với `AICHATMESSAGE`. Tracking model used per response |
| `summarized BOOLEAN` | Reuse summarization pattern từ existing chat |
| Composite index `(conversationId, createdAt)` | Ordered message retrieval — pattern từ `idx_chatmessage_conversation` |
| Không column `topK`, `fallbackPath` | Không cần trong agent context (khác RAG chat). Giữ schema focused |
| Không column `sequenceNumber` | Dùng `messageId SERIAL` + `createdAt` cho ordering — đơn giản, đã proven trong chat cũ |

**Lưu ý quan trọng về content cho tool messages:**

| Role | Content chứa | Ví dụ |
|---|---|---|
| `user` | Text message từ HR | "Phân tích 10 ứng viên rank cao nhất" |
| `assistant` | Response text từ agent | Full analysis text |
| `system` | System prompt hoặc summary | Context injection, summarization |
| `tool_call` | JSON params của tool call | `{"job_post_id": 123, "limit": 10}` |
| `tool_result` | **Summary** tool result (KHÔNG full result) | `{"returnedCount": 10, "topScore": 0.95}` |

**KHÔNG BAO GIỜ** lưu full CV text, email, phone trong content của bất kỳ role nào.

### 3.3 `AIJOBPOSTINGCHATSTATE`

State JSON cho working set, filters, context multi-turn. Quan hệ 1:1 với conversation.

```sql
CREATE TABLE AIJOBPOSTINGCHATSTATE (
    conversationId  UUID PRIMARY KEY,
    stateJson       JSONB NOT NULL DEFAULT '{}',
    updatedAt       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversationId) REFERENCES AIJOBPOSTINGCHATCONVERSATION(conversationId)
);
```

**Không cần index riêng** — `conversationId` là PK, đã có unique index tự động.

**Quyết định thiết kế:**

| Quyết định | Lý do |
|---|---|
| `conversationId UUID` là PK (1:1) | Mỗi conversation chỉ có 1 state. PK tự nhiên hơn UNIQUE constraint riêng |
| `JSONB` (không `TEXT`) | PostgreSQL JSONB cho phép query operators (`->`, `->>`, `@>`), indexing, và validation tốt hơn plain TEXT. Nhất quán với `CVPARSED.parsedJson JSONB` và `AIDOCUMENTCHUNK.metadata JSONB` |
| Bảng riêng thay vì column trên conversation | Tách concern: metadata (title, dates) thay đổi ít, state thay đổi mỗi turn. Tránh lock contention. Deep Advisory + Planning Brief đều recommend |
| `updatedAt` | Track khi state thay đổi lần cuối, independent từ `lastMessageAt` trên conversation |
| DEFAULT `'{}'` | State luôn tồn tại, bắt đầu từ empty object. Tránh NULL check |

> **Decision Lock** (Planning Brief §2): `AIJOBPOSTINGCHATSTATE` là bắt buộc.

### 3.4 `AIJOBPOSTINGTOOLCALLLOG`

Audit log cho mọi tool call agent thực hiện. Mục đích: debug, monitoring, performance tracking. KHÔNG phải replay.

```sql
CREATE TABLE AIJOBPOSTINGTOOLCALLLOG (
    toolCallLogId   SERIAL PRIMARY KEY,
    conversationId  UUID NOT NULL,
    messageId       INT,                    -- FK tới message tool_call tương ứng, NULL nếu log trước save message
    jobPostId       INT NOT NULL,           -- denormalized cho query tiện
    hrId            INT NOT NULL,           -- denormalized cho query tiện
    toolName        VARCHAR(100) NOT NULL,
    toolInput       JSONB,                  -- params đã sanitize (KHÔNG PII)
    toolOutputMeta  JSONB,                  -- summary result (KHÔNG full data)
    status          VARCHAR(20) NOT NULL DEFAULT 'success', -- 'success' | 'error' | 'timeout'
    latencyMs       INT,
    errorMsg        TEXT,
    createdAt       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversationId) REFERENCES AIJOBPOSTINGCHATCONVERSATION(conversationId),
    FOREIGN KEY (messageId) REFERENCES AIJOBPOSTINGCHATMESSAGE(messageId)
);

CREATE INDEX IF NOT EXISTS idx_jpchat_toollog_conv
    ON AIJOBPOSTINGTOOLCALLLOG (conversationId);
```

**Quyết định thiết kế:**

| Quyết định | Lý do |
|---|---|
| `JSONB` cho `toolInput`/`toolOutputMeta` | Nhất quán với JSONB usage trong project. Query operators tiện cho debugging |
| `jobPostId`, `hrId` denormalized | Deep Advisory đề xuất. Cho phép query tool call log theo job posting hoặc HR mà không cần JOIN conversation table |
| `messageId INT` nullable | Tool call có thể log trước khi message saved, hoặc khi tool fail trước message creation |
| `status VARCHAR(20)` | Application-level enum: `success`, `error`, `timeout` |
| `errorMsg TEXT` nullable | Chỉ populate khi status ≠ `success` |
| `latencyMs INT` nullable | Performance tracking. NULL nếu tool bị interrupt |
| `toolInput` đã sanitize | KHÔNG chứa PII. Chỉ log params như `{"job_post_id": 123, "limit": 10}` |
| `toolOutputMeta` là summary | KHÔNG full output. Ví dụ: `{"returnedCount": 10, "totalCount": 50}` |

### 3.5 `AIJOBPOSTINGTOOL` (Tool Catalog — Quyết định cần WS-A confirm)

Registry tool declarations. Planning Brief §2 nghiêng về TẠO bảng này để tool-call log có `toolId` FK thay vì chỉ `toolName` text.

```sql
-- TÙY CHỌN — Tạo nếu WS-A confirm cần tool catalog table
CREATE TABLE AIJOBPOSTINGTOOL (
    toolId          SERIAL PRIMARY KEY,
    toolName        VARCHAR(100) NOT NULL UNIQUE,
    displayName     VARCHAR(200) NOT NULL,
    description     TEXT,
    inputSchemaJson JSONB,
    outputSchemaJson JSONB,
    isEnabled       BOOLEAN NOT NULL DEFAULT TRUE,
    category        VARCHAR(50),
    createdAt       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**Nếu tạo bảng này**, thêm FK từ `AIJOBPOSTINGTOOLCALLLOG`:
```sql
ALTER TABLE AIJOBPOSTINGTOOLCALLLOG
    ADD COLUMN toolId INT REFERENCES AIJOBPOSTINGTOOL(toolId);
```

**Phân tích lựa chọn:**

| Lựa chọn | Ưu | Nhược |
|---|---|---|
| **Tạo ngay (Planning Brief nghiêng về đây)** | Tool-call log có FK integrity. Admin UI sau này dễ. WS-A có thể load tool declarations từ DB. Version/enable control | Thêm 1 bảng + INSERT seed data cho 7 tools |
| **Defer sang Phase 2+** | Đơn giản hơn. Tool declarations hardcode, chỉ 7 tools | Tool-call log chỉ có `toolName` text, không integrity check |

**Đề xuất:** Tạo `AIJOBPOSTINGTOOL` ngay Phase 1, seed 7 MVP tools. Lý do:
1. Planning Brief §2 đã nghiêng về có.
2. Cost rất thấp (1 bảng, 7 rows seed).
3. Tool-call log có FK integrity.
4. Extensible cho Phase 2+ mà không cần migration sửa `AIJOBPOSTINGTOOLCALLLOG`.

**Tuy nhiên, cần WS-A confirm:** Nếu WS-A quyết định tool declarations static trong code (không dynamic), thì defer. Open question cho synthesis.

---

## 4. State JSON Design

### 4.1 Schema `stateJson` (JSONB)

```json
{
    "schemaVersion": 1,
    "workingSetJobAppIds": [456, 789, 12],
    "workingSetLabel": "Top 10 ranking cho vị trí Backend Developer",
    "lastToolName": "get_job_candidate_ranking",
    "lastToolParams": {
        "job_post_id": 123,
        "limit": 10
    },
    "activeFilters": {
        "language": "English",
        "proficiency": "C1",
        "province": "Hồ Chí Minh"
    }
}
```

### 4.2 Giải thích từng field

| Field | Kiểu | Mô tả | Bắt buộc? |
|---|---|---|---|
| `schemaVersion` | `int` | Version schema state cho backward compatibility nếu evolve | ✅ Recommended |
| `workingSetJobAppIds` | `int[]` | Danh sách `jobAppId` đang trong working set. Nguồn: ranking service, search, filter. **Key là `jobAppId`, KHÔNG phải `candidateId`** (Decision Lock) | ✅ Required |
| `workingSetLabel` | `string` | Label người đọc cho working set. Agent tự generate | ✅ Required |
| `lastToolName` | `string \| null` | Tên tool cuối cùng. Context cho turn tiếp theo | ⚠️ Optional |
| `lastToolParams` | `object \| null` | Params tool call cuối | ⚠️ Optional |
| `activeFilters` | `object \| null` | Filters đang active. Values dùng normalized enum (WS-C dependency) | ⚠️ Optional |

### 4.3 Thêm fields có thể mở rộng (từ Planning Brief scope)

Planning Brief §6 WS-B cũng đề cập:

| Field | Mô tả | Phase |
|---|---|---|
| `lastRanking` | Last ranking result IDs (nếu cần phân biệt ranking vs filter result) | Phase 1 nếu cần, nhưng `workingSetJobAppIds` đã cover |
| `lastCandidateSummaries` | Summaries of prior analysis | ⚠️ **Cân nhắc kỹ** — lưu summary text có thể stale. Khuyến nghị KHÔNG lưu, agent re-analyze từ tools |
| `compareScope` | Comparison target IDs | Có thể dùng `workingSetJobAppIds` thay thế |
| `warnings` | Guardrail warnings | Phase 1 nếu cần. Ví dụ: `"warning": "working set truncated from 50 to 25"` |

**Khuyến nghị:** Giữ minimal schema ở Section 4.1. Không lưu `lastCandidateSummaries` (vi phạm nguyên tắc "don't store derived data" — KINH_NGHIEM.md). `compareScope` dùng `workingSetJobAppIds` luôn.

### 4.4 Nguyên tắc state

1. **Chỉ references, không data:** State lưu `jobAppId[]`, KHÔNG lưu candidate name, score, CV content. Data luôn re-fetch.
2. **Không lưu ranking scores:** Scores thay đổi khi re-rank. Always fetch fresh (KINH_NGHIEM.md: "Don't store derived data").
3. **Filter values dùng normalized enum:** `activeFilters.proficiency` phải là giá trị normalized (`"C1"`, `"B2"`) mà WS-C đảm bảo tồn tại. **Dependency lên WS-C.**
4. **State update mỗi turn có tool call:** Sau tool call → update state. Turn chỉ text response → state không đổi.
5. **Size limit:** Working set tối đa 25 `jobAppId` (HR max top N = 25, configurable). State JSON estimated max: ~2KB.
6. **`schemaVersion`:** Thêm field này cho future-proofing. Nếu state schema evolve, application code kiểm tra version và migrate in-place.

### 4.5 Ví dụ flow state evolution

| Turn | User message | Agent action | `workingSetJobAppIds` | `workingSetLabel` | `activeFilters` |
|---|---|---|---|---|---|
| 1 | "Phân tích 10 ứng viên rank cao nhất" | Gọi `get_job_candidate_ranking(limit=10)` | `[456,789,12,…]` (10 IDs) | "Top 10 ranking" | `null` |
| 2 | "Trong 10 ông này lọc tiếng Anh hạng C trở lên" | Filter working set theo language data | `[456,12]` (2 IDs) | "2/10 ứng viên tiếng Anh C1+" | `{"language":"English","proficiency":"C1"}` |
| 3 | "So sánh chi tiết 2 người này" | 2 ≤ 25, cho phép compare | Unchanged | Unchanged | Unchanged |
| 4 | "So sánh tất cả ứng viên" | totalCount > 25, từ chối, tư vấn filter | Unchanged | Unchanged | Unchanged |

### 4.6 Validation rules (application layer)

- `workingSetJobAppIds` mỗi item: `INT > 0`
- `workingSetJobAppIds.length` ≤ 25 (configurable via `.env`)
- `workingSetLabel.length` ≤ 200 chars
- `lastToolName` nếu có: match tool name trong WS-C tool contract
- `activeFilters` values: normalized enum space (WS-C responsibility)
- Toàn bộ validation ở Pydantic model, KHÔNG ở SQL constraint
- **Validate working set membership:** Khi load state, verify mỗi `jobAppId` trong `workingSetJobAppIds` thực sự thuộc về `jobPostId` của conversation (query `JOBAPPLICATION WHERE jobAppId IN (...) AND jobPostId = ?`)

---

## 5. Conversation UX Persistence

### 5.1 Conversation lifecycle operations

| Operation | SQL Pattern | Notes |
|---|---|---|
| **Create** | `INSERT INTO AIJOBPOSTINGCHATCONVERSATION (jobPostId, hrId) VALUES ($1, $2) RETURNING conversationId` | Title mặc định, auto-UUID |
| **Create state** | `INSERT INTO AIJOBPOSTINGCHATSTATE (conversationId) VALUES ($1)` | Init empty `{}` state cùng lúc tạo conversation |
| **List** | `SELECT ... FROM AIJOBPOSTINGCHATCONVERSATION WHERE jobPostId=$1 AND hrId=$2 AND isArchived=FALSE ORDER BY lastMessageAt DESC` | Chỉ conversations chưa archive, mới nhất trước |
| **Get history** | `SELECT * FROM AIJOBPOSTINGCHATMESSAGE WHERE conversationId=$1 ORDER BY createdAt ASC` | Load toàn bộ messages |
| **Get state** | `SELECT stateJson FROM AIJOBPOSTINGCHATSTATE WHERE conversationId=$1` | Load state hiện tại |
| **Save message** | `INSERT INTO AIJOBPOSTINGCHATMESSAGE (...) VALUES (...); UPDATE AIJOBPOSTINGCHATCONVERSATION SET lastMessageAt=CURRENT_TIMESTAMP WHERE conversationId=$1` | Touch conversation on new message |
| **Update state** | `UPDATE AIJOBPOSTINGCHATSTATE SET stateJson=$1, updatedAt=CURRENT_TIMESTAMP WHERE conversationId=$2` | After tool call changes working set |
| **Rename** | `UPDATE AIJOBPOSTINGCHATCONVERSATION SET title=$1 WHERE conversationId=$2` | HR rename conversation |
| **Archive** | `UPDATE AIJOBPOSTINGCHATCONVERSATION SET isArchived=TRUE WHERE conversationId=$1` | Soft-delete |

### 5.2 Default title và auto-generate

- **Initial:** Title mặc định `'Cuộc trò chuyện mới'` (nhất quán, nhưng context khác: JobPosting Agent thay vì CV Chat).
- **Auto-generate strategy:**
  - Sau message đầu tiên của user, backend hoặc agent generate title từ user message (truncate ~100 chars).
  - Ví dụ: "Phân tích 10 ứng viên rank…" → title = "Phân tích 10 ứng viên rank cao nhất"
  - **Responsibility:** WS-A (agent runtime) hoặc backend code. KHÔNG DB trigger. KHÔNG stored procedure.
- **Rename:** HR rename qua API endpoint (WS-D).

### 5.3 History loading strategy

| Phase | Strategy |
|---|---|
| **Phase 1** | Load toàn bộ messages cho conversation. Expected conversation length < 50 messages (read-only tools, max 25 working set) |
| **Phase 2+** (defer) | Pagination hoặc summarization cho long conversations. Summarization pattern đã proven trong chat cũ (`summarized BOOLEAN`, `mark_messages_summarized()`) |

**Tái sử dụng summarization pattern từ chat cũ:** Column `summarized BOOLEAN` đã có trong `AIJOBPOSTINGCHATMESSAGE` schema. Summarization flow (summarize in-place + branch-new) có thể adapt cho JobPosting Agent nếu cần.

### 5.4 Multi-conversation per job posting

- Một HR có thể tạo nhiều conversations cho cùng 1 `jobPostId`.
- Mỗi conversation có state riêng biệt, working set riêng biệt.
- Use case: thử các góc nhìn khác nhau (kỹ năng vs vùng miền vs language filter).
- List conversations cho HR trên job posting: `WHERE jobPostId=$1 AND hrId=$2` → composite index `idx_jpchat_conv_jobpost_hr` handles.

---

## 6. Tool Catalog and Tool Call Logging

### 6.1 Tool Catalog (`AIJOBPOSTINGTOOL`)

**Planning Brief §2 nghiêng về TẠO** — "Lean toward dedicated tool catalog table để tool-call log có `toolId` FK."

Nếu tạo, seed 7 MVP tools (WS-C định nghĩa):

| `toolName` | `displayName` | `category` |
|---|---|---|
| `get_job_posting_context` | Xem thông tin tin tuyển dụng | `context` |
| `get_job_candidate_ranking` | Xếp hạng ứng viên | `ranking` |
| `search_job_applications_text` | Tìm kiếm ứng viên | `search` |
| `get_job_application_summary` | Tóm tắt ứng viên | `detail` |
| `get_job_application_full_cv` | Xem CV đầy đủ | `detail` |
| `get_candidate_ats_history` | Lịch sử tuyển dụng | `detail` |
| `count_job_applications` | Đếm ứng viên | `aggregate` |

**Open question cho synthesis:** WS-A cần confirm tool declarations static (hardcode trong config) hay dynamic (load từ DB). Nếu dynamic → tạo `AIJOBPOSTINGTOOL` ngay. Nếu static → defer.

### 6.2 Tool Call Logging (`AIJOBPOSTINGTOOLCALLLOG`)

**Quyết định: Tạo ngay Phase 1.** Lý do:
1. Debug agent behavior: tool nào gọi, params gì, result gì, bao lâu
2. Performance monitoring: latency trends, error rates
3. Audit trail cho compliance
4. Cost thấp: ~1 row per tool call, ~1-2KB JSONB

### 6.3 Tool name alignment — Critical

`toolName` trong `AIJOBPOSTINGCHATMESSAGE` và `AIJOBPOSTINGTOOLCALLLOG` **phải match chính xác** WS-C tool names.

**Dependency:** Nếu WS-C đổi tên tool, WS-B log sẽ dùng tên mới. Nếu tạo `AIJOBPOSTINGTOOL`, tool name là UNIQUE constraint → rename cần UPDATE, không INSERT mới.

---

## 7. Privacy and Logging Boundaries

### 7.1 KHÔNG được lưu

| Dữ liệu | Nơi bị cấm | Lý do |
|---|---|---|
| Full CV text/PDF content | `AIJOBPOSTINGCHATMESSAGE`, `AIJOBPOSTINGTOOLCALLLOG` | PII risk, table bloat. CV fetch on-demand từ `CVPARSED` |
| Candidate email, phone | Tất cả bảng agent | PII |
| Full ranking result JSON | `toolOutputMeta` trong log | Quá lớn, chứa PII (names). Chỉ lưu summary counts |
| Full candidate data | `stateJson` | State chỉ chứa `jobAppId` references |
| Raw CV parsed JSON | `AIJOBPOSTINGCHATMESSAGE` content | Dùng `jobAppId` reference, fetch từ `CVPARSED.parsedJson` |

### 7.2 ĐƯỢC lưu

| Dữ liệu | Bảng/Column | Ví dụ |
|---|---|---|
| User message text | `AIJOBPOSTINGCHATMESSAGE.content` | "Phân tích 10 ứng viên rank cao nhất" |
| Assistant response text | `AIJOBPOSTINGCHATMESSAGE.content` | Full analysis text (đã redact nếu cần) |
| Tool call params (sanitized) | `toolInput JSONB` | `{"job_post_id": 123, "limit": 10}` |
| Tool result summary | `toolOutputMeta JSONB` | `{"returnedCount": 10, "totalCount": 50}` |
| Working set `jobAppId` list | `stateJson` | `[456, 789, 12]` |
| Tool performance | `latencyMs`, `status` | `1250`, `"success"` |

### 7.3 Assistant response — edge case

Agent response (`role = 'assistant'`) có thể mention candidate names vì HR đã có quyền truy cập data này qua `JOBPOSTING`. Tuy nhiên:
- Agent system prompt sẽ enforce: không mention email/phone
- Response text là nội dung HR trực tiếp đọc — acceptable to store

---

## 8. Migration and Index Plan Input

### 8.1 Migration strategy

| Aspect | Approach |
|---|---|
| **Placement** | Thêm DDL vào `schema_ai_core.sql` (hoặc file migration riêng nếu team adopt migration framework) |
| **Convention** | Theo pattern hiện tại: raw DDL, `CREATE TABLE` + `CREATE INDEX IF NOT EXISTS` |
| **Idempotent** | Indexes dùng `IF NOT EXISTS`. Tables không có `IF NOT EXISTS` trong PostgreSQL standard (`CREATE TABLE IF NOT EXISTS` supported) |
| **Rollback** | `DROP TABLE IF EXISTS` theo thứ tự ngược FK: `AIJOBPOSTINGTOOLCALLLOG` → `AIJOBPOSTINGCHATSTATE` → `AIJOBPOSTINGCHATMESSAGE` → `AIJOBPOSTINGCHATCONVERSATION` → (optional) `AIJOBPOSTINGTOOL` |
| **Data migration** | Không cần — tất cả bảng mới, không migrate data từ chat cũ |
| **Template variables** | Không cần `__TTCS_EMBEDDING_DIM__` hay tương tự — schema thuần SQL types |

### 8.2 Order tạo bảng

1. `AIJOBPOSTINGTOOL` (optional, nếu tạo — no FK dependency)
2. `AIJOBPOSTINGCHATCONVERSATION` (FK → `JOBPOSTING`, `HR`)
3. `AIJOBPOSTINGCHATMESSAGE` (FK → conversation)
4. `AIJOBPOSTINGCHATSTATE` (FK → conversation)
5. `AIJOBPOSTINGTOOLCALLLOG` (FK → conversation, message; optional FK → tool)

### 8.3 Index plan

| Index | Bảng | Columns | Purpose |
|---|---|---|---|
| `idx_jpchat_conv_jobpost_hr` | `AIJOBPOSTINGCHATCONVERSATION` | `(jobPostId, hrId)` | List conversations per HR per job |
| `idx_jpchat_msg_conv_created` | `AIJOBPOSTINGCHATMESSAGE` | `(conversationId, createdAt)` | Ordered message retrieval |
| `idx_jpchat_toollog_conv` | `AIJOBPOSTINGTOOLCALLLOG` | `(conversationId)` | Tool call lookup per conversation |

**Naming convention:** `idx_jpchat_{table_suffix}_{columns}` — ngắn gọn, nhất quán với `idx_conversation_hr_jobapp` pattern.

### 8.4 FK risk assessment

| FK | Risk | Mitigation |
|---|---|---|
| `conversation.jobPostId` → `JOBPOSTING(jobPostId)` | Job posting bị xóa → conversations orphaned | Không cascade. Application check job posting exists trước khi tạo conversation. Orphaned conversations vẫn accessible cho audit |
| `conversation.hrId` → `HR(userId)` | HR account bị xóa → conversations orphaned | Không cascade. HR deletion là rare event. Orphaned conversations accessible cho admin |
| `message.conversationId` → `conversation` | Conversation archived → messages vẫn tồn tại | Expected behavior: archive ≠ delete messages |
| `toolcalllog.messageId` → `message` | Message deleted → log orphaned | Không cascade. Log is audit record, phải persist |
| Working set `jobAppId` trong `stateJson` | `JOBAPPLICATION` bị xóa → stale ID | Không FK (JSONB). Application validate khi load: nếu `jobAppId` not in `JOBAPPLICATION`, loại khỏi working set + log warning |

### 8.5 Không sửa bảng hiện tại

- ❌ KHÔNG thêm column vào `JOBPOSTING`
- ❌ KHÔNG thêm column vào `AICHATCONVERSATION` hoặc `AICHATMESSAGE`
- ❌ KHÔNG tạo FK từ bảng mới tới `JOBAPPLICATION` (working set dùng JSONB reference)
- ❌ KHÔNG tạo circular FK
- ❌ KHÔNG nhồi tool call log vào `AIQUERYLOG` (mất ý nghĩa log chat hiện tại — KINH_NGHIEM)

---

## 9. Impact on Other Workstreams

### 9.1 Impact lên WS-A (Agent Runtime and Tool Calling)

| WS-B cung cấp | WS-A cần |
|---|---|
| DDL cho tables | Python persistence layer / ORM models tương ứng |
| State JSON schema (`schemaVersion`, `workingSetJobAppIds`, etc.) | Agent loop: load state → decide tools → call tools → update state → save |
| Message role enum (`user`, `assistant`, `system`, `tool_call`, `tool_result`) | Agent loop save messages đúng role, match `toolCallId` |
| `toolCallId` concept | Agent generate/receive `toolCallId`, save cả `tool_call` + `tool_result` messages |
| `AIJOBPOSTINGTOOL` catalog (nếu tạo) | Agent load tool declarations từ DB hoặc config |
| Summarization column `summarized BOOLEAN` | Agent/backend mark old messages khi context budget gần limit |

**Cần từ WS-A:** Confirm state JSON schema đáp ứng agent loop needs. Confirm `toolCallId` generation strategy (LLM provider vs FANG UUID).

### 9.2 Impact lên WS-C (Read-only Tool Contract)

| WS-B cung cấp | WS-C cần |
|---|---|
| Tool call log schema | Align tool names chính xác (7 MVP tools) |
| `toolName VARCHAR(100)` constraint | Tool name length ≤ 100 chars |
| `toolInput JSONB` / `toolOutputMeta JSONB` | Define cái gì log (sanitized) và không (PII) |
| `AIJOBPOSTINGTOOL` catalog seed data | WS-C provide tool descriptions, input/output schemas |

**Cần từ WS-C:**
- Final tool name list (exact strings, 7 MVP tools)
- Normalized enum values cho `activeFilters` (language, proficiency, province)
- Confirmation normalization fix deliver normalized data trước agent go-live

### 9.3 Impact lên WS-D (Product, API, and UI Contract)

| WS-B cung cấp | WS-D cần |
|---|---|
| Conversation CRUD semantics | API endpoints: create, list, get history, rename, archive |
| `ConversationSummary` fields | `conversationId`, `jobPostId`, `hrId`, `title`, `createdAt`, `lastMessageAt`, `isArchived` + message count (computed) |
| Message load pattern | Endpoint trả message history ordered by `createdAt ASC` |
| State → working set label | UI hiển thị `workingSetLabel` cho context |
| Tool call log → tool usage display | UI hiển thị tools used per message |

**Cần từ WS-D:** Confirm CRUD operations đủ. Confirm cần thêm fields (ví dụ: `messageCount` — computed via query hay stored?).

### 9.4 Dependency lên WS-C (Normalization Bug)

WS-B **không fix** normalization bug nhưng **bị ảnh hưởng trực tiếp:**

- `stateJson.activeFilters` dùng normalized enum values (ví dụ: `proficiency: "C1"`)
- Nếu data chưa normalized → filter state không khớp data → agent trả lời sai
- **Assumption documented:** WS-C fix normalization trước go-live
- **Risk nếu assumption sai:** Agent filter silently miss candidates → HR mất tin tưởng

> [!WARNING]
> Nếu WS-C không deliver normalized language/proficiency data, filter functionality trong agent sẽ broken. Đây là cross-workstream blocker, không phải "nice to have".

---

## 10. Open Questions for Synthesis

### 10.1 Cần quyết định tại Synthesis

| # | Question | Impact | Suggested Default |
|---|---|---|---|
| Q1 | `AIJOBPOSTINGTOOL` (tool catalog): tạo Phase 1 hay defer? Planning Brief nghiêng về tạo. | Tool-call log FK integrity, WS-A tool loading strategy | Tạo Phase 1, seed 7 tools |
| Q2 | `stateJson` field `schemaVersion`: thêm hay không? | Backward compatibility nếu state evolve | Thêm, cost = 0 |
| Q3 | Auto-generate title: WS-A (agent), WS-D (backend), hay cả hai? | Separation of concerns | Backend code (WS-D endpoint hoặc persistence layer) |
| Q4 | `toolCallId`: LLM provider generate hay FANG generate UUID? | Consistency, traceability | LLM provider nếu có, FANG fallback UUID |
| Q5 | `messageCount` cho conversation list: computed via COUNT query hay stored column? | Query performance vs data consistency | Computed query (LEFT JOIN COUNT) — pattern đã dùng trong chat cũ (`chat_persistence.py`) |
| Q6 | Ranking service hiện trả `candidate_id` hay `jobAppId`? Nếu `candidate_id`, cần enrichment/lookup để state chứa `jobAppId` | Working set correctness | WS-C verify và enrich ranking wrapper nếu cần |

### 10.2 Cần input từ workstream khác

| Từ WS | Input cần | Urgency |
|---|---|---|
| **WS-A** | State JSON schema đáp ứng agent loop? `toolCallId` strategy? Tool catalog static/dynamic? | Trước synthesis |
| **WS-C** | Final 7 tool names (exact strings). Tool input/output schemas cho catalog seed. Normalized enum values. Normalization fix timeline. Ranking output có `jobAppId` không? | Trước synthesis |
| **WS-D** | Conversation CRUD đủ? Thêm fields? `messageCount` strategy? Conversation list response format? | Trước synthesis |

---

## 11. Acceptance Criteria

### 11.1 Schema acceptance

- [ ] 4 bảng chính DDL hoàn chỉnh, PostgreSQL syntax
- [ ] Tất cả FK constraints defined, KHÔNG cascade delete
- [ ] 3 indexes tạo cùng bảng, `IF NOT EXISTS`
- [ ] `stateJson` schema documented rõ ràng (JSONB)
- [ ] DDL idempotent (`CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS`)
- [ ] Rollback DDL có sẵn (`DROP TABLE IF EXISTS` đúng order)
- [ ] (Optional) Tool catalog table + seed data cho 7 MVP tools

### 11.2 Design acceptance

- [ ] Bảng mới hoàn toàn tách biệt khỏi `AICHATCONVERSATION`/`AICHATMESSAGE`
- [ ] Conversation scope theo `jobPostId`, KHÔNG `jobAppId`
- [ ] PK conversation: UUID `gen_random_uuid()` — nhất quán
- [ ] Message roles: `user`, `assistant`, `system`, `tool_call`, `tool_result`
- [ ] Working set trong state: `jobAppId[]` references (max 25, configurable)
- [ ] Không PII trong tool call log
- [ ] Không full CV content trong messages
- [ ] Soft-delete: `isArchived BOOLEAN`
- [ ] Title + rename support trên conversation
- [ ] Summarization support: `summarized BOOLEAN` trên message
- [ ] Không sửa bất kỳ bảng hiện tại nào

### 11.3 Cross-workstream acceptance

- [ ] WS-A có đủ thông tin implement persistence layer (column names, types, state JSON)
- [ ] WS-C có đủ thông tin align tool names và define log format
- [ ] WS-D có đủ thông tin design conversation CRUD API endpoints
- [ ] Normalization dependency trên WS-C documented rõ ràng
- [ ] Ranking `jobAppId` gap documented (WS-C cần verify)

---

## Recommended Decisions For Synthesis

1. **Tạo 4 bảng chính** theo PostgreSQL DDL đề xuất, tách biệt hoàn toàn khỏi chat hiện tại.
2. **Tạo `AIJOBPOSTINGTOOL`** Phase 1 với seed 7 MVP tools (Planning Brief nghiêng về đây). Nếu WS-A confirm static tool loading, defer.
3. **State JSON minimal:** `schemaVersion`, `workingSetJobAppIds`, `workingSetLabel`, `lastToolName`, `lastToolParams`, `activeFilters`. KHÔNG lưu derived data (scores, summaries).
4. **Working set key:** `jobAppId[]`, KHÔNG `candidateId` (Decision Lock).
5. **UUID PK** cho conversation — nhất quán với `AICHATCONVERSATION`.
6. **Không cascade delete** từ `JOBPOSTING`/`HR`.
7. **Tool call log Phase 1** — critical debug/audit.
8. **3 indexes tạo ngay** — follow "index early" pattern.
9. **DDL thêm vào `schema_ai_core.sql`** hoặc file riêng nếu team adopt migration tool.
10. **Conversation title + rename + archive** — full lifecycle support.
11. **Summarization ready** — column `summarized BOOLEAN` sẵn sàng, logic Phase 2+.

## Risks If Ignored

| Risk | Severity | Consequence |
|---|---|---|
| Reuse `AICHATCONVERSATION`/`AICHATMESSAGE` | 🔴 Critical | Schema conflict `jobAppId` vs `jobPostId`, regression existing chat |
| Không tạo tool call log | 🟠 High | Mù debug agent behavior, không audit trail |
| State lưu full candidate data | 🟠 High | Bloat, stale data, PII risk |
| Cascade delete từ `JOBPOSTING` | 🟠 High | Mất audit trail khi HR xóa job posting |
| Không align tool names với WS-C | 🟡 Medium | Log inconsistency, debug difficult |
| Ignore normalization dependency | 🔴 Critical | Filter state ≠ actual data → sai kết quả |
| Không index early | 🟡 Medium | Performance degradation scale |
| Dùng `candidateId` thay vì `jobAppId` cho working set | 🔴 Critical | Vi phạm Decision Lock, mismatch với tool contract WS-C |
| Nhồi tool call log vào `AIQUERYLOG` | 🟠 High | Mất ý nghĩa log cũ, schema conflict |

## Inputs Needed From Other Workstreams

| Workstream | Input cần | Deadline |
|---|---|---|
| **WS-A** | State JSON đáp ứng agent loop? `toolCallId` generation? Tool catalog static/dynamic? | Trước synthesis |
| **WS-C** | 7 MVP tool names (exact strings). Input/output schemas. Normalized enum values. Normalization timeline. Ranking output có `jobAppId`? | Trước synthesis |
| **WS-D** | Conversation CRUD đủ? Additional metadata fields? `messageCount` strategy? | Trước synthesis |

## Checklist For Official Implementation Plan

- [ ] Include DDL cho tables (4 chính + optional catalog) trong migration section
- [ ] Include `DROP TABLE IF EXISTS` rollback DDL
- [ ] Include state JSON schema definition + Pydantic model
- [ ] Document privacy boundaries rõ ràng (lưu gì, không lưu gì)
- [ ] Document FK strategy (không cascade) + orphan handling
- [ ] Document index plan (3 indexes)
- [ ] Cross-reference WS-A: persistence layer, ORM, state management
- [ ] Cross-reference WS-C: tool name alignment, normalization dependency
- [ ] Cross-reference WS-D: conversation CRUD API mapping, response schema
- [ ] Include acceptance criteria measurable + testable
- [ ] Note: Tool catalog quyết định pending WS-A confirm
- [ ] Note: History pagination/summarization logic defer Phase 2+
- [ ] Note: Auto-generate title là backend responsibility, không DB trigger
- [ ] Note: `messageCount` dùng computed query (LEFT JOIN), không stored column
- [ ] Note: Ranking `jobAppId` gap — WS-C phải verify/enrich

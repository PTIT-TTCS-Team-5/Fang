# FANG Next Phase JobPosting C3 Official Implementation Plan

Ngày lập: 2026-05-29  
Phạm vi: **JobPosting Agent C3.1 - Dedicated tables + Gemini native tool calling + read-only tools + best-effort NMAIex normalization**  
Trạng thái: **Official implementation plan** sau synthesis WS-A/B/C/D và user approval.

## 1. Executive Summary

Triển khai JobPosting Agent theo hướng **C3.1**: một assistant read-only gắn với `jobPostId`, có dedicated conversation tables, persistent working-set state, 7 MVP tools, và agent runtime riêng dùng **Google GenAI native tool calling** theo manual controller loop.

Plan này khóa các quyết định sau:

1. Không refactor JobApplication chat hiện tại (`/v2/chat`, `AICHATCONVERSATION`, `AICHATMESSAGE`, `rag_orchestrator.py`, `rag_model_adapters.py`).
2. Tạo runtime riêng: `jobposting_agent_runtime.py`, Gemini-only phase 1, native function calling, manual loop.
3. Tạo persistence riêng: conversation, message, state, tool-call log, tool catalog.
4. Tạo 7 read-only tools, tất cả scope theo `jobPostId`; tools nhận `jobAppId` phải verify application thuộc job hiện tại.
5. API phase 1 dùng namespace `/v2/agent/job-posting`, request-response, không streaming.
6. Không expose `modelMode` cho HR phase 1; backend chọn model theo config.
7. Tool messages hiển thị trong UI dạng collapsible/debug, không lẫn như chat message bình thường.
8. Normalization nằm ở **best-effort enrichment sau ingestion**, không đưa vào parser hoặc agent runtime. Enrichment được mở rộng để normalize province/language/proficiency, update `"user".provId`, tạo/ghi `CANDIDATELANGUAGE`; nếu enrichment fail thì ingestion vẫn không fail, enrichment job retry theo cơ chế hiện có.

Blocker lớn nhất là data normalization. Nếu không có `CANDIDATELANGUAGE` và `user.provId` từ enrichment, các câu như "trong 10 ứng viên này, ai có tiếng Anh hạng C trở lên" sẽ sai hoặc thiếu ứng viên.

## 2. Inputs Synthesized

Tài liệu đầu vào:

1. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_PLANNING_BRIEF.md`
2. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_OPTION_C_IMPLEMENTATION_ADVISORY.md`
3. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_OPTION_C3_DEEP_ADVISORY.md`
4. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSA_AGENT_RUNTIME_DECISION.md`
5. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSB_CONVERSATION_MEMORY_SCHEMA.md`
6. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSC_TOOL_CONTRACT.md`
7. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSD_API_UI_CONTRACT.md`

Code reality đã kiểm tra:

1. `app/services/rag_orchestrator.py` và `app/services/rag_model_adapters.py` là text-only generation.
2. `app/models/chat.py`, `app/api/routes_chat.py`, `app/services/chat_persistence.py` hard-scope theo `jobAppId`.
3. `database/schema_ai_core.sql` đã có `CVPARSED`, `AIDOCUMENTCHUNK`, `AIQUERYLOG`, `AICHATCONVERSATION`, `AICHATMESSAGE`.
4. `database/schema_web_core.sql` đã có `JOBPOSTING`, `JOBAPPLICATION`, `LANGUAGE`, `JOB_LANG_REQUIREMENT`, `APPSTATUSHISTORY`, `INTERVIEW`, `INTERVIEWFEEDBACK`.
5. `app/services/nmaiex_candidate_enrichment.py` hiện chỉ enrich `experience` và `skills`; chưa extract `languages` hoặc location.
6. `app/services/nmaiex_mapper_service.py` đã có `map_string_to_province_id()` và `normalize_proficiency()` nhưng pipeline hiện chưa gọi.
7. `app/services/nmaiex_ranking_service.py` hiện `rank_candidates_for_job()` trả `candidate_id`, chưa trả `jobAppId`; tool wrapper phải enrich kết quả.
8. `requirements.txt` đã pin `google-genai==1.69.0`.

## 3. Final Decisions

| Chủ đề | Quyết định chính thức |
|---|---|
| Runtime | Google GenAI native tool calling, manual controller loop. |
| Provider | Gemini-only phase 1. Không multi-provider fallback trong agent. |
| Model default | `agent-lite` -> candidate `gemini-3.1-flash-lite`; `agent-pro` -> candidate `gemini-3.5-flash`. Exact availability phải verify trong environment trước code/deploy. |
| Runtime boundary | Tạo `jobposting_agent_runtime.py`; không mở rộng `rag_model_adapters.py` hoặc `rag_orchestrator.py`. |
| Parallel function calls | Cho phép phase 1 nếu Gemini trả nhiều calls; controller validate từng call và có thể execute sequential hoặc bounded parallel. |
| Tool result context | Gửi structured summary/truncated result vào model, không gửi raw blob lớn. |
| History context | Old history: user/assistant + state summary. Current turn: có tool call/result parts. |
| Persistence | 4 bảng chính + `AIJOBPOSTINGTOOL` catalog phase 1. |
| State table | Có `AIJOBPOSTINGCHATSTATE`. |
| Working set key | `jobAppId[]`, không dùng `candidateId[]`. |
| Normalization | Best-effort enrichment sau ingestion; mở rộng enrichment, không chặn ingestion. |
| Language data | Tạo `CANDIDATELANGUAGE` phase 1. |
| Language unknown filter | Inclusive default + `data_quality` warning; strict filtering để phase sau hoặc explicit filter. |
| "Tiếng Anh hạng C trở lên" | Agent map về `ADVANCED` trở lên (`ADVANCED`, `FLUENT`, `NATIVE`) trong 5-level enum nội bộ. |
| Ranking language scoring | Refactor `compute_language_score()` để ưu tiên `CANDIDATELANGUAGE` phase 1. |
| Full CV | Summary-first, single `jobAppId`, PII masking bắt buộc. |
| API namespace | `/v2/agent/job-posting`. |
| HR model mode | Không expose phase 1. Backend dùng config. |
| Tool UI | Collapsible/debug view mặc định available; không render như normal assistant text. |
| Streaming | Không streaming phase 1. |
| Title | Backend auto-title bằng prompt đầu tiên, truncate; agent title generation defer phase 2. |
| messageCount | Computed query, không stored column. |

## 4. Target Architecture

```text
FastAPI route: app/api/routes_jobposting_agent.py
    |
    v
Query service: app/services/jobposting_agent_query.py
    - validate jobPostId/hrId/conversation
    - create/load conversation
    - persist user message
    - load state + compressed history
    - call runtime
    - persist assistant + tool messages/logs
    - update state
    |
    v
Runtime: app/services/jobposting_agent_runtime.py
    - Gemini native function calling
    - manual loop, max steps
    - controller guardrails
    - tool registry
    - tool result truncation
    |
    v
Tools: app/services/jobposting_tools.py
    - read-only DB/service tools
    - jobPostId/jobAppId scope checks
    - source metadata, warnings, structured errors
    |
    v
Data foundation:
    - dedicated JobPosting chat tables
    - CANDIDATELANGUAGE
    - enriched user.provId
    - NMAIex ranking/search/CV/ATS sources
```

Existing JobApplication chat remains unchanged.

## 5. Implementation Order

### Phase 0 - Verification and branch hygiene

1. Verify current test baseline relevant to chat/ranking/enrichment.
2. Verify Google model candidates in target environment using existing `scripts/list_gemini_models_direct.py` or an equivalent one-off check.
3. Confirm no active branch is modifying the same chat/enrichment files; do not overwrite unrelated user work.

### Phase 1 - Schema foundation

1. Add `CANDIDATELANGUAGE` to `database/schema_web_core.sql` near `CANDIDATESKILL`.
2. Add JobPosting Agent tables to `database/schema_ai_core.sql`.
3. Seed `AIJOBPOSTINGTOOL` with 7 MVP tools.
4. Add rollback notes or migration rollback file if project adopts separate migration scripts.

### Phase 2 - Best-effort enrichment normalization

1. Extend enrichment payload to extract `languages` and candidate location.
2. Create language mapping helper using alias map + `LANGUAGE` lookup + LLM fallback.
3. Normalize proficiency through existing `normalize_proficiency()`.
4. Normalize province through existing `map_string_to_province_id()`.
5. Persist normalized languages into `CANDIDATELANGUAGE`.
6. Update `"user".provId` when province mapping succeeds.
7. Preserve current behavior: ingestion queues enrichment and continues; enrichment failures mark retryable jobs and do not fail ingestion.
8. Add re-enrichment path for old CV data.

### Phase 3 - Tool layer

1. Implement 7 read-only tools and shared scope validation utilities.
2. Wrap `rank_candidates_for_job()` so every candidate result includes `job_app_id`.
3. Implement language/province/status filters against normalized tables where available.
4. Add PII masking for full CV.
5. Add structured warnings and error convention.

### Phase 4 - Persistence service and models

1. Add Pydantic models for requests, responses, state, tool calls, warnings.
2. Add JobPosting-specific persistence service.
3. Ensure no full CV/email/phone raw values are logged into message/tool-call tables.

### Phase 5 - Agent runtime and query orchestration

1. Implement Gemini manual tool loop.
2. Implement guardrails: max steps, max full CV loads, max compare/deep set, max top N, scope checks.
3. Implement system prompt/tool policy and state-aware history builder.
4. Persist current-turn tool call/result messages and sanitized logs.

### Phase 6 - API route and app registration

1. Add route file and register it in `app/main.py` under `/v2/agent/job-posting`.
2. Implement query, list conversations, get messages, rename, archive.
3. Map runtime/tool errors to HTTP codes and Vietnamese API messages.

### Phase 7 - Tests, smoke, and rollout

1. Unit tests for enrichment, tools, persistence, runtime loop, routes.
2. Integration/smoke tests for top 10, language refine, too-large compare, rename/archive.
3. Re-enrich old data before enabling language/province filters in production.
4. Release behind config flag if needed.

## 6. Schema Plan

### 6.1 `CANDIDATELANGUAGE`

Add to `database/schema_web_core.sql`:

```sql
CREATE TABLE CANDIDATELANGUAGE (
    candidateLangId SERIAL PRIMARY KEY,
    userId          INT NOT NULL,
    langId          INT,
    rawName         VARCHAR(100),
    proficiency     VARCHAR(20) CHECK (proficiency IN ('BASIC','INTERMEDIATE','ADVANCED','FLUENT','NATIVE')),
    rawProficiency  VARCHAR(100),
    certification   VARCHAR(200),
    createdAt       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updatedAt       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (userId) REFERENCES CANDIDATE(userId) ON DELETE CASCADE,
    FOREIGN KEY (langId) REFERENCES LANGUAGE(langId)
);

CREATE INDEX IF NOT EXISTS idx_candidate_language_user
    ON CANDIDATELANGUAGE (userId);

CREATE INDEX IF NOT EXISTS idx_candidate_language_lang_level
    ON CANDIDATELANGUAGE (langId, proficiency);

CREATE UNIQUE INDEX IF NOT EXISTS uq_candidate_language_known
    ON CANDIDATELANGUAGE (userId, langId)
    WHERE langId IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_candidate_language_unknown
    ON CANDIDATELANGUAGE (userId, lower(rawName))
    WHERE langId IS NULL AND rawName IS NOT NULL;
```

Implementation notes:

1. `langId` nullable by design. Unknown language names are preserved as `rawName`.
2. Raw values are preserved for audit/debug.
3. Surrogate `candidateLangId` is required because PostgreSQL primary-key columns cannot be nullable, while phase 1 explicitly allows unknown `langId`.
4. Partial unique indexes prevent duplicate known and unknown language rows without blocking nullable `langId`.

### 6.2 JobPosting Agent tables

Add to `database/schema_ai_core.sql`:

```sql
CREATE TABLE AIJOBPOSTINGTOOL (
    toolId           SERIAL PRIMARY KEY,
    toolName         VARCHAR(100) NOT NULL UNIQUE,
    displayName      VARCHAR(200) NOT NULL,
    description      TEXT,
    inputSchemaJson  JSONB,
    outputSchemaJson JSONB,
    isEnabled        BOOLEAN NOT NULL DEFAULT TRUE,
    category         VARCHAR(50),
    createdAt        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE AIJOBPOSTINGCHATCONVERSATION (
    conversationId UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jobPostId      INT NOT NULL,
    hrId           INT NOT NULL,
    title          VARCHAR(200) NOT NULL DEFAULT 'Cuộc trò chuyện mới',
    createdAt      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    lastMessageAt  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    isArchived     BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (jobPostId) REFERENCES JOBPOSTING(jobPostId),
    FOREIGN KEY (hrId) REFERENCES HR(userId)
);

CREATE INDEX IF NOT EXISTS idx_jpchat_conv_jobpost_hr
    ON AIJOBPOSTINGCHATCONVERSATION (jobPostId, hrId);

CREATE TABLE AIJOBPOSTINGCHATMESSAGE (
    messageId      SERIAL PRIMARY KEY,
    conversationId UUID NOT NULL,
    role           VARCHAR(20) NOT NULL,
    content        TEXT NOT NULL,
    toolName       VARCHAR(100),
    toolCallId     VARCHAR(100),
    model          VARCHAR(100),
    modelMode      VARCHAR(50),
    latencyMs      INT,
    summarized     BOOLEAN NOT NULL DEFAULT FALSE,
    createdAt      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversationId) REFERENCES AIJOBPOSTINGCHATCONVERSATION(conversationId)
);

CREATE INDEX IF NOT EXISTS idx_jpchat_msg_conv_created
    ON AIJOBPOSTINGCHATMESSAGE (conversationId, createdAt);

CREATE TABLE AIJOBPOSTINGCHATSTATE (
    conversationId UUID PRIMARY KEY,
    stateJson      JSONB NOT NULL DEFAULT '{}',
    updatedAt      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversationId) REFERENCES AIJOBPOSTINGCHATCONVERSATION(conversationId)
);

CREATE TABLE AIJOBPOSTINGTOOLCALLLOG (
    toolCallLogId  SERIAL PRIMARY KEY,
    conversationId UUID NOT NULL,
    messageId      INT,
    jobPostId      INT NOT NULL,
    hrId           INT NOT NULL,
    toolId         INT,
    toolName       VARCHAR(100) NOT NULL,
    toolInput      JSONB,
    toolOutputMeta JSONB,
    status         VARCHAR(20) NOT NULL DEFAULT 'success',
    latencyMs      INT,
    errorMsg       TEXT,
    createdAt      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversationId) REFERENCES AIJOBPOSTINGCHATCONVERSATION(conversationId),
    FOREIGN KEY (messageId) REFERENCES AIJOBPOSTINGCHATMESSAGE(messageId),
    FOREIGN KEY (toolId) REFERENCES AIJOBPOSTINGTOOL(toolId)
);

CREATE INDEX IF NOT EXISTS idx_jpchat_toollog_conv
    ON AIJOBPOSTINGTOOLCALLLOG (conversationId);
```

No cascade delete from `JOBPOSTING`/`HR`. Conversation archive is soft-delete only.

### 6.3 Tool catalog seed

Seed exactly these 7 tool names:

| toolName | displayName | category |
|---|---|---|
| `get_job_posting_context` | Xem thông tin tin tuyển dụng | `context` |
| `get_job_candidate_ranking` | Xếp hạng ứng viên | `ranking` |
| `search_job_applications_text` | Tìm kiếm ứng viên | `search` |
| `get_job_application_summary` | Tóm tắt ứng viên | `detail` |
| `get_job_application_full_cv` | Xem CV đầy đủ | `detail` |
| `get_candidate_ats_history` | Lịch sử tuyển dụng | `detail` |
| `count_job_applications` | Đếm ứng viên | `aggregate` |

## 7. Config and Environment

Modify `app/core/config.py`:

```python
# --- JobPosting Agent (C3) ---
jobposting_agent_enabled: bool = True
jobposting_agent_model: str = "agent-lite"
jobposting_agent_max_tool_steps: int = 8
jobposting_agent_max_full_cv_loads: int = 3
jobposting_agent_max_compare: int = 25
jobposting_agent_default_top_n: int = 10
jobposting_agent_hr_max_top_n: int = 25
jobposting_agent_max_turn_seconds: int = 60
jobposting_agent_temperature: float = 0.2
jobposting_agent_max_output_tokens: int = 4096
jobposting_agent_max_tool_result_chars: int = 12000
```

Add to `.env.example` if present or project env docs:

```bash
JOBPOSTING_AGENT_ENABLED=true
JOBPOSTING_AGENT_MODEL=agent-lite
JOBPOSTING_AGENT_MAX_TOOL_STEPS=8
JOBPOSTING_AGENT_MAX_FULL_CV_LOADS=3
JOBPOSTING_AGENT_MAX_COMPARE=25
JOBPOSTING_AGENT_DEFAULT_TOP_N=10
JOBPOSTING_AGENT_HR_MAX_TOP_N=25
JOBPOSTING_AGENT_MAX_TURN_SECONDS=60
JOBPOSTING_AGENT_TEMPERATURE=0.2
JOBPOSTING_AGENT_MAX_OUTPUT_TOKENS=4096
JOBPOSTING_AGENT_MAX_TOOL_RESULT_CHARS=12000
```

No new provider key is needed; use existing `GOOGLE_API_KEY`.

## 8. Normalization Implementation Plan

### 8.1 Existing bug

Current enrichment:

1. `_coerce_enrichment_payload()` extracts only `experience` and `skills`.
2. `enrich_candidate_structured_data()` writes `CANDIDATE.expyears`, `CANDIDATESKILL`, `CANDIDATE_SKILL_RAW`.
3. `languages` and candidate location are ignored.
4. `compute_language_score()` reads raw `CVPARSED.parsedJson.languages` and interprets unknown raw proficiency as `BASIC`.

### 8.2 Desired enrichment behavior

Extend `EnrichmentPayload`:

```python
class EnrichmentPayload:
    experience: list[Any]
    skills: list[str]
    languages: list[dict[str, Any]]
    candidate_location: str | None
```

Extend `_coerce_enrichment_payload()`:

1. Extract `parsed_payload["languages"]` as list of language objects.
2. Extract candidate location from likely fields:
   - `candidateInfo.location`
   - `candidateInfo.address`
   - `personalInfo.location`
   - `personalInfo.address`
   - any existing parsed CV structure confirmed by `app/models/cv_models.py`
3. Preserve raw values; do not mutate `CVPARSED.parsedJson`.

Add helpers:

```python
async def _map_language_to_lang_id(raw_language: str, conn) -> int | None:
    ...

async def _normalize_and_persist_languages(candidate_id: int, raw_languages: list[dict], conn) -> None:
    ...

async def _normalize_and_update_province(candidate_id: int, raw_location: str | None, conn) -> None:
    ...
```

Required behavior:

1. Language alias map handles at least: English, Japanese, Chinese, Korean, French, German, Vietnamese, Spanish, Portuguese, Italian, Russian, Thai and common Vietnamese spellings.
2. DB lookup uses `LANGUAGE.langCode` and `LANGUAGE.langName`.
3. LLM fallback may use `invoke_generation(..., "auto-lite")`, but mapper failure must not crash the entire ingestion request.
4. `normalize_proficiency()` remains the canonical 5-level mapper.
5. Province mapper uses `map_string_to_province_id()`.
6. When province mapping succeeds, update `"user".provId`.
7. When language mapping fails, write `CANDIDATELANGUAGE.langId = NULL`, preserve `rawName`, return warning later from tools.

### 8.3 Best-effort failure semantics

Ingestion already queues/runs enrichment after parse and save. Keep this behavior:

1. Parsing and `CVPARSED` save remain the ingestion success boundary.
2. Enrichment exceptions mark `NMAIEX_CANDIDATE_ENRICHMENT_JOB` as failed/retryable.
3. Do not raise enrichment failure back as ingestion failure.
4. Partial mapper failure inside a candidate enrichment should degrade per field when safe:
   - province unknown -> keep current `user.provId`;
   - language unknown -> write raw row with nullable `langId`;
   - proficiency unknown -> `BASIC` via existing fallback.
5. DB transaction should keep candidate structured writes consistent for each enrichment run. If a database write fails, let enrichment job retry.

### 8.4 Batch re-enrichment

Required for old data:

1. Reuse `scripts/retry_nmaiex_candidate_enrichment.py` and `enqueue_missing_enrichment_jobs()` where possible.
2. Add a language/province re-enrichment mode if existing job uniqueness prevents rerun for already-successful jobs.
3. Re-enrichment must not re-parse CV; it reads existing `CVPARSED.parsedJson`.
4. Produce an operational command/report with counts:
   - CVs scanned
   - candidates updated with language
   - candidates updated with province
   - unknown language rows
   - mapper failures

## 9. Tool Layer Contract

Implement `app/services/jobposting_tools.py`.

Common result shape:

```python
{
    "ok": bool,
    "data": dict | list | None,
    "source": dict,
    "warnings": list[dict],
    "error": {"code": str, "message": str} | None
}
```

Common rules:

1. Every tool is read-only.
2. Every tool is scoped to the current `jobPostId`.
3. Tool functions should accept `job_post_id` explicitly when natural, or receive runtime scope out-of-band for `job_app_id` tools.
4. `job_app_id` tools must verify `JOBAPPLICATION.jobPostId = current jobPostId`.
5. Tool output must be JSON-serializable.
6. Tool output sent to model is truncated/summarized.
7. Tool log uses sanitized args and result summary only.

### Tool 1 - `get_job_posting_context(job_post_id)`

Reads `JOBPOSTING`, `COMPANY`, `PROVINCE`, `JOBAPPLICATION` aggregate counts, and language/skill requirements.

Returns job metadata, requirements summary, application counts, and source metadata.

### Tool 2 - `get_job_candidate_ranking(job_post_id, limit=10, filters=None)`

Uses `rank_candidates_for_job()` as base, then wrapper enriches:

1. `job_app_id` lookup from `JOBAPPLICATION` for each `candidate_id` in the same `jobPostId`.
2. candidate normalized languages from `CANDIDATELANGUAGE` + `LANGUAGE`.
3. `user.provId` and status from `JOBAPPLICATION.stat`.
4. language/province/status filters.

Limit rules:

1. Default 10.
2. HR max 25.
3. If user asks >25, cap to 25 and emit warning.

When `filters.language` and candidate has unknown `langId`, include candidate by default with `data_quality` warning unless future strict mode is explicit.

### Tool 3 - `search_job_applications_text(job_post_id, query, limit=10, filters=None)`

Phase 1 should prefer DB-backed text search over a new semantic tool:

1. Search `CVPARSED.rawText` scoped through `JOBAPPLICATION.jobPostId`.
2. Optionally use `ts_rank` and snippet extraction.
3. Group by `jobAppId`.
4. Apply same normalized filters as ranking.

Vector/semantic search across `AIDOCUMENTCHUNK` can be deferred unless existing query can be made scoped safely and cheaply.

### Tool 4 - `get_job_application_summary(job_app_id)`

Returns a compact candidate summary:

1. name and application status;
2. education highlights;
3. experience highlights;
4. top skills;
5. years experience;
6. normalized languages;
7. province;
8. ranking score if available.

No full parsed JSON dump.

### Tool 5 - `get_job_application_full_cv(job_app_id)`

Single-candidate drill-down only.

Rules:

1. Enforce max full CV loads per turn in runtime.
2. Use Full-CV helper from the JobApplication Full-CV track if available; otherwise implement a shared helper now and make JobApp chat eligible to reuse later.
3. Mask email and phone.
4. Redact address/street where not essential.
5. Do not store full CV in `AIJOBPOSTINGCHATMESSAGE` or `AIJOBPOSTINGTOOLCALLLOG`.

### Tool 6 - `get_candidate_ats_history(job_app_id)`

Reads:

1. `APPSTATUSHISTORY`
2. `INTERVIEW`
3. `INTERVIEWFEEDBACK`
4. `OFFER` and `EMAILLOG` only if needed and with PII-safe summaries

Returns timeline summary, current status, and source IDs.

### Tool 7 - `count_job_applications(job_post_id, filters=None)`

Returns total count for too-large guardrails and filtered counts.

This is the default first tool for broad requests like "so sánh tất cả ứng viên".

## 10. State and Memory Design

Use `AIJOBPOSTINGCHATSTATE.stateJson`:

```json
{
  "schemaVersion": 1,
  "workingSetJobAppIds": [101, 102],
  "workingSetLabel": "Top 10 ứng viên cho Backend Developer",
  "lastRanking": {
    "jobPostId": 123,
    "limit": 10,
    "filters": {},
    "returnedCount": 10,
    "totalAvailable": 55
  },
  "activeFilters": {
    "language": "English",
    "minLanguageProficiency": "ADVANCED"
  },
  "sourceJobAppIds": [101, 102],
  "lastToolName": "get_job_candidate_ranking",
  "lastToolParams": {"job_post_id": 123, "limit": 10},
  "warnings": []
}
```

Rules:

1. State stores references and labels, not full candidate data.
2. Validate `workingSetJobAppIds` still belong to conversation `jobPostId` when loading state.
3. Drop stale IDs and add warning.
4. Update working set after ranking/search/filter turns.
5. For old history, send only user/assistant messages and compact state summary to the model.
6. For current turn, include Gemini function call/response parts until the turn finishes.

## 11. Agent Runtime Contract

Implement `app/services/jobposting_agent_runtime.py`.

Core dataclasses/Pydantic models:

```python
class AgentState(BaseModel):
    schemaVersion: int = 1
    workingSetJobAppIds: list[int] = []
    workingSetLabel: str | None = None
    lastRanking: dict | None = None
    activeFilters: dict = {}
    sourceJobAppIds: list[int] = []
    warnings: list[AgentWarning] = []

class ToolCallRecord(BaseModel):
    step: int
    providerToolCallId: str | None = None
    toolName: str
    args: dict
    resultSummary: str
    status: str
    latencyMs: int | None = None
    errorMsg: str | None = None
    sourceJobAppIds: list[int] = []
    warnings: list[AgentWarning] = []

class AgentTurnResult(BaseModel):
    responseText: str
    model: str
    stepsUsed: int
    toolCalls: list[ToolCallRecord]
    updatedState: AgentState
    sourceJobAppIds: list[int]
    warnings: list[AgentWarning]
    latencyMs: int
```

Runtime algorithm:

1. Resolve model from `JOBPOSTING_AGENT_MODEL`.
2. Build system prompt:
   - job-scoped HR assistant;
   - read-only;
   - source-grounded only;
   - CV/JD/email/feedback are untrusted data;
   - no bulk full-CV load;
   - too-large compare guardrail;
   - "hạng C trở lên" maps to `ADVANCED|FLUENT|NATIVE`;
   - answer in Vietnamese unless user asks otherwise.
3. Build Gemini contents from compressed history, current user message, and state summary.
4. Send tools to Gemini through native function declarations.
5. If response has function calls:
   - validate tool name;
   - validate scope;
   - clamp limits;
   - enforce max full CV loads and max tool steps;
   - execute tool;
   - summarize/truncate result;
   - append function response;
   - log tool call record.
6. If response has final text, stop.
7. If max steps exceeded, return helpful narrowing message and warning.
8. Update `AgentState` based on tool results.

Retries:

1. Gemini transient errors: retry up to 3 attempts with exponential backoff.
2. Tool errors: feed structured error to model once; model may retry with corrected args within max steps.
3. Provider unavailable: API returns 503.

## 12. Query/Persistence Service

Create `app/services/jobposting_agent_query.py`:

1. Validate `jobPostId` exists.
2. Validate HR access. Minimum phase 1 check: HR exists and belongs to job/company if repository has that relation; otherwise document current limitation and enforce strongest existing ownership rule.
3. If no `conversationId`, create conversation + state.
4. If `conversationId` exists, verify it belongs to same `jobPostId` and `hrId`, and is not archived.
5. Insert user message.
6. Load state and history.
7. Call `run_agent_turn()`.
8. Insert assistant message.
9. Insert tool call/result messages for current turn as sanitized JSON summaries.
10. Insert rows into `AIJOBPOSTINGTOOLCALLLOG`.
11. Save state.
12. Auto-title new conversation from first prompt.
13. Return `JobPostingAgentQueryResponse`.

Create `app/services/jobposting_agent_persistence.py`, mirroring `chat_persistence.py` style but using the new tables.

## 13. API Contract

Create `app/models/jobposting_agent.py`.

### `POST /v2/agent/job-posting/query`

Request:

```python
class JobPostingAgentQueryRequest(BaseModel):
    jobPostId: int
    hrId: int
    prompt: str
    conversationId: UUID | None = None
```

Do not expose `modelMode` to HR phase 1. If internal model switching is needed, use backend config only.

Response:

```python
class JobPostingAgentQueryResponse(BaseModel):
    conversationId: UUID
    messageId: int
    response: str
    model: str
    stepsUsed: int
    toolCalls: list[ToolCallDetail]
    sourceJobAppIds: list[int]
    workingSet: WorkingSetInfo | None = None
    latencyMs: int
    warnings: list[AgentWarning] = []
```

### `GET /v2/agent/job-posting/conversations`

Query params:

1. `jobPostId`
2. `hrId`

Returns active conversations sorted by `lastMessageAt DESC`.

`messageCount` is computed with `COUNT` over user/assistant messages only. Exclude `system`, `tool_call`, and `tool_result` so conversation list counts reflect visible chat turns rather than debug records.

### `GET /v2/agent/job-posting/conversations/{conversationId}/messages`

Query params:

1. `includeToolMessages=true` default
2. `includeSystem=false` default

Returns chronological messages. Tool messages are sanitized JSON summaries.

### `PATCH /v2/agent/job-posting/conversations/{conversationId}`

Body:

```python
class RenameConversationRequest(BaseModel):
    title: str
```

Max title length 200.

### `DELETE /v2/agent/job-posting/conversations/{conversationId}`

Query param:

1. `hrId`

Soft-archives conversation, returns 204.

### HTTP error mapping

| Condition | HTTP |
|---|---|
| invalid prompt/title | 400 |
| no HR/job access | 403 |
| job/conversation not found | 404 |
| archived conversation | 410 |
| rate limit | 429 |
| Gemini/provider unavailable | 503 |
| unexpected server error | 500 |

Agent/tool warnings stay in 200 response when the turn completed.

## 14. Files to Create or Modify

### Create

1. `app/models/jobposting_agent.py`
2. `app/api/routes_jobposting_agent.py`
3. `app/services/jobposting_agent_runtime.py`
4. `app/services/jobposting_agent_query.py`
5. `app/services/jobposting_agent_persistence.py`
6. `app/services/jobposting_tools.py`
7. `tests/unit/unit_test_jobposting_agent_runtime.py`
8. `tests/unit/unit_test_jobposting_agent_tools.py`
9. `tests/unit/unit_test_jobposting_agent_persistence.py`
10. `tests/unit/unit_test_routes_jobposting_agent.py`
11. Optional: `scripts/re_enrich_candidate_language_province.py`

### Modify

1. `database/schema_web_core.sql`
   - add `CANDIDATELANGUAGE`.
2. `database/schema_ai_core.sql`
   - add JobPosting Agent tables and tool seed.
3. `app/core/config.py`
   - add agent config values.
4. `app/main.py`
   - include new router with prefix `/v2/agent/job-posting`.
5. `app/services/nmaiex_candidate_enrichment.py`
   - extend payload and persist language/province normalization.
6. `app/services/nmaiex_mapper_service.py`
   - add language mapper only if not kept local to enrichment.
7. `app/services/nmaiex_ranking_service.py`
   - refactor `compute_language_score()` to use normalized candidate languages or provide helper used by tool wrapper.
8. `tests/unit/unit_test_nmaiex_candidate_enrichment.py`
   - add normalization tests.
9. `.env.example` or environment docs if present.

Do not modify:

1. Existing `AICHATCONVERSATION`/`AICHATMESSAGE` semantics.
2. `ChatQueryRequest`/`ChatQueryResponse`.
3. Existing `/v2/chat` route behavior.
4. `GenerationAdapter` return types.

## 15. Tests

### Enrichment tests

1. Extract languages from parsed payload.
2. Extract candidate location from parsed payload.
3. Map "Tiếng Anh" to English `langId`.
4. Map "tiếng nhật" to Japanese `langId`.
5. Unknown language writes `langId = NULL` and preserves raw name.
6. Normalize "hạng C" to `ADVANCED`.
7. Normalize "IELTS 7.5" to `ADVANCED`.
8. Normalize "N3" to `INTERMEDIATE`.
9. Update `"user".provId` for "TP.HCM".
10. Do not update province when mapper returns unknown.
11. Enrichment transaction updates skills, language, province without losing existing skill behavior.
12. Enrichment mapper failure marks/retries job and does not fail ingestion route.

### Tool tests

1. Ranking caps limit at 25 and warns.
2. Ranking wrapper returns `job_app_id`.
3. Scope check blocks `jobAppId` from another job.
4. Language filter includes unknown normalized candidates with warning.
5. Full CV masks email/phone.
6. Count tool returns filtered and unfiltered totals.
7. Text search is scoped by `jobPostId`.

### Runtime tests

1. Happy path: model calls job context + ranking, then final answer.
2. Follow-up path: state working set used for "trong 10 ứng viên này".
3. Too-large path: calls count, refuses broad compare.
4. Max steps exceeded returns narrowing message.
5. Max full CV loads enforced.
6. Provider tool call ID used when present, FANG UUID fallback when absent.
7. Tool result truncation occurs before model context/log persistence.

### Persistence/API tests

1. Create conversation and state.
2. List conversations with computed message count.
3. Get messages with tool messages included by default.
4. Rename conversation.
5. Archive conversation and prevent later query with 410.
6. Query endpoint creates new conversation when no `conversationId`.
7. Query endpoint rejects mismatched `jobPostId`/`conversationId`.

### Smoke flows

1. "Phân tích 10 ứng viên xếp hạng cao nhất".
2. "Trong 10 ứng viên này, ai có tiếng Anh hạng C trở lên?"
3. "So sánh chi tiết tất cả ứng viên cho vị trí này".
4. Rename conversation.
5. New conversation auto-title.
6. Archive conversation.
7. Invalid request handling.

## 16. Rollout Plan

1. Merge schema changes first in a controlled deploy.
2. Deploy enrichment normalization with feature-compatible behavior; ingestion remains successful even if enrichment jobs fail.
3. Run re-enrichment for existing `CVPARSED` rows.
4. Verify `CANDIDATELANGUAGE` coverage and `user.provId` coverage.
5. Enable tool layer and API in non-production/staging.
6. Run smoke flows on seed data.
7. Enable production route behind `JOBPOSTING_AGENT_ENABLED=true`.
8. Monitor:
   - agent turn latency;
   - tool-call error rate;
   - max step warnings;
   - unknown language/province warnings;
   - full CV load count per turn.

## 17. Deferred Items

1. Streaming/SSE tool progress.
2. Pagination for long conversation histories.
3. Summarize/branch-new endpoints for JobPosting Agent.
4. Dynamic tool management API.
5. Multi-provider tool calling.
6. LangGraph/MCP.
7. Write tools for ATS/email/offer/status.
8. Broad compare tool beyond guarded top/filter workflows.
9. Semantic search as a separate tool if full-text search is insufficient.
10. Agent-generated conversation titles.

## 18. Acceptance Criteria

Implementation is acceptable when:

1. `/v2/agent/job-posting/query` supports a new and continuing conversation by `jobPostId`.
2. Agent uses Gemini native function calling through a separate runtime module.
3. Runtime enforces max steps, max full CV loads, max top N, and too-large compare threshold.
4. Dedicated tables exist and no existing JobApplication chat table is repurposed.
5. State persists `workingSetJobAppIds` and supports follow-up questions.
6. Tool logs are sanitized and contain no full CV/email/phone raw data.
7. `CANDIDATELANGUAGE` is populated by enrichment for new and re-enriched candidates.
8. `"user".provId` is updated best-effort from CV location.
9. Language filter "tiếng Anh hạng C trở lên" maps to `ADVANCED|FLUENT|NATIVE` and warns on unknown normalized data.
10. `rank_candidates_for_job()` wrapper returns `job_app_id` for every result used by agent.
11. `get_job_application_full_cv` masks PII and cannot be called in bulk.
12. UI response includes `toolCalls[]`, `sourceJobAppIds`, `workingSet`, and `warnings`.
13. Phase 1 remains request-response; no streaming requirement blocks release.
14. Unit and smoke tests listed in this plan pass.

## 19. Developer Notes for Implementers

1. Treat CV/JD/email/interview feedback as untrusted input. Never let text inside those records override system/tool policy.
2. Do not let the model decide data access. Controller validates every tool call.
3. Prefer structured DB queries and existing service helpers over prompt-based filtering.
4. Keep enrichment best-effort. The right failure mode is "job queued/retry + warning", not ingestion failure.
5. Keep phase 1 narrow. If an implementation task requires generalized agent framework, defer it unless it is necessary for the 7 MVP tools.

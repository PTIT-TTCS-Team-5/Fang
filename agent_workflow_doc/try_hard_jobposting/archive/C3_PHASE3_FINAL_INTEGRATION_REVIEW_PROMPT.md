# C3 Phase 3 Final Integration + Review Prompt

Bạn là **Final Integration + Code Review Agent** cho FANG JobPosting Agent C3.1.

Model khuyến nghị: **GPT-5.5 high/xhigh** hoặc **Claude Opus 4.6**.  
Nếu dùng Claude Sonnet 4.6, chọn reasoning high và giữ review thật kỹ.  
Mục tiêu của phiên này là **review + integration hardening**, không phải mở thêm scope sản phẩm.

## 0. Workspace status

Workspace hiện tại:

`C:\Users\os\Desktop\cur_prj\Fang`

WS1, WS2, WS3 đã được implement trong cùng workspace chính, chưa chắc đã commit.

Trước khi làm:

```powershell
git status --short
```

Không revert, không cleanup, không format toàn repo, không động vào `.understand-anything/*`.

## 1. Truth sources

Đọc các tài liệu này trước:

1. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_OFFICIAL_IMPLEMENTATION_PLAN.md`
2. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_PHASE0_BASELINE_REPORT.md`
3. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WS1_DATA_FOUNDATION_REPORT.md`
4. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WS2_PERSISTENCE_API_REPORT.md`
5. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WS3_TOOLS_RUNTIME_REPORT.md`
6. `agent_workflow_doc/KINH_NGHIEM.md`

Then review source code directly. Source code is final truth.

## 2. Mission

Perform final integration review and fix only necessary integration bugs.

You must verify:

1. WS1 + WS2 + WS3 compile together.
2. Tests from all WS still pass when run explicitly.
3. Existing `/v2/chat` and text-generation architecture were not modified semantically.
4. JobPosting Agent route/query/runtime/tools line up correctly.
5. Google GenAI SDK type/field names used by runtime are valid for installed `google-genai==1.69.0`.
6. DB SQL uses correct asyncpg/PostgreSQL JSONB casts and parameter handling.
7. Tool outputs and logs do not leak full CV/email/phone raw values.
8. Scope checks prevent `jobAppId` leakage across `jobPostId`.
9. Runtime result shape matches WS2 persistence expectations.
10. `pytest tests/unit` discovery issue is documented and either fixed through pytest config or left as an explicit known issue with a safe command alternative.

## 3. Allowed edits

Allowed to modify only if needed for integration correctness:

1. `app/services/jobposting_agent_runtime.py`
2. `app/services/jobposting_tools.py`
3. `app/services/jobposting_agent_query.py`
4. `app/services/jobposting_agent_persistence.py`
5. `app/models/jobposting_agent.py`
6. `app/api/routes_jobposting_agent.py`
7. `app/core/config.py`
8. `.env.example`
9. tests related to JobPosting Agent or enrichment
10. optional `pytest.ini` / `pyproject.toml` only if you choose to fix test discovery
11. final report file under `agent_workflow_doc/try_hard_jobposting/`

Do not modify unless a real regression requires it and you document why:

1. `app/api/routes_chat.py`
2. `app/models/chat.py`
3. `app/services/chat_persistence.py`
4. `app/services/rag_orchestrator.py`
5. `app/services/rag_model_adapters.py`
6. `.understand-anything/*`
7. broad unrelated docs

Do not add new product features:

1. no write tools;
2. no streaming/SSE;
3. no LangGraph/MCP;
4. no multi-provider agent fallback;
5. no HR-exposed `modelMode`;
6. no generalized chat schema refactor.

## 4. Review checklist

### 4.1 Runtime SDK compatibility

Inspect installed `google-genai==1.69.0` locally if possible. Verify these usages are valid:

1. `types.GenerateContentConfig(...)` field names.
2. `types.Tool(...)` field names.
3. `types.FunctionDeclaration(...)` field names.
4. `types.Part.from_function_response(...)` or equivalent.
5. function call part access: `part.function_call` vs `part.functionCall`.
6. function response content role and part shape.

If current code uses wrong field aliases, patch runtime and add/update tests.

Do not call real Gemini in unit tests.

### 4.2 Query/persistence alignment

Verify:

1. `run_agent_turn_boundary(...)` loads state/history and calls runtime exactly once.
2. runtime result dict has keys WS2 expects.
3. `ToolCallDetail` includes `toolCallId` and route responses still validate.
4. `save_state()` writes valid JSONB. If passing a JSON string is unsafe, add explicit `$2::jsonb`.
5. `insert_tool_call_log()` writes `toolInput`/`toolOutputMeta` as JSONB safely. If passing JSON string is unsafe, add explicit casts.
6. Multiple `acquire_conn()` calls inside one logical tool log insert do not create correctness issues. Prefer simple/clear fix only if necessary.

### 4.3 Tool correctness

Verify:

1. `get_job_candidate_ranking()` adds `job_app_id` for every candidate it returns.
2. `get_job_candidate_ranking()` caps limit and warns.
3. language filter inclusive behavior is implemented and warns for unknown/missing normalized data.
4. `search_job_applications_text()` is scoped by `jobPostId`.
5. `get_job_application_summary()`, `get_job_application_full_cv()`, `get_candidate_ats_history()` verify `jobAppId` scope.
6. `get_job_application_full_cv()` masks email/phone and redacts address/location.
7. `count_job_applications()` returns scoped counts and only bounded `job_app_ids`.
8. `OFFER` table columns referenced by ATS history actually exist in `database/schema_web_core.sql`; if not, fix query or defer offer section safely.

### 4.4 Existing chat regression check

Verify no semantic changes to:

1. `app/models/chat.py`
2. `app/api/routes_chat.py`
3. `app/services/chat_persistence.py`
4. `app/services/rag_orchestrator.py`
5. `app/services/rag_model_adapters.py`

If untouched, record that. If touched unexpectedly, stop and report.

### 4.5 SQL/schema sanity

Verify:

1. New DDL order is valid.
2. `gen_random_uuid()` has required extension in deployed DB context. If missing, document or add extension only if existing schema already assumes it.
3. `CANDIDATELANGUAGE` partial unique indexes are valid PostgreSQL syntax.
4. `AIJOBPOSTINGTOOL` seed uses `ON CONFLICT` correctly.
5. Column casing in SQL result access matches asyncpg lowercase behavior.

## 5. Required commands

Run explicit tests:

```powershell
.\venv\Scripts\python.exe -m pytest tests/unit/unit_test_jobposting_agent_tools.py tests/unit/unit_test_jobposting_agent_runtime.py -q
.\venv\Scripts\python.exe -m pytest tests/unit/unit_test_jobposting_agent_persistence.py tests/unit/unit_test_routes_jobposting_agent.py -q
.\venv\Scripts\python.exe -m pytest tests/unit/unit_test_nmaiex_candidate_enrichment.py -q
.\venv\Scripts\python.exe -m compileall app
```

Also run one discovery test:

```powershell
.\venv\Scripts\python.exe -m pytest tests/unit -q
```

If it says `no tests ran`, decide whether to add `pytest.ini`:

```ini
[pytest]
python_files = test_*.py *_test.py unit_test_*.py
```

Only add this if it does not introduce broad failures from old tests. If adding it reveals unrelated old failures, report clearly and do not hide them.

Optional but useful:

```powershell
.\venv\Scripts\python.exe -m pytest tests/unit/unit_test_jobposting_agent_tools.py tests/unit/unit_test_jobposting_agent_runtime.py tests/unit/unit_test_jobposting_agent_persistence.py tests/unit/unit_test_routes_jobposting_agent.py tests/unit/unit_test_nmaiex_candidate_enrichment.py -q
git diff --stat
```

## 6. Output report

Create:

`agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_FINAL_INTEGRATION_REVIEW_REPORT.md`

Report sections:

1. Executive verdict:
   - `READY_TO_COMMIT`
   - `READY_WITH_KNOWN_RISKS`
   - `NEEDS_FIXES`
   - `BLOCKED`
2. Files reviewed.
3. Files changed during final integration, if any.
4. Issues found and fixes applied.
5. Issues found but not fixed, with severity.
6. Test commands and results.
7. Existing chat regression assessment.
8. Runtime SDK compatibility assessment.
9. Security/privacy/scope assessment.
10. Remaining operational steps:
    - re-enrichment for old candidates;
    - live Gemini model availability check;
    - DB migration/deploy note;
    - optional Postman/manual smoke.
11. Final recommendation.

## 7. Stop conditions

Stop and report `BLOCKED` if:

1. Runtime cannot be made compatible with installed `google-genai` without architectural rewrite.
2. Core schema DDL is invalid and requires user-level migration decision.
3. Scope validation cannot be made safe.
4. Tests show widespread unrelated failures and you cannot distinguish C3 regressions.
5. Fixing requires modifying existing `/v2/chat` or text-generation adapters.

## 8. Final chat response

After completion, respond briefly:

1. Report path.
2. Verdict.
3. Tests run.
4. Files changed by final integration.
5. Whether user can commit or should run another fix pass.

# FANG Next Phase JobPosting C3 WS3 Tools + Runtime Report

Date: 2026-05-29
Workspace: `C:\Users\os\Desktop\cur_prj\Fang`
Status: COMPLETE

## 1. Summary

WS3 implements the JobPosting Agent read-only tool layer, Gemini native manual tool-calling runtime, query boundary wiring, focused unit tests, and this implementation report.

The implementation preserves WS1/WS2 uncommitted changes in the main workspace. Existing `/v2/chat`, RAG orchestrator/adapters, schema files, and `.understand-anything` were not modified by WS3.

## 2. Files Changed

- Created `app/services/jobposting_tools.py`
- Created `app/services/jobposting_agent_runtime.py`
- Updated `app/services/jobposting_agent_query.py`
- Updated `app/models/jobposting_agent.py`
- Created `tests/unit/unit_test_jobposting_agent_tools.py`
- Created `tests/unit/unit_test_jobposting_agent_runtime.py`
- Created `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WS3_TOOLS_RUNTIME_REPORT.md`

## 3. Tools Implemented

Implemented exactly 7 read-only tools:

- `get_job_posting_context(job_post_id)`
- `get_job_candidate_ranking(job_post_id, limit=10, filters=None)`
- `search_job_applications_text(job_post_id, query, limit=10, filters=None)`
- `get_job_application_summary(job_post_id, job_app_id)`
- `get_job_application_full_cv(job_post_id, job_app_id)`
- `get_candidate_ats_history(job_post_id, job_app_id)`
- `count_job_applications(job_post_id, filters=None)`

Common behavior:

- All tools return `{ok, data, source, warnings, error}`.
- All `job_app_id` tools verify `JOBAPPLICATION.jobPostId == current jobPostId`.
- Ranking wraps `rank_candidates_for_job()` and enriches rows with `job_app_id`, application status, province, years experience, and normalized languages.
- Ranking, count, and text search support normalized filters for status, province, language, min language proficiency, min score where applicable.
- Unknown or missing language/province normalized data is included by default with `data_quality` warnings.
- Full CV output masks email/phone and redacts address/location fields.

## 4. Runtime Implementation

Created `app/services/jobposting_agent_runtime.py` with:

- Gemini-only native function calling through `google-genai==1.69.0`.
- Manual controller loop, not SDK automatic function calling.
- Model candidates:
  - `agent-lite`: `gemini-3.1-flash-lite`, `gemini-flash-lite-latest`
  - `agent-pro`: `gemini-3.5-flash`, `gemini-flash-latest`
- Model-facing tool declarations hide `job_post_id`; controller injects the scoped `job_post_id`.
- Controller validates allowed tool names, scoped `job_app_id`, max steps, full CV load limit, top-N cap, broad compare threshold, and tool result truncation.
- Broad compare guardrail calls `count_job_applications` directly and returns a narrowing message if count exceeds `settings.jobposting_agent_max_compare`.
- Runtime returns the WS2 result dict shape exactly.

## 5. Query Boundary / Wiring Changes

`run_agent_turn_boundary(...)` in `app/services/jobposting_agent_query.py` now:

1. Loads persisted state with `get_state(conversation_id)`.
2. Loads full conversation history with `get_full_history(conversation_id)`.
3. Calls `run_agent_turn(...)`.
4. Returns the WS2-compatible runtime result dict.

`ToolCallDetail` in `app/models/jobposting_agent.py` now includes optional `toolCallId` so the provider/fallback tool call id is not dropped from API responses.

## 6. Guardrails Implemented

- Max tool steps: `settings.jobposting_agent_max_tool_steps`
- Max full CV loads per turn: `settings.jobposting_agent_max_full_cv_loads`
- Max compare/deep set: `settings.jobposting_agent_max_compare`
- Default/top-N cap: `settings.jobposting_agent_default_top_n`, `settings.jobposting_agent_hr_max_top_n`
- Max tool result chars: `settings.jobposting_agent_max_tool_result_chars`
- Tool allowlist: exactly the 7 WS3 tools
- Scope validation for every `job_app_id`
- PII masking for full CV and text snippets
- No full raw CV in `resultSummary`

## 7. Tests Run and Results

Required targeted suites:

```powershell
.\venv\Scripts\python.exe -m pytest tests/unit/unit_test_jobposting_agent_tools.py tests/unit/unit_test_jobposting_agent_runtime.py -q
# 14 passed, 1 warning

.\venv\Scripts\python.exe -m pytest tests/unit/unit_test_jobposting_agent_persistence.py tests/unit/unit_test_routes_jobposting_agent.py -q
# 20 passed, 1 warning

.\venv\Scripts\python.exe -m pytest tests/unit/unit_test_nmaiex_candidate_enrichment.py -q
# 20 passed, 1 warning

.\venv\Scripts\python.exe -m compileall app
# OK
```

Full unit attempt:

```powershell
.\venv\Scripts\python.exe -m pytest tests/unit -q
# no tests ran in 0.01s
```

Reason: current unit files use `unit_test_*.py` names, which are collected when files are passed explicitly but not by pytest's default directory discovery pattern.

## 8. Drift / Conflicts Found

- No schema drift found for WS3-required tables.
- `rank_candidates_for_job()` still returns `candidate_id` but not `jobAppId`; WS3 tool wrapper handles the required scoped `JOBAPPLICATION` join.
- No Google GenAI SDK stop condition found. The installed SDK has `GenerateContentConfig`, `Tool`, `FunctionDeclaration`, and `Part.from_function_response` / `FunctionResponse`.
- Workspace remains dirty from WS1/WS2 and prior docs. WS3 did not revert or clean unrelated changes.

## 9. Integration Notes

- Unit tests mock Gemini and DB/service dependencies; no real provider/network calls are used.
- Production runtime requires `GOOGLE_API_KEY`.
- Current runtime sends only user/assistant history plus a compact state summary to Gemini. Tool call/result parts are only kept inside the current turn.
- Full CV load limits are enforced in the runtime controller, while PII masking is also enforced in the tool layer.
- The existing `/v2/agent/job-posting/query` API contract remains stable; adding optional `toolCallId` is backward-compatible.

## 10. Remaining Risks

- Full-text search currently uses scoped `CVPARSED.rawText ILIKE` for phase 1 rather than vector/semantic search.
- Tool filters are inclusive for unknown language/province data by design; HR may see extra candidates until re-enrichment coverage is high.
- Gemini model candidate availability is not verified with a live API call in unit tests.
- `pytest tests/unit` does not collect the repo's current `unit_test_*.py` naming convention unless pytest config is updated later.


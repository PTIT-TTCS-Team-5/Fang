# FANG C3.1 JobPosting Agent — Final Integration Review Report

**Reviewed by:** Final Integration + Code Review Agent  
**Date:** 2026-05-29  
**SDK Version:** `google-genai==1.69.0`  
**asyncpg Version:** `0.31.0`  
**Python:** 3.14 (venv)

---

## 1. Executive Verdict

### ✅ READY_WITH_KNOWN_RISKS

All 3 workstreams (WS1 Data Foundation, WS2 Persistence/API, WS3 Tools/Runtime) compile together, all 77 unit tests pass, existing chat architecture is untouched, and one integration bug has been fixed during this review. Two known operational risks remain (re-enrichment for old data, live Gemini model availability) but neither blocks a commit.

---

## 2. Files Reviewed

### New C3 Files (untracked)
| File | Lines | WS | Review Status |
|------|-------|----|---------------|
| `app/models/jobposting_agent.py` | 86 | WS2 | ✅ Clean |
| `app/api/routes_jobposting_agent.py` | 267 | WS2 | ✅ Clean |
| `app/services/jobposting_agent_persistence.py` | 277 | WS2 | ⚠️ Fixed (JSONB) |
| `app/services/jobposting_agent_query.py` | 235 | WS2+WS3 | ✅ Clean |
| `app/services/jobposting_agent_runtime.py` | 613 | WS3 | ✅ Clean |
| `app/services/jobposting_tools.py` | 845 | WS3 | ✅ Clean |
| `tests/unit/unit_test_jobposting_agent_persistence.py` | 209 | WS2 | ⚠️ Fixed (assertions) |
| `tests/unit/unit_test_jobposting_agent_runtime.py` | 247 | WS3 | ✅ Clean |
| `tests/unit/unit_test_jobposting_agent_tools.py` | 147 | WS3 | ✅ Clean |
| `tests/unit/unit_test_routes_jobposting_agent.py` | 233 | WS2 | ✅ Clean |

### Modified Tracked Files
| File | WS | Review Status |
|------|----|---------------|
| `app/core/config.py` | WS2 | ✅ Clean — 11 C3 config fields added |
| `app/main.py` | WS2 | ✅ Clean — router registration only |
| `app/services/nmaiex_candidate_enrichment.py` | WS1 | ✅ Clean |
| `app/services/nmaiex_ranking_service.py` | WS1 | ✅ Clean |
| `database/schema_ai_core.sql` | WS1 | ✅ Clean |
| `database/schema_web_core.sql` | WS1 | ✅ Clean |
| `.env.example` | WS2 | ✅ Clean |
| `tests/unit/unit_test_nmaiex_candidate_enrichment.py` | WS1 | ✅ Clean |

### Existing Chat Files (regression check)
| File | Status |
|------|--------|
| `app/models/chat.py` | ✅ **UNTOUCHED** — no diff |
| `app/api/routes_chat.py` | ✅ **UNTOUCHED** — no diff |
| `app/services/chat_persistence.py` | ✅ **UNTOUCHED** — no diff |
| `app/services/rag_orchestrator.py` | ✅ **UNTOUCHED** — no diff |
| `app/services/rag_model_adapters.py` | ✅ **UNTOUCHED** — no diff |

---

## 3. Files Changed During Final Integration

| File | Change | Reason |
|------|--------|--------|
| `app/services/jobposting_agent_persistence.py` | Removed `json.dumps()` pre-serialisation for JSONB params | **Bug fix:** asyncpg's JSONB codec calls `json.dumps()` internally; passing a pre-serialised string causes double-encoding (stored as JSON string, not JSON object) |
| `app/services/jobposting_agent_persistence.py` | Removed unused `import json` | Cleanup after JSONB fix |
| `tests/unit/unit_test_jobposting_agent_persistence.py` | Updated `save_state` assertion from string to dict | Test was asserting buggy (double-encoding) behavior |
| `tests/unit/unit_test_jobposting_agent_persistence.py` | Added JSONB dict assertions for `insert_tool_call_log` | Verify correct dict-passing for `toolInput`/`toolOutputMeta` |
| `pytest.ini` | **NEW** — `python_files = test_*.py *_test.py unit_test_*.py` | Fix `pytest tests/unit` discovery (was 0 tests found) |

---

## 4. Issues Found and Fixes Applied

### 4.1 JSONB Double-Encoding in Persistence (P1 — Fixed)

**Location:** `app/services/jobposting_agent_persistence.py` — `save_state()` (line 217) and `insert_tool_call_log()` (line 246)

**Problem:** Both functions called `json.dumps()` on Python dicts before passing them as asyncpg parameters to JSONB columns. asyncpg 0.31.0's built-in JSONB codec calls `json.dumps()` internally, so the value was double-encoded:
- Input: `{"key": "val"}` → `json.dumps()` → `'{"key": "val"}'` → asyncpg `json.dumps()` → `'"{\\"key\\": \\"val\\"}"'`
- Stored as JSON string `"{"key": "val"}"` instead of JSON object `{"key": "val"}`

**Impact:** The `get_state()` read path accidentally handled this (it checked `isinstance(val, str)` and ran `json.loads()`), so the bug was functionally masked. However, SQL queries on `stateJson` (e.g. `stateJson->>'key'`) would fail, and the stored data was semantically wrong.

**Fix:** Pass Python dicts directly to asyncpg instead of pre-serialised strings.

### 4.2 pytest Test Discovery (P2 — Fixed)

**Problem:** All test files use the `unit_test_` prefix. pytest's default pattern is `test_*.py`, so `pytest tests/unit` found 0 tests.

**Fix:** Created `pytest.ini` with `python_files = test_*.py *_test.py unit_test_*.py`. Verified 77 tests pass with no unrelated failures.

---

## 5. Issues Found but Not Fixed (with Severity)

| # | Severity | Issue | Location | Rationale for Not Fixing |
|---|----------|-------|----------|--------------------------|
| 1 | **Low** | `jobposting_agent_enabled` config defined but never checked — routes always active | `config.py` L48, `routes_jobposting_agent.py` | Feature flag enforcement is a new feature, not integration correctness |
| 2 | **Low** | `jobposting_agent_max_turn_seconds` defined but never enforced as timeout | `config.py` L55, `runtime.py` | Timeout enforcement is a new feature scope |
| 3 | **Low** | Router missing `tags=["JobPosting Agent"]` for OpenAPI docs | `routes_jobposting_agent.py` L34 | Cosmetic; does not affect correctness |
| 4 | **Low** | Uses `BufferError` (built-in) for archived conversations instead of custom exception | `query.py` L102, `routes.py` L66-70 | Works correctly; architectural preference |
| 5 | **Info** | `_sanitize_args` line 264 can raise `TypeError` on missing `job_app_id` | `runtime.py` L264 | Caught by outer `try/except` in `_execute_tool` — safe |
| 6 | **Info** | GET messages returns 404 when conversation exists but has no messages | `routes.py` L153-157 | Potential UX concern for new conversations, but functionally acceptable |

---

## 6. Test Commands and Results

### Required Tests (all from prompt §5)

```
.\venv\Scripts\python.exe -m pytest tests/unit/unit_test_jobposting_agent_tools.py tests/unit/unit_test_jobposting_agent_runtime.py -q
→ 14 passed ✅

.\venv\Scripts\python.exe -m pytest tests/unit/unit_test_jobposting_agent_persistence.py tests/unit/unit_test_routes_jobposting_agent.py -q
→ 20 passed ✅

.\venv\Scripts\python.exe -m pytest tests/unit/unit_test_nmaiex_candidate_enrichment.py -q
→ 20 passed ✅

.\venv\Scripts\python.exe -m compileall app
→ All modules compile successfully ✅

.\venv\Scripts\python.exe -m pytest tests/unit -q
→ 77 passed ✅ (after adding pytest.ini)
```

### Optional Combined Test

```
.\venv\Scripts\python.exe -m pytest tests/unit/unit_test_jobposting_agent_tools.py tests/unit/unit_test_jobposting_agent_runtime.py tests/unit/unit_test_jobposting_agent_persistence.py tests/unit/unit_test_routes_jobposting_agent.py tests/unit/unit_test_nmaiex_candidate_enrichment.py -q
→ 54 passed ✅
```

### Test Breakdown by WS

| Workstream | Test File | Tests | Status |
|------------|-----------|-------|--------|
| WS1 | `unit_test_nmaiex_candidate_enrichment.py` | 20 | ✅ |
| WS2 | `unit_test_jobposting_agent_persistence.py` | 8 | ✅ |
| WS2 | `unit_test_routes_jobposting_agent.py` | 12 | ✅ |
| WS3 | `unit_test_jobposting_agent_tools.py` | 6 | ✅ |
| WS3 | `unit_test_jobposting_agent_runtime.py` | 8 | ✅ |
| Pre-existing | 6 other unit_test files | 23 | ✅ |
| **TOTAL** | | **77** | **✅ All pass** |

---

## 7. Existing Chat Regression Assessment

**Verdict: ✅ NO REGRESSION**

All 5 existing chat files were verified via `git diff --name-only HEAD`:
- `app/models/chat.py` — 0 changes
- `app/api/routes_chat.py` — 0 changes
- `app/services/chat_persistence.py` — 0 changes
- `app/services/rag_orchestrator.py` — 0 changes
- `app/services/rag_model_adapters.py` — 0 changes

The JobPosting Agent C3 is a **completely separate parallel system** sharing only:
- `app.core.config.settings` (additive fields)
- `app.core.database.acquire_conn` (read-only shared utility)
- `app.core.logging.logger` (shared utility)
- `app.services.nmaiex_ranking_service` (WS1 extended, backward-compatible)
- `app.services.nmaiex_mapper_service` (WS3 reads `PROFICIENCY_LEVELS` constant)

---

## 8. Runtime SDK Compatibility Assessment

**Verdict: ✅ FULLY COMPATIBLE with `google-genai==1.69.0`**

Verified by direct Python inspection of the installed SDK:

| Usage in Code | SDK Field | Status |
|---------------|-----------|--------|
| `types.GenerateContentConfig(systemInstruction=..., maxOutputTokens=...)` | Accepts camelCase kwargs → maps to `system_instruction`, `max_output_tokens` | ✅ |
| `types.Tool(functionDeclarations=...)` | Maps to `function_declarations` | ✅ |
| `types.FunctionDeclaration(name=..., description=..., parametersJsonSchema=...)` | Maps to `parameters_json_schema` | ✅ |
| `types.Part.from_function_response(name=..., response=...)` | Static method exists, correct signature | ✅ |
| `types.Part(functionResponse=types.FunctionResponse(name=..., response=..., id=...))` | `FunctionResponse` has `id`, `name`, `response` fields | ✅ |
| `part.function_call` attribute access | Field exists on `Part` as `function_call` (snake_case) | ✅ |
| `getattr(fc, 'name')`, `getattr(fc, 'args')`, `getattr(fc, 'id')` | `FunctionCall` has `name`, `args`, `id` fields | ✅ |
| `response.candidates[0].content.parts` | `GenerateContentResponse` → `Candidate` → `Content` → `parts` | ✅ |
| `client.aio` as async context manager | `AsyncClient` has `__aenter__` | ✅ |

**Key note:** The Pydantic-based SDK models support both snake_case field names and camelCase aliases as constructor kwargs. The code consistently uses camelCase kwargs which are correctly mapped.

---

## 9. Security / Privacy / Scope Assessment

**Verdict: ✅ ADEQUATE for Phase 1**

### Scope Validation
| Check | Status | Evidence |
|-------|--------|----------|
| `get_job_candidate_ranking()` adds `job_app_id` for every candidate | ✅ | `jobposting_tools.py:454` via `_fetch_application_enrichment` |
| `get_job_candidate_ranking()` caps limit and warns | ✅ | `jobposting_tools.py:421-429` |
| Language filter inclusive behavior with warnings | ✅ | `jobposting_tools.py:199-241` |
| `search_job_applications_text()` scoped by `jobPostId` | ✅ | SQL `WHERE ja.jobPostId = $1` at L550 |
| `get_job_application_summary()` verifies scope | ✅ | `jobposting_tools.py:637` calls `_get_application_detail` which calls `validate_job_application_scope` |
| `get_job_application_full_cv()` verifies scope | ✅ | Same pattern at L692 |
| `get_candidate_ats_history()` verifies scope | ✅ | Direct call to `validate_job_application_scope` at L732 |
| `get_job_application_full_cv()` masks email/phone | ✅ | `mask_email()` at L709, `mask_phone()` at L710 |
| `get_job_application_full_cv()` redacts address | ✅ | `"address": "REDACTED"` at L712 |
| `count_job_applications()` returns scoped counts | ✅ | SQL scoped by `jobPostId` at L806, bounded `job_app_ids` at L840 |
| OFFER table columns exist | ✅ | `offerId, jobAppId, salary, description, stat, subAt, ver, hrId` all present in `schema_web_core.sql:302-313` |

### Privacy — Tool Outputs and Logs
| Check | Status | Evidence |
|-------|--------|----------|
| Tool `resultSummary` does NOT contain raw CV/email/phone | ✅ | `_summarize_tool_result()` returns counts and generic messages only |
| `toolInput` in audit log does NOT contain `job_post_id` | ✅ | `_model_visible_args()` removes `job_post_id` at L270 |
| Full CV text is PII-masked before returning to model | ✅ | `mask_pii_text()` applied to raw text at L702 |
| CV search snippets are PII-masked | ✅ | `mask_pii_text()` applied at L572 |
| Interview feedback comments are PII-masked | ✅ | `mask_pii_text()` at L778 |
| Offer descriptions are PII-masked | ✅ | `mask_pii_text()` at L783 |

### Scope Leakage Prevention
| Check | Status | Evidence |
|-------|--------|----------|
| `job_post_id` injected by controller, not by model | ✅ | `_sanitize_args()` at L257 |
| `jobAppId` cross-scope blocked with `ACCESS_DENIED` | ✅ | `_validate_job_app_arg()` at L274-283 |
| Runtime `_sanitize_args` always overwrites `job_post_id` | ✅ | L257 unconditionally sets it |

---

## 10. SQL / Schema Sanity

### DDL Validation
| Check | Status | Notes |
|-------|--------|-------|
| DDL order valid (no forward references) | ✅ | `schema_web_core.sql` runs first; `schema_ai_core.sql` references its tables. Within `schema_ai_core.sql`, all FKs point to previously-declared tables. |
| `gen_random_uuid()` extension | ✅ | Built-in in PostgreSQL 13+. No `pgcrypto` needed. Both `AICHATCONVERSATION` and `AIJOBPOSTINGCHATCONVERSATION` use it consistently. |
| `CANDIDATELANGUAGE` partial unique indexes | ✅ | Valid PostgreSQL syntax: `WHERE langId IS NOT NULL` and `WHERE langId IS NULL AND rawName IS NOT NULL` with `lower(rawName)` expression. |
| `AIJOBPOSTINGTOOL` seed uses `ON CONFLICT` correctly | ✅ | `ON CONFLICT (toolName) DO NOTHING` — targets the UNIQUE constraint on `toolName`. |
| Column casing in SQL result access | ✅ | asyncpg returns lowercase. Code uses `_get(d, "camelCase", "lowercase")` helper throughout for safe access. Tests correctly mock lowercase keys. |
| JSONB parameter handling | ✅ | **Fixed during this review** — dicts passed directly to asyncpg (no pre-serialisation). |

### OFFER Table Column Verification
The `get_candidate_ats_history` tool queries:
```sql
SELECT offerId AS source_id, stat, salary, description, subAt AS submitted_at, ver, hrId AS hr_id FROM OFFER
```
Against `schema_web_core.sql:302-313`:
```sql
CREATE TABLE OFFER (offerId, jobAppId, salary, description, stat, subAt, ver, hrId)
```
✅ All columns exist and match.

---

## 11. Remaining Operational Steps

### A. Re-enrichment for Old Candidates (Pre-production)
Old candidates have no `CANDIDATELANGUAGE` rows. Until re-enrichment runs:
- Language filters include these candidates with a `data_quality` warning (inclusive fallback)
- Province filters include candidates without `user.provId` (inclusive fallback)
- Language scoring falls back to `(0.0, 0.0)` for un-enriched candidates

**Action:** Run `_normalize_and_persist_languages()` and `_normalize_and_update_province()` for all existing candidates before production launch.

### B. Live Gemini Model Availability Check
Model candidates are `gemini-3.1-flash-lite` and `gemini-3.5-flash`. These models have NOT been verified against a live Gemini API endpoint.

**Action:** Before production, verify with a real `GOOGLE_API_KEY` that at least one model candidate is available in the target GCP project/region.

### C. DB Migration / Deploy Note
New tables to create in production:
1. `CANDIDATELANGUAGE` (in `schema_web_core.sql`) + 4 indexes
2. `AIJOBPOSTINGTOOL` (in `schema_ai_core.sql`) + 7 seed rows
3. `AIJOBPOSTINGCHATCONVERSATION` + index
4. `AIJOBPOSTINGCHATMESSAGE` + index
5. `AIJOBPOSTINGCHATSTATE`
6. `AIJOBPOSTINGTOOLCALLLOG` + index

**Prerequisites:**
- PostgreSQL 13+ (for `gen_random_uuid()`)
- `schema_web_core.sql` tables (JOBPOSTING, HR, etc.) must exist first

### D. Optional Postman / Manual Smoke Test
After deploying, smoke-test the following endpoints:
1. `POST /v2/agent/job-posting/query` — happy path (requires valid `jobPostId`, `hrId`, and `GOOGLE_API_KEY`)
2. `POST /v2/agent/job-posting/query` — with invalid `hrId` → expect 403
3. `GET /v2/agent/job-posting/conversations?jobPostId=X&hrId=Y` → expect 200
4. `GET /v2/agent/job-posting/conversations/{id}/messages` → expect 200/404
5. `PATCH /v2/agent/job-posting/conversations/{id}` → expect 200
6. `DELETE /v2/agent/job-posting/conversations/{id}?hrId=Y` → expect 204

---

## 12. Final Recommendation

**The C3.1 JobPosting Agent code is READY TO COMMIT.**

One integration bug was found and fixed (JSONB double-encoding in persistence). pytest discovery was also fixed. All 77 tests pass. Existing chat architecture is completely untouched. SDK compatibility is confirmed. Security/privacy/scope checks pass.

The user should:
1. ✅ Commit all files (tracked + untracked) including `pytest.ini`
2. ⚠️ Run re-enrichment for old candidates before production
3. ⚠️ Verify Gemini model availability with a real API key before production
4. ⚠️ Execute DB migration (6 new tables) in the correct order

No further fix pass is needed.

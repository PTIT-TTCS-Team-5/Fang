# FANG Next Phase JobPosting C3 Phase 0 Baseline Report

Date: 2026-05-29  
Scope: Phase 0 baseline + execution readiness for JobPosting Agent C3.1.  
Constraint: No feature implementation performed.

## 1. Executive Readiness Verdict

`READY_WITH_WARNINGS`

- WS1 Data Foundation and WS2 Persistence/API Shell can start in parallel if they stay inside their file boundaries.
- WS3 Tools/Runtime should wait until WS1 schema decisions are merged and WS2 model/persistence contracts are stable.
- No P0 blocker found in the official plan versus current code reality.
- Current Python interpreters can compile the app, but pytest is not installed in either global Python or repo `venv`, so unit baseline is environment-blocked.
- Worktree was already dirty before this report: `.understand-anything/knowledge-graph.json`, `.understand-anything/meta.json`, and untracked `C3_PHASE0_BASELINE_ORCHESTRATOR_PROMPT.md`.

## 2. Repo Baseline

1. Current branch: `try-hard-jobposting`.
2. `git status --short` before writing this report:
   - `M .understand-anything/knowledge-graph.json`
   - `M .understand-anything/meta.json`
   - `?? agent_workflow_doc/try_hard_jobposting/C3_PHASE0_BASELINE_ORCHESTRATOR_PROMPT.md`
3. Knowledge graph exists at `.understand-anything/knowledge-graph.json`. Metadata: project `FANG - AI Core v2.0`, languages `python/sql/markdown/yaml/json/config`, frameworks `FastAPI`, `SQLAlchemy`, `LangChain`, `Pydantic`, `pgvector`.
4. Python/test environment:
   - Global `python` resolves to `C:\Python314\python.exe`.
   - Repo `venv` exists at `C:\Users\os\Desktop\cur_prj\Fang\venv`.
   - `pytest` is missing from both interpreters.
5. Dependency observation:
   - `requirements.txt:13` pins `google-genai==1.69.0`.
   - `requirements.txt` does not include `pytest`.
   - `app/core/config.py:4-51` has no JobPosting Agent config yet; only existing DB, embedding, LLM key, RAG, context, and CORS settings.

## 3. Code Reality Map

| Area | Current files | What exists now | C3 impact |
|---|---|---|---|
| Existing JobApplication chat | `app/models/chat.py`, `app/api/routes_chat.py`, `app/services/chat_persistence.py`, `database/schema_ai_core.sql` | `ChatQueryRequest` requires `jobAppId` and `modelMode` (`app/models/chat.py:14-19`). `/chat/query` calls `process_chat_query(job_app_id=...)` (`app/api/routes_chat.py:47-66`). Tables `AICHATCONVERSATION` and `AICHATMESSAGE` are `jobAppId` scoped (`database/schema_ai_core.sql:88-114`). | Do not reuse or mutate existing chat semantics. JobPosting Agent needs dedicated models/routes/persistence/tables. |
| Existing text generation runtime | `app/services/rag_orchestrator.py`, `app/services/rag_model_adapters.py` | `GenerationMessage` is text-only role/content (`rag_model_adapters.py:35-37`). `GenerationAdapter.generate()` returns `tuple[str, str]` (`rag_model_adapters.py:46-54`). Gemini adapter calls `generate_content` without tools/function declarations (`rag_model_adapters.py:148-161`). `invoke_generation()` returns `GenerationTrace.response` text (`rag_orchestrator.py:66-72`, `282-318`). | Official plan is correct: create separate `jobposting_agent_runtime.py`; do not extend `GenerationAdapter` for C3. |
| NMAIex enrichment | `app/services/nmaiex_candidate_enrichment.py`, `app/services/nmaiex_mapper_service.py` | `EnrichmentPayload` has only `experience` and `skills` (`nmaiex_candidate_enrichment.py:23-26`). `_coerce_enrichment_payload()` extracts only these two fields (`nmaiex_candidate_enrichment.py:341-357`). `enrich_candidate_structured_data()` writes `CANDIDATE.expyears`, `CANDIDATESKILL`, and `CANDIDATE_SKILL_RAW` only (`nmaiex_candidate_enrichment.py:250-308`). | WS1/normalization work must add language/location extraction and persistence before language/province tools can be trusted. |
| NMAIex ranking/language scoring | `app/services/nmaiex_ranking_service.py`, `app/services/nmaiex_mapper_service.py` | `compute_language_score()` reads candidate language dicts and maps raw names with inline heuristics; raw proficiency not in `PROFICIENCY_LEVELS` falls back to level 1 (`nmaiex_ranking_service.py:125-183`). `rank_candidates_for_job()` returns `candidate_id`, `candidate_name`, `match_score`, `score_breakdown`; no `job_app_id` in result (`nmaiex_ranking_service.py:304-515`). | Tool wrapper must enrich ranking output with `jobAppId`; ranking language score should be refactored to normalized `CANDIDATELANGUAGE` after schema exists. |
| DB schema | `database/schema_ai_core.sql`, `database/schema_web_core.sql` | AI schema has `CVPARSED`, `NMAIEX_CANDIDATE_ENRICHMENT_JOB`, `AIDOCUMENTCHUNK`, `AIQUERYLOG`, `AICHATCONVERSATION`, `AICHATMESSAGE` (`schema_ai_core.sql:15-114`). Web schema has `LANGUAGE`, `JOB_LANG_REQUIREMENT`, `JOBAPPLICATION`, ATS tables, and `"user".provId` (`schema_web_core.sql:41-59`, `171-240`, `247-310`). No `AIJOBPOSTING*` or `CANDIDATELANGUAGE` tables found. | WS1 owns schema additions. WS2 must wait for exact table names/columns or use agreed stubs only. |
| Tests | `tests/unit/unit_test_nmaiex_candidate_enrichment.py` | Existing enrichment test includes `languages` in payload but asserts only skill behavior (`unit_test_nmaiex_candidate_enrichment.py:61-110`). No JobPosting Agent test files exist yet. | C3 needs new tests. Baseline pytest currently cannot run until test dependency is installed. |

## 4. Drift / Blockers

### No P0 blockers found

The official implementation plan matches current code reality: required JobPosting Agent tables, runtime, routes, tools, config, and normalization are not present yet and are correctly scoped as implementation work.

### P1 must-fix: Test runner missing from environment

1. Evidence: `python -m pytest tests/unit/unit_test_nmaiex_candidate_enrichment.py` fails with `No module named pytest`; `.\venv\Scripts\python.exe -m pip show pytest` reports package not found; `requirements.txt` has no pytest entry.
2. Why it matters: WS agents cannot provide meaningful pass/fail evidence for required unit suites until the local/dev test dependency is available.
3. Recommendation: before accepting implementation PRs, install or document dev test dependencies. Prefer adding a dev requirements file or project test setup instead of silently relying on global packages.

### P1 must-fix: Normalized candidate language data does not exist yet

1. Evidence: `database/schema_web_core.sql` contains `LANGUAGE` and `JOB_LANG_REQUIREMENT` (`schema_web_core.sql:41-45`, `171-176`) but no `CANDIDATELANGUAGE`; enrichment payload has no language/location fields (`nmaiex_candidate_enrichment.py:23-26`, `341-357`).
2. Why it matters: C3's "tiếng Anh hạng C trở lên" and province filters cannot be correct until WS1 adds schema and enrichment persistence.
3. Recommendation: merge WS1 data foundation before WS3 filter-dependent tools and runtime smoke tests.

### P1 must-fix: Ranking output lacks `job_app_id`

1. Evidence: `rank_candidates_for_job()` result appends `candidate_id`, `candidate_name`, `match_score`, and `score_breakdown` only (`nmaiex_ranking_service.py:500-515`).
2. Why it matters: C3 memory is locked to `workingSetJobAppIds`, and drill-down tools must scope by `jobAppId`.
3. Recommendation: implement a tool-layer wrapper or ranking service enhancement that joins `JOBAPPLICATION` for the current `jobPostId` and returns `job_app_id` for every candidate.

### P2 warning: WS-D discovery differs from official plan on `modelMode`

1. Evidence: WS-D discovery proposed optional `modelMode`, but official plan locks no HR-exposed `modelMode`; current chat request exposes `modelMode` for existing `/v2/chat` (`app/models/chat.py:14-19`).
2. Why it matters: An implementation agent reading WS-D alone may accidentally expose model selection in the new API.
3. Recommendation: WS2 must follow the official plan: backend config chooses model; new `JobPostingAgentQueryRequest` must not expose HR `modelMode`.

### P2 warning: `PROVINCE.provId` is string, not int

1. Evidence: `PROVINCE.provId VARCHAR(20)` and `"user".provId VARCHAR(20)` (`schema_web_core.sql:17-18`, `51-59`).
2. Why it matters: Some planning prose says `province_id` as integer; implementation must use current string `provId` values such as `TPHCM`.
3. Recommendation: WS1/WS3 contracts should name it `province_id` only at API level if desired, but DB access must use `VARCHAR(20)` `provId`.

## 5. Workstream Execution Plan

### WS1 Data Foundation

1. Branch/worktree: `codex/ws1-jobposting-data-foundation`.
2. Agent/model: Tier 2 coding agent, high reasoning if editing enrichment + ranking together.
3. Files allowed to modify:
   - `database/schema_web_core.sql`
   - `database/schema_ai_core.sql`
   - `app/services/nmaiex_candidate_enrichment.py`
   - `app/services/nmaiex_mapper_service.py` if language mapper is shared
   - `app/services/nmaiex_ranking_service.py`
   - `tests/unit/unit_test_nmaiex_candidate_enrichment.py`
   - optional `scripts/re_enrich_candidate_language_province.py`
4. Files must not modify:
   - `app/api/routes_chat.py`
   - `app/models/chat.py`
   - `app/services/rag_orchestrator.py`
   - `app/services/rag_model_adapters.py`
   - new API/runtime files owned by WS2/WS3 unless explicitly coordinated.
5. Acceptance criteria:
   - `CANDIDATELANGUAGE` exists with indexes and raw-value preservation.
   - JobPosting Agent AI tables/tool catalog exist in `schema_ai_core.sql`.
   - Enrichment extracts languages and location, writes `CANDIDATELANGUAGE`, updates `"user".provId` best-effort, and preserves current skill/exp behavior.
   - Ranking language score or helper can use normalized language data.
   - Re-enrichment path is documented or scripted.
6. Tests to run:
   - `python -m compileall app`
   - `python -m pytest tests/unit/unit_test_nmaiex_candidate_enrichment.py`
   - targeted ranking tests if added.
7. Merge prerequisites: test dependency available; no API/runtime branch should assume normalized filters before WS1 merge.

### WS2 Persistence/API Shell

1. Branch/worktree: `codex/ws2-jobposting-api-shell`.
2. Agent/model: Tier 2 coding agent, medium/high reasoning.
3. Files allowed to modify/create:
   - `app/models/jobposting_agent.py`
   - `app/services/jobposting_agent_persistence.py`
   - `app/services/jobposting_agent_query.py` as a shell around a stub/mock runtime only if needed
   - `app/api/routes_jobposting_agent.py`
   - `app/main.py`
   - `app/core/config.py`
   - `.env.example` if present
   - route/persistence tests.
4. Files must not modify:
   - Existing `/v2/chat` models/routes/persistence.
   - `rag_orchestrator.py` and `rag_model_adapters.py`.
   - Enrichment/ranking internals owned by WS1.
5. Acceptance criteria:
   - `/v2/agent/job-posting` route namespace exists.
   - Query/list/messages/rename/archive contracts match official plan.
   - New request model does not expose HR `modelMode`.
   - Conversation CRUD uses `jobPostId` + `hrId`, title, archive, state, and sanitized tool message fields.
   - Router registration does not change existing `/v2/chat`.
6. Tests to run:
   - `python -m compileall app`
   - persistence/route unit tests with mocked DB/runtime once pytest is available.
7. Merge prerequisites: can run in parallel with WS1 if it does not require final tool implementation; final merge should occur after WS1 schema or be rebased onto WS1.

### WS3 Tools/Runtime

1. Branch/worktree: `codex/ws3-jobposting-tools-runtime`.
2. Agent/model: stronger Tier 2 or Tier 1-coded implementation because this touches runtime guardrails and tool security.
3. Files allowed to modify/create:
   - `app/services/jobposting_tools.py`
   - `app/services/jobposting_agent_runtime.py`
   - `app/services/jobposting_agent_query.py`
   - `app/core/config.py` only for agent limits/model fields if not already done by WS2
   - runtime/tool tests.
4. Files must not modify:
   - `rag_orchestrator.py`
   - `rag_model_adapters.py`
   - existing `/v2/chat`.
   - schema files unless WS1 missed a field and synthesis approves a follow-up.
5. Acceptance criteria:
   - 7 read-only tools implemented with job scope validation.
   - Gemini native manual tool loop implemented separately from text-generation adapters.
   - Guardrails enforced in controller: max steps, max full CV loads, max compare/top N, scope, truncation, PII masking.
   - Ranking tool returns `job_app_id`.
   - Tool output/log summaries are sanitized.
6. Tests to run:
   - `python -m compileall app`
   - runtime loop unit tests with mocked Gemini responses
   - tool unit tests with mocked DB/service calls.
7. Merge prerequisites: wait for WS1 schema and preferably WS2 Pydantic/persistence contracts. Do not begin final integration until WS1 + WS2 APIs are stable.

### Final Integration

1. Branch/worktree: `codex/final-jobposting-c3-integration`.
2. Agent/model: Tier 1 review/integration agent.
3. Files allowed to modify:
   - Integration glue across `jobposting_agent_query.py`, route registration, config, tests, docs.
   - Minimal bug fixes in WS-owned files after reading diffs.
4. Files must not modify:
   - Existing JobApplication chat behavior unless a test proves accidental regression and user approves.
5. Acceptance criteria:
   - End-to-end query flow works with mocked or local DB.
   - Smoke flows from official plan/WS-D are represented in tests or manual evidence.
   - Existing `/v2/chat` compile/test baseline remains unchanged.
6. Tests to run:
   - `python -m compileall app`
   - `python -m pytest tests/unit`
   - targeted smoke/manual API checks if DB and provider keys are configured.
7. Merge prerequisites: WS1, WS2, and WS3 merged/rebased; pytest/dev dependency resolved.

## 6. Conflict Risk Matrix

| File/Area | WS likely touching it | Conflict risk | Mitigation |
|---|---|---|---|
| `database/schema_ai_core.sql` | WS1, possibly WS2 | High | WS1 owns DDL for `AIJOBPOSTING*`; WS2 reads schema only until WS1 merges. |
| `database/schema_web_core.sql` | WS1 | Medium | WS1 owns `CANDIDATELANGUAGE`; no other WS edits schema_web. |
| `app/core/config.py` | WS2, WS3 | Medium | WS2 adds fields from official plan; WS3 only reads them or adds missing runtime constants after rebase. |
| `app/main.py` | WS2, Final Integration | Low | WS2 owns router include; final only verifies registration. |
| `app/services/nmaiex_candidate_enrichment.py` | WS1 | High | Single owner. WS3 must consume normalized data, not patch enrichment. |
| `app/services/nmaiex_ranking_service.py` | WS1, WS3 | Medium | WS1 may refactor language scoring; WS3 should wrap ranking output unless WS1 explicitly adds `job_app_id`. |
| new JobPosting Agent files | WS2, WS3 | High | Split persistence/API shell (`models`, `routes`, `persistence`, query shell) from tools/runtime. Use final integration branch to wire. |

## 7. Baseline Test Results

| Command | Result | Notes | Blocking? |
|---|---|---|---|
| `git status --short` | Pass | Dirty before report: `.understand-anything/*` modified and Phase 0 prompt untracked. | No, but agents must not overwrite unrelated changes. |
| `python -m pytest tests/unit/unit_test_nmaiex_candidate_enrichment.py` | Fail | Global Python `C:\Python314\python.exe` has no `pytest`. Environment/setup failure, not code regression evidence. | Yes for test evidence quality. |
| `.\venv\Scripts\python.exe -m pytest tests/unit/unit_test_nmaiex_candidate_enrichment.py` | Fail | Repo `venv` also has no `pytest`. | Yes for test evidence quality. |
| `python -m pytest tests/unit` | Fail | Same missing `pytest` failure. | Yes for full unit baseline. |
| `.\venv\Scripts\python.exe -m pip show pytest` | Fail | Confirms pytest is not installed in repo `venv`. | Yes until resolved. |
| `python -m compileall app` | Pass | App files compile under Python 3.14. | No. |
| `.\venv\Scripts\python.exe -m compileall app` | Pass | App files compile under repo `venv`. | No. |

## 8. WS Handoff Notes

### WS1 Data Foundation

- Implement only schema + normalization foundation. Do not create API/runtime.
- Add `CANDIDATELANGUAGE` and JobPosting Agent AI tables exactly per official plan, adapting `provId` as `VARCHAR(20)` to current schema.
- Extend enrichment from `experience/skills` to `languages/location`, preserving existing skill and expyear behavior.
- Use existing `normalize_proficiency()` and `map_string_to_province_id()`; add language mapper using `LANGUAGE`.
- Add tests for language extraction, unknown language, proficiency normalization, province update, and existing skill behavior.

### WS2 Persistence/API Shell

- Implement dedicated JobPosting Agent models, persistence, and routes. Keep existing `/v2/chat` untouched.
- Do not expose `modelMode` in HR request; use backend config.
- Persist state references and sanitized tool messages only; no full CV/email/phone in messages or logs.
- API namespace is `/v2/agent/job-posting`; implement query/list/messages/rename/archive.
- Runtime/tool layer may be stubbed/mocked for tests until WS3 is merged.

### WS3 Tools/Runtime

- Implement a separate Gemini native manual tool loop; do not modify `rag_model_adapters.py` or `rag_orchestrator.py`.
- Implement exactly 7 MVP read-only tools and enforce job scope in controller/tool layer.
- Ranking tool must return `job_app_id` and cap HR top N at 25 with warnings.
- Full CV tool is single-candidate only and must mask PII before model/log persistence.
- Treat CV/JD/email/interview content as untrusted data.

### Final Integration Agent

- Rebase/merge WS1 first, then WS2, then WS3, then integration fixes.
- Run compile and unit suites after test environment is fixed.
- Verify `/v2/chat` still compiles and existing chat models/routes have not changed semantically.
- Run smoke flows: top 10 ranking, language refine, too-large compare, rename, auto-title, archive, invalid request.

## 9. Final Recommendation

1. Start WS1 + WS2 in parallel: yes, with strict ownership. WS1 owns schema/normalization; WS2 owns API/persistence shell.
2. WS3 should not start full implementation immediately. It can prepare tests/contracts, but real tool/runtime coding should wait for WS1 schema and WS2 model/persistence contracts.
3. Merge order:
   - WS1 Data Foundation
   - WS2 Persistence/API Shell rebased onto WS1
   - WS3 Tools/Runtime rebased onto WS1 + WS2
   - Final Integration
4. User approval needed before code: no architecture re-approval required. The only practical gate is fixing or approving test environment setup so implementation agents can run pytest and report real pass/fail results.

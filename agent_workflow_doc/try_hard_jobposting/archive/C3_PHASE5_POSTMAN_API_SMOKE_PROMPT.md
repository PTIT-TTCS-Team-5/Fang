# C3 Phase 5 Prompt — JobPosting Agent Postman API Smoke Test

You are working in the FANG repository at:

`C:\Users\os\Desktop\cur_prj\Fang`

Your task is narrowly scoped: create and run a Postman-first smoke test suite for the completed C3 JobPosting Agent backend after Risk A re-enrichment/backfill has been handled. Do not implement frontend, do not change runtime behavior, and do not refactor backend code unless a smoke-test blocker is conclusively found and you document it first.

## Recommended Model

Use Claude Sonnet if available because this task requires careful operational testing, Postman collection maintenance, DB inspection, and clear failure diagnosis. Gemini Flash 3.5 is also acceptable if it has Postman MCP access.

## Context to Read First

Read these files before editing:

1. `postman/POSTMAN_SETUP_GUIDE.md`
2. `postman/FANG_v2_Collection.postman_collection.json`
3. `postman/collections/FANG v2 API Test Suite/Chat API/POST v2-chat-query.request.yaml`
4. `postman/collections/FANG v2 API Test Suite/Smoke Tests/Test Chat-Ingestion-Ranking Flow.request.yaml`
5. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_OFFICIAL_IMPLEMENTATION_PLAN.md`
6. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_FINAL_INTEGRATION_REVIEW_REPORT.md`
7. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_RISK_A_REENRICHMENT_REPORT.md` if it exists
8. `app/api/routes_jobposting_agent.py`
9. `app/models/jobposting_agent.py`

## Database and Server

Use this local DB:

```powershell
$env:DATABASE_URL="postgresql://postgres:hungklv123@localhost:5432/micareer_lite_db"
```

Use local API base URL:

```text
http://localhost:8000
```

If the FastAPI server is not running, start it in the repo:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If port 8000 is occupied by a correct FANG server, reuse it. If it is occupied by something else, use another port and set `base_url` accordingly in Postman.

## Deliverables

Create/update Postman artifacts in the existing style:

1. Add a new folder/group for `JobPosting Agent API`.
2. Add request YAML files under:
   - `postman/collections/FANG v2 API Test Suite/JobPosting Agent API/`
3. Update `postman/FANG_v2_Collection.postman_collection.json` if the repo expects the JSON collection to stay in sync with YAML request files.
4. Create a report:
   - `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_POSTMAN_API_SMOKE_REPORT.md`

## Required Smoke Cases

Use real IDs from the local DB. Do not hardcode invalid toy IDs unless the DB inspection proves they exist.

Before making requests, use `psql` to select:

- a valid `hrId`
- a valid `jobPostId` owned by that HR's company
- at least one valid `jobAppId` for that `jobPostId`
- one job posting that has enough applications for ranking tests

Minimum psql discovery queries:

```powershell
psql "$env:DATABASE_URL" -c "SELECT hrId, companyId FROM HR ORDER BY hrId LIMIT 10;"
psql "$env:DATABASE_URL" -c "SELECT jp.jobPostId, jp.companyId, hr.hrId FROM JOBPOSTING jp JOIN HR hr ON hr.companyId = jp.companyId ORDER BY jp.jobPostId LIMIT 20;"
psql "$env:DATABASE_URL" -c "SELECT jobPostId, count(*) AS app_count FROM JOBAPPLICATION GROUP BY jobPostId ORDER BY app_count DESC LIMIT 10;"
psql "$env:DATABASE_URL" -c "SELECT ja.jobAppId, ja.jobPostId, ja.candidateId FROM JOBAPPLICATION ja ORDER BY ja.jobAppId LIMIT 20;"
psql "$env:DATABASE_URL" -c "SELECT count(DISTINCT candidateId) AS candidates_with_languages, count(*) AS language_rows FROM CANDIDATELANGUAGE;"
```

Run these API smoke scenarios:

1. **Health/master sanity**
   - `GET /health` or existing health endpoint in Postman.
   - one existing master-data endpoint to verify app and DB are alive.
2. **JobPosting query: top candidates**
   - `POST /v2/agent/job-posting/query`
   - prompt example: `Liệt kê top 10 ứng viên phù hợp nhất cho job này, nêu lý do ngắn gọn.`
   - assert HTTP 200 and response has assistant answer, `conversationId`, and structured `toolCalls`/warnings shape if returned by API.
3. **JobPosting query: language filter**
   - Continue same conversation if API supports it.
   - prompt example: `Trong nhóm ứng viên này, lọc những người có tiếng Anh hạng C trở lên hoặc tương đương advanced trở lên.`
   - assert HTTP 200, no scope errors, and language warnings are acceptable if mapper returns unknowns.
4. **JobPosting query: full CV drill-down**
   - Use a valid `jobAppId` from the previous ranking result if possible.
   - prompt example: `Xem chi tiết CV đã mask PII của ứng viên jobAppId=<ID> và tóm tắt điểm mạnh/yếu.`
   - assert PII masking: response must not expose raw email/phone/address.
5. **Conversation list/messages**
   - `GET /v2/agent/job-posting/conversations?jobPostId=<ID>&hrId=<ID>` or actual route contract.
   - `GET /v2/agent/job-posting/conversations/<conversationId>/messages?hrId=<ID>` or actual route contract.
   - assert the conversation/message history includes the smoke conversation.
6. **Authorization/scope negative smoke**
   - Use a mismatched `hrId`/`jobPostId` if the DB has one.
   - assert 403 or the expected error from route contract.
   - If DB has only one HR/company, document that the negative test was skipped.

## Postman Requirements

Prefer using Postman MCP if available. If MCP is unavailable, use one of:

- Postman app manual instructions with saved request YAML/collection
- Newman CLI if available
- direct HTTP fallback only for diagnosis, not as the primary deliverable

Each new request should include useful tests/assertions where the current Postman format supports them. If the existing YAML format does not support scripts cleanly, document manual expected assertions in the request description and enforce assertions in the final report.

Use `{{base_url}}` rather than hardcoding `http://localhost:8000` inside requests.

Use Postman variables where practical:

- `job_post_id`
- `hr_id`
- `conversation_id`
- `job_app_id`

Do not commit secrets or hardcode database passwords into Postman collection variables. The DB URL may appear only in the operational report/prompt context, not as a collection runtime variable unless the existing repo already does that.

## Verification Commands

Run:

```powershell
.\venv\Scripts\python.exe -m compileall app scripts
.\venv\Scripts\python.exe -m pytest tests/unit -q
```

Then run the Postman smoke suite using the best available method:

- Postman MCP collection/folder run, preferred
- Newman, if installed
- manual Postman run with evidence and screenshots/logs, if neither MCP nor Newman is available

If you use Newman, prefer:

```powershell
newman run postman/FANG_v2_Collection.postman_collection.json --env-var "base_url=http://localhost:8000"
```

If the existing collection is too broad and includes old unrelated smoke requests, run only the new JobPosting Agent folder if Newman/Postman supports folder selection.

## Failure Handling

If an API test fails:

1. Capture HTTP status, request body, response body, and relevant server log excerpt.
2. Determine whether it is:
   - test data issue
   - Postman request/variable issue
   - DB migration/backfill issue
   - backend bug
   - model/provider availability issue
3. Only patch backend code if the bug is clearly in C3 backend and the patch is minimal.
4. Re-run the failed smoke case after a fix.

Do not hide flaky/model-output variation. For model text, assert structure and safety, not exact wording.

## Final Report Must Include

1. Postman artifacts created/updated.
2. Exact DB IDs used: `hrId`, `jobPostId`, `jobAppId`, `conversationId`.
3. Server start command/base URL used.
4. Postman execution method: MCP/Newman/manual.
5. Result per smoke case: pass/fail/skipped.
6. Any API/backend bugs found and whether fixed.
7. Remaining blockers before frontend.
8. Recommendation: whether frontend implementation can start.

## Expected Outcome

The repo should have a reusable Postman smoke suite proving the C3 JobPosting Agent works against real local data after backfill. If all required cases pass, report that frontend work can begin.

# Tier 2 Prompt — FANG Full API Verification With Postman MCP

Bạn là Model Tier 2 phụ trách **thực thi** test API bằng Postman MCP. Không tự thiết kế lại test scope. Chỉ chạy đúng matrix dưới đây, ghi nhận kết quả, phân loại lỗi, và trả báo cáo cho Tier 1 duyệt.

## Context

- Repo backend: `C:\Users\os\Desktop\cur_prj\Fang`
- Server expected: `http://localhost:8000`
- Collection/assets: `C:\Users\os\Desktop\cur_prj\Fang\postman`
- Test matrix source: `postman/FANG_V2_FULL_API_TEST_MATRIX.md`
- Không chạy reset DB, không seed DB. Local DB là fixture ổn định.
- Nếu gặp lỗi quota/API key của LLM provider, phân loại là provider/environment issue khi backend log chứng minh rõ.
- Fixture hồ sơ ưu tiên: username `nguyenhaihung`, `candidate_id=518`, `job_app_id_full_cv=2002`, `job_post_id=13`, có `CVPARSED.parsedJson` và `rawText`; CV thật `sample_2` ở `C:\Users\os\Desktop\cur_prj\Fang\sample_2.pdf`
- Account ứng viên chuẩn nhất để smoke candidate-related flows là `nguyenhaihung`.
- HR account không hard-code: nếu cần HR phù hợp với company/job đang test, tự truy vấn DB để chọn HR cùng `compId`.
- Máy có công cụ `psql`; có thể dùng `psql`, Python, hoặc công cụ DB khác để đọc fixture. Không mutate DB trừ case fixture-only được nêu rõ.

## Preflight, Server Startup, And Logs — Bắt Buộc

Trước khi chạy Postman MCP, phải tự kiểm tra compile/test và tự chạy server để đọc log. Không dùng server mơ hồ không biết log nằm đâu.

### 1. Backend compile/pytest

```powershell
cd C:\Users\os\Desktop\cur_prj\Fang
.\venv\Scripts\python.exe -m py_compile app/main.py app/services/jobposting_tools.py app/services/jobposting_agent_runtime.py app/services/jobposting_agent_query.py app/models/jobposting_agent.py
.\venv\Scripts\python.exe -m pytest tests/unit/unit_test_jobposting_agent_tools.py tests/unit/unit_test_jobposting_agent_runtime.py tests/unit/unit_test_jobposting_agent_persistence.py tests/unit/unit_test_routes_jobposting_agent.py -q
```

### 2. Frontend compile smoke

Postman chủ yếu test API, nhưng vẫn phải đảm bảo frontend code compile được vì đây là full-system gate.

```powershell
cd C:\Users\os\Desktop\cur_prj\miCareer-mini
.\venv\Scripts\python.exe -m py_compile app.py test_playwright.py test_playwright_full.py test_playwright_job_agent.py
```

### 3. Start backend and capture logs

Nếu port 8000 đã có server, verify `GET /healthz` và chỉ reuse nếu đúng FANG local server. Nếu không chắc, dừng server cũ theo cách an toàn rồi chạy lại.

```powershell
cd C:\Users\os\Desktop\cur_prj\Fang
$backendOut = "agent_workflow_doc\tier2\backend_postman_stdout.log"
$backendErr = "agent_workflow_doc\tier2\backend_postman_stderr.log"
$backend = Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList @("-m","uvicorn","app.main:app","--reload","--host","127.0.0.1","--port","8000") -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 6
Invoke-WebRequest http://localhost:8000/healthz -UseBasicParsing
Get-Content $backendErr -Tail 80
```

### 4. Start frontend and capture logs

```powershell
cd C:\Users\os\Desktop\cur_prj\miCareer-mini
$env:FANG_API_URL = "http://localhost:8000/v2"
$frontendOut = "agent_workflow_doc\frontend_postman_stdout.log"
$frontendErr = "agent_workflow_doc\frontend_postman_stderr.log"
$frontend = Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList @("-m","streamlit","run","app.py","--server.address","127.0.0.1","--server.port","8501") -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 8
Invoke-WebRequest http://localhost:8501 -UseBasicParsing
Get-Content $frontendErr -Tail 80
```

### 5. DB fixture query guidance

Use `DATABASE_URL=postgresql://postgres:hungklv123@localhost:5432/micareer_lite_db`.

```powershell
$env:DATABASE_URL = "postgresql://postgres:hungklv123@localhost:5432/micareer_lite_db"
$hrQuery = @'
select hr.userid, hr.compid, company.compname, "user".username, "user".pwd, "user".fname, "user".lname
from hr
join "user" on "user".userid = hr.userid
join company on company.compid = hr.compid;
'@
psql $env:DATABASE_URL -c $hrQuery
```

Nếu `psql` không tiện, dùng Python/asyncpg hoặc API list endpoint, nhưng báo rõ cách chọn fixture trong report.

## Environment Variables

Set hoặc verify các biến Postman trước khi chạy:

- `base_url=http://localhost:8000`
- `hr_id=2`
- `job_post_id=13`
- `job_app_id_full_cv=2002`
- `job_app_id_missing_cv=999999`
- `candidate_id=518`
- `conversation_id=` capture từ Chat happy path
- `agent_conversation_id=` capture từ JobPosting Agent happy path
- `ingestion_job_id=` capture từ Ingestion create job nếu chạy ingestion
- `cv_snap_url=https://res.cloudinary.com/dfwkw1guc/raw/upload/v1778998872/nmaiex/sample_2` chỉ dùng nếu cần chạy ingestion smoke

Nếu fixture id không tồn tại, query/read DB hoặc API list endpoint để tìm id thay thế tương đương, ghi rõ id đã dùng trong báo cáo. Không đổi scope test.

## Required API Cases

Use Postman MCP to run the existing collection/assets under `C:\Users\os\Desktop\cur_prj\Fang\postman`. Do not redesign requests. Do not spend time reading all implementation code; run the API matrix, inspect failures, and use backend logs/DB only for diagnosis.

1. System
   - `GET /healthz`
   - `GET /v2/healthz`
   - `GET /docs`

2. Chat full-CV
   - `POST /v2/chat/query` happy path với `job_app_id_full_cv`; assert `topK=0`, UUID, non-empty response.
   - `POST /v2/chat/query` missing CV với `job_app_id_missing_cv`; expect HTTP 400 and clear `detail`.
   - `POST /v2/chat/query` invalid `modelMode`; expect HTTP 400.
   - `GET /v2/chat/conversations`.
   - `GET /v2/chat/conversations/{conversation_id}/messages`.
   - Create enough turns, then `POST /v2/chat/conversations/{conversation_id}/summarize`; expect `summarizedMessageCount > 0`.
   - After summarize, send follow-up chat and verify behavior is stable; note that backend should keep system summary and exclude summarized user/assistant messages from LLM context.
   - `POST /v2/chat/conversations/{conversation_id}/branch-new`.

3. Ingestion
   - `POST /v2/ingestion/jobs` only if `cv_snap_url` is valid and the chosen JobApplication is safe to re-ingest.
   - `GET /v2/ingestion/jobs/{ingestion_job_id}`.
   - Do not reset DB.

4. NMAIex Master Data
   - `GET /v2/nmaiex/master/provinces`
   - `GET /v2/nmaiex/master/levels`
   - `GET /v2/nmaiex/master/categories`
   - `GET /v2/nmaiex/master/skills`

5. NMAIex Ranking
   - `GET /v2/nmaiex/ranking/candidates/{job_post_id}`
   - `GET /v2/nmaiex/ranking/jobs/{candidate_id}`

6. NMAIex Management
   - `PATCH /v2/nmaiex/management/jobs/{job_id}/structured`
   - `PATCH /v2/nmaiex/management/jobs/{job_id}/content`
   - `PATCH /v2/nmaiex/management/candidates/{candidate_id}/cv`
   - Treat these as fixture-only/manual-safe. Capture original values first and restore if modified. If no disposable fixture is available, mark skipped with reason instead of mutating stable data.

7. JobPosting Agent
   - `POST /v2/agent/job-posting/query` top candidates.
   - `POST /v2/agent/job-posting/query` TOEIC structured language certificate filter: `Những ứng viên nào có chứng chỉ tiếng Anh TOEIC từ 600 trở lên?`
   - `POST /v2/agent/job-posting/query` skill filter: `Ứng viên nào thiếu nhiều kỹ năng bắt buộc nhất?`
   - `POST /v2/agent/job-posting/query` seniority filter: `Ứng viên nào phù hợp level Junior hoặc Middle?`
   - `POST /v2/agent/job-posting/query` work location filter: `Ứng viên nào ở Hà Nội hoặc phù hợp làm remote?`
   - `POST /v2/agent/job-posting/query` salary expectation filter: `Ứng viên nào có kỳ vọng lương nằm trong budget?`
   - `POST /v2/agent/job-posting/query` education filter: `Ứng viên nào có bằng đại học trở lên ngành liên quan?`
   - `POST /v2/agent/job-posting/query` compare top 3: `So sánh 3 ứng viên nổi bật nhất.`
   - `POST /v2/agent/job-posting/query` CV drilldown.
   - `POST /v2/agent/job-posting/query` out-of-scope negative prompt.
   - `POST /v2/agent/job-posting/query` professional certification limitation negative: `Tìm ứng viên có AWS-SAA hoặc chứng chỉ cloud chuyên ngành.`
   - `GET /v2/agent/job-posting/conversations`.
   - `GET /v2/agent/job-posting/conversations/{agent_conversation_id}/messages`.
   - `PATCH /v2/agent/job-posting/conversations/{agent_conversation_id}` rename.
   - `DELETE /v2/agent/job-posting/conversations/{agent_conversation_id}` archive.

## Assertions

For every request, record:

- HTTP status.
- Response schema validity.
- Required IDs: UUID/integer/non-empty fields.
- Expected error shape for negative cases.
- Backend log note if status is 5xx.
- Classification: PASS, FAIL, SKIP, PROVIDER/ENV.

For JobPosting Agent API requests, additionally record:

- `toolCalls[].toolName`, `args`, `status`, `resultSummary`.
- Whether `toolCalls[].resultPreview` exists and has useful structured data.
- Expected tool vs actual tool:
  - Ranking/top/compare -> `get_job_candidate_ranking`
  - TOEIC -> `find_candidates_by_language_certificate`
  - Skill -> `filter_candidates_by_skills`
  - Seniority -> `filter_candidates_by_seniority`
  - Location -> `filter_candidates_by_work_location`
  - Salary -> `filter_candidates_by_salary_expectation`
  - Education -> `filter_candidates_by_education_level`
- Whether assistant response is grounded and does not hallucinate candidate facts.

## Final Report Format

Return one Markdown report with:

- Environment used: base URL, fixture IDs, server start time if available.
- Pass/fail summary table.
- Per-case table: request name, status, assertion result, notes, captured IDs.
- Bugs requiring Tier 1 action.
- JobPosting Agent tool routing table: prompt, expected tool, actual tool, resultPreview evidence.
- System prompt learning notes: where Agent routed wrong, lacked evidence, or needs stronger few-shot guidance.
- Provider/environment issues separated from backend bugs.
- Any skipped mutation tests and exact reason.

Do not propose a new test design. Execute this plan and report evidence.

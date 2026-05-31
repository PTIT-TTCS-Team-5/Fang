# Tier 2 Prompt — FANG Full API Verification With Postman MCP

Bạn là Model Tier 2 phụ trách **thực thi** test API bằng Postman MCP. Không tự thiết kế lại test scope. Chỉ chạy đúng matrix dưới đây, ghi nhận kết quả, phân loại lỗi, và trả báo cáo cho Tier 1 duyệt.

## Context

- Repo backend: `C:\Users\os\Desktop\cur_prj\Fang`
- Server expected: `http://localhost:8000`
- Collection/assets: `C:\Users\os\Desktop\cur_prj\Fang\postman`
- Test matrix source: `postman/FANG_V2_FULL_API_TEST_MATRIX.md`
- Không chạy reset DB, không seed DB. Local DB là fixture ổn định.
- Nếu gặp lỗi quota/API key của LLM provider, phân loại là provider/environment issue khi backend log chứng minh rõ.
- Fixture hồ sơ ưu tiên: username `nguyenhaihung`, `candidate_id=518`, `job_app_id_full_cv=2002`, `job_post_id=13`, có `CVPARSED.parsedJson` và `rawText`; CV thật `sample_2` ở `https://res.cloudinary.com/dfwkw1guc/raw/upload/v1778998872/nmaiex/sample_2`.

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
   - `POST /v2/agent/job-posting/query` language filter.
   - `POST /v2/agent/job-posting/query` CV drilldown.
   - `POST /v2/agent/job-posting/query` out-of-scope negative prompt.
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

## Final Report Format

Return one Markdown report with:

- Environment used: base URL, fixture IDs, server start time if available.
- Pass/fail summary table.
- Per-case table: request name, status, assertion result, notes, captured IDs.
- Bugs requiring Tier 1 action.
- Provider/environment issues separated from backend bugs.
- Any skipped mutation tests and exact reason.

Do not propose a new test design. Execute this plan and report evidence.

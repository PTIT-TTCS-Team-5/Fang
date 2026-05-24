# FANG Next Phase - Tier 2 Full System Test Assignment

## Brief

Task này giao cho model tier 2 hoặc agent trong Antigravity kiểm thử sâu FANG sau P0-A cleanup và commit `b8d0544`. Mục tiêu là xác nhận hệ thống chạy thật với DB/Postman/API, đặc biệt là thay đổi NMAIex candidate enrichment sidecar, ProTierGate self-report, score clipping và compatibility với dataset 500 CV cũ.

Agent được phép dùng terminal, `psql`, Postman MCP, browser/devtools MCP và đọc repo. Không tự sửa code trừ khi user giao task fix riêng.

## Context Bắt Buộc Đọc

1. `README.md`
2. `agent_workflow_doc/FANG_NEXT_PHASE_DECISIONS.md`
3. `agent_workflow_doc/FANG_NEXT_PHASE_P0A_USER_NOTE_TRIAGE.md`
4. `agent_workflow_doc/FANG_NEXT_PHASE_P0A_REPO_REALITY_AUDIT_REPORT.md`
5. `database/schema_ai_core.sql`
6. `database/schema_web_core.sql`
7. `app/api/routes_ingestion.py`
8. `app/services/nmaiex_candidate_enrichment.py`
9. `app/services/cv_parser.py`
10. `app/services/cv_parser_adapters.py`
11. `app/services/nmaiex_ranking_service.py`
12. `.postman/resources.yaml`
13. `postman/collections/FANG v2 API Test Suite/`

## Environment Notes

- Branch hiện tại: `chore/p0-abc-repo-ai-docs-audit`
- Commit cần test: `b8d0544 feat: tách enrichment NMAIex khỏi ingestion chính`
- Postman collection cloud mapping: `.postman/resources.yaml`
- Local Postman collection path: `postman/collections/FANG v2 API Test Suite`
- Dataset backup nếu cần restore: `synthetic_data/backup/FULL_DATA_SET_500CV_20JOB_3PM50_21_05_test_ngon.backup`
- Không restore DB nếu user chưa xác nhận. Trước mọi thao tác destructive phải báo rõ.
- psql url = DATABASE_URL=postgresql://postgres:hungklv123@localhost:5432/micareer_lite_db
- Tự chạy (venv) "python -m uvicorn app.main:app --reload": Backend (đọc cả log xem có gì bất thường)
- Tự chạy (venv của miCareer-mini) "python -m streamlit run app.py": front-end


## Test Scope

### 1. Static/Unit Verification

Chạy:

```powershell
venv\Scripts\python -m unittest discover -s tests/unit -p "unit_test_*.py"
venv\Scripts\python -m compileall app scripts tests\unit
```

Kỳ vọng:
- Unit suite pass.
- Không có import/compile error.
- Nếu fail, báo file/test/error, không tự sửa.

### 2. DB Schema Verification bằng psql

Kiểm tra:
- Bảng `NMAIEX_CANDIDATE_ENRICHMENT_JOB` tồn tại.
- `jobAppId` unique.
- Có FK tới `AIINDEXJOB`, `JOBAPPLICATION`, `CANDIDATE`, `CVPARSED`.
- `CVPARSED.parsedJson` cũ không cần có `parserSelfReport`.
- Đếm số `CVPARSED`, `AIINDEXJOB`, `NMAIEX_CANDIDATE_ENRICHMENT_JOB`.

Gợi ý query:

```sql
SELECT COUNT(*) FROM CVPARSED;
SELECT COUNT(*) FROM AIINDEXJOB;
SELECT COUNT(*) FROM NMAIEX_CANDIDATE_ENRICHMENT_JOB;
SELECT stat, COUNT(*) FROM NMAIEX_CANDIDATE_ENRICHMENT_JOB GROUP BY stat ORDER BY stat;
SELECT cvParsedId, jobAppId, parsedJson ? 'parserSelfReport' AS has_self_report FROM CVPARSED LIMIT 10;
```

### 3. Enrichment Backfill/Retry Verification

Chạy limited batch:

```powershell
venv\Scripts\python scripts\retry_nmaiex_candidate_enrichment.py --enqueue-missing --limit 10
venv\Scripts\python scripts\retry_nmaiex_candidate_enrichment.py --limit 10
```

Kỳ vọng:
- Script không crash.
- Tạo sidecar job cho parsed CV cũ nếu thiếu.
- Job `SUCCESS` cập nhật được `CANDIDATE.expyears`, `CANDIDATESKILL`, `CANDIDATE_SKILL_RAW`.
- Job `FAILED` có `retryCount`, `nextRunAt`, `errorMsg`; không ảnh hưởng `AIINDEXJOB.SUCCESS`.

### 4. API/Postman Smoke Test

Dùng Postman MCP collection `FANG v2 API Test Suite`:

- Smoke Tests / Test Health Check
- Ingestion API / POST `/v2/ingestion/jobs`
- Ingestion API / GET `/v2/ingestion/jobs/{indexJobId}`
- Chat API / POST `/v2/chat/query`
- NMAIex Master Data APIs
- NMAIex Ranking API / J to C
- NMAIex Ranking API / C to J
- NMAIex Management API: PATCH job content, PATCH job structured, PATCH candidate CV nếu test data an toàn.

Kỳ vọng:
- API không trả 500 ngoài lỗi cấu hình/API key thật.
- Ranking response có `score_breakdown`.
- `match_score` không bị clip mặc định khi raw score ngoài `[0,1]` nếu có case phù hợp.
- Chat vẫn hoạt động với jobApp đã ingestion thành công dù enrichment sidecar có thể fail.

### 5. Browser/DevTools Check nếu Có UI

Nếu có UI đang trỏ vào FANG:
- Mở các màn hình chat/ranking liên quan.
- Kiểm tra network request tương ứng Postman.
- Kiểm tra lỗi console.
- Không đánh giá UI nếu repo này chỉ chạy backend.

## Edge Cases Cần Cố Ý Kiểm Tra

- Parsed CV legacy thiếu `parserSelfReport`.
- Enrichment mapper fail nhưng ingestion chính vẫn SUCCESS.
- Enrichment job retry đã hết `maxRetryCount`.
- `skills=[]` hoặc thiếu skill trong parsed JSON.
- Experience date lỗi hoặc thiếu `startDate`.
- Score clipping default false và bật true bằng patch/mock/unit nếu không tiện đổi env.
- `GET /v2/nmaiex/master/languages` không được gọi như endpoint production vì hiện là planned/gap.

## Output Report

Tạo báo cáo ngắn bằng tiếng Việt, không sửa code:

1. Summary: pass/fail tổng quan.
2. Commands/API đã chạy.
3. DB counts trước/sau nếu có backfill.
4. Findings có severity: Critical/High/Medium/Low.
5. Evidence: path, SQL result, request name, response status.
6. Rủi ro còn lại trước P0-B/P0-C.
7. Khuyến nghị có nên tiếp tục P0-B, P0-C, hoặc cần fix trước.

## Ràng Buộc

- Không tự reset/restore DB nếu user chưa xác nhận.
- Không commit.
- Không sửa docs/code.
- Không dùng docs/research cũ làm runtime truth.
- Nếu API key/provider fail, phân loại rõ là environment issue hay code issue.

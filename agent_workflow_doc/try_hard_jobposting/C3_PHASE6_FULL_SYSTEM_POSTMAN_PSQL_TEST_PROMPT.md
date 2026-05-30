# C3 Phase 6 Prompt — Full System Test with Postman MCP + psql

You are working in the FANG repository at:

`C:\Users\os\Desktop\cur_prj\Fang`

Your task is to run a **full system verification pass** after recent backend and database changes around JobPosting Agent C3, language normalization, and language certificate backfill.

This is a QA/system-test task. Do not implement new features. Do not refactor source code. Do not patch source code. If you find a clear, reproducible blocker, stop the affected test path, capture evidence, and report it back for the user/owner to decide.

## Preferred Model and Tooling

Use Gemini Flash 3.5 with Postman MCP if available. Claude Sonnet is also acceptable if it has Postman MCP access.

Primary test tools:

1. **Postman MCP** for API smoke/e2e execution.
2. **psql** for database verification.
3. Existing Python tests only as supporting evidence.

## Database

Use this exact local DB:

```powershell
$env:DATABASE_URL="postgresql://postgres:hungklv123@localhost:5432/micareer_lite_db"
```

Use local FANG API:

```text
http://localhost:8000/v2
```

If server is not running, start it:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

If port 8000 is occupied, verify it is actually FANG. If not, use another port and update Postman `base_url`.

## Context to Read First

Read these files before testing:

1. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_OFFICIAL_IMPLEMENTATION_PLAN.md`
2. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_POSTMAN_API_SMOKE_REPORT.md`
3. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_LANGUAGE_CERTIFICATE_BACKFILL_REPORT.md`
4. `app/models/jobposting_agent.py`
5. `app/api/routes_jobposting_agent.py`
6. `app/services/jobposting_agent_persistence.py`
7. `app/services/nmaiex_candidate_enrichment.py`
8. `app/services/jobposting_tools.py`
9. `database/schema_web_core.sql`
10. `database/root_data.sql`
11. `postman/POSTMAN_SETUP_GUIDE.md`
12. `postman/FANG_v2_Collection.postman_collection.json`
13. `postman/collections/FANG v2 API Test Suite/JobPosting Agent API/`

## Known Recent Changes to Verify

The system changed in these areas:

1. `CANDIDATELANGUAGE` backfill no longer loops over all duplicated `CVPARSED` rows for synthetic data.
2. New schema:
   - `LANGUAGECERTIFICATE`
   - `CANDIDATELANGUAGECERTIFICATE`
3. `CANDIDATELANGUAGE.certification` remains for backward compatibility.
4. Enrichment now extracts language certificates such as:
   - IELTS
   - TOEIC
   - JLPT
   - HSK
5. `sample_2.pdf` parse/enrich smoke passed once with rollback, extracting:
   - `Tiếng Anh` / `IELTS 8.0 | TOEIC 895`
   - `Tiếng Trung` / `HSK 6`
6. Synthetic full backfill expected DB state:
   - 500 synthetic candidates
   - 462 synthetic candidates with language rows
   - 38 synthetic candidates without language rows because cached CV has `languages=[]`
   - 479 `CANDIDATELANGUAGE` rows
   - 126 `CANDIDATELANGUAGECERTIFICATE` links
   - certificate distribution approximately `IELTS=95`, `TOEIC=24`, `JLPT=7`
7. JobPosting Agent API previously passed 6/6 smoke tests.

## Required psql Verification

Run these checks and record outputs in the report.

```powershell
$env:DATABASE_URL="postgresql://postgres:hungklv123@localhost:5432/micareer_lite_db"
```

### DB Identity and Schema

```powershell
psql "$env:DATABASE_URL" -c "SELECT current_database(), now();"
psql "$env:DATABASE_URL" -c "\dt *language*"
psql "$env:DATABASE_URL" -c "\d CANDIDATELANGUAGE"
psql "$env:DATABASE_URL" -c "\d LANGUAGECERTIFICATE"
psql "$env:DATABASE_URL" -c "\d CANDIDATELANGUAGECERTIFICATE"
```

### Language and Certificate Counts

```powershell
psql "$env:DATABASE_URL" -c "SELECT count(*) AS candidate_count FROM CANDIDATE;"
psql "$env:DATABASE_URL" -c "SELECT count(*) AS cvparsed_count FROM CVPARSED;"
psql "$env:DATABASE_URL" -c "SELECT count(*) AS synthetic_candidates FROM CANDIDATE WHERE cvUrl LIKE 'synth://pipeline/%';"
psql "$env:DATABASE_URL" -c "SELECT count(DISTINCT c.userId) AS synthetic_with_language FROM CANDIDATE c JOIN CANDIDATELANGUAGE cl ON cl.userId = c.userId WHERE c.cvUrl LIKE 'synth://pipeline/%';"
psql "$env:DATABASE_URL" -c "SELECT count(*) AS synthetic_without_language FROM CANDIDATE c LEFT JOIN CANDIDATELANGUAGE cl ON cl.userId = c.userId WHERE c.cvUrl LIKE 'synth://pipeline/%' AND cl.userId IS NULL;"
psql "$env:DATABASE_URL" -c "SELECT count(DISTINCT userId) AS candidates_with_languages, count(*) AS language_rows FROM CANDIDATELANGUAGE;"
psql "$env:DATABASE_URL" -c "SELECT count(*) AS cert_links FROM CANDIDATELANGUAGECERTIFICATE;"
psql "$env:DATABASE_URL" -c "SELECT lc.certCode, count(*) AS n FROM CANDIDATELANGUAGECERTIFICATE clc JOIN LANGUAGECERTIFICATE lc ON lc.certId = clc.certId GROUP BY lc.certCode ORDER BY n DESC, lc.certCode;"
```

### Integrity Checks

```powershell
psql "$env:DATABASE_URL" -c "SELECT count(*) AS language_rows_without_langid FROM CANDIDATELANGUAGE WHERE langId IS NULL;"
psql "$env:DATABASE_URL" -c "SELECT count(*) AS cert_links_without_language FROM CANDIDATELANGUAGECERTIFICATE clc LEFT JOIN CANDIDATELANGUAGE cl ON cl.candidateLangId = clc.candidateLangId WHERE cl.candidateLangId IS NULL;"
psql "$env:DATABASE_URL" -c "SELECT count(*) AS cert_links_without_catalog FROM CANDIDATELANGUAGECERTIFICATE clc LEFT JOIN LANGUAGECERTIFICATE lc ON lc.certId = clc.certId WHERE lc.certId IS NULL;"
psql "$env:DATABASE_URL" -c "SELECT count(*) AS duplicate_language_rows FROM (SELECT userId, langId, lower(rawName) AS rawName, count(*) FROM CANDIDATELANGUAGE GROUP BY userId, langId, lower(rawName) HAVING count(*) > 1) d;"
psql "$env:DATABASE_URL" -c "SELECT count(*) AS duplicate_cert_links FROM (SELECT candidateLangId, certId, COALESCE(rawText, '') AS rawText, count(*) FROM CANDIDATELANGUAGECERTIFICATE GROUP BY candidateLangId, certId, COALESCE(rawText, '') HAVING count(*) > 1) d;"
```

### Representative Rows

```powershell
psql "$env:DATABASE_URL" -c "SELECT cl.userId, l.langCode, cl.rawName, cl.proficiency, cl.rawProficiency, cl.certification, lc.certCode, clc.rawText, clc.normalizedScore FROM CANDIDATELANGUAGE cl LEFT JOIN LANGUAGE l ON l.langId = cl.langId LEFT JOIN CANDIDATELANGUAGECERTIFICATE clc ON clc.candidateLangId = cl.candidateLangId LEFT JOIN LANGUAGECERTIFICATE lc ON lc.certId = clc.certId WHERE clc.candidateLanguageCertId IS NOT NULL ORDER BY cl.userId LIMIT 20;"
```

## Required Python Verification

Run:

```powershell
.\venv\Scripts\python.exe -m compileall app scripts
.\venv\Scripts\python.exe -m pytest tests/unit -q
.\venv\Scripts\python.exe -m ruff check app scripts tests
```

If full `ruff check app scripts tests` fails due unrelated legacy files, narrow to touched C3 files and report the reason.

## Required API/Postman Tests

Use Postman MCP as the primary runner. If Postman MCP is unavailable, use Newman if installed. If neither is available, use the saved Postman requests plus direct HTTP only as a fallback and clearly mark the method.

### Existing Collection

Use:

- `postman/FANG_v2_Collection.postman_collection.json`
- New folder: `JobPosting Agent API`
- Existing folders:
  - Smoke Tests
  - NMAIex Master Data API
  - NMAIex Ranking API
  - Chat API
  - Ingestion API if safe

Do not run destructive or expensive ingestion/parser flows by default unless explicitly stated below. If an ingestion/parser smoke is needed, it must use only `sample_2.pdf`.

### Mandatory API Cases

Run these against real local data:

1. **Health**
   - `GET /v2/healthz`
   - expect 200

2. **Master Data**
   - `GET /v2/nmaiex/master/provinces`
   - `GET /v2/nmaiex/master/skills`
   - expect 200 and non-empty results

3. **NMAIex Ranking**
   - `GET /v2/nmaiex/ranking/candidates/1?limit=10`
   - expect 200 and candidates with job/candidate scores

4. **JobPosting Agent: Top Candidates**
   - `POST /v2/agent/job-posting/query`
   - body:
     ```json
     {
       "jobPostId": 1,
       "hrId": 2,
       "prompt": "Liệt kê top 10 ứng viên phù hợp nhất cho job này, nêu lý do ngắn gọn.",
       "conversationId": null
     }
     ```
   - expect 200, `conversationId`, non-empty `response`, `toolCalls[]`

5. **JobPosting Agent: Language + Certificate Query**
   - Continue same conversation if possible.
   - prompt:
     ```text
     Trong nhóm ứng viên này, lọc người có tiếng Anh Advanced trở lên và ưu tiên ai có IELTS hoặc TOEIC. Nêu rõ jobAppId và chứng chỉ nếu có.
     ```
   - expect 200.
   - The answer does not need exact wording, but should not crash and should use language/certificate-backed data where available.

6. **JobPosting Agent: Full CV Drill-down**
   - Use a valid `jobAppId` returned from ranking or known valid `jobAppId=2`.
   - prompt:
     ```text
     Xem chi tiết CV đã mask PII của ứng viên jobAppId=2 và tóm tắt điểm mạnh/yếu.
     ```
   - expect 200.
   - verify no raw email/phone/address leak in response.

7. **Conversation List + Messages**
   - `GET /v2/agent/job-posting/conversations?jobPostId=1&hrId=2`
   - `GET /v2/agent/job-posting/conversations/<conversationId>/messages?includeToolMessages=true&includeSystem=false`
   - expect smoke conversation and tool messages.

8. **Scope Negative**
   - `POST /v2/agent/job-posting/query` with mismatched `hrId=3`, `jobPostId=1`.
   - expect 403.

9. **Old Single-Application Chat Regression**
   - Existing `POST /v2/chat/query` smoke request if local data supports it.
   - This is to confirm JobPosting Agent changes did not break old `jobAppId` chat.
   - If blocked by model quota or old data state, mark as blocked with exact error.

10. **Certificate DB/API Cross-Check**
   - psql should show certificate links.
   - JobPosting Agent language/certificate prompt should complete without tool/runtime error.
   - If the model does not explicitly mention certificates, do not fail automatically; inspect whether the tool output exposes `certification` fields and document the gap if UI/API needs better surfacing.

## Optional Parser/Enrichment/Ingestion Smoke

Run this only once if API quota is available and the user has not forbidden it. Use **only** `sample_2.pdf`; do not use any other CV file, URL, synthetic batch, or broad ingestion path.

```powershell
$env:DATABASE_URL="postgresql://postgres:hungklv123@localhost:5432/micareer_lite_db"
.\venv\Scripts\python.exe scripts\smoke_parse_enrich_sample_cv.py --pdf sample_2.pdf
```

Expected:

- rollback mode by default
- parser succeeds
- enrichment produces language rows and certificate links for IELTS/TOEIC/HSK in the probe output

If API quota is tight, skip and cite the prior report.

If you decide to test the public ingestion API instead of the rollback smoke script, you must still use only `sample_2.pdf` and must document exactly what local/Cloudinary URL or upload mechanism was used. Do not ingest multiple files.

## Error Handling

If any API test fails:

1. Capture:
   - request URL
   - request body
   - HTTP status
   - response body
   - relevant server log excerpt if available
2. Classify:
   - DB/schema issue
   - source regression
   - Postman variable issue
   - model/provider quota issue
   - old test data issue
3. Do not hide flaky LLM wording. Assert structure, safety, and non-crash behavior rather than exact prose.
4. Do not patch code. Report the root cause, evidence, and recommended owner action.

## Deliverables

Create the final report:

`agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_FULL_SYSTEM_TEST_REPORT.md`

Report must include:

1. Executive verdict:
   - `PASS`
   - `PASS_WITH_WARNINGS`
   - `FAIL`
2. Environment:
   - DB URL without password redaction is acceptable in this local report, but do not print API keys.
   - API base URL
   - server start command
   - Postman execution method
3. Git/worktree status before and after.
4. psql verification outputs summarized.
5. Python verification outputs.
6. API/Postman test matrix:
   - case
   - endpoint
   - status
   - pass/fail/skipped
   - notes
7. Any backend bugs found.
8. Any recommended source changes, if any. Do not make those changes yourself.
9. Whether frontend implementation can continue.
10. Remaining risks.

## Constraints

- Do not commit.
- Do not edit `.env`.
- Do not commit or print API keys.
- Do not reset DB.
- Do not run destructive SQL.
- Do not run full backfill under any circumstance. If verification suggests backfill drift or missing rows, report the evidence and stop.
- Do not run `scripts/backfill_c3_candidate_language_province.py` or `scripts/backfill_c3_language_certificates_from_synthetic_batches.py`.
- Do not run ingestion/parser tests on any file except `sample_2.pdf`.
- Do not modify `.understand-anything` generated files.
- Keep this task focused on system verification.

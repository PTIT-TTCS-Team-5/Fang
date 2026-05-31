# Hướng Dẫn JobApplication Full-CV Chat (v2)

Tài liệu này hướng dẫn dev/ops cách luồng `/v2/chat/query` cho 1 `JobApplication` hoạt động sau khi chuyển từ fixed top-k chunk RAG sang full CV markdown context.

Strategy doc liên quan: `../strategy/job_application_full_cv_chat_strategy.md`.

## 1. Request flow

```
HR client → POST /v2/chat/query
              ↓
   process_chat_query() ở app/services/rag_query.py
              ↓
   1. _fetch_cv_context(jobAppId)             ← source of truth, thay embed+vector search
        ↳ CVPARSED.parsedJson → ParsedCV → convert_json_to_markdown
        ↳ fallback rawText nếu validate fail
        ↳ raise CvContextMissingError nếu cả hai rỗng
   2. Load hoặc create AICHATCONVERSATION
   3. Persist user message
   4. _fetch_job_application_context(jobAppId)
        ↳ _fetch_job_posting (extended: salary, workMode, levels, categories, skills)
        ↳ _fetch_candidate_profile (extended: skills)
        ↳ _fetch_ats_history (interview feedback)
        ↳ _fetch_offers (N=3 versions gần nhất)
        ↳ _fetch_email_log (N=5 emails, body trunc 300 chars)
   5. _build_full_cv_system_prompt(cv_context, app_ctx)
        ↳ 8 guardrails + untrusted markers cho mỗi block
   6. _check_full_context_budget(system, filtered history, prompt, model_mode)
        ↳ tính token toàn payload
        ↳ giữ system summary, bỏ user/assistant turns đã summarized
        ↳ trả BudgetResult với action: proceed | warn_proceed | block
   7. Nếu action == "block": deterministic response, KHÔNG gọi LLM
      Ngược lại: invoke_generation(budget_result.messages, model_mode)
   8. Persist assistant message + AIQUERYLOG (topK = 0)
   9. Trả ChatQueryResponse
```

## 2. Data Source — bảng nào, query gì

### CVPARSED (full CV markdown)

```sql
SELECT parsedJson, rawText, parserVer
FROM CVPARSED
WHERE jobAppId = $1;
```

Logic fallback ở `_fetch_cv_context`:

1. `parsedJson` dict valid → merge `rawText` vào nếu thiếu key → `ParsedCV.model_validate` → `convert_json_to_markdown`.
2. Lỗi validate → `rawText` (log warning).
3. Cả hai rỗng → `CvContextMissingError` → HTTP 400.

### JobPosting (extended)

Một query với `array_agg` subqueries (tránh cardinality explosion từ multi-join):

```sql
SELECT
  jp.title, jp.description, jp.minSalary, jp.maxSalary,
  jp.workMode, jp.workLoc, p.provName AS provinceName,
  COALESCE((SELECT array_agg(l.levelName)
            FROM JOB_LEVEL_MAP m JOIN JOBLEVEL l ON l.levelId = m.levelId
            WHERE m.jobPostId = jp.jobPostId), ARRAY[]::varchar[]) AS levels,
  COALESCE((SELECT array_agg(c.catName)
            FROM JOB_CATEGORY_MAP m JOIN JOBCATEGORY c ON c.catId = m.catId
            WHERE m.jobPostId = jp.jobPostId), ARRAY[]::varchar[]) AS categories,
  COALESCE((SELECT array_agg(s.skillName)
            FROM JOBREQUIREMENT r JOIN SKILL s ON s.skillId = r.skillId
            WHERE r.jobPostId = jp.jobPostId), ARRAY[]::varchar[]) AS requiredSkills
FROM JOBPOSTING jp
INNER JOIN JOBAPPLICATION ja ON ja.jobPostId = jp.jobPostId
LEFT JOIN PROVINCE p ON p.provId = jp.provId
WHERE ja.jobAppId = $1;
```

### Candidate profile (extended)

```sql
SELECT
  u.fName || ' ' || u.lName AS fullname, u.email, u.phone,
  c.bio, c.expyears, p.provName AS location,
  COALESCE((SELECT array_agg(s.skillName)
            FROM CANDIDATESKILL cs JOIN SKILL s ON s.skillId = cs.skillId
            WHERE cs.userId = c.userId), ARRAY[]::varchar[]) AS skills
FROM CANDIDATE c
INNER JOIN "user" u ON c.userId = u.userId
LEFT JOIN PROVINCE p ON u.provId = p.provId
INNER JOIN JOBAPPLICATION ja ON ja.candidateId = c.userId
WHERE ja.jobAppId = $1;
```

### Interview feedback, Offer, EmailLog

Xem `_fetch_ats_history`, `_fetch_offers`, `_fetch_email_log` trong `app/services/rag_query.py`.

EMAILLOG đặc biệt: cột tên `"content"` (lowercase quote trong DDL), `LEFT(el."content", $3)` để truncate; JOIN `EMAILTEMPLATE.subj` để có subject.

## 3. Response behavior

### Normal (action == "proceed")

```json
{
  "conversationId": "uuid",
  "messageId": 123,
  "response": "Ứng viên có 3 năm Spring Boot...",
  "model": "google:gemini-flash-001",
  "modelMode": "auto-lite",
  "fallbackPath": "tier1:google:gemini-flash-001(succeeded)",
  "latencyMs": 1234,
  "topK": 0,
  "contextWarning": null
}
```

### Warn proceed (80% <= used < 95%)

LLM vẫn được gọi. Response giống normal nhưng có `contextWarning`:

```json
"contextWarning": {
  "type": "budget_near_limit",
  "usedPercent": 86,
  "options": ["summarize_and_continue", "new_conversation_with_summary"]
}
```

### Blocked (used >= 95%)

LLM **KHÔNG** được gọi. Response deterministic:

```json
{
  "response": "Câu hỏi không thể xử lý vì context đã vượt ngưỡng cho phép (96% của budget 180,000 tokens).\n\nVui lòng chọn một trong các hành động sau:\n- Bấm **Tóm tắt & tiếp tục** để FANG nén lịch sử hội thoại.\n- Bấm **Sang hội thoại mới** để bắt đầu hội thoại mới với bản tóm tắt.\n- Hoặc rút gọn câu hỏi và gửi lại.",
  "model": null,
  "fallbackPath": "blocked:budget_hard_limit",
  "latencyMs": 0,
  "topK": 0,
  "contextWarning": {
    "type": "budget_over_hard_limit",
    "usedPercent": 96,
    "options": ["summarize_and_continue", "new_conversation_with_summary"]
  }
}
```

Vẫn persist `AICHATMESSAGE` + `AIQUERYLOG` để giữ chat history nhất quán.

### Lỗi không có CV (HTTP 400)

`CvContextMissingError` → route handler trả 400:

```json
{ "detail": "Không có CV content dùng được cho jobAppId=42: parsedJson=missing, rawText=missing." }
```

Hoặc: `Không tìm thấy CVPARSED cho jobAppId=42.`

## 4. Cấu hình (env / settings)

| Setting | Default | Mô tả |
|---|---|---|
| `context_budget_lite` | 180,000 | Token budget cho group Lite (Flash/Mini/Haiku/auto-lite) |
| `context_budget_pro` | 960,000 | Token budget cho group Pro (Pro/Full/auto-pro) |
| `context_budget_warning_threshold` | 0.80 | Ngưỡng cảnh báo (warn_proceed) |
| `context_budget_hard_limit` | 0.95 | Ngưỡng chặn (block) — **Phase 1.3 new** |
| `chat_offer_history_limit` | 3 | Số version Offer đưa vào context — **Phase 2 new** |
| `chat_email_history_limit` | 5 | Số EmailLog đưa vào context — **Phase 2 new** |
| `chat_email_body_char_limit` | 300 | Cắt body email theo chars — **Phase 2 new** |
| `rag_top_k_chunks` | 3 | **KHÔNG còn dùng** trong luồng full-CV |

Override qua `.env` theo prefix `CONTEXT_*`, `CHAT_*`.

## 5. Troubleshooting

### "Không tìm thấy CVPARSED cho jobAppId=X" (HTTP 400)

`/v2/chat/query` chỉ cần `CVPARSED` usable; không hard-gate `AIINDEXJOB.SUCCESS`.
Nếu lỗi này xuất hiện, chưa có parsed CV cho application đó hoặc cả `parsedJson`
và `rawText` đều không dùng được. Kiểm tra:

```sql
SELECT cvParsedId, length(rawText), parsedJson IS NOT NULL AS has_json, parserVer
FROM CVPARSED
WHERE jobAppId = X;
```

### Fallback rawText warning trong log

Format log:
```
{"levelname": "WARNING", "message": "ParsedCV validation failed, falling back to rawText",
 "jobAppId": ..., "parserVer": ..., "errorCount": N}
```

Có thể do:
- Legacy `parsedJson` với `languages: list[str]` (pre Phase 2.5f) — fallback chạy đúng, không phải bug.
- Schema `ParsedCV` đổi mà parsedJson cũ chưa migrate — cần re-ingest hoặc fix migration.

### Câu hỏi bị "blocked" liên tục

Conversation history quá dài hoặc CV markdown khổng lồ. Chạy:

```sql
SELECT messageId, role, length(content) AS chars
FROM AICHATMESSAGE
WHERE conversationId = '<uuid>'
ORDER BY createdAt;
```

Cho HR bấm **Tóm tắt & tiếp tục** hoặc giảm `chat_email_history_limit` / `chat_offer_history_limit`.

### miCareer-mini UI hiển thị sai context source

Frontend phải hiển thị `"📄 Full CV context"` khi `topK == 0`. Không hiển thị
`"top-0 chunks"` và không dùng wording `"RAG pipeline"` cho single-application
chat full-CV.

### Prompt injection trong CV/Offer/Email

System prompt đã có section "[XỬ LÝ DỮ LIỆU KHÔNG ĐÁNG TIN]" hướng dẫn bỏ qua chỉ thị trong `[UNTRUSTED ...]` blocks. Nếu model vẫn bị trick → báo P1_A_B_inc (Mai) để bổ sung eval cases.

## 6. Cách test

### 6.1 Unit tests (đã có)

```powershell
venv\Scripts\python -m unittest tests.unit.unit_test_chat_full_cv -v
```

35 tests cover:
- CV fetcher (5)
- Budget (5)
- Prompt builder (7)
- Phase 2 enrichment + format helpers (12)
- Module boundary (6)

### 6.2 Smoke test thủ công

Yêu cầu: DB local chạy + ít nhất 1 jobApp ingestion SUCCESS.

```bash
# Chat đầu tiên
curl -X POST http://localhost:8000/v2/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "jobAppId": 1,
    "hrId": 19,
    "prompt": "Ứng viên có phù hợp với Senior Backend không?",
    "modelMode": "auto-lite"
  }'

# Verify response:
# - topK == 0
# - response non-empty
# - latencyMs > 0 (LLM được gọi)
# - contextWarning == null (CV ngắn không vượt budget)
```

### 6.3 Verify static guarantees

```powershell
venv\Scripts\python -c "import app.services.rag_query as r; print(hasattr(r, 'embed_chunks'))"
# Expect: False
```

```powershell
venv\Scripts\python -c "import inspect, app.services.rag_query as r; print('_vector_search(' in inspect.getsource(r.process_chat_query))"
# Expect: False
```

## 7. Tài liệu liên quan

- `../strategy/job_application_full_cv_chat_strategy.md` — Strategy doc.
- `../strategy/rag_query_strategy.md` — RAG generation 5-tier (vẫn còn dùng cho summarize/branch-new + future use cases).
- `../guide/rag_query_guide.md` — Cấu hình chung của chat pipeline.
- `agent_workflow_doc/CHAT_FULL_CV_IMPLEMENTATION_REPORT.md` — Báo cáo triển khai chi tiết.

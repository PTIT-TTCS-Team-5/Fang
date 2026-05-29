# CHAT_FULL_CV Implementation Report

Ngày: 2026-05-29
Owner: CHAT_FULL_CV
Trạng thái: Phase 1 + Phase 2 + Phase 3 (docs) done. Smoke E2E + handoff Mai còn lại.

## 1. Brief

Triển khai cụm việc `CHAT_FULL_CV` theo `agent_workflow_doc/assign_to_team/FANG_NEXT_PHASE_CHAT_FULL_CV_ASSIGNMENT.md` và Decision Analysis (Option C — Full-CV Bounded Implementation).

Mục tiêu: Chuyển luồng `/v2/chat/query` cho 1 `JobApplication` từ fixed top-k chunk RAG sang full CV markdown context, mở rộng multi-source context (Offer + EmailLog), siết prompt policy, tính budget cho toàn payload với hard limit block.

## 2. Việc đã làm theo Phase

### Phase 0 — Reality Audit
- Đọc `ParsedCV`, `EMAILLOG`, `OFFER`, `JOBPOSTING`, `AIQUERYLOG`/`AICHATMESSAGE` schema, `miCareer-mini` consumer.
- Lưu findings tại `agent_workflow_doc/CHAT_FULL_CV_AUDIT_NOTES.md`.
- Phát hiện chính:
  - `ParsedCV.rawText` REQUIRED `min_length=1` → phải merge từ `CVPARSED.rawText` cột trước khi `model_validate(parsedJson)`.
  - Legacy `parsedJson.languages: list[str]` (pre Phase 2.5f) sẽ FAIL validate → fallback rawText quan trọng.
  - `EMAILLOG.content` lowercase quote trong DDL, không có subject riêng → JOIN `EMAILTEMPLATE.subj`.
  - `miCareer-mini/app.py:346` hardcode `"top-{topK} chunks"` → cần patch UI.

### Phase 1.1 — Types + structural refactor
- Thêm dataclasses `CvContext`, `ApplicationContext`, `BudgetResult` và exception `CvContextMissingError` trong `app/services/rag_query.py`.
- Helper mới `_fetch_job_application_context(job_app_id)` wrap 3 fetcher hiện có.
- Rename `_check_context_budget` → `_check_full_context_budget`.
- Behavior identical, 29/29 tests pass.

### Phase 1.2 + 1.4 — CV fetcher + unhook embedding
- Implement `_fetch_cv_context(job_app_id) -> CvContext` với fallback ladder.
- Bỏ `embed_chunks(prompt)` + `_vector_search` khỏi `process_chat_query` (giữ function `_vector_search` trong module per leader's scope: không xóa pipeline; bỏ import `embed_chunks`).
- `topK = 0` cho response + audit log.

### Phase 1.3 — Budget refactor
- Thêm `context_budget_hard_limit: float = 0.95` vào `app/core/config.py`.
- Rewrite `_check_full_context_budget`:
  - Signature mới `(system_prompt, history, user_prompt, model_mode) -> BudgetResult`.
  - Tính token CHO TOÀN BỘ payload (system + history + user).
  - 3 ngưỡng: `proceed < 0.80`, `warn_proceed [0.80, 0.95)`, `block >= 0.95`.
- `_build_blocked_response()` helper trả deterministic message khi block.
- `process_chat_query` branch theo `budget_result.action`.

### Phase 1.5 — Prompt v1 với 8 guardrails
- Constant `_SYSTEM_INSTRUCTIONS` với 8 nguyên tắc theo Decision Analysis §Prompt Policy.
- Replace `_build_system_prompt` → `_build_full_cv_system_prompt(cv_context, app_ctx)`.
- Untrusted markers cho mỗi block. CV marker phân biệt `parsed_json` vs `raw_text` source.
- Section `[XỬ LÝ DỮ LIỆU KHÔNG ĐÁNG TIN]` chống prompt injection.

### Phase 1.6 — Unit tests
- 23 tests trong `tests/unit/unit_test_chat_full_cv.py`:
  - CV fetcher (5)
  - Budget (5)
  - Prompt builder (7)
  - Module boundary (6)
- Tổng suite: 52/52 pass.

### Phase 2 — Context enrichment
- 3 settings mới trong `app/core/config.py`:
  - `chat_offer_history_limit: int = 3`
  - `chat_email_history_limit: int = 5`
  - `chat_email_body_char_limit: int = 300`
- Extend `ApplicationContext` với `offers` + `emails` (default `[]` → backward compat).
- Rewrite `_fetch_job_posting` với `array_agg` subqueries (levels, categories, required skills, salary, work mode, location).
- Rewrite `_fetch_candidate_profile` với skills.
- Thêm `_fetch_offers` + `_fetch_email_log`.
- Update `_build_full_cv_system_prompt` với 2 blocks mới + JD/Candidate extended.
- Helper `_format_salary_range`.
- 12 tests mới: fetchers (3), salary format (4), prompt blocks Phase 2 (5).
- Tổng suite: 64/64 pass.

### Phase 3 — Docs + miCareer-mini patch
- Tạo mới `docs/strategy/job_application_full_cv_chat_strategy.md` (12 sections).
- Tạo mới `docs/guide/job_application_full_cv_chat_guide.md` (7 sections).
- Update `docs/strategy/rag_query_strategy.md`: WARNING blocks → NOTE blocks về full-CV merged, hard limit, Section 11 split thành "legacy 12 bước" + reference pipeline mới.
- Update `docs/guide/rag_query_guide.md`: tương tự, thêm env vars mới, đánh dấu prompt cũ là reference.
- Patch `miCareer-mini/app.py:340-347`: wording "📚 top-X chunks" → "📄 Full CV context" khi `topK = 0`.
- Tạo report này.

## 3. File/code paths đã sửa

```
Fang/
  app/core/config.py
    + context_budget_hard_limit
    + chat_offer_history_limit
    + chat_email_history_limit
    + chat_email_body_char_limit
  app/services/rag_query.py
    + 3 dataclasses + 1 exception
    + _fetch_cv_context (new)
    + _fetch_offers (new)
    + _fetch_email_log (new)
    + _fetch_job_application_context (new wrapper)
    + _build_full_cv_system_prompt (replace _build_system_prompt)
    + _SYSTEM_INSTRUCTIONS constant
    + _format_salary_range (new)
    + _build_blocked_response (new)
    M _fetch_job_posting (extended fields via array_agg)
    M _fetch_candidate_profile (+ skills)
    M _check_full_context_budget (signature + 3 thresholds + BudgetResult)
    M process_chat_query (use new helpers, no embed/vector search, top_k=0, branch on action)
    - embed_chunks import (removed)
    K _vector_search (kept per scope)
  docs/strategy/
    + job_application_full_cv_chat_strategy.md (new)
    M rag_query_strategy.md (3 update sites)
  docs/guide/
    + job_application_full_cv_chat_guide.md (new)
    M rag_query_guide.md (4 update sites)
  tests/unit/
    + unit_test_chat_full_cv.py (35 tests)
  agent_workflow_doc/
    + CHAT_FULL_CV_AUDIT_NOTES.md (Phase 0 notes)
    + CHAT_FULL_CV_IMPLEMENTATION_REPORT.md (this file)

miCareer-mini/
  app.py
    M chat caption wording (top-X chunks → Full CV context khi topK=0)
```

## 4. Behavior trước/sau

| Aspect | Trước | Sau |
|---|---|---|
| CV source | embed prompt → vector search top-3 chunks từ `AIDOCUMENTCHUNK` | Full CV markdown từ `CVPARSED.parsedJson` (fallback `rawText`) |
| Multi-source | title, description, candidate basic, interview feedback | + salary/workMode/location/levels/categories/requiredSkills, candidate skills, 3 offers, 5 emails (body trunc 300) |
| System prompt | 1 block "RAG instructions" + sections không có untrusted markers | 8 guardrails + untrusted markers per block + anti-injection policy |
| Budget | Chỉ đếm history; trả warning rồi vẫn gọi LLM | Đếm full payload; 3 ngưỡng (proceed/warn_proceed/block); block KHÔNG gọi LLM |
| `topK` response | 3 (default từ `rag_top_k_chunks`) | 0 |
| Response schema | unchanged | unchanged (new value `contextWarning.type = "budget_over_hard_limit"`) |
| `embed_chunks` import | có | bỏ |
| `_vector_search` function | dùng | giữ trong module nhưng không gọi từ `process_chat_query` |

## 5. Test đã chạy

```powershell
venv\Scripts\python -m unittest discover -s tests/unit -p "unit_test_*.py"
```

Kết quả: **64/64 pass**. Trong đó:
- 29 existing tests (parser, chunking, embedding, ingestion flow, persistence, NMAIex) → vẫn pass.
- 35 mới (`tests/unit/unit_test_chat_full_cv.py`):

| Class | Tests | Cover |
|---|---|---|
| `FetchCvContextTests` | 5 | parsedJson valid, legacy languages fallback, empty raises, no CVPARSED raises, rawText auto-inject |
| `BudgetTests` | 5 | counts system+user, counts history, block hard limit, warn between, proceed under |
| `FullCvSystemPromptTests` | 7 | 8 guardrails, out-of-scope examples, untrusted policy, markers per block, CV source marker, body included, empty blocks omitted |
| `FetchOffersTests` | 2 | offers capped by setting, empty |
| `FetchEmailLogTests` | 1 | join EMAILTEMPLATE subject |
| `FormatSalaryRangeTests` | 4 | both, only_min, only_max, both_none |
| `Phase2PromptBlocksTests` | 5 | JD extended, candidate skills, offer block, email block, omit when empty |
| `ModuleBoundaryTests` | 6 | no embed_chunks import, _vector_search kept, process_chat_query contracts |

**Mapping với leader's 10-case test table** (Decision Analysis §Test Strategy):

| # | Case | Status |
|---|---|---|
| 1 | parsedJson → markdown | ✅ |
| 2 | rawText fallback | ✅ |
| 3 | Empty context → raise | ✅ |
| 4 | KHÔNG gọi `embed_chunks` | ✅ |
| 5 | KHÔNG gọi `_vector_search` | ✅ |
| 6 | Budget tính cả system prompt | ✅ |
| 7 | Prompt blocks (CV/JD/ATS/Offer/Email + untrusted) | ✅ |
| 8 | API compat ChatQueryResponse | ✅ (schema không đổi) |
| 9 | Over hard budget → deterministic | ✅ |
| 10 | Smoke E2E `/v2/chat/query` | ⏳ pending DB+server |

## 6. Acceptance criteria status (từ assignment §Acceptance criteria)

| # | Criterion | Status |
|---|---|---|
| 1 | `/v2/chat/query` vẫn hoạt động với jobAppId SUCCESS | ✅ (signature route + response schema không đổi) |
| 2 | Không còn embed prompt + vector search top-k cho JobApplication full-CV | ✅ |
| 3 | Full CV markdown trong system prompt theo data source đã chốt | ✅ |
| 4 | Offer/EmailLog đưa vào context hoặc có report | ✅ Đưa vào: 3 offers, 5 emails (body trunc) |
| 5 | Context budget tính cả system prompt + behavior rõ khi vượt ngưỡng | ✅ |
| 6 | Response schema không vỡ miCareer-mini, hoặc có patch frontend | ✅ schema không đổi + patch UI wording |
| 7 | Unit tests pass + compile sạch | ✅ 64/64, compile EXIT=0 |
| 8 | Implementation report + strategy doc + guide doc | ✅ |
| 9 | Không claim JobPosting Agent đã implement | ✅ scope chỉ JobApplication |

## 7. Rủi ro còn lại

| Rủi ro | Mitigation đã có | Việc còn |
|---|---|---|
| Prompt v1 chưa qua eval — có thể chưa robust với edge case (prompt injection sophisticated, abuse case mới) | 8 guardrails + untrusted markers + anti-injection section | P1_A_B_inc (Mai) refine v2 với eval seed cases |
| EmailLog content có thể chứa PII nhạy cảm — chưa qua legal review | Body trunc 300 chars, không log; quyết định không mask (audit decision #4) | User/tier 1 quyết khi có production data |
| Auto-compact (như Codex) chưa implement; HR phải tự bấm summarize/branch | Deterministic warning + 2 options rõ | Phase sau nếu UX cần |
| Per-model budget vẫn dùng group Lite/Pro thay vì per-model thực | Group budget đã đủ cho budget 180k/960k | Tinh chỉnh khi production cho thấy CV dài thực tế |
| Legacy `parsedJson` phân bố chưa đo trong production | 4 query verify trong `CHAT_FULL_CV_AUDIT_NOTES.md` §0.2.8 | Chạy 4 query khi có DB |
| Smoke E2E test chưa chạy | 35 unit tests cover internal contracts | Chạy smoke khi có DB + ít nhất 1 jobApp SUCCESS |

## 8. Open questions

1. Có cần cột `cvMarkdown` cache trong DB không (perf/observability)? — chưa cần, có thể bổ sung phase sau.
2. EmailLog có cần filter theo loại template (chỉ user-facing emails, bỏ system notifications)? — hiện đưa hết, user feedback nếu noise quá.
3. Khi block, có nên auto-trigger summarize ngay thay vì chờ HR bấm? — UX decision, để Mai (P1_A_B_inc) cân nhắc.
4. `topK = 0` trong response: miCareer-mini đã patch wording, nhưng nếu có client khác consume `topK > 0` thì sẽ bị surprise. — chưa biết client khác.
5. `contextSource` field mới (vd `"full_cv_markdown"` / `"raw_text_fallback"`) có nên thêm vào `ChatQueryResponse` để client dùng riêng? — không thêm Phase 1 vì giữ schema strict. Có thể bổ sung phase sau nếu cần.

## 9. Phối hợp Mai (P1_A_B_inc)

Owner CHAT_FULL_CV đã cung cấp đủ artifacts cho Mai theo §Phối hợp:

| Artifact | Path |
|---|---|
| Draft system prompt full-CV | `app/services/rag_query.py:_SYSTEM_INSTRUCTIONS` (8 guardrails) |
| Context blocks thực tế | `_build_full_cv_system_prompt` + sample render trong `tests/unit/unit_test_chat_full_cv.py` (`_sample_app_ctx`) |
| Budget behavior | `docs/strategy/job_application_full_cv_chat_strategy.md` §5 |
| API response behavior khi over budget | `docs/guide/job_application_full_cv_chat_guide.md` §3 Blocked section |

Mai có thể:
1. Review prompt v1 theo rubric P1-A (task boundary, grounding, security, output contract, observability).
2. Bổ sung eval seed cases — đặc biệt: prompt injection trong CV/Offer/Email, scope abuse, sensitive inference, hire/reject decision.
3. Đề xuất prompt v2 patch nếu cần — sửa trực tiếp `_SYSTEM_INSTRUCTIONS` hoặc tách thành module riêng.

## 10. Tài liệu liên quan

- `docs/strategy/job_application_full_cv_chat_strategy.md` — Strategy doc.
- `docs/guide/job_application_full_cv_chat_guide.md` — Guide doc.
- `docs/strategy/rag_query_strategy.md` — Updated (multi-source, budget, pipeline split).
- `docs/guide/rag_query_guide.md` — Updated (pipeline 12 vs 11 bước, env vars mới, prompt blocks mới).
- `agent_workflow_doc/CHAT_FULL_CV_AUDIT_NOTES.md` — Phase 0 findings.
- `agent_workflow_doc/assign_to_team/FANG_NEXT_PHASE_CHAT_FULL_CV_ASSIGNMENT.md` — Đề bài gốc.
- `agent_workflow_doc/assign_to_team/FANG_NEXT_PHASE_CHAT_FULL_CV_DECISION_ANALYSIS.md` — Decision tier 1.

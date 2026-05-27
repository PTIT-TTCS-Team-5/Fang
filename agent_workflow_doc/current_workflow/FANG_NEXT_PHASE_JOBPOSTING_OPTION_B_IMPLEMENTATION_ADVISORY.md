# JobPosting Agent Option B Implementation Advisory

Ngày lập: 2026-05-27  
Phạm vi: tư vấn user trực tiếp triển khai **Option B - Design-first + Read-only Tool Layer** cho JobPosting Agent

## Executive Summary

**Khuyến nghị chiến lược: triển khai Option B như một `read-only domain tool layer` trong FANG services, không triển khai agent runtime/chat UI/MCP/LangGraph trong bước đầu.** Mục tiêu của bạn ở phase này không phải là "làm agent", mà là tạo một lớp tool an toàn, testable, có contract rõ để sau này agent, MCP adapter hoặc UI có thể gọi.

**Điểm quyết định quan trọng:** làm Option B theo hướng **backend service layer trước**, sau đó mới expose API/internal adapter. Không để tool contract bị phụ thuộc vào LangGraph, MCP hay prompt. Tool phải là deterministic service functions càng nhiều càng tốt; LLM chỉ xuất hiện ở phase agent sau, không nằm trong tool read-only core.

**Option đề xuất để bạn chọn:** **Option B2 - Implement Tool Contract + Service Skeleton + Deterministic Tests**.

Lý do: B2 tạo artifact thật trong repo, đủ để unblock prototype sau này, nhưng vẫn không nhảy sang agent framework. Nó cân bằng tốt giữa "chỉ viết spec" và "làm quá sâu".

**Tóm tắt các lựa chọn triển khai:**

| Option | Mô tả | Khi nên chọn | Khuyến nghị |
|---|---|---|---|
| B1. Spec-only | Chỉ viết tool contract/spec, chưa code | Khi bạn muốn chốt product/architecture trước | Tốt nếu còn nhiều câu hỏi mở |
| B2. Spec + service skeleton + tests | Viết contract, module service read-only, Pydantic schemas, unit tests cơ bản | Khi muốn tạo nền kỹ thuật thật nhưng chưa làm agent | **Khuyến nghị** |
| B3. Internal API endpoints | B2 + expose FastAPI endpoints cho từng tool | Khi cần frontend/dev kiểm thử sớm | Làm sau B2 |
| B4. Agent-ready adapter | B2/B3 + adapter format cho tool calling/LangGraph/MCP | Khi đã chốt runtime agent | Defer |
| B5. Full read-only agent prototype | Tool layer + LLM orchestration + conversation theo jobPostId | Khi Full-CV/P1/eval đã ổn | Không làm ngay |

**Final recommendation:** bắt đầu bằng B2 trong 3 deliverables:

1. `JOBPOSTING_AGENT_TOOL_CONTRACT.md` - contract/spec.
2. `app/services/jobposting_tools.py` hoặc tên tương đương - read-only service functions.
3. Unit tests cho tool behavior và permission/data-scope checks.

Nếu trong quá trình làm thấy schema/API quá rộng, dừng ở B1 và ghi decision questions. Không tự chuyển sang agent runtime.

## Current Context

Hiện trạng resource/team:

1. `JobApplication Full-CV Chat` đã có owner và đang làm.
2. `P1-A/P1-B Prompt Review + Minimal Eval` đã có owner và đang làm.
3. Thành viên còn lại nên làm `miCareer-mini + API Contract Readiness` hoặc QA/readiness pack.
4. User sẽ trực tiếp làm JobPosting Agent Option B.

Hiện trạng code liên quan:

1. `rank_candidates_for_job(job_id, limit, province_id, work_mode)` đã có trong `app/services/nmaiex_ranking_service.py`.
2. `AIDOCUMENTCHUNK` có CV chunks + embeddings theo `jobAppId`.
3. `CVPARSED` có `parsedJson` và `rawText`.
4. `JOBAPPLICATION` nối `jobPostId` với `candidateId`.
5. `INTERVIEW`, `INTERVIEWFEEDBACK`, `OFFER`, `EMAILLOG` có dữ liệu ATS liên quan `jobAppId`.
6. Chat hiện tại đang theo `jobAppId`; chưa có conversation theo `jobPostId`.

Điểm cần giữ rõ: Option B **không phụ thuộc** vào việc Full-CV Chat đã merge, nhưng tool `get_job_application_full_cv` nên reuse cùng logic/fallback với Full-CV Chat sau khi owner kia hoàn thành.

## Strategic Goal

Mục tiêu của Option B:

> Tạo một lớp tool read-only, framework-agnostic, có schema rõ cho phạm vi một `JobPosting`, để sau này JobPosting Agent có thể dùng ranking/search/filter/summary/full-CV/ATS tools mà không phải viết SQL tùy hứng trong agent.

Không phải mục tiêu của Option B:

1. Không build chat endpoint cho JobPosting ngay.
2. Không build LangGraph/MCP runtime ngay.
3. Không cho LLM tự gọi tool trong phase này.
4. Không write/update ATS/email/offer/status.
5. Không refactor JobApplication chat.
6. Không xóa hoặc thay đổi NMAIex ranking hiện tại nếu không cần.

## Recommended Implementation Strategy

### Chọn B2 làm baseline

Nên làm B2 vì:

1. Có artifact code thật để kiểm tra feasibility.
2. Tool functions có thể test độc lập không cần LLM.
3. Sau này expose qua FastAPI, MCP hay LangGraph đều dễ.
4. Giữ quyền kiểm soát data boundary trước khi model được quyền điều phối.

### Luồng triển khai khuyến nghị

1. Viết tool contract trước.
2. Tạo Pydantic schemas cho input/output.
3. Implement service functions read-only.
4. Thêm unit tests với mocked DB/service.
5. Viết implementation report ngắn: tool nào done, tool nào deferred, risk nào còn mở.
6. Sau đó mới quyết định có expose API endpoints không.

## Option Details

### B1 - Spec-only

Mô tả: chỉ viết tài liệu contract, không code.

Ưu điểm:

- Rủi ro thấp nhất.
- Phù hợp nếu còn nhiều câu hỏi product/permission.
- Không conflict với workstream khác.

Nhược điểm:

- Chưa chứng minh SQL/data feasibility.
- Prototype sau này vẫn phải tự validate lại.

Nên chọn nếu:

- Bạn chưa muốn đụng code trước khi Full-CV Chat merge.
- Bạn muốn thành viên khác review trước.

Deliverable:

- `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_JOBPOSTING_AGENT_TOOL_CONTRACT.md`

### B2 - Spec + Service Skeleton + Deterministic Tests

Mô tả: viết spec + module service read-only + schema + tests.

Ưu điểm:

- Tạo nền kỹ thuật thật.
- Chưa kéo LLM/agent runtime.
- Dễ review và mở rộng.
- Tests có thể bắt lỗi data-scope sớm.

Nhược điểm:

- Cần đọc schema/SQL kỹ.
- Có thể bị scope creep nếu cố implement đủ 7-8 tools ngay.

Nên chọn nếu:

- Bạn muốn tiến lên một bước thực chất nhưng vẫn an toàn.

Deliverables:

1. Tool contract doc.
2. `app/models/jobposting_tools.py` hoặc schemas trong model phù hợp.
3. `app/services/jobposting_tools.py`.
4. Unit tests.
5. Implementation report.

### B3 - Internal API Endpoints

Mô tả: expose các read-only tools qua FastAPI endpoints nội bộ.

Ưu điểm:

- Frontend/readiness owner có thể gọi thử.
- Dễ smoke test bằng Postman.
- Tạo API contract sớm.

Nhược điểm:

- API surface dễ đóng băng sớm.
- Cần route naming, auth assumption, response compatibility.

Nên làm sau B2, không làm cùng lúc nếu chưa cần.

Endpoint gợi ý:

- `GET /v2/job-postings/{jobPostId}/ai/context`
- `GET /v2/job-postings/{jobPostId}/ai/ranking`
- `POST /v2/job-postings/{jobPostId}/ai/search/semantic`
- `POST /v2/job-postings/{jobPostId}/ai/search/text`
- `GET /v2/job-applications/{jobAppId}/ai/summary`
- `GET /v2/job-applications/{jobAppId}/ai/full-cv`
- `GET /v2/job-applications/{jobAppId}/ai/ats-history`

Tên route có thể đổi; quan trọng là không gọi đây là "agent" nếu chưa có agent.

### B4 - Agent-ready Adapter

Mô tả: thêm lớp adapter chuyển service functions thành tool definitions cho LangGraph/MCP/function calling.

Ưu điểm:

- Chuẩn bị nhanh cho agent runtime.

Nhược điểm:

- Dễ phụ thuộc framework sớm.
- Có thể phải rewrite nếu chọn runtime khác.

Khuyến nghị: defer. Chỉ làm sau khi service functions ổn.

### B5 - Full Read-only Agent Prototype

Mô tả: làm LLM orchestration, conversation theo `jobPostId`, tool calling và answer generation.

Ưu điểm:

- Sản phẩm nhìn thấy ngay.

Nhược điểm:

- Cần prompt/eval, conversation schema, tool call log, budget, source attribution.
- Dễ conflict với Full-CV/P1 chưa xong.

Khuyến nghị: không làm trong Option B phase đầu.

## Minimal Tool Set

Không cần implement tất cả ngay. Nên chia thành MVP và deferred.

### MVP Tool Set

#### 1. `get_job_posting_context(job_post_id)`

Mục tiêu: lấy context nền của job.

Data sources:

- `JOBPOSTING`
- `JOB_LEVEL_MAP`, `JOBLEVEL`
- `JOB_CATEGORY_MAP`, `JOBCATEGORY`
- `JOBREQUIREMENT`, `SKILL`
- `JOB_LANG_REQUIREMENT`, `LANGUAGE`
- `COMPANY` nếu cần

Output:

- job id/title/description.
- salary/workMode/workLoc/province.
- levels/categories/skills/languages.
- source metadata.

Guardrail:

- Không để description quá dài nếu expose cho model sau này.
- Treat JD as untrusted data.

#### 2. `get_job_candidate_ranking(job_post_id, limit, filters)`

Mục tiêu: lấy ranking snapshot có score breakdown.

Reuse:

- `rank_candidates_for_job()`

Output:

- jobAppId nếu có thể bổ sung.
- candidate id/name.
- match score.
- score breakdown.
- filter applied.

Important note:

- Ranking service hiện trả `candidate_id`, `candidate_name`, `match_score`, `score_breakdown`; nếu thiếu `jobAppId`, cần quyết định có enrich thêm không. JobPosting Agent về sau cần `jobAppId` để drill-down.

#### 3. `search_job_applications_text(job_post_id, query, limit, filters)`

Mục tiêu: exact/full-text search trong ứng viên của một job.

Data sources:

- `JOBAPPLICATION`
- `CVPARSED.rawText`
- `CANDIDATE.bio`
- `CANDIDATESKILL`/`SKILL`

Output:

- jobAppId.
- candidate id/name.
- snippets.
- rank/score nếu có.

Guardrail:

- Query luôn phải scoped theo `jobPostId`.
- Không search toàn DB nếu thiếu job id.

#### 4. `get_job_application_summary(job_app_id)`

Mục tiêu: summary structured, không LLM, trước khi load full CV.

Data sources:

- `JOBAPPLICATION`
- `CANDIDATE`, `"user"`, `PROVINCE`
- `CVPARSED.parsedJson` selected fields
- `CANDIDATESKILL`, `SKILL`
- latest interview/offer/email metadata nếu nhẹ

Output:

- candidate basic.
- application status.
- years/location/skills.
- CV section summary from parsed JSON.
- latest ATS signals.

Guardrail:

- Không dùng LLM để summarize trong Option B.
- Không trả full rawText ở summary.

### Near-MVP Tool Set

#### 5. `get_job_application_full_cv(job_app_id)`

Mục tiêu: lấy full CV markdown cho một application.

Dependency:

- Nên reuse logic của `CHAT_FULL_CV` khi branch đó xong.

Fallback:

1. `CVPARSED.parsedJson` -> `convert_json_to_markdown()`
2. fallback `rawText`
3. clear error nếu không có usable CV

Guardrail:

- Chỉ nhận một `jobAppId`.
- Không bulk load.
- Return source metadata.

#### 6. `get_candidate_ats_history(job_app_id)`

Mục tiêu: lấy lịch sử ATS.

Data sources:

- `INTERVIEW`
- `INTERVIEWFEEDBACK`
- `OFFER`
- `EMAILLOG`
- `APPSTATUSHISTORY` nếu cần

Guardrail:

- Email content recent N + truncate.
- Offer latest hoặc version-limited.
- Treat all content as untrusted.

### Deferred Tool

#### 7. `search_job_applications_semantic(job_post_id, query, limit, filters)`

Mục tiêu: semantic search trên CV chunks trong phạm vi job.

Lý do defer có thể hợp lý:

- Cần gọi embedding provider.
- Tests phức tạp hơn.
- Có cost/external dependency.
- Ranking J->C đã dùng semantic-ish vector path cho job text; text search đủ cho MVP.

Nếu implement:

- Join `AIDOCUMENTCHUNK` với `JOBAPPLICATION`.
- Scope cứng theo `jobPostId`.
- Limit snippets.
- Không trả full CV.

#### 8. `compare_job_applications(job_post_id, job_app_ids, criteria)`

Mục tiêu: so sánh nhiều applications.

Khuyến nghị: defer vì comparison có thể cần LLM hoặc rule phức tạp. Phase đầu chỉ nên cung cấp raw summaries để agent sau này compare.

## Recommended Module Boundary

### Suggested Files

Option B2:

1. `app/models/jobposting_tools.py`
2. `app/services/jobposting_tools.py`
3. `tests/unit/unit_test_jobposting_tools.py`
4. `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_JOBPOSTING_AGENT_TOOL_CONTRACT.md`
5. `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_JOBPOSTING_OPTION_B_IMPLEMENTATION_REPORT.md`

Nếu repo pattern muốn gom models vào `nmaiex_schemas.py` hoặc `chat.py`, vẫn nên cân nhắc file riêng để không trộn ranking/chat với future agent tools.

### Service Design

Service functions nên là async và nhận primitive inputs:

```python
async def get_job_posting_context(job_post_id: int) -> JobPostingContext: ...
async def get_job_candidate_ranking(job_post_id: int, limit: int, filters: RankingFilters) -> JobCandidateRanking: ...
async def search_job_applications_text(job_post_id: int, query: str, limit: int, filters: ApplicationSearchFilters) -> ApplicationSearchResult: ...
async def get_job_application_summary(job_app_id: int) -> JobApplicationSummary: ...
async def get_job_application_full_cv(job_app_id: int) -> JobApplicationFullCv: ...
async def get_candidate_ats_history(job_app_id: int) -> AtsHistory: ...
```

Không nên:

- Nhận raw SQL từ caller.
- Trả asyncpg rows trực tiếp.
- Gọi LLM trong service.
- Gọi semantic embedding trong MVP nếu không cần.
- Tự quyết định permission bằng placeholder mơ hồ mà không ghi rõ assumption.

## Data Scope and Permission Guardrails

Mỗi tool phải enforce scope:

1. Nếu input là `job_post_id`, mọi query phải scoped theo job đó.
2. Nếu input là `job_app_id`, nên có helper lấy `jobPostId/candidateId` và verify ownership khi sau này có `hrId/companyId`.
3. Không trả full CV/email hàng loạt.
4. Không trả email content đầy đủ nếu không có reason.
5. Output nên có source IDs để audit: `jobPostId`, `jobAppId`, `candidateId`, `cvParsedId`, `offerId`, `emailLogId`.

Vì auth middleware chưa rõ, phase này nên ghi trong contract:

- Permission enforcement production sẽ cần HR/company/job ownership.
- Service hiện có thể chỉ enforce relationship integrity: application thuộc job, records thuộc application.
- API exposure sau này không được bỏ qua HR/company check.

## Output Contract Principles

Tool outputs nên:

1. Có schema typed/Pydantic.
2. Có source IDs.
3. Có `includedSources` hoặc metadata.
4. Có `warnings` khi dữ liệu thiếu/truncated/fallback.
5. Không trả text quá dài nếu không phải full CV tool.
6. Không bịa reason bằng LLM.
7. Tách `display` fields và `raw/source` fields nếu cần.

Ví dụ warning:

- `cv_missing`
- `parsed_json_invalid_raw_text_fallback`
- `email_content_truncated`
- `ranking_missing_job_app_id`
- `no_applications_for_job`
- `semantic_search_deferred`

## Testing Strategy

Theo `current_workflow/rule.md`, nếu có code backend phải chạy kiểm thử phù hợp. Với Option B2:

### Unit Tests bắt buộc

1. `get_job_posting_context` trả job + skills/levels/categories/languages.
2. Tool trả clear error/not found khi `jobPostId` không tồn tại.
3. Ranking wrapper gọi/reuse ranking service và limit đúng.
4. Text search luôn scoped theo `jobPostId`.
5. `get_job_application_summary` không trả full raw CV.
6. `get_job_application_full_cv` dùng parsedJson -> markdown khi hợp lệ.
7. Full CV fallback rawText khi parsedJson invalid.
8. ATS history truncates email content.
9. Không có tool nào write DB.

### Integration/Smoke sau B3

Nếu expose API endpoints:

1. Gọi endpoint bằng Postman/test_api.http.
2. Verify 404/400 behavior.
3. Verify response schema.
4. Verify application không leak khỏi job.

### Không cần trong Option B

- Không cần LLM eval.
- Không cần browser/UI test nếu chưa sửa frontend.
- Không cần test LangGraph/MCP.

## Suggested Phased Checklist

### Phase 1 - Contract

- [ ] Viết tool list MVP/deferred.
- [ ] Định nghĩa input/output schema.
- [ ] Ghi permission assumptions.
- [ ] Ghi truncation/budget policy.
- [ ] Ghi error/warning codes.
- [ ] Ghi test plan.

### Phase 2 - Service Skeleton

- [ ] Tạo model schemas.
- [ ] Tạo service module.
- [ ] Implement `get_job_posting_context`.
- [ ] Implement `get_job_candidate_ranking`.
- [ ] Implement `search_job_applications_text`.
- [ ] Implement `get_job_application_summary`.

### Phase 3 - CV/ATS Drill-down

- [ ] Implement `get_job_application_full_cv` sau khi thống nhất với Full-CV owner.
- [ ] Implement `get_candidate_ats_history`.
- [ ] Add truncation/fallback warnings.

### Phase 4 - Tests and Report

- [ ] Unit tests.
- [ ] `compileall`.
- [ ] Implementation report.
- [ ] List deferred items and blockers.

### Phase 5 - Optional API Exposure

- [ ] Decide route namespace.
- [ ] Add read-only routes.
- [ ] Add Postman/test_api smoke.
- [ ] Coordinate with miCareer-mini readiness owner.

## Key Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Tool layer phình thành agent runtime | Scope creep | Cấm LLM/tool-calling orchestration trong Option B |
| Full CV logic duplicate với CHAT_FULL_CV | Inconsistent behavior | Reuse helper sau khi Full-CV owner hoàn thành |
| Ranking không trả `jobAppId` | Agent không drill-down được | Enrich ranking wrapper hoặc add lookup |
| Text/semantic search leak ngoài job | Data privacy bug | Mọi query scoped cứng theo `jobPostId` |
| Email content quá dài/prompt injection | Unsafe future context | Recent N + truncate + untrusted metadata |
| API route đóng băng quá sớm | Future refactor cost | Service first, API after contract |
| Permission chưa có auth layer | False safety | Ghi assumption rõ, không expose production write |
| Tests phụ thuộc DB thật | Fragile | Unit tests mock DB/service; smoke riêng nếu có DB |

## Coordination With Other Owners

### Với Full-CV Chat owner

Cần lấy:

1. Full CV context helper/fallback cuối cùng.
2. `topK=0`/context warning behavior.
3. Prompt/data source policy.
4. Tests liên quan parsedJson/rawText fallback.

Không nên:

- Tự sửa `rag_query.py`.
- Tạo logic full CV khác hoàn toàn.

### Với P1-A/P1-B owner

Cần lấy:

1. Prompt safety rules cho untrusted CV/JD/email.
2. Minimal eval cases liên quan multi-candidate nếu có.
3. Output/source attribution recommendations.

Không nên:

- Tự viết production agent prompt trong Option B.

### Với miCareer-mini readiness owner

Cần gửi:

1. Tool/API shape nếu B3.
2. Expected fields for future JobPosting Assistant.
3. Ranking/summary/full CV drill-down flow.

Không nên:

- Yêu cầu frontend implement agent UI khi backend chưa có agent.

## Open Questions for User

Bạn nên chốt các câu này trước hoặc trong khi viết contract:

1. Option B phase đầu bạn muốn dừng ở B1, B2 hay làm luôn B3?
2. Tool MVP có cần semantic search ngay không, hay text search + ranking đủ?
3. Ranking output có bắt buộc phải include `jobAppId` để drill-down không?
4. Full CV tool có được load full CV của nhiều ứng viên nếu caller gửi list không, hay chỉ một `jobAppId` mỗi lần?
5. EmailLog phase đầu trả full content, snippet, metadata-only hay deferred?
6. Tool layer có nhận `hrId` ngay để chuẩn bị permission, hay để phase API/agent sau?
7. Có muốn tạo bảng/log tool calls ngay ở Option B không, hay chỉ ghi logging recommendation?
8. Có expose FastAPI endpoints trong phase này không?
9. Tên namespace nên là `jobposting_tools`, `jobposting_ai`, hay `jobposting_agent_tools`?
10. Semantic search nếu làm sẽ dùng embedding provider thật trong tests hay mock hoàn toàn?

## Recommended Final Call

Nên chốt:

**Triển khai Option B theo B2: Tool Contract + Service Skeleton + Deterministic Tests.**

Scope MVP:

1. `get_job_posting_context`
2. `get_job_candidate_ranking`
3. `search_job_applications_text`
4. `get_job_application_summary`
5. `get_job_application_full_cv` nếu reuse được từ Full-CV owner, nếu chưa thì để interface/deferred
6. `get_candidate_ats_history` với truncation policy

Deferred:

1. Semantic search nếu cần embedding/cost phức tạp.
2. Compare tool.
3. FastAPI endpoints nếu chưa cần.
4. MCP/LangGraph adapter.
5. Agent runtime/conversation schema.
6. Write tools.

Definition of Done:

1. Có contract doc.
2. Có service/module schema nếu chọn B2.
3. Có tests hoặc ít nhất test plan nếu dừng ở B1.
4. Không có LLM orchestration.
5. Không write DB.
6. Không phá Full-CV/P1 workstreams.
7. Có implementation report và list decision questions còn mở.


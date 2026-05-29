# Prompt Template For Tier 1: C3 Discovery Workstream


## Role

Bạn là tier 1 discovery architect cho dự án FANG. Bạn chỉ làm **một discovery workstream** của kế hoạch JobPosting Agent C3, theo mã `{{WS_CODE}}`.

Nhiệm vụ của bạn là đọc context, đọc code/schema đủ sâu, rồi viết một report discovery/decision input cho workstream được giao. Report của bạn sẽ là input cho một tier 1 khác synthesize thành `FANG_NEXT_PHASE_JOBPOSTING_C3_OFFICIAL_IMPLEMENTATION_PLAN.md`.

Bạn **không được code**, **không được sửa file runtime**, và **không được viết implementation plan chính thức** trong lượt này.

## Required Reading

Đọc các tài liệu sau trước:

0. `agent_workflow_doc\try_hard_jobposting\FANG_NEXT_PHASE_JOBPOSTING_C3_PLANNING_BRIEF.md`
1. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_PLANNING_BRIEF.md`
2. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_OPTION_C3_DEEP_ADVISORY.md`
3. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_OPTION_C_IMPLEMENTATION_ADVISORY.md`
4. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_AGENT_DECISION_ANALYSIS.md`
5. `agent_workflow_doc/KINH_NGHIEM.md`

Đọc code/schema chung đủ để tránh hallucination:

1. `app/services/rag_orchestrator.py`
2. `app/services/rag_model_adapters.py`
3. `app/models/chat.py`
4. `app/services/rag_query.py`
5. `app/services/nmaiex_ranking_service.py`
6. `app/services/nmaiex_mapper_service.py`
7. `database/schema_ai_core.sql`
8. `database/schema_web_core.sql`

Nếu `{{WS_CODE}}` là `WS-C`, bắt buộc đọc thêm:

1. `app/services/cv_parser.py`
2. `app/services/cv_parser_adapters.py`
3. `app/api/routes_ingestion.py`
4. `app/services/nmaiex_candidate_enrichment.py`
5. `app/models/cv_models.py`
6. `tests/unit/unit_test_ingestion_flow.py`
7. `tests/unit/unit_test_nmaiex_candidate_enrichment.py`

Nếu line references drift, ưu tiên code hiện tại.

## Project Context

User đã chốt hướng **JobPosting Agent C3.1**:

1. Dedicated JobPosting conversation tables.
2. Single-agent runtime/controller.
3. Minimal read-only tool set.
4. Conversation scoped by `jobPostId`.
5. Agent có memory/state để hiểu working set như "10 ứng viên này".
6. Agent tự gọi tool hệ thống, nhận tool result, rồi trả lời có grounding.
7. Không write tools trong phase đầu.
8. Không LangGraph/MCP/full multi-provider tool-calling trong phase đầu nếu workstream không chứng minh cần.

Desired product behavior:

1. HR mở `JobPosting`, bên phải có chat pane.
2. HR hỏi "phân tích 10 ứng viên rank cao nhất" -> agent gọi ranking tool `limit=10`, lưu working set, phân tích.
3. HR hỏi tiếp "trong 10 ông này lọc ra tiếng Anh hạng C trở lên" -> agent nhớ working set và lọc theo dữ liệu language đã normalize.
4. HR hỏi "so sánh tất cả ứng viên" -> agent phát hiện tập quá lớn, không so sánh bừa, mà tư vấn dùng top N/filter/ranking.

## Critical New Finding: NMAIex Normalization Bug

User vừa phát hiện một bug cần đưa vào official implementation plan:

> CV parser hiện tại không normalize province, language, language proficiency ngay khi parse/enrichment. `nmaiex_mapper_service.py` đã có `map_string_to_province_id()` và `normalize_proficiency()`, nhưng parser/ingestion chưa dùng đúng để normalize tỉnh, ngôn ngữ, trình độ ngôn ngữ. Đây là blocker/risk cho JobPosting Agent, đặc biệt filter kiểu "tiếng Anh hạng C trở lên".

Ownership:

- `WS-C` là owner chính của bug này.
- `WS-C` phải phân tích và đưa ra implementation-plan input cụ thể để fix normalization ở parse/enrichment stage.
- `WS-A`, `WS-B`, `WS-D` không cần thiết kế fix chi tiết, nhưng phải ghi dependency/assumption nếu scope của mình phụ thuộc vào normalized language/province data.

Important boundary:

- Không normalize lặp trong JobPosting Agent runtime như workaround lâu dài.
- Normalization phải nằm trước ở parse/enrichment/data preparation để Ranking, JobApplication Chat và JobPosting Agent dùng chung dữ liệu sạch.

## Workstream Mapping

### If `{{WS_CODE}}` = `WS-A`

Workstream name:

`WS-A - Agent Runtime and Tool Calling Decision`

Output file:

`agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSA_AGENT_RUNTIME_DECISION.md`

Main questions:

1. Native tool calling với Google GenAI nên dùng thế nào trong FANG?
2. Có dùng một provider/model agent riêng hay reuse toàn bộ `modelMode` hiện tại?
3. Exact model IDs/aliases nào phải verify trước khi code?
4. Agent runtime loop nên có schema nào: tool declarations, max steps, retry, failure, final answer.
5. Runtime module boundary nên là adapter riêng hay mở rộng `rag_model_adapters.py`?
6. Có cần LangGraph/MCP không? Default là không, chỉ đề xuất nếu có lý do kỹ thuật rõ.
7. `.env` cần thêm biến gì?

Required report sections:

1. Executive Summary
2. Current Runtime Reality
3. Tool Calling Options
4. Recommended Runtime Design
5. Provider/Model Decision
6. Agent Loop Contract
7. Failure Semantics and Guardrails
8. Required Config
9. Impact on Other Workstreams
10. Open Questions for Synthesis
11. Acceptance Criteria

### If `{{WS_CODE}}` = `WS-B`

Workstream name:

`WS-B - Dedicated Conversation Tables and Memory State`

Output file:

`agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSB_CONVERSATION_MEMORY_SCHEMA.md`

Main questions:

1. Table design cho conversation/message/tool/tool-call/state là gì?
2. Có tạo tool catalog table như `AIJOBPOSTINGTOOL` hoặc `AIAGENTTOOL` không?
3. `AIJOBPOSTINGCHATSTATE` có bắt buộc không?
4. State JSON nên lưu gì để hiểu "10 ông này"?
5. Conversation rename/default title/history hoạt động thế nào?
6. Tool-call log nên lưu gì và không lưu gì để tránh PII/full CV/email leak?
7. Migration/index/FK risk với `JOBPOSTING`, `HR`, `JOBAPPLICATION` là gì?

Required report sections:

1. Executive Summary
2. Current Persistence Reality
3. Proposed Tables
4. State JSON Design
5. Conversation UX Persistence
6. Tool Catalog and Tool Call Logging
7. Privacy and Logging Boundaries
8. Migration and Index Plan Input
9. Impact on Other Workstreams
10. Open Questions for Synthesis
11. Acceptance Criteria

### If `{{WS_CODE}}` = `WS-C`

Workstream name:

`WS-C - Read-only Tool Contract, Data Scope, and NMAIex Normalization Dependency`

Output file:

`agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSC_TOOL_CONTRACT.md`

Main questions:

1. MVP tool list và deferred tools là gì?
2. Input/output schema cho từng tool là gì?
3. Source metadata, warnings và error semantics như thế nào?
4. Full CV policy: summary-first, single `jobAppId`, no bulk load.
5. Count/too-large guardrail: default threshold 25, HR top N max 25.
6. Language filter feasibility, đặc biệt "hạng C trở lên" map vào enum/schema nào?
7. Làm sao đảm bảo mọi tool scoped theo `jobPostId`, không leak application ngoài job?
8. NMAIex normalization bug phải fix ở parse/enrichment stage thế nào?

Required MVP tools:

1. `get_job_posting_context(job_post_id)`
2. `get_job_candidate_ranking(job_post_id, limit, filters)`
3. `search_job_applications_text(job_post_id, query, limit, filters)`
4. `get_job_application_summary(job_app_id)`
5. `get_job_application_full_cv(job_app_id)`
6. `get_candidate_ats_history(job_app_id)`
7. `count_job_applications(job_post_id, filters)`

Required normalization analysis:

1. Identify current parser/ingestion path where `ParsedCV` is produced and persisted.
2. Identify where candidate province, languages and language proficiency currently end up.
3. Confirm `map_string_to_province_id()` and `normalize_proficiency()` are not called in the parser/ingestion path where needed.
4. Decide exact normalization stage: after `ParsedCV.model_validate(json_obj)` and before `save_parsed_cv()`, or inside enrichment sidecar, or both with clear single source of truth.
5. Propose function boundary, for example `normalize_parsed_cv_for_nmaiex(parsed_cv, job_app_id)` or equivalent.
6. Define how to normalize language name if existing code lacks a language-name mapper.
7. Define tests needed to prove province/language/proficiency normalized before ranking/agent use.
8. Decide fallback behavior if LLM mapper fails.

Required report sections:

1. Executive Summary
2. Current Data and Tool Reality
3. MVP Tool Contract
4. Deferred Tools
5. Data Scope and Leak Prevention
6. Full CV and ATS Policies
7. Count and Too-large Guardrails
8. Language Filter Semantics
9. NMAIex Normalization Bug Analysis
10. Normalization Fix Input for Official Implementation Plan
11. Tests Required
12. Impact on Other Workstreams
13. Open Questions for Synthesis
14. Acceptance Criteria

### If `{{WS_CODE}}` = `WS-D`

Workstream name:

`WS-D - Product, API, and UI Contract`

Output file:

`agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSD_API_UI_CONTRACT.md`

Main questions:

1. Route namespace cho JobPosting Agent là gì?
2. Request/response schema cho query endpoint là gì?
3. Có cần endpoints list/history/rename/delete/archive conversation không?
4. UI chat pane cần fields nào: used tools, source IDs, latency, warnings, state/working-set label?
5. UI hiển thị tool progress và tool detail thế nào?
6. Streaming/tool progress có cần phase đầu không?
7. Manual/Postman smoke flows cho top 10, refine language, too-large compare, rename conversation là gì?

Required report sections:

1. Executive Summary
2. Current API/UI Reality Assumptions
3. Proposed Route Namespace
4. Request/Response Schemas
5. Conversation Management API
6. Chat Pane UX Contract
7. Tool Usage Visibility
8. Smoke Test Flows
9. Dependency on WS-A/B/C
10. Open Questions for Synthesis
11. Acceptance Criteria

## Shared Constraints For All Workstreams

You must not:

1. Write code.
2. Modify runtime files.
3. Create migrations.
4. Write the official implementation plan.
5. Open scope to write tools.
6. Assume LangGraph/MCP unless your assigned workstream proves it is necessary.
7. Ignore the normalization bug.
8. Ignore coordination with Full-CV Chat and P1-A/P1-B.

You must:

1. Ground findings in actual files/code/schema.
2. Distinguish recommendation from confirmed code reality.
3. List assumptions explicitly.
4. Identify conflicts with other workstreams.
5. Produce an output file at the exact path assigned to `{{WS_CODE}}`.
6. Write in Vietnamese.
7. Use clear tables/checklists where helpful.

## Cross-Workstream Facts To Preserve

1. `invoke_generation()` currently returns text only; it is not a tool-calling runtime.
2. Existing chat request/response is `jobAppId`-scoped.
3. JobPosting Agent conversation must be `jobPostId`-scoped.
4. `jobAppId` should be the working-set key for candidate/application memory.
5. Default top N is 10.
6. HR max top N is 25.
7. Too-large deep compare threshold defaults to 25 and should be configurable.
8. Phase 1 is read-only.
9. Full CV must be summary-first and single-application drill-down, not bulk-loaded.
10. Language/proficiency normalization belongs upstream in parse/enrichment.

## Required Closing Section

End your report with:

1. `Recommended Decisions For Synthesis`
2. `Risks If Ignored`
3. `Inputs Needed From Other Workstreams`
4. `Checklist For Official Implementation Plan`

## Quality Bar

Your report is successful if:

1. A synthesis tier 1 can directly use it as input for the official implementation plan.
2. Tier 2 cannot mistakenly read it as permission to code.
3. The report does not hide uncertainty.
4. The report makes code reality and proposed design clearly separable.
5. The report explains how this workstream affects C3 end state: HR chat pane on `JobPosting` with memory, tool use, and grounded answers.


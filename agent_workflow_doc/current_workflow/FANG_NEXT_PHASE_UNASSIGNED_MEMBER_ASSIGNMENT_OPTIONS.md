# Unassigned Member Assignment Options

Ngày lập: 2026-05-27  
Phạm vi: giao việc cho thành viên còn lại sau khi `CHAT_FULL_CV`, `P1-A/P1-B` và `JobPosting Agent Option B` đã có owner

## Executive Summary

**Khuyến nghị chiến lược: giao thành viên còn lại làm `miCareer-mini + API Contract Readiness`, mở rộng thêm phần readiness cho `JobPosting Agent` tương lai nhưng không cho implement backend agent/tool layer.**

Lý do chính: hiện ba luồng lõi đã có owner:

1. `JobApplication Full-CV Chat` đã giao cho một thành viên và đang làm.
2. `P1-A/P1-B Prompt Review + Minimal Eval` đã giao cho một thành viên và đang làm.
3. `JobPosting Agent Option B - Design-first + Read-only Tool Layer` do user trực tiếp đảm nhiệm.

Vì vậy thành viên còn lại không nên đụng vào backend core của Full-CV, prompt/eval core, hoặc tool layer JobPosting mà user đang làm. Việc tốt nhất là giao một workstream độc lập nhưng có tác dụng giảm rủi ro nghiệm thu: kiểm tra `miCareer-mini`, API contract, UI wording, client assumptions, smoke checklist và readiness cho các thay đổi sắp tới.

**Option đề xuất để giao ngay:** **Option A - miCareer-mini + API Contract Readiness**.

**Nếu thành viên mạnh QA/test hơn frontend:** chọn **Option B - Cross-workstream QA/Eval Harness Pack**.

**Nếu thành viên mạnh backend phân tích hơn frontend:** chọn **Option C - JobPosting Data Access, Permission and Audit Inventory**.

**Không nên giao hiện tại:** implement JobPosting Agent, MCP adapter, LangGraph runtime, write tools, hoặc sửa trực tiếp backend Full-CV/P1 nếu không có owner chính phối hợp.

## Quick Option Summary

| Option | Nên chọn khi | Giá trị | Conflict risk | Khuyến nghị |
|---|---|---:|---:|---|
| A. miCareer-mini + API Contract Readiness | Thành viên có thể đọc UI/client/API flow | Cao | Thấp | **Chọn mặc định** |
| B. Cross-workstream QA/Eval Harness Pack | Thành viên mạnh test/checklist hơn code feature | Cao | Thấp | Chọn nếu QA-minded |
| C. JobPosting Data Access, Permission and Audit Inventory | Thành viên mạnh backend/schema/security | Medium-High | Thấp-Medium | Chọn nếu backend-minded |
| D. NMAIex Ranking Explainability Pack | Muốn hỗ trợ JobPosting tool/ranking explanation | Medium | Thấp | Chọn nếu muốn tăng chất lượng ranking |
| E. JobPosting Agent Product Workflow Sketch | Muốn nghiên cứu UX/product, không code | Medium | Thấp | Chỉ nếu cần product clarity |
| F. Implement JobPosting Agent/MCP/Framework | Muốn ship agent ngay | High potential | Cao | **Không chọn** |

## Recommended Assignment

Giao **Option A - miCareer-mini + API Contract Readiness**.

Diễn đạt assignment đề xuất:

> Rà soát `miCareer-mini` và API contract readiness cho các thay đổi sắp tới của FANG: `JobApplication Full-CV Chat`, `P1-A/P1-B` prompt/eval output, và hướng `JobPosting Agent` read-only tool layer. Không sửa backend FANG, không implement JobPosting Agent. Output là một readiness report bằng tiếng Việt: client đang phụ thuộc field nào, UI wording nào cần đổi, flow nào cần smoke test, `topK=0/contextWarning/model/fallback/latency` xử lý thế nào, và cần chuẩn bị gì để sau này có JobPosting read-only assistant.

Đây là việc ít conflict nhất vì:

1. Không đụng vào backend Full-CV đang có owner.
2. Không đụng vào prompt/eval core đang có owner.
3. Không tranh với user ở Option B tool layer.
4. Tạo checklist nghiệm thu ngay khi Full-CV backend branch sẵn sàng.
5. Bắt sớm các giả định frontend/API như `topK`, RAG wording, candidate/job identifiers, context warning và display score breakdown.

## Option A - miCareer-mini + API Contract Readiness

### Mục tiêu

Chuẩn bị client/UI/API readiness cho các thay đổi đã và sắp xảy ra:

1. `JobApplication Full-CV Chat`: response vẫn có `topK`, nhưng full-CV path có thể trả `topK = 0`; context warning có thể thay đổi; wording không nên nói fixed chunk RAG.
2. `P1-A/P1-B`: prompt/eval report có thể yêu cầu UI hiển thị source/evidence hoặc guardrail warning.
3. `JobPosting Agent Option B`: chưa có agent, nhưng client nên được audit để biết sau này cần surface nào cho job-level assistant.

### Scope

In scope:

- Đọc `miCareer-mini` nếu repo/project có trong workspace hoặc theo path user cung cấp.
- Tìm API calls tới FANG chat, NMAIex ranking và ingestion.
- Tìm UI text/labels giả định "RAG chunks", "top K", "semantic chunks", hoặc wording dễ sai sau full-CV.
- Kiểm tra client có phụ thuộc `topK > 0` không.
- Kiểm tra cách client hiển thị `contextWarning`, `model`, `modelMode`, `fallbackPath`, `latencyMs`.
- Kiểm tra flow ranking candidates theo job và link sang JobApplication chat.
- Viết UI/API smoke checklist để nghiệm thu Full-CV Chat khi backend xong.
- Viết "future readiness note" cho JobPosting read-only assistant: cần màn hình/entry point nào, data nào, và không cần làm gì ngay.

Out of scope:

- Không sửa FANG backend.
- Không implement JobPosting Agent.
- Không đổi schema API nếu chưa có backend owner duyệt.
- Không tự viết prompt/eval thay owner P1-A/P1-B.
- Không rewrite UI lớn nếu chưa có acceptance criteria.

### Deliverables

1. `agent_workflow_doc/current_workflow/MICAREER_MINI_API_READINESS_REPORT.md`
2. Danh sách API calls hiện tại: endpoint, request, response fields đang dùng.
3. Danh sách UI assumptions cần sửa hoặc theo dõi.
4. Smoke checklist cho `CHAT_FULL_CV`.
5. Future readiness note cho `JobPosting Agent`: entry point, expected API needs, risk.

### Acceptance Criteria

Hoàn thành khi report trả lời được:

1. Client hiện có gọi `/v2/chat/query` như thế nào?
2. Client có giả định `topK` là số chunk không?
3. Nếu backend trả `topK = 0`, UI có lỗi/hiểu sai không?
4. `contextWarning` hiện có được hiển thị hoặc bỏ qua?
5. UI có wording nào cần đổi từ "RAG/chunk" sang "Full CV context" không?
6. Ranking UI có thể là entry point tự nhiên cho JobPosting Assistant sau này không?
7. Cần smoke test thủ công nào khi Full-CV backend merge?

### Suggested Prompt to Give Member

```text
Bạn phụ trách miCareer-mini + API Contract Readiness cho FANG next phase.

Bối cảnh:
- CHAT_FULL_CV đang được owner khác implement: JobApplication chat sẽ chuyển từ fixed top-k chunk RAG sang full CV markdown context.
- P1-A/P1-B prompt review + minimal eval đang được owner khác làm.
- User sẽ trực tiếp làm JobPosting Agent Option B: read-only tool layer design/implementation planning.

Nhiệm vụ của bạn:
1. Rà soát miCareer-mini/client code và API usage liên quan FANG chat, ranking, ingestion.
2. Không sửa backend FANG và không implement JobPosting Agent.
3. Tìm mọi giả định UI/client về topK, RAG chunks, contextWarning, model/fallback/latency, jobAppId/jobPostId flow.
4. Viết report tiếng Việt tại agent_workflow_doc/current_workflow/MICAREER_MINI_API_READINESS_REPORT.md.
5. Report phải có: API usage map, UI wording/assumption list, CHAT_FULL_CV smoke checklist, future readiness note cho JobPosting read-only assistant.

Definition of done:
- Có file report.
- Có checklist nghiệm thu rõ cho CHAT_FULL_CV.
- Có danh sách rủi ro client/API cần owner backend biết.
- Không thay đổi backend FANG.
```

## Option B - Cross-workstream QA/Eval Harness Pack

### Mục tiêu

Tạo một QA/eval pack đứng ngoài code feature để nghiệm thu cả Full-CV Chat và JobPosting tool layer sau này.

### Scope

In scope:

- Viết test scenarios tiếng Việt cho `CHAT_FULL_CV`.
- Viết scenarios cho JobPosting read-only tools: ranking, search, summary, full CV drill-down, ATS history.
- Viết prompt injection cases từ CV/JD/email.
- Viết over-budget/large context cases.
- Viết expected behavior, không cần model output exact.

Out of scope:

- Không implement backend tests nếu owner chưa có branch.
- Không thay P1-A/P1-B eval rubric production.
- Không gọi LLM/API nếu chưa có môi trường.

### Deliverables

1. `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_CROSS_WORKSTREAM_QA_PACK.md`
2. Test case table cho Full-CV Chat.
3. Test case table cho JobPosting read-only tools.
4. Prompt injection and grounding cases.
5. Manual smoke flow.

### Khi nên chọn

Chọn nếu thành viên này không mạnh frontend nhưng cẩn thận, đọc spec tốt, và có thể viết checklist/test cases rõ.

## Option C - JobPosting Data Access, Permission and Audit Inventory

### Mục tiêu

Hỗ trợ user làm Option B bằng cách inventory dữ liệu, quyền truy cập và audit cần cho tool layer JobPosting.

### Scope

In scope:

- Đọc schema `JOBPOSTING`, `JOBAPPLICATION`, `CANDIDATE`, `INTERVIEW`, `INTERVIEWFEEDBACK`, `OFFER`, `EMAILLOG`, `CVPARSED`, `AIDOCUMENTCHUNK`.
- Map tool nào cần bảng nào.
- Xác định PII/sensitive fields.
- Đề xuất logging metadata cho tool call.
- Đề xuất permission assumptions: HR chỉ xem job thuộc company của mình, application thuộc job đó.

Out of scope:

- Không implement SQL/tool.
- Không thiết kế toàn bộ agent framework.
- Không sửa auth middleware.

### Deliverables

1. `agent_workflow_doc/current_workflow/JOBPOSTING_AGENT_DATA_PERMISSION_AUDIT_INVENTORY.md`
2. Data source map theo từng proposed tool.
3. PII/sensitive data risk list.
4. Permission assumption list.
5. Tool-call logging recommendation.

### Khi nên chọn

Chọn nếu thành viên này backend-minded và có thể đọc schema/code tốt. Việc này hữu ích trực tiếp cho user nhưng vẫn cần coordination để không duplicate phần Option B user đang làm.

## Option D - NMAIex Ranking Explainability Pack

### Mục tiêu

Chuẩn bị lớp giải thích ranking để sau này JobPosting Agent có thể trả lời "vì sao ứng viên này đứng top" mà không hallucinate.

### Scope

In scope:

- Đọc `nmaiex_ranking_service.py` và response `RankingResponse`.
- Giải thích các thành phần score: RRF, exact overlap, fuzzy overlap, skill score, seniority penalty.
- Đề xuất format display cho HR.
- Đề xuất mapping từ score breakdown sang natural-language explanation.

Out of scope:

- Không đổi công thức ranking.
- Không implement agent.
- Không làm tuning.

### Deliverables

1. `agent_workflow_doc/current_workflow/NMAIEX_RANKING_EXPLAINABILITY_PACK.md`
2. Score breakdown glossary.
3. Explanation templates.
4. Risks: overclaiming, clipped score, missing data.

### Khi nên chọn

Chọn nếu muốn tăng chất lượng sản phẩm cho JobPosting Agent về sau, nhưng ít khẩn cấp hơn Option A.

## Option E - JobPosting Agent Product Workflow Sketch

### Mục tiêu

Nghiên cứu workflow sản phẩm trước khi code: HR vào đâu, hỏi gì, output dạng chat/table/shortlist thế nào.

### Scope

In scope:

- Vẽ user journeys dạng text.
- Đề xuất entry points trong UI.
- Đề xuất screen states: ranking table, assistant panel, candidate drill-down, compare mode.
- Liệt kê câu hỏi HR thật sự sẽ hỏi.

Out of scope:

- Không thiết kế UI pixel-level.
- Không implement frontend/backend.
- Không chọn framework agent.

### Deliverables

1. `agent_workflow_doc/current_workflow/JOBPOSTING_AGENT_PRODUCT_WORKFLOW_SKETCH.md`
2. HR workflow scenarios.
3. UI entry point recommendation.
4. Open questions for user.

### Khi nên chọn

Chọn nếu user cần product clarity hơn technical readiness. Nếu mục tiêu hiện tại là giảm rủi ro nghiệm thu kỹ thuật, Option A vẫn tốt hơn.

## Option F - Implement JobPosting Agent/MCP/Framework

Không khuyến nghị.

Lý do:

1. User đã nhận Option B trực tiếp.
2. Tool contract chưa xong.
3. Full-CV chat và prompt/eval chưa merge.
4. MCP/framework lúc này dễ tạo architecture branch song song với decision chưa chốt.
5. Write tools chưa có permission/audit/human approval.

Chỉ nên xét lại sau khi có:

- Tool contract.
- Read-only tool implementation.
- Eval cases.
- Frontend/API readiness.
- User chọn framework/MCP cụ thể.

## Coordination Plan

Nếu chọn Option A, luồng phối hợp nên như sau:

1. Thành viên A `CHAT_FULL_CV` gửi expected response behavior: `topK`, `contextWarning`, error cases, changed docs.
2. Thành viên P1-A/P1-B gửi prompt/eval guardrail nào cần UI surface hoặc smoke test.
3. User gửi draft tool contract hoặc high-level tools cho JobPosting Option B khi có.
4. Thành viên còn lại cập nhật readiness report theo các input trên.

Không cần chờ tất cả input mới bắt đầu. Người này có thể audit client/API hiện tại trước.

## Questions for User

Bạn có thể trả lời một lượt để chọn hướng:

1. Thành viên còn lại mạnh hơn về frontend/client, backend/schema, hay QA/test?
2. `miCareer-mini` có nằm trong cùng workspace/repo không? Nếu có, path là gì?
3. Bạn muốn người này được phép sửa code frontend ngay hay chỉ viết readiness report trước?
4. Full-CV Chat khi backend xong có cần người này chạy UI smoke bằng browser không?
5. Bạn muốn readiness cho JobPosting Agent chỉ ở mức future note, hay cần người này đề xuất UI entry point cụ thể?
6. Có ưu tiên nào về thời hạn: cần report nhanh 1 ngày, hay có thể làm sâu 2-3 ngày?
7. Người này có được đọc/chạy DB local và Postman/smoke tests không?

## Final Recommendation

Chọn **Option A - miCareer-mini + API Contract Readiness** làm assignment mặc định cho thành viên còn lại.

Nếu người đó không có khả năng đọc frontend/client tốt, chuyển sang **Option B - Cross-workstream QA/Eval Harness Pack**. Nếu người đó mạnh backend/schema, chọn **Option C - JobPosting Data Access, Permission and Audit Inventory** để hỗ trợ trực tiếp cho user làm JobPosting Option B.


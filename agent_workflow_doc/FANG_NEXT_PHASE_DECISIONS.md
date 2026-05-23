# FANG Next Phase Decisions

## Brief

File này ghi lại các quyết định, workstream và điều cần cân nhắc được chốt sau buổi trao đổi về cách làm việc mới với GPT Plus/Codex, Antigravity và các model mạnh hiện có. Đây là bản ghi định hướng cho giai đoạn kế tiếp; các tài liệu work package riêng trong `agent_workflow_doc` mới là đề bài thực thi chi tiết cho từng cụm việc.

## Quyết định đã chốt

1. **P0 phải làm trước và dùng model tier 1.**
   - Mục tiêu không chỉ là audit mà là dựng lại "current reality" của repo, bóc drift code-doc, inventory AI/LLM và sinh backlog đủ rõ để model tier 2 hoặc thành viên nhóm thực thi.
   - Thứ tự hiện tại: P0-A trước, P0-B sau, user dùng tier 1 resolve conflict/decision từ hai đầu vào này, cuối cùng mới làm P0-C để cập nhật tài liệu theo quyết định đã rõ.
2. **Phân vai model theo tầng.**
   - Tier 1: GPT-5.5 hoặc Claude Opus 4.6 cho phân tích repo rộng, quyết định kiến trúc, tài liệu chỉ huy và review quan trọng.
   - Tier 2: GPT-5.4, Claude Sonnet 4.6, Gemini 3.5 Flash cho thực thi khi spec đã rõ.
   - Tier nhẹ/Copilot: hỏi nhanh, edit nhỏ, hỗ trợ theo đoạn code.
3. **Prompt engineering là workstream ưu tiên cao.**
   - P1-A review toàn bộ prompt theo task boundary, grounding, security, compliance, output contract và observability.
   - P1-B eval tối thiểu được giao cùng người làm P1-A để rubric và case đánh giá không bị tách rời.
4. **JobApplication chat sẽ bỏ fixed chunk-RAG.**
   - Chat trên một `JobApplication` sẽ dùng full CV markdown context vì CV đủ nhỏ, đầy đủ hơn top-k chunk và phù hợp bài toán một ứng viên.
   - Việc này cần một tài liệu tier 1 riêng trước khi giao cho một thành viên thực thi phần backend/docs/tests/UI liên quan.
   - Prompt engineering mức cơ bản trong luồng chat mới do người làm JobApplication Full-CV Chat tự đảm bảo trước; sau đó người phụ trách P1-A/P1-B sẽ hỗ trợ review/nâng cấp prompt và eval tối thiểu.
5. **P0-D không làm ngay từ đầu.**
   - Sau P0-A/P0-B, user dùng tier 1 resolve conflict và ra quyết định trước khi chạy P0-C.
   - Sau P0-C, user phân tích thêm ở mức vừa đủ để giao việc cho thành viên.
6. **JobPosting chat chưa được chốt thành feature phải làm.**
   - Cần một decision analysis riêng do tier 1 thực hiện.
   - Phải so sánh phương án dừng ở `AI Ranking + JobApplication Full-CV Chat` với phương án mở `JobPosting Agent`.
   - Thành viên còn lại sẽ chỉ được giao việc sau khi user nghiên cứu rõ hơn hướng JobPosting Agent hoặc chọn cụm việc khác, ví dụ UI/miCareer-mini/NMAIex.

## Workstream đã phân cụm

| Cụm | Owner dự kiến | Ghi chú |
|---|---|---|
| P0-A Repo Reality Audit | User + tier 1, tier 2 nếu có checklist hẹp | Làm đầu tiên bằng prompt trong tài liệu P0-A để có current reality và conflict map. |
| P0-B AI/LLM Inventory | User + tier 1 | Làm sau P0-A để bóc sâu toàn bộ điểm AI/LLM/prompt/model routing. |
| Conflict/Decision Resolve | User + tier 1 | Đọc P0-A và P0-B, chốt quyết định trước khi sửa docs. |
| P0-C Doc Reconciliation | User + tier 1 + tier 2 | Làm sau khi đã có P0-A/P0-B và quyết định conflict; tier 1 lập plan, tier 2 thực thi. |
| P1-A + P1-B Prompt Review + Minimal Eval | Một thành viên | Giao cùng một cụm sau P0-B/P0-C; người làm giữ chung rubric prompt và eval. |
| JobApplication Full-CV Chat | Một thành viên sau khi có guide tier 1 | Gộp feature, docs, tests và UI liên quan; phối hợp với người làm P1-A/P1-B cho prompt/eval. |
| JobPosting Agent Decision | User + tier 1 | Chưa giao implementation trước khi quyết định kiến trúc. |

* Cần lưu ý ở đây là trước khi chỉnh sửa tài liệu doc/strategy hoặc docs/guide ví dụ như bỏ RAG rag chat thì hãy đưa tài liệu cũ vào thư mục docs/archive

## P0-D và bước giao việc sau P0-C

P0-D không phải việc chạy độc lập ngay từ đầu. Nó là bước user dùng tier 1 để tổng hợp lại sau khi đã có P0-A, P0-B, conflict decisions và P0-C.

1. Đọc tài liệu và report từ P0-A, P0-B và P0-C.
2. Kiểm tra các conflict còn lại giữa code, docs, prompt rubric và hướng JobApplication chat.
3. Chốt roadmap tiếp theo theo work package ít phụ thuộc nhau.
4. Giao ngay hai cụm đã đủ rõ:
   - P1-A + P1-B cho một thành viên.
   - JobApplication Full-CV Chat cho một thành viên khác.
5. Giữ JobPosting Agent Decision cho user/tier 1 nghiên cứu thêm trước khi giao thành viên thứ ba.

## Ghi chú cho JobPosting Agent Decision

### Điều phải cân nhắc

1. Có thực sự cần nâng từ chat một `JobApplication` lên phạm vi một `JobPosting` không.
2. Nếu không làm, hệ thống giữ lõi gọn: AI Ranking + JobApplication Full-CV Chat + prompt quality work.
3. Nếu làm, đây không chỉ là đổi khóa từ `jobAppId` sang `jobPostId`; nó là một nhánh agent/tool architecture mới.
4. Kiến trúc mới có tách biệt được khỏi chat JobApplication và ranking hiện tại không.
   - Ưu tiên bảo toàn hai tính năng cũ.
   - Nếu tách được trong cùng source bằng module/service boundary rõ thì tốt.
   - Nếu `JobPosting Agent` dùng framework mới như LangGraph mà không kéo feature cũ vào refactor rủi ro thì càng đáng cân nhắc.

### MCP và retrieval

- Hướng tool-based retrieval có tiềm năng hơn fixed RAG cho phạm vi JobPosting: agent có thể tự quyết định dùng semantic search, text search, ranking, filter hay lấy full CV theo câu hỏi HR.
- Semantic search do agent gọi vẫn là retrieval-augmented generation; khác biệt là retrieval được agent điều phối bằng tools thay vì pipeline luôn kéo top-k cố định trước khi generate.
- MCP đáng cân nhắc nếu muốn expose bộ tool cho agent runtime/host khác nhau. Tuy nhiên quyết định đầu tiên vẫn là **domain tool layer của JobPosting Agent gồm tool nào, quyền hạn nào, input/output nào**.
- Domain logic nên nằm trong FANG services/tool interface. MCP nếu dùng nên là lớp adapter/exposure, không phải nơi business logic và SQL tùy hứng phình ra.
- Việc viết MCP server có thể là phần dễ hơn phần thiết kế tool an toàn. Vì vậy nếu tool layer ổn, MCP adapter nhỏ và hữu ích thì nên cân nhắc làm; không dùng độ dễ của MCP để bỏ qua tool boundary, permission và audit.

### Tool set khởi đầu nên cân nhắc

Read-only vertical slice trước:

1. `get_job_posting_context(job_post_id)`
2. `get_job_candidate_ranking(job_post_id, limit, filters)`
3. `search_job_applications_semantic(job_post_id, query, limit, filters)`
4. `search_job_applications_text(job_post_id, query, limit, filters)`
5. `get_job_application_summary(job_app_id)`
6. `get_job_application_full_cv(job_app_id)`
7. `get_candidate_ats_history(job_app_id)`

Tool filter/compare có thể đến sau:

1. Filter theo seniority, skill, location, work mode.
2. So sánh một tập `JobApplication` đã chọn.
3. Lấy ranking score breakdown để giải thích shortlist.

Tool ghi dữ liệu để sau cùng:

1. Draft interview plan/note/email trước.
2. Tool cập nhật ATS hoặc ghi dữ liệu phải có permission, human approval, audit log và failure semantics rõ.

## Framework/Research Decision còn mở

- User sẽ dùng tier 1 phân tích ADK, LangChain, LangGraph, MCP và có thể yêu cầu tier 1 sinh prompt cho Deep Research rồi phân tích kết quả trả về.
- Không đưa nhiều framework vào cùng một pha chỉ vì chúng đều liên quan agent.
- Quyết định framework phải xét:
  - tách khỏi tính năng cũ,
  - phù hợp tool boundary,
  - persistence/human approval nếu cần,
  - chi phí refactor và khả năng nhóm kiểm soát.

## Định nghĩa gốc các workstream

Các mã P0-A/P0-B/P0-C/P0-D/P1-A/P1-B là quy ước cho giai đoạn Next Phase của FANG. Mọi tài liệu `FANG_NEXT_PHASE_*` nên tham chiếu định nghĩa dưới đây khi dùng các mã này.

### P0 - Re-grounding and Direction

P0 là nhóm việc dựng lại nền quyết định cho FANG trước khi triển khai tính năng mới. P0 ưu tiên model tier 1 vì mục tiêu là đọc rộng, phát hiện drift/conflict, quyết định truth source và tạo tài liệu đủ rõ để người khác hoặc model tier 2 thực thi.

### P0-A - Repo Reality Audit

P0-A là audit hiện trạng toàn repo. Mục tiêu là xác định code hiện đang làm gì thật, feature nào implemented/partial/documented-only/stale, test nào có hoặc thiếu, và conflict nào cần user/tier 1 chốt. Output chính là current reality, feature map, code-doc drift map, risk list và work package gợi ý.

Tài liệu chi tiết: `agent_workflow_doc/FANG_NEXT_PHASE_P0A_REPO_REALITY_AUDIT.md`.

### P0-B - AI/LLM Inventory

P0-B là inventory toàn bộ điểm dùng AI/LLM/embedding/retrieval/prompt/model routing trong FANG. Mục tiêu là không bỏ sót use case trước khi review prompt, làm eval, refactor LLM layer hoặc đổi chat architecture. Output chính là bảng use case, prompt location index, model/fallback map, schema/output-contract map và risk/test gaps.

Tài liệu chi tiết: `agent_workflow_doc/FANG_NEXT_PHASE_P0B_AI_LLM_INVENTORY.md`.

### P0-C - Documentation Reconciliation

P0-C là chuẩn hóa tài liệu sau khi đã có P0-A/P0-B và các quyết định conflict cần thiết. Mục tiêu là xác định truth source, phân loại drift, lập plan cập nhật tài liệu và cho tier 2 thực thi theo checklist. P0-C không phải sửa docs theo cảm giác; mọi docs change lớn phải truy được về drift register hoặc quyết định đã chốt.

Tài liệu chi tiết: `agent_workflow_doc/FANG_NEXT_PHASE_P0C_DOC_RECONCILIATION.md`.

### P0-D - Synthesis and Work Assignment

P0-D là bước tổng hợp sau P0-A/P0-B/P0-C. User dùng model tier 1 để đọc các output/report, resolve phần còn mơ hồ còn lại, chia workstream ít phụ thuộc nhau và quyết định việc nào giao thành viên, việc nào giữ cho user/core owner, việc nào cần decision memo riêng.

Trong kế hoạch hiện tại, P0-D trước mắt dùng để giao hai việc đã rõ: P1-A/P1-B cho một thành viên và JobApplication Full-CV Chat cho một thành viên khác. JobPosting Agent vẫn là decision track riêng.

### P1-A - Prompt Review

P1-A là review toàn bộ prompt production-relevant dựa trên P0-B/P0-C và các quyết định mới. Rubric gồm task boundary, grounding, security, HR/compliance risk, output contract, validation/fallback và observability. P1-A không tự đổi architecture, nhưng phải chỉ ra prompt nào cần rewrite, prompt nào cần guardrail, và prompt nào cần decision từ user/tier 1.

Tài liệu chi tiết: `agent_workflow_doc/FANG_NEXT_PHASE_P1A_PROMPT_REVIEW_AND_MIN_EVAL.md`.

### P1-B - Minimal Eval

P1-B là eval tối thiểu đi kèm P1-A. Mục tiêu là có seed cases đầu tiên cho prompt/use case quan trọng, không xây platform eval lớn ngay. P1-B phải cùng owner với P1-A ở pha đầu để rubric review và test cases khớp nhau. Các use case ưu tiên gồm CV parser, JobApplication chat full-CV, NMAIex mapper và language proficiency normalization.

Tài liệu chi tiết: `agent_workflow_doc/FANG_NEXT_PHASE_P1A_PROMPT_REVIEW_AND_MIN_EVAL.md`.

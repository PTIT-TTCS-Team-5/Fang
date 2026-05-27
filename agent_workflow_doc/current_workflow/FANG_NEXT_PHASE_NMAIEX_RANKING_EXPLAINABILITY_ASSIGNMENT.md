# NMAIex Ranking Explainability Assignment

## Brief

Bạn phụ trách cụm **NMAIex Ranking Explainability Pack**.

Mục tiêu của cụm này là biến logic ranking hiện tại của NMAIex thành một lớp giải thích rõ ràng, nhất quán và an toàn cho HR, để sau này `JobPosting Agent` có thể trả lời các câu hỏi kiểu "vì sao ứng viên này đứng top", "điểm mạnh/yếu của ứng viên là gì", "score này đến từ đâu" mà không bịa hoặc diễn giải quá mức.

Đây là **workstream tài liệu/phân tích trước**, không phải workstream sửa công thức ranking, không implement JobPosting Agent, không implement MCP/LangGraph, không làm tuning.

Lý do chọn cụm này trước: user (Hưng) đang trực tiếp làm `JobPosting Agent Option B - Design-first + Read-only Tool Layer`. Option C trong tài liệu phân việc cũng hữu ích, nhưng cần phối hợp sát với tool-layer workstream nên dễ tốn coordination. Explainability pack ít conflict hơn, vẫn hỗ trợ trực tiếp cho JobPosting Agent về sau, và có thể làm độc lập với quỹ thời gian hạn hẹp.

## Cách đọc tài liệu

Đọc theo thứ tự dưới đây trước khi viết report:

1. `agent_workflow_doc/README.md`
2. `agent_workflow_doc/KINH_NGHIEM.md`
3. `agent_workflow_doc/current_workflow/rule.md`
4. `README.md`
5. `docs/system_architecture.md`
6. `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_DECISIONS.md`
7. `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_UNASSIGNED_MEMBER_ASSIGNMENT_OPTIONS.md`
8. `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_JOBPOSTING_AGENT_DECISION_ANALYSIS.md`
9. `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_JOBPOSTING_OPTION_B_IMPLEMENTATION_ADVISORY.md`
10. NMAIex docs:
    - `docs/strategy/nmaiex_ranking_strategy.md`
    - `docs/guide/nmaiex_ranking_guide.md`
11. Code entry points:
    - `app/api/nmaiex_routes_ranking.py`
    - `app/services/nmaiex_ranking_service.py`
    - `app/models/nmaiex_schemas.py`
    - `app/core/nmaiex_config.py`
    - `database/schema_web_core.sql`
    - `database/schema_ai_core.sql`

Nếu cần truy vết lịch sử audit, đọc thêm:

- `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_P0A_REPO_REALITY_AUDIT_REPORT.md`
- `agent_workflow_doc/current_workflow/P0B_AI_LLM_INVENTORY_REPORT.md`
- `agent_workflow_doc/current_workflow/P0C_DOC_RECONCILIATION_PLAN.md`

## Nguồn chuẩn

1. Code hiện tại là truth source cho ranking formula và response shape.
2. `docs/strategy/nmaiex_ranking_strategy.md` và `docs/guide/nmaiex_ranking_guide.md` là docs nền, nhưng nếu lệch code thì phải ghi rõ drift.
3. `FANG_NEXT_PHASE_JOBPOSTING_AGENT_DECISION_ANALYSIS.md` là nguồn chuẩn cho định hướng JobPosting Agent: hiện mới làm read-only tool layer, chưa làm agent runtime.
4. `FANG_NEXT_PHASE_JOBPOSTING_OPTION_B_IMPLEMENTATION_ADVISORY.md` là nguồn chuẩn cho tool layer mà user đang trực tiếp làm.
5. Không dùng `docs/research` hoặc `archive` làm runtime truth.

## Scope bắt buộc

### 1. Giải thích ranking J->C hiện tại

Phân tích luồng `rank_candidates_for_job()` trong `app/services/nmaiex_ranking_service.py`.

Cần giải thích tối thiểu:

1. Input của ranking: `job_id`, `limit`, `province_id`, `work_mode`.
2. Data source dùng trong query:
   - `JOBPOSTING`
   - `JOBREQUIREMENT`
   - `JOB_LEVEL_MAP`
   - `JOBAPPLICATION`
   - `AIDOCUMENTCHUNK`
   - `CVPARSED`
   - `CANDIDATE`
   - `CANDIDATESKILL`
   - raw skill vector tables nếu liên quan.
3. RRF score là gì trong code hiện tại.
4. Exact skill overlap là gì.
5. Fuzzy skill overlap là gì.
6. Skill score và `skill_alpha` hoạt động thế nào.
7. Seniority penalty hoạt động thế nào.
8. `match_score` được tổng hợp từ các thành phần nào.
9. Response hiện trả những field gì qua `RankingResponse` / `CandidateRankResult` / `ScoreBreakdown`.

### 2. Viết glossary cho score breakdown

Tạo glossary tiếng Việt cho từng thành phần score để HR/dev đọc được:

1. `match_score`
2. `rrf_score`
3. `exact_overlap`
4. `fuzzy_overlap`
5. `skill_score`
6. `skill_alpha`
7. `seniority_penalty`
8. `hard_filter_passed`
9. Các field C->J nếu có thời gian: `text_score`, `title_score`, `salary_adjustment`, `lang_penalty`, `lang_bonus`, `lang_breakdown`.

Với mỗi field, cần có:

- Ý nghĩa ngắn gọn.
- Nguồn dữ liệu.
- HR nên hiểu như thế nào.
- Điều không nên suy diễn.
- Rủi ro/missing-data caveat.

### 3. Đề xuất explanation templates

Đề xuất template tự nhiên bằng tiếng Việt để sau này UI hoặc JobPosting Agent dùng.

Tối thiểu có các template:

1. Giải thích vì sao một ứng viên đứng top.
2. Giải thích điểm mạnh chính của ứng viên theo ranking.
3. Giải thích điểm yếu/rủi ro theo ranking.
4. Giải thích skill match.
5. Giải thích seniority fit/risk.
6. Giải thích khi thiếu dữ liệu hoặc score không đáng tin.
7. Giải thích khi hai ứng viên có score gần nhau.

Các template phải tránh overclaiming. Không được biến ranking score thành quyết định tuyển dụng tuyệt đối.

### 4. Đề xuất mapping từ score breakdown sang explanation

Không chỉ viết glossary; cần đề xuất rule mapping cụ thể.

Ví dụ dạng:

- Nếu `skill_score` cao và `seniority_penalty = 0`, explanation có thể nói ứng viên phù hợp tốt về skill và seniority.
- Nếu `exact_overlap` thấp nhưng `fuzzy_overlap` cao, explanation phải nói matching dựa nhiều vào kỹ năng tương đương/semantic, cần HR kiểm tra lại evidence.
- Nếu `seniority_penalty` cao, explanation phải nói có rủi ro thiếu hoặc vượt seniority tùy logic code.
- Nếu ranking thiếu CV/chunk/skill data, explanation phải hạ độ tự tin.

Không cần implement code, nhưng rule phải đủ rõ để sau này user hoặc tier 2 chuyển thành function.

### 5. Phân tích risk khi dùng explanation cho JobPosting Agent

Cần nêu rõ:

1. Ranking score không phải quyết định tuyển dụng.
2. Score breakdown là tín hiệu hỗ trợ, không thay thế review CV/phỏng vấn.
3. Fuzzy skill có thể match sai hoặc quá rộng.
4. Text/vector rank có thể bị ảnh hưởng bởi CV wording/chunk quality.
5. Seniority penalty phụ thuộc `expyears` và job level mapping.
6. Missing data phải được nói rõ thay vì tự tin giả.
7. Không suy luận đặc điểm nhạy cảm.
8. Nếu dùng trong agent, agent phải phân biệt score-derived explanation và evidence từ CV/ATS.

## Scope nên giữ nhỏ

Không làm các việc sau:

1. Không sửa công thức ranking.
2. Không tuning weight.
3. Không bỏ hoặc thêm score clipping.
4. Không implement JobPosting Agent.
5. Không implement MCP/LangGraph/adapter.
6. Không sửa UI/frontend.
7. Không gọi LLM để generate explanation production.
8. Không tạo eval platform lớn.
9. Không sửa DB schema.

Nếu trong quá trình đọc code phát hiện bug hoặc drift lớn, ghi vào report dưới mục `Findings / Follow-up`, không tự sửa nếu chưa được giao.

## Deliverables

Tạo report/tài liệu bằng tiếng Việt.

### 1. Main report

Đề xuất file:

`agent_workflow_doc/current_workflow/NMAIEX_RANKING_EXPLAINABILITY_PACK.md`

Nội dung bắt buộc:

1. Executive summary.
2. Current ranking flow J->C.
3. Score breakdown glossary.
4. Explanation template set.
5. Mapping rules từ score breakdown sang explanation.
6. Missing-data and confidence policy.
7. Risks and anti-overclaiming rules.
8. Recommendation cho JobPosting Agent Option B.
9. Open questions cho user.

### 2. Optional concise handoff section

Trong cùng report, thêm mục `Implementation Handoff Notes` nếu có thể:

1. Function/module gợi ý nếu sau này implement explanation builder.
2. Input/output gợi ý cho explanation function.
3. Test cases tối thiểu.
4. Field nào cần JobPosting tool layer trả thêm, ví dụ `jobAppId`, raw evidence snippets, missing-data warnings.

Không cần tạo code patch.

## Acceptance criteria

1. Report có thể đọc độc lập mà không cần mở code ngay.
2. Mỗi thành phần score quan trọng có glossary rõ.
3. Explanation templates không overclaim và không ra quyết định tuyển dụng tuyệt đối.
4. Mapping rules đủ cụ thể để sau này implement thành deterministic helper.
5. Có phân biệt rõ:
   - score-derived explanation,
   - CV evidence,
   - ATS evidence,
   - HR decision.
6. Có nêu missing-data/confidence policy.
7. Có link/file references tới code/docs liên quan.
8. Không implement agent, không sửa ranking formula.
9. Có open questions cho user nếu phát hiện điểm cần quyết định.

## Phối hợp với user làm JobPosting Option B

User đang làm `JobPosting Agent Option B - Design-first + Read-only Tool Layer`.

Bạn cần hỗ trợ bằng cách chỉ ra:

1. Tool `get_job_candidate_ranking` nên trả thêm field nào để explanation tốt hơn.
2. Ranking response có đủ `jobAppId` để drill-down không.
3. Tool layer nên trả warnings nào để agent biết khi score thiếu tin cậy.
4. Explanation nên được build deterministic ở service layer hay để agent tự viết.

Khuyến nghị hiện tại: explanation core nên là deterministic helper hoặc template-based helper ở service layer. Agent chỉ diễn đạt lại trong phạm vi đã được cung cấp, không tự bịa rationale từ score.

## Suggested prompt để giao trực tiếp

```text
Bạn phụ trách NMAIex Ranking Explainability Pack cho FANG.

Bối cảnh:
- CHAT_FULL_CV và P1-A/P1-B đã có owner riêng.
- User đang trực tiếp làm JobPosting Agent Option B: read-only tool layer.
- Cụm của bạn hỗ trợ JobPosting Agent về khả năng giải thích ranking, nhưng không implement agent và không sửa công thức ranking.

Nhiệm vụ:
1. Đọc docs/code liên quan NMAIex ranking theo assignment.
2. Viết report tiếng Việt tại:
   agent_workflow_doc/current_workflow/NMAIEX_RANKING_EXPLAINABILITY_PACK.md
3. Report phải có executive summary, ranking flow, glossary score breakdown, explanation templates, mapping rules, missing-data/confidence policy, risks và handoff notes cho JobPosting Option B.
4. Không sửa backend formula, không tuning, không implement JobPosting Agent/MCP/LangGraph.

Definition of done:
- Có report đủ để user/agent sau này chuyển thành explanation helper.
- Có file references rõ.
- Có open questions nếu phát hiện điểm cần user quyết định.
- Không thay đổi code production trừ khi được giao thêm.
```

## Open questions cho người nhận việc

Khi làm report, nếu chưa rõ thì ghi vào mục open questions:

1. `match_score` hiện tại nên được giải thích là điểm tương đối trong job hay điểm tuyệt đối?
2. Có cần hiển thị từng thành phần score cho HR hay chỉ dùng nội bộ để tạo explanation?
3. `fuzzy_overlap` có cần kèm caveat bắt buộc không?
4. Khi `seniority_penalty` cao, wording nên phân biệt thiếu seniority và overqualified như thế nào?
5. Nếu thiếu CV/chunk/skill data, ranking result hiện có đủ metadata để cảnh báo không?
6. JobPosting tool layer có nên trả `confidence` hoặc `explanationWarnings` không?
7. Nên implement explanation builder ở NMAIex service hay JobPosting tool service sau này?


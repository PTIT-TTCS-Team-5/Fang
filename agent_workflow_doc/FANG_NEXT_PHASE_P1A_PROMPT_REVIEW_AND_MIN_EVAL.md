# P1-A/B Assignment - Prompt Review and Minimal Eval

> [!IMPORTANT]
> Trạng thái handoff: **tạm stall** cho tới khi user/tier 1 duyệt xong LLM safety precheck trong `agent_workflow_doc/FANG_NEXT_PHASE_LLM_SAFETY_PRECHECK_REPORT.md`. Không giao task này cho thành viên trước khi bổ sung safety/adversarial rubric vào scope thực thi.
>
> HR chat abuse eval đã mô phỏng JobApplication chat với model cheap `openai/gpt-4.1-nano`: kịch bản system prompt yếu có **3/6 case `unsafe_or_needs_review`**, kịch bản có guardrail còn **1/6 case `unsafe_or_needs_review`**. Xem `agent_workflow_doc/HR_CHAT_ABUSE_GUARDRAIL_EVAL_REPORT.md` và `agent_workflow_doc/HR_CHAT_ABUSE_GUARDRAIL_EVAL_RESULTS.json`. Đây là evidence trực tiếp rằng nếu HR chat không có scope/guardrail rõ, user có thể abuse luồng chat để yêu cầu code vi phạm ToS, thu thập secret, giám sát hoặc làm theo prompt injection trong CV.

## Brief

Bạn phụ trách cụm `P1_A_B_inc`: P1-A Prompt Review và P1-B Minimal Eval cho FANG.
Mục tiêu của cụm này là rà toàn bộ prompt production-relevant trong FANG, đánh giá rủi ro theo rubric đã chốt, đề xuất rewrite cho prompt ưu tiên cao và tạo bộ eval seed tối thiểu để các thay đổi prompt có cách kiểm tra thực tế.

P1-A và P1-B được giao cùng một owner để rubric review và test cases không bị lệch nhau.

## Cách đọc tài liệu

Đọc theo thứ tự dưới đây trước khi sửa code hoặc viết report:

1. `agent_workflow_doc/README.md`
2. `agent_workflow_doc/KINH_NGHIEM.md`
3. `README.md`
4. `../miCareer-mini/README.md`
5. `docs/system_architecture.md`
6. `agent_workflow_doc/FANG_NEXT_PHASE_DECISIONS.md`
7. `agent_workflow_doc/FANG_NEXT_PHASE_P0A_USER_NOTE_TRIAGE.md`
8. `agent_workflow_doc/P0B_AI_LLM_INVENTORY_REPORT.md`
9. `agent_workflow_doc/P0C_DOC_RECONCILIATION_PLAN.md`
* NOTE FROM HƯNG: Cái 6-7-8-9 này khuyên ng ae dùng AI để hỗ trợ đọc hiểu nhé
10. `agent_workflow_doc/FANG_NEXT_PHASE_LLM_SAFETY_PRECHECK_REPORT.md`
11. Các strategy/guide liên quan:
* NOTE FROM HƯNG: Cái này cũng thế, hoặc đọc thủ công có chọn lọc
    - `docs/strategy/rag_query_strategy.md`
    - `docs/guide/rag_query_guide.md`
    - `docs/strategy/integration_strategy.md`
    - `docs/strategy/nmaiex_ranking_strategy.md`
    - `docs/guide/nmaiex_ranking_guide.md`
    - `docs/strategy/embedding_strategy.md`
    - `docs/guide/embedding_guide.md`

Nếu cần truy vết các note ban đầu của user (Hưng), đọc thêm `agent_workflow_doc/FANG_NEXT_PHASE_P0A_REPO_REALITY_AUDIT_REPORT.md` và tìm `P1_A_B_inc`.
* NOTE FROM HƯNG: Ý ở đây là ae vào file đó rồi Ctrl + f tìm mã, chỗ nào mình đánh mã là mình chỉ đinh/comment đó là phần việc của b

## Nguồn chuẩn

1. Prompt/model/use-case inventory: `agent_workflow_doc/P0B_AI_LLM_INVENTORY_REPORT.md`.
2. Quyết định phân việc và constraint: `agent_workflow_doc/FANG_NEXT_PHASE_DECISIONS.md`.
3. Phần user đã gán cho `P1_A_B_inc`: `agent_workflow_doc/FANG_NEXT_PHASE_P0A_USER_NOTE_TRIAGE.md`.
4. Safety precheck: `agent_workflow_doc/FANG_NEXT_PHASE_LLM_SAFETY_PRECHECK_REPORT.md`.
5. Code hiện tại vẫn là truth source khi docs và code mâu thuẫn
* NOTE FROM HƯNG: Đã resolve hầu hết mâu thuân. Docs - code đã chuẩn

## Phạm vi bắt buộc

Review các prompt production-relevant trong P0-B Appendix B:
xem: agent_workflow_doc\P0B_AI_LLM_INVENTORY_REPORT.md
1. `P1` - CV Parse Prompt.
2. `P2` - Anthropic Schema Prompt.
3. `P3` - HR Co-pilot System Prompt.
4. `P4` - Chat Summarization Prompt.
5. `P5` - Chat Branch Summarization Prompt.
6. `P6` - Province Mapping Prompt.
7. `P7` - Skill Mapping Prompt.
8. `P8` - Proficiency Normalization Prompt.

Prompt synthetic/dev tooling (`P9`, `P10`) chỉ review nếu nó ảnh hưởng trực tiếp tới dữ liệu eval/ranking.

## Ưu tiên xử lý

1. HR Co-pilot System Prompt, vì luồng này sẽ đổi sang full CV markdown trong `CHAT_FULL_CV`.
2. CV Parse Prompt, vì đây là pipeline dữ liệu đầu vào cho toàn hệ thống.
3. NMAIex Skill Mapping, Province Mapping và Proficiency Normalization, vì lỗi mapping ảnh hưởng ranking.
4. Summarization/Branch prompts, vì liên quan context continuity và context budget.

## Rubric review

Mỗi prompt cần được đánh giá theo các tiêu chí sau:

1. **Task boundary**: model được làm gì, không được làm gì, có tự ý ra quyết định HR tuyệt đối không.
2. **Grounding**: evidence nằm ở đâu, thiếu dữ liệu thì trả lời thế nào, có tách evidence và inference không.
3. **Security**: CV/JD/ATS/chat history có được coi là untrusted input không, có chống prompt injection và data exfiltration không.
4. **HR/compliance risk**: có suy đoán nhạy cảm, đánh giá thiếu căn cứ, hoặc khuyến nghị tuyển dụng tuyệt đối không.
5. **Output contract**: free text/JSON/schema có rõ không, code validation/fallback có khớp prompt không.
6. **Operational quality**: có versioning, observability, log/eval trace, test case và fallback behavior chưa.

## Phần việc được gán từ P0-A

Các mục sau là phần việc của `P1_A_B_inc`:

1. Review prompt engineering cho multi-source RAG context, bao gồm skills, Offer/Email content và các nguồn context mới.
2. Review context window management cho luồng chat mới: warning, hard-stop behavior, summarize/branch option và per-model budget.
3. Đề xuất per-model context budget map nếu khối lượng vẫn kiểm soát được; nếu quá tải, tách thành open question cho Hưng.
4. Tạo eval tối thiểu cho parser, JobApplication full-CV chat, NMAIex mapper và language proficiency normalization.
5. Bổ sung rubric và seed cases cho prompt injection/jailbreak/adversarial attacks, đặc biệt là indirect prompt injection từ CV/JD/email/ATS.

Lưu ý: `CHAT_FULL_CV` là người implement feature chuyển chat sang full CV. Bạn hỗ trợ review prompt/eval cho luồng mới, nhưng không tự đổi retrieval architecture nếu chưa nằm trong scope của task bạn đang làm.

## Deliverables

Tạo report và tài liệu strategy-level bằng tiếng Việt, có file references rõ. Không chỉ giao code patch hoặc nhận xét rời rạc.

1. **Prompt review report**
   - Bảng prompt/use case.
   - Điểm rủi ro theo rubric.
   - File refs và dòng/hàm liên quan.
   - Mức ưu tiên nâng cấp.
2. **Prompt strategy-level document**
   - Định nghĩa prompt policy cho FANG: grounding, untrusted input, HR/compliance, output contract, fallback, safety refusal và observability.
   - Nêu rõ prompt nào là current behavior, prompt nào là target design, prompt nào cần user/tier 1 quyết định.
   - Chất lượng tối thiểu phải tương đương tài liệu trong `docs/strategy/`: có bối cảnh, quyết định, trade-off, scope, risks và acceptance criteria.
3. **Prompt redesign proposals**
   - Không cần rewrite tất cả.
   - Với prompt priority cao phải có draft prompt mới hoặc rewrite spec đủ rõ.
4. **Minimal eval plan + seed cases**
   - Format case.
   - Rubric/assertions.
   - Case tối thiểu cho các prompt priority cao.
   - Adversarial seed cases cho direct harmful request, roleplay jailbreak, authority override, translation/encoding bypass, partial code completion và indirect prompt injection.
5. **Open questions**
   - Những điểm cần Hưng quyết định trước khi đổi behavior hoặc kiến trúc.

Đề xuất nơi đặt output:

- `agent_workflow_doc/P1A_B_PROMPT_REVIEW_REPORT.md`
- `docs/strategy/prompt_engineering_strategy.md`
- `agent_workflow_doc/P1B_MINIMAL_EVAL_SEED_CASES.md`

## Eval seed tối thiểu

Bắt đầu bằng seed cases nhỏ, không xây eval platform lớn ngay:

1. CV parser:
   - field có trong CV phải extract được,
   - field không có không được bịa,
   - CV mơ hồ/lỗi phải có warning hoặc failure behavior đúng policy.
2. JobApplication full-CV chat:
   - trả lời từ full CV/JD/ATS context,
   - nói thiếu dữ liệu khi không có evidence,
   - không làm theo instruction độc hại nằm trong CV/JD/email text.
3. NMAIex mapper:
   - province mapping exact/ambiguous/unmatched cases,
   - skill mapping exact/unmatched/hallucinated-id cases,
   - language proficiency normalization cases.

## Parser quality note

Parser hiện đã có `parserSelfReport`. Khi đề xuất cải tiến prompt/quality gate:

1. Tách rõ tín hiệu model tự báo và tín hiệu deterministic validator xác nhận.
2. Không coi self-reported confidence là chân lý duy nhất.
3. Đề xuất policy kết hợp prompt, schema, warning fields, quality gate và escalation.

## Không làm trong scope này

1. Không tự đổi provider/router/framework.
2. Không tự implement JobPosting Agent.
3. Không tự chuyển JobApplication chat sang full CV nếu task hiện tại không phải `CHAT_FULL_CV`.
4. Không rewrite prompt production mà không có risk analysis và eval/test đi kèm.
5. Không dùng `docs/research` hoặc tài liệu archive làm current runtime truth.

## Acceptance criteria

1. Không bỏ sót prompt production-relevant đã có trong P0-B.
2. Mỗi nhận xét chính có file reference và rubric reason.
3. Có eval seed thực tế cho prompt priority cao, không chỉ backlog chung chung.
4. JobApplication full-CV chat có prompt/eval guidance đủ để phối hợp với owner `CHAT_FULL_CV`.
5. Parser confidence/warning idea được phân tích với guardrail rõ.
6. Có report và ít nhất một tài liệu strategy-level đủ chất lượng để team dùng lại sau này.

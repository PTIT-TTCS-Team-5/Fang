# Prompt For Tier 1: Write C3 Planning Brief

## How To Use

Copy toàn bộ prompt này sang một đoạn chat tier 1 mới, dùng GPT-5.5 high hoặc Claude Opus high. Sau prompt này, user sẽ dán thêm quyết định cá nhân dài về tài liệu `FANG_NEXT_PHASE_JOBPOSTING_OPTION_C3_DEEP_ADVISORY.md`.

Mục tiêu của tier 1 trong lượt này **không phải code** và **không phải viết implementation plan cuối cùng**. Mục tiêu là viết một bản **C3 Planning Brief / Decision Lock** đủ rõ để sau đó tách các workstream tier 1 WS-A/B/C/D.

## Role

Bạn là tier 1 architecture/planning agent cho dự án FANG. Nhiệm vụ của bạn là đọc bối cảnh hiện có, đọc quyết định của user, rồi viết một tài liệu chỉ huy ngắn-gọn-nhưng-đủ-chặt cho hướng **JobPosting Agent Option C3 + Dedicated JobPosting Conversation Tables**.

Bạn phải làm việc như một senior architect:

1. Phân biệt rõ decision đã khóa với decision còn mở.
2. Không tự implement.
3. Không tự mở scope sang write tools, MCP, LangGraph hoặc generalized chat refactor nếu user chưa khóa.
4. Tạo tài liệu đủ rõ để các tier 1 khác chạy discovery workstream song song mà không hiểu lệch hướng.

## Required Reading

Đọc các tài liệu sau trước khi viết:

1. `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_JOBPOSTING_OPTION_C3_DEEP_ADVISORY.md`
2. `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_JOBPOSTING_OPTION_C_IMPLEMENTATION_ADVISORY.md`
3. `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_JOBPOSTING_AGENT_DECISION_ANALYSIS.md`
4. `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_JOBPOSTING_OPTION_B_IMPLEMENTATION_ADVISORY.md`
5. `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_DECISIONS.md`
6. `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_P0A_USER_NOTE_TRIAGE.md`
7. `agent_workflow_doc/KINH_NGHIEM.md`

Đọc code/schema hiện tại ở mức vừa đủ để tránh hallucination:

1. `app/services/rag_orchestrator.py`
2. `app/services/rag_model_adapters.py`
3. `app/models/chat.py`
4. `app/services/rag_query.py`
5. `app/services/nmaiex_ranking_service.py`
6. `database/schema_ai_core.sql`
7. `database/schema_web_core.sql`

Nếu line references drift, ưu tiên code hiện tại.

## User Decision Context

User đang nghiêng về:

1. Chọn **Option C3 - Read-only JobPosting Agent Vertical Slice + Dedicated JobPosting Conversation Tables**.
2. Muốn HR đứng ở màn hình `JobPosting`, bên phải có cửa sổ chat.
3. Chat nằm trong phạm vi một `JobPosting`, không phải một `JobApplication`.
4. LLM/agent có thể nhớ ngữ cảnh hội thoại, tự gọi tool hệ thống, và trả lời có grounding.
5. Ví dụ user muốn:
   - HR hỏi: "Phân tích 10 ứng viên rank cao nhất" -> agent gọi ranking tool với `limit=10`, lấy context phù hợp, phân tích cho HR.
   - HR hỏi tiếp: "Trong 10 ông này lọc ra phải có tiếng Anh hạng C trở lên" -> agent nhớ working set top 10 trước, lọc hoặc gọi tool phù hợp.
   - HR hỏi: "So sánh tất cả ứng viên" -> agent biết tập quá lớn, ví dụ 789 `JobApplication`, nên không so sánh bừa mà tư vấn HR dùng rank/filter/top N.
6. User hiểu đây là module lớn và muốn dùng pipeline nhiều agent:
   - đầu tiên tier 1 viết C3 Planning Brief / Decision Lock;
   - sau đó các tier 1 chạy WS-A/B/C/D song song;
   - sau đó một tier 1 synthesize thành Official Implementation Plan;
   - cuối cùng mới viết Work Plan điều phối tier 1/tier 2 code.

User sẽ dán thêm một đoạn quyết định cá nhân dài sau prompt này. Bạn phải xem đoạn đó là input ưu tiên cao hơn các khuyến nghị cũ nếu có conflict.

## Main Task

Viết tài liệu:

`agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_JOBPOSTING_C3_PLANNING_BRIEF.md`

Tài liệu này là **Planning Brief / Decision Lock**, không phải implementation plan cuối cùng.

Nó phải trả lời:

1. C3 sẽ được hiểu chính xác là gì trong FANG.
2. Những quyết định nào user đã khóa.
3. Những quyết định nào vẫn mở và cần WS-A/B/C/D phân tích.
4. Workstream discovery tier 1 nào cần chạy song song.
5. Output expected của từng workstream là gì.
6. Điều gì tuyệt đối không được tự ý làm trong các workstream.
7. Sau WS-A/B/C/D, tier 1 synthesis cần tạo Official Implementation Plan như thế nào.

## Required Output Structure

Tài liệu phải có cấu trúc sau.

### 1. Executive Summary

Viết ngắn nhưng đủ quyết định:

- User chọn C3 direction.
- Dedicated JobPosting conversation tables là hướng ưu tiên.
- Agent runtime/controller là bắt buộc nếu muốn LLM tự gọi tool.
- Tool layer read-only là bắt buộc.
- Không write tools phase đầu.
- Không full framework/MCP/LangGraph nếu chưa được WS-A quyết định.
- Tài liệu này là Planning Brief, không phải Implementation Plan.

### 2. Decision Lock

Liệt kê các quyết định đã khóa.

Ví dụ các quyết định có thể khóa nếu không bị user decision override:

1. C3 scope là JobPosting-scoped read-only assistant.
2. Conversation target là `jobPostId`.
3. Không reuse trực tiếp `AICHATCONVERSATION` theo `jobAppId`.
4. Dedicated tables được ưu tiên.
5. Agent phải có memory/state đủ để hiểu working set như "10 ông này".
6. Agent không được bulk load full CV.
7. Agent không được write ATS/email/offer/status.
8. Agent phải biết guardrail khi request quá lớn.

### 3. Current Reality Constraints

Tóm tắt code reality cần chú ý:

1. `invoke_generation()` hiện chỉ text generation, chưa có native tool-calling runtime.
2. Chat hiện tại theo `jobAppId`.
3. NMAIex ranking J->C đã có nhưng output có thể chưa đủ `jobAppId` cho drill-down.
4. `CVPARSED`, `AIDOCUMENTCHUNK`, ATS tables có thể làm tool source.
5. Full-CV Chat đang có owner khác, nên C3 phải phối hợp/reuse logic khi có.
6. P1-A/P1-B prompt/eval đang có owner khác, nên C3 phải lấy guardrails/eval input từ họ.

### 4. Desired End State

Mô tả end state bằng ngôn ngữ product + technical:

- HR chat pane bên phải màn hình JobPosting.
- Conversation scoped by `jobPostId`.
- Agent nhớ previous turns và working set.
- Agent có tool registry và controller loop.
- Agent trả lời dựa trên tool results/source metadata.
- Agent biết giới hạn khi câu hỏi quá lớn.

### 5. Non-Goals For Phase 1

Phải ghi rõ:

1. Không write tools.
2. Không auto-send email.
3. Không update application status.
4. Không generate offer/note rồi ghi DB.
5. Không support compare all candidates nếu tập lớn.
6. Không generalized all-entity chat.
7. Không refactor toàn bộ chat architecture hiện tại.
8. Không multi-provider tool calling đầy đủ nếu chưa có quyết định riêng.

### 6. Discovery Workstreams

Định nghĩa rõ 4 workstream tier 1 song song.

#### WS-A - Agent Runtime and Tool Calling Decision

Phải trả lời:

- Native tool calling hay JSON-loop controller?
- Một provider/model agent riêng hay reuse `modelMode` hiện tại?
- Tool call schema, max steps, failure semantics.
- Agent runtime file/module boundary.
- Khi nào cần LangGraph/MCP, nếu có.

Output:

- `FANG_NEXT_PHASE_JOBPOSTING_C3_WSA_AGENT_RUNTIME_DECISION.md`

#### WS-B - Dedicated Conversation Tables and Memory State

Phải trả lời:

- Table design cho conversation/message/tool-call/state.
- Có cần `AIJOBPOSTINGCHATSTATE` không?
- State JSON gồm gì: working set, filters, last ranking ids, summaries.
- Retention/summarization strategy.
- Migration risk.

Output:

- `FANG_NEXT_PHASE_JOBPOSTING_C3_WSB_CONVERSATION_MEMORY_SCHEMA.md`

#### WS-C - Read-only Tool Contract and Data Scope

Phải trả lời:

- Tool list MVP.
- Input/output schema.
- Source metadata/warnings.
- Full CV policy.
- Count/too-large guardrail.
- English/language filter feasibility.
- How to avoid data leak outside `jobPostId`.

Output:

- `FANG_NEXT_PHASE_JOBPOSTING_C3_WSC_TOOL_CONTRACT.md`

#### WS-D - Product/API/UI Contract

Phải trả lời:

- Route namespace.
- Request/response schema.
- Frontend chat pane needs.
- Conversation history endpoints.
- How UI displays used tools/source/latency/warnings.
- Postman/manual smoke flows.

Output:

- `FANG_NEXT_PHASE_JOBPOSTING_C3_WSD_API_UI_CONTRACT.md`

### 7. Cross-Workstream Conflict Points

Liệt kê các conflict chắc chắn cần synthesis:

1. Runtime tool format vs tool contract.
2. Memory state shape vs UI/API response.
3. Dedicated table schema vs route persistence.
4. Full CV helper dependency on Full-CV owner.
5. Language filter expectation vs current normalized data reality.
6. Model/provider choice vs existing fallback architecture.

### 8. Synthesis Step

Chỉ rõ sau WS-A/B/C/D, một tier 1 phải viết:

`FANG_NEXT_PHASE_JOBPOSTING_C3_OFFICIAL_IMPLEMENTATION_PLAN.md`

Implementation Plan chính thức phải bao gồm:

1. final architecture;
2. schema migrations;
3. file/module creation list;
4. function/class contracts;
5. route contracts;
6. agent runtime loop;
7. state/memory design;
8. tool registry;
9. testing and eval plan;
10. rollout order;
11. risks/deferred items.

### 9. Later Work Plan

Nói rõ Work Plan chỉ viết sau Official Implementation Plan.

Work Plan sẽ chia code tasks cho tier 1/tier 2:

- DB/persistence;
- tool layer;
- runtime;
- API;
- tests/eval;
- UI readiness;
- docs sync.

### 10. Questions For User

Liệt kê câu hỏi còn cần user chốt trước hoặc sau WS-A/B/C/D.

Các câu hỏi nên bao gồm:

1. Chọn native tool calling hay JSON-loop nếu WS-A không có câu trả lời dứt khoát?
2. Có chấp nhận agent phase đầu dùng một provider/model riêng không?
3. Có bắt buộc phải có persistent state table ngay không?
4. Default top N là bao nhiêu?
5. Threshold too-large compare là bao nhiêu?
6. Language filter "hạng C trở lên" map vào schema hiện tại thế nào?
7. UI có cần stream/tool progress không?
8. Có cần endpoint conversation history ngay phase đầu không?

### 11. Acceptance Criteria

Planning Brief đạt khi:

1. Tier 1 khác đọc vào hiểu C3 là gì.
2. WS-A/B/C/D có đề bài rõ để chạy song song.
3. Không ai hiểu nhầm rằng phải code ngay.
4. Không ai hiểu nhầm rằng Option C3 chỉ là thêm bảng.
5. Decision locked/open được phân biệt rõ.
6. Có đường dẫn rõ tới Official Implementation Plan và Work Plan sau này.

## Important Constraints

Không được:

1. Viết implementation plan chi tiết trong lượt này.
2. Chỉ định code patch cụ thể khi chưa có WS-A/B/C/D.
3. Tự chọn LangGraph/MCP/tool-calling provider nếu user chưa chốt và WS-A chưa phân tích.
4. Bỏ qua thực tế code hiện tại chưa có tool-calling runtime.
5. Bỏ qua coordination với Full-CV Chat và P1-A/P1-B.

Được phép:

1. Đề xuất default recommendation.
2. Nêu risk mạnh nếu user direction có điểm nguy hiểm.
3. Đưa checklist cho WS-A/B/C/D.
4. Đề xuất naming convention cho tài liệu/workstreams.

## Tone And Language

Viết bằng tiếng Việt.

Phong cách:

- rõ ràng;
- có tính chỉ huy;
- không marketing;
- không lan man;
- đủ cụ thể để giao việc.

Ưu tiên bảng/checklist khi giúp điều phối. Không cần viết quá dài; mục tiêu là Planning Brief, không phải implementation plan.


# FANG Next Phase JobPosting C3 Planning Brief

Ngày lập: 2026-05-28  
Phạm vi: **JobPosting Agent Option C3 + Dedicated JobPosting Conversation Tables**  
Loại tài liệu: **Planning Brief / Decision Lock**, không phải implementation plan cuối cùng.

## 1. Executive Summary

User đã chốt hướng **C3.1 - Dedicated tables + single-agent runtime + minimal tool set** cho JobPosting Agent.

C3 trong FANG được hiểu là một assistant read-only theo phạm vi `JobPosting`: HR đứng ở màn hình `JobPosting`, chat pane bên phải, conversation gắn với `jobPostId`, agent có memory/state đủ để hiểu follow-up như "trong 10 ông này", và agent được quyền gọi tool hệ thống để lấy ranking/search/summary/full-CV/ATS context trước khi trả lời.

Các quyết định lớn đã khóa:

1. Dùng dedicated JobPosting conversation tables, không reuse trực tiếp `AICHATCONVERSATION` đang gắn `jobAppId`.
2. Có agent runtime/controller thật sự, không chỉ prompt RAG.
3. Tool calling là bắt buộc; ưu tiên **R2 - native tool calling, single provider first**.
4. Provider ưu tiên là **Google/Gemini** nếu runtime hỗ trợ tốt.
5. Phase đầu chỉ có read-only tools; không write ATS/email/offer/status.
6. Không đưa LangGraph/MCP/full multi-provider tool-calling vào phase đầu nếu WS-A chưa chứng minh cần.
7. Tài liệu này chỉ khóa hướng và chia discovery workstreams; chưa chỉ định code patch.

Ghi chú model: user ưu tiên hai lane model `gemini/gemini-3.1-flash-lite` và `gemini/gemini-3.5-flash`, hoặc alias `gemini-flash-lite-latest` và `gemini-flash-latest`; nếu chỉ chọn một model thì chọn Flash-Lite. WS-A phải xác minh model ID thực tế trong Google GenAI SDK trước khi code, vì tên model/alias có thể thay đổi theo thời điểm và môi trường API.

## 2. Decision Lock

| Chủ đề | Quyết định đã khóa |
|---|---|
| Option | Chọn **C3.1 - Dedicated tables + single-agent runtime + minimal tool set**. |
| Product scope | JobPosting-scoped read-only assistant cho HR. |
| Conversation target | Conversation gắn với `jobPostId`. |
| Dedicated persistence | Có bảng riêng cho conversation/message/tool-call/state. |
| Tool catalog | Nghiêng về có bảng quản lý tool riêng để tool-call log có `toolId` FK, không chỉ lưu `toolName` text. |
| Runtime | Cần agent runtime/controller có tool loop thật. |
| Tool calling | Chắc chắn tool calling; ưu tiên native tool calling R2. |
| Provider | Ưu tiên Google/Gemini cho agent runtime phase đầu. |
| Model preference | Hai model/lane nếu được: Flash-Lite + Flash. Một model thì Flash-Lite. Exact model IDs do WS-A verify. |
| Working set key | Lưu working set bằng `jobAppId[]`, không dùng candidate id làm khóa chính của memory. |
| Default top N | Mặc định top 10 khi HR không chỉ rõ. |
| HR max top N | Trần HR có thể yêu cầu là 25. |
| Too-large compare | Mặc định threshold phân tích/so sánh sâu là 25, phải cấu hình được qua `.env`; rough/list/count có thể cân nhắc cao hơn nhưng không phải default phân tích sâu. |
| Language normalization | Normalize phải hoàn thành ở khâu parse/enrichment, để ranking, JobApp chat và JobPosting chat không normalize lặp lại. |
| UI tool visibility | UI nên show tool usage/progress và xem chi tiết tool/source được. |
| Conversation UX | Có quản lý hội thoại; tối thiểu tốt hơn JobApp chat ở điểm conversation đổi được tên. |

Các guardrail đã khóa:

1. Agent không được bulk-load full CV hàng loạt.
2. Agent không được write/update ATS, gửi email, tạo offer, đổi status trong phase đầu.
3. Agent phải biết từ chối/redirect yêu cầu quá lớn như "so sánh tất cả ứng viên" khi vượt threshold.
4. Agent phải trả lời dựa trên tool results/source metadata, không tự tưởng tượng dữ liệu.
5. CV/JD/email/feedback là untrusted data, không phải instruction.

## 3. Current Reality Constraints

Các constraint từ code/schema hiện tại:

1. `invoke_generation()` trong `app/services/rag_orchestrator.py` chỉ nhận messages và trả text generation trace; chưa có native tool-calling runtime, tool registry hoặc controller loop.
2. `app/services/rag_model_adapters.py` hiện là adapter text generation. Gemini adapter đang gọi `generate_content`, chưa expose function/tool declarations cho JobPosting Agent.
3. Chat API hiện tại nằm ở `app/api/routes_chat.py`, request model `ChatQueryRequest` bắt buộc `jobAppId`; persistence `AICHATCONVERSATION` cũng `jobAppId NOT NULL`.
4. `database/schema_ai_core.sql` đã có `AICHATCONVERSATION`, `AICHATMESSAGE`, `AIQUERYLOG`, nhưng đều xoay quanh `jobAppId`; chưa có JobPosting chat tables/tool-call tables.
5. `CVPARSED` và `AIDOCUMENTCHUNK` đã có theo `jobAppId`, có thể làm nguồn cho summary/full-CV/search tools.
6. `database/schema_web_core.sql` có `JOBPOSTING`, `JOBAPPLICATION`, `CANDIDATE`, `JOB_LANG_REQUIREMENT`, `LANGUAGE`, `INTERVIEW`, `INTERVIEWFEEDBACK`, `OFFER`, `EMAILLOG`; đây là nguồn cho tools read-only.
7. `rank_candidates_for_job()` đã có J->C ranking nhưng output hiện trả `candidate_id`, `candidate_name`, `match_score`, `score_breakdown`; JobPosting Agent cần wrapper/enrichment để luôn có `jobAppId` cho drill-down.
8. Language proficiency normalization đang drift: `normalize_proficiency()` tồn tại trong `app/services/nmaiex_mapper_service.py`, nhưng parse prompt giữ raw proficiency, ranking đọc `parsedJson.languages` và chỉ map đúng nếu proficiency đã là enum `BASIC|INTERMEDIATE|ADVANCED|FLUENT|NATIVE`. Đây là blocker/risk cho filter kiểu "tiếng Anh hạng C trở lên".
9. JobApplication Full-CV Chat và P1-A/P1-B có owner/track riêng; C3 phải reuse guardrails/full-CV helper khi các track đó ổn, không fork logic tùy tiện.

## 4. Desired End State

Product end state:

1. HR mở một `JobPosting` và thấy chat pane ở bên phải.
2. HR có thể tạo, xem lịch sử, đổi tên và tiếp tục conversation theo `jobPostId`.
3. HR hỏi "phân tích 10 ứng viên rank cao nhất"; agent gọi ranking tool với `limit=10`, lưu working set `jobAppId[]`, rồi phân tích có grounding.
4. HR hỏi tiếp "trong 10 ông này lọc ra phải có tiếng Anh hạng C trở lên"; agent dùng state từ turn trước và dữ liệu language đã normalize.
5. HR hỏi "so sánh tất cả ứng viên"; agent gọi count/ranking metadata, phát hiện quá lớn nếu vượt threshold, rồi hướng HR dùng top N/filter thay vì so sánh bừa.

Technical end state:

1. Có `jobposting_agent_runtime` hoặc module tương đương với native tool-calling loop.
2. Có tool registry và tool catalog/table quản lý tool identity/version/status.
3. Có dedicated tables cho conversation, message, tool-call log và state.
4. Có state JSON lưu working set, active filters, last ranking IDs, selected candidate IDs, summary ngắn của prior turns.
5. Tool outputs có source metadata, warnings, latency/status và không log raw full CV/email nếu không cần.
6. Runtime có hard limits: max tool steps, max candidates analyzed, max full CV loads per turn, max compare threshold.

## 5. Non-Goals For Phase 1

Phase 1 không làm:

1. Không write tools.
2. Không auto-send email.
3. Không update application status.
4. Không generate offer/note rồi ghi DB.
5. Không support compare all candidates nếu tập lớn.
6. Không generalized all-entity chat.
7. Không refactor toàn bộ JobApplication chat architecture.
8. Không full multi-provider tool-calling abstraction nếu chưa có quyết định riêng.
9. Không LangGraph/MCP adapter trong phase đầu nếu WS-A không chứng minh cần.
10. Không normalize language lại trong JobApp chat/JobPosting chat như workaround lâu dài; normalization phải nằm trước ở parse/enrichment.

## 6. Discovery Workstreams

Chạy song song 4 workstream tier 1. Mỗi workstream chỉ discovery/design, không tự code.

### WS-A - Agent Runtime and Tool Calling Decision

Phải trả lời:

1. Native tool calling với Google GenAI sẽ được dùng thế nào trong FANG.
2. Exact model IDs/aliases nào khả dụng trong môi trường hiện tại.
3. Nếu có hai lane model thì Flash-Lite và Flash phân vai ra sao; nếu một model thì Flash-Lite làm default thế nào.
4. Tool schema, tool declaration, max steps, retry/failure semantics.
5. Runtime module boundary: adapter riêng cho agent hay mở rộng `rag_model_adapters.py`.
6. Có cần LangGraph/MCP không; default là không.
7. `.env` cần thêm biến gì: provider/model IDs, max steps, max compare candidates, max full CV loads.

Output:

`agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSA_AGENT_RUNTIME_DECISION.md`

### WS-B - Dedicated Conversation Tables and Memory State

Phải trả lời:

1. Table design cho conversation/message/tool/tool-call/state.
2. Có tạo bảng tool catalog như `AIJOBPOSTINGTOOL` hoặc `AIAGENTTOOL` không, và FK từ tool-call log ra sao.
3. Conversation title rename flow: field nào, endpoint nào, default title sinh thế nào.
4. `AIJOBPOSTINGCHATSTATE` có bắt buộc không; default decision là có.
5. State JSON gồm gì: `workingSetJobAppIds`, `activeFilters`, `lastRanking`, `lastCandidateSummaries`, `compareScope`, warnings.
6. Retention/summarization strategy khi message/tool result dài.
7. Migration/index/FK risk với `JOBPOSTING`, `HR`, `JOBAPPLICATION`.

Output:

`agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSB_CONVERSATION_MEMORY_SCHEMA.md`

### WS-C - Read-only Tool Contract and Data Scope

Phải trả lời:

1. Tool list MVP và deferred.
2. Input/output schema cho từng tool.
3. Source metadata/warnings/error semantics.
4. Policy full CV: summary-first, full-CV by single `jobAppId`, no bulk load.
5. Count/too-large guardrail: default 25 via `.env`, HR top N max 25.
6. Language filter feasibility, đặc biệt "hạng C trở lên" map vào normalized enum nào.
7. Cách đảm bảo mọi tool scoped theo `jobPostId` và không leak application ngoài job.
8. NMAIex normalization dependency: `normalize_proficiency()` và các normalizer khác phải được gọi ở parse/enrichment stage, không để ranking/chat tự normalize lặp.

MVP tools tối thiểu:

1. `get_job_posting_context(job_post_id)`
2. `get_job_candidate_ranking(job_post_id, limit, filters)`
3. `search_job_applications_text(job_post_id, query, limit, filters)`
4. `get_job_application_summary(job_app_id)`
5. `get_job_application_full_cv(job_app_id)`
6. `get_candidate_ats_history(job_app_id)`
7. `count_job_applications(job_post_id, filters)`

Deferred/cẩn trọng:

1. Semantic search nếu cần embedding/cost/test phức tạp.
2. Compare tool rộng.
3. Any write tool.

Output:

`agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSC_TOOL_CONTRACT.md`

### WS-D - Product/API/UI Contract

Phải trả lời:

1. Route namespace cho JobPosting Agent.
2. Request/response schema cho query endpoint.
3. Endpoint conversation history/list/rename/delete hoặc archive.
4. UI chat pane cần fields nào: used tools, source IDs, latency, warnings, state/working set label.
5. UI hiển thị tool progress và tool detail thế nào.
6. Streaming/tool progress có cần phase đầu không, hay response final + tool log là đủ.
7. Postman/manual smoke flows cho top 10, refine language, too-large compare, rename conversation.

Output:

`agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSD_API_UI_CONTRACT.md`

## 7. Cross-Workstream Conflict Points

Các điểm chắc chắn cần synthesis:

1. Runtime tool format từ WS-A phải khớp tool contract WS-C.
2. State JSON từ WS-B phải đủ cho UI/API WS-D.
3. Tool catalog/table từ WS-B phải khớp registry/runtime WS-A.
4. Conversation rename và history UX từ WS-D phải khớp schema WS-B.
5. Ranking wrapper WS-C phải bổ sung `jobAppId` nếu ranking core chưa trả.
6. Language filter kỳ vọng của user phụ thuộc normalize parse/enrichment; không thể để C3 tự vá bằng heuristic runtime.
7. Model/provider choice WS-A phải khớp `.env`, existing fallback architecture và deployment keys.
8. Full-CV tool WS-C phải reuse logic từ JobApplication Full-CV track khi available.
9. P1-A/P1-B prompt/eval guardrails phải feed vào system prompt/tool policy của C3.

## 8. Synthesis Step

Sau WS-A/B/C/D, một tier 1 phải viết:

`agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_OFFICIAL_IMPLEMENTATION_PLAN.md`

Implementation Plan chính thức phải bao gồm:

1. final architecture;
2. schema migrations;
3. file/module creation list;
4. function/class contracts;
5. route contracts;
6. Google native tool-calling runtime loop;
7. model/provider/env config;
8. state/memory design;
9. tool registry và tool catalog;
10. read-only tool implementations;
11. conversation rename/history UX;
12. normalization dependency plan cho language/proficiency;
13. testing and eval plan;
14. rollout order;
15. risks/deferred items.

## 9. Later Work Plan

Work Plan chỉ viết sau Official Implementation Plan.

Work Plan sẽ chia code tasks cho tier 1/tier 2:

1. DB/persistence migration.
2. Tool catalog + tool-call logging.
3. Read-only tool layer.
4. Agent runtime/controller.
5. API routes.
6. Conversation history/rename endpoints.
7. Tests/eval.
8. UI readiness contract.
9. Docs sync.
10. NMAIex language/proficiency normalization fix nếu chưa được xử lý ở track khác.

## 10. Questions For User

Không còn câu hỏi blocker trước khi chạy WS-A/B/C/D. Các quyết định user đã trả lời đủ để viết Planning Brief và giao discovery.

Các câu dưới đây không hỏi lại user ngay; chúng là verification/discovery items cho workstreams:

1. WS-A xác minh exact Google model IDs/aliases và tool-calling API hiện dùng được.
2. WS-A xác định Flash-Lite/Flash routing nếu cả hai model khả dụng.
3. WS-B chốt tên bảng/tool catalog cụ thể và migration details.
4. WS-C chốt mapping "hạng C trở lên" sang enum chuẩn sau khi xem data thực tế.
5. WS-D chốt stream/tool progress phase đầu có cần không; default có thể là final response + inspectable tool log.

Nếu cần user chốt thêm sau discovery, synthesis agent phải gom thành một danh sách ngắn, không mở lại các decision đã khóa ở mục 2.

## 11. Acceptance Criteria

Planning Brief đạt khi:

1. Tier 1 khác đọc vào hiểu C3 là JobPosting-scoped read-only agent, không chỉ là thêm bảng.
2. Decision locked/open được phân biệt rõ.
3. WS-A/B/C/D có đề bài rõ để chạy song song.
4. Không ai hiểu nhầm rằng phải code ngay.
5. Không ai tự mở scope sang write tools, MCP, LangGraph hoặc generalized chat refactor.
6. Provider/model preference của user được ghi lại nhưng exact model IDs vẫn được verify đúng lúc.
7. Language/proficiency normalization drift được ghi là dependency bắt buộc, không bị bỏ qua.
8. Có đường dẫn rõ tới Official Implementation Plan và Work Plan sau này.


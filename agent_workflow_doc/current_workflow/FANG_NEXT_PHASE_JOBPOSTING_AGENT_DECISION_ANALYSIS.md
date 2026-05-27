# JobPosting Agent Decision Analysis

Ngày lập: 2026-05-27  
Phạm vi: FANG AI core, phạm vi một `JobPosting`, nhiều `JobApplication`

## Executive Summary

**Khuyến nghị chiến lược: chưa nên greenlight implementation `JobPosting Agent` ngay. Nên chọn hướng staged decision: hoàn tất `JobApplication Full-CV Chat` + `P1-A/P1-B`, sau đó thiết kế và thử một read-only JobPosting tool layer trước khi đưa agent framework/MCP vào.**

Lý do chính: `JobPosting Agent` không phải là việc đổi khóa từ `jobAppId` sang `jobPostId`. Nó là một lớp sản phẩm mới cho HR hỏi và hành động trên một tập ứng viên. FANG đã có nền tốt để làm việc này trong tương lai: NMAIex ranking J->C, CV chunks, `CVPARSED`, ATS history, offer/email và chat generation. Nhưng hiện tại các boundary còn thiếu: tool contract, permission, audit, conversation schema theo `jobPostId`, prompt/eval cho multi-candidate reasoning, và quy tắc khi agent được phép drill-down vào full CV.

**Quyết định nên chốt ở mức chiến lược:**

1. Không giao implementation JobPosting Agent cho tier 2/thành viên ngay trong phase hiện tại.
2. Giữ roadmap gần: `AI Ranking + JobApplication Full-CV Chat + Prompt Review/Minimal Eval`.
3. Mở một decision/design workstream riêng cho JobPosting Agent, nhưng chỉ ở mức read-only tool layer và product workflow.
4. Nếu làm prototype, làm **read-only vertical slice** trước: hỏi trên một job, xem ranking, search/filter ứng viên, mở summary/full CV của một ứng viên, giải thích score breakdown.
5. Không làm write tools cập nhật ATS/email/offer trước khi có permission, human approval và audit log rõ.
6. MCP nếu dùng chỉ nên là adapter/exposure sau khi domain tool layer trong FANG đã ổn; không đặt business logic trong MCP server.
7. LangGraph/LangChain/ADK chỉ nên chọn sau khi đã biết workflow cần orchestration stateful thật sự; phase đầu có thể dùng service/tool interface bình thường trong FastAPI.

**Option đề xuất:** chọn **Option B - Design-first + Read-only Tool Layer**, sau đó điều kiện hóa sang **Option C - Read-only Agent Vertical Slice** khi full-CV chat và prompt/eval baseline đã ổn.

**Không nên chọn ngay:**

- Không chọn `Option A` như quyết định vĩnh viễn "không bao giờ làm", vì JobPosting Agent có giá trị sản phẩm thật nếu HR muốn hỏi trên candidate pool.
- Không chọn `Option D/E` là mở full agent framework/MCP/write tools ngay, vì rủi ro architecture và compliance cao hơn lợi ích trước mắt.

**Final call ngắn:** hiện tại chưa implement JobPosting Agent. Làm memo/spec tool layer trước, sau đó chỉ prototype read-only nếu user muốn mở track này sau khi hai workstream đang rõ đã chạy.

## Current Reality

### FANG hiện có gì liên quan

Theo knowledge graph, P0-A/P0-B/P0-D và code hiện tại, FANG đang là FastAPI AI core gồm các cụm chính:

- CV ingestion: parse CV, tạo markdown/chunks, embed và lưu `CVPARSED`, `AIDOCUMENTCHUNK`.
- JobApplication chat: hiện code vẫn dùng top-k chunk RAG trên một `jobAppId`; next phase đã chốt chuyển sang full CV markdown.
- NMAIex ranking: đã có J->C ranking cho một `jobPostId` và C->J ranking cho một `candidateId`.
- Persistence chat: `AICHATCONVERSATION` hiện gắn với `jobAppId`, chưa có conversation theo `jobPostId`.
- Web/ATS schema: có `JOBPOSTING`, `JOBAPPLICATION`, `CANDIDATE`, `CANDIDATESKILL`, `INTERVIEW`, `INTERVIEWFEEDBACK`, `OFFER`, `EMAILLOG`.

Các file/code surface trọng yếu:

- `app/api/routes_chat.py`: API chat hiện tại theo `jobAppId`.
- `app/services/rag_query.py`: pipeline chat hiện tại.
- `app/services/nmaiex_ranking_service.py`: J->C/C->J ranking, score breakdown.
- `app/api/nmaiex_routes_ranking.py`: endpoint `/v2/nmaiex/ranking/candidates/{job_id}`.
- `app/services/markdown_builder.py`: có `convert_json_to_markdown()` để dựng full CV.
- `database/schema_web_core.sql`: dữ liệu job/application/ATS/offer/email.
- `database/schema_ai_core.sql`: ingestion/chat/query log.

### Nền hiện có cho JobPosting Agent

FANG đã có một số khối có thể tái dùng:

1. **Candidate ranking:** `rank_candidates_for_job(job_id, limit, province_id, work_mode)` đã trả danh sách ứng viên kèm `match_score` và `score_breakdown`.
2. **Semantic retrieval:** `AIDOCUMENTCHUNK` có embedding CV chunks; ranking J->C đã dùng vector distance và full-text rank.
3. **Full CV source:** `CVPARSED.parsedJson` + `rawText` có thể dùng để agent drill-down từng ứng viên.
4. **ATS context:** interview feedback, offer và email log có schema sẵn.
5. **Generation layer:** `invoke_generation()` và 7 `modelMode` đã có.

Nhưng đây mới là raw capabilities. Chưa có domain tool layer ổn định cho agent gọi, chưa có audit/permission layer, và chưa có prompt/eval cho multi-candidate HR reasoning.

### Điều còn thiếu

Các gap quan trọng:

1. **Conversation target:** `AICHATCONVERSATION` hiện bắt buộc `jobAppId`; JobPosting Agent cần conversation theo `jobPostId` hoặc bảng/conversation type mới.
2. **Tool contract:** hiện ranking là service/API, chưa phải tool interface với input/output, permission, limit, truncation, error semantics rõ.
3. **Candidate pool semantics:** cần định nghĩa agent được xem tất cả ứng viên của job hay chỉ shortlist/ranked candidates.
4. **Full CV access policy:** full CV là dữ liệu sâu và nhiều PII; agent không nên tự load hàng loạt full CV nếu chưa cần.
5. **Source attribution:** khi agent trả lời trên nhiều ứng viên, phải nói rõ dựa trên ranking, CV, ATS feedback hay email/offer.
6. **Prompt injection risk:** CV/JD/email đều là untrusted context; rủi ro tăng khi agent tự chọn tool và tổng hợp nhiều nguồn.
7. **Write safety:** chưa có human approval/audit nếu agent cập nhật status, gửi email, tạo offer hoặc ghi note.
8. **Eval:** chưa có seed eval cho câu hỏi multi-candidate như "top 5 ai phù hợp nhất và vì sao", "so sánh A với B", "lọc người có React + remote".

## Strategic Question

Câu hỏi cần quyết không phải là "có dùng agent framework không", mà là:

**FANG có nên mở một lớp HR assistant ở phạm vi `JobPosting`, nơi model có thể điều phối ranking/search/filter/drill-down trên nhiều ứng viên, hay nên giữ sản phẩm ở AI Ranking + JobApplication Full-CV Chat trong phase này?**

Cần tách 4 phạm vi:

1. **Ranking/Search:** deterministic/scored candidate list cho một job.
2. **JobApplication Full-CV Chat:** hỏi sâu về một ứng viên.
3. **JobPosting Read-only Assistant:** hỏi trên candidate pool, dùng tools để ranking/search/filter/compare/drill-down.
4. **JobPosting Action Agent:** có thể draft hoặc ghi dữ liệu ATS/email/offer/status với approval.

Ranking và Full-CV Chat là nền. JobPosting Agent chỉ nên đến sau khi tool boundary của phạm vi 3 rõ.

## Decision Criteria

| Tiêu chí | Ý nghĩa |
|---|---|
| Strategic HR value | Có giúp HR ra shortlist, so sánh và điều phối pipeline nhanh hơn không |
| Architecture isolation | Có tách khỏi JobApplication chat và ranking cũ không |
| Reuse existing capabilities | Có tận dụng NMAIex ranking, chunks, full CV, ATS context không |
| Risk containment | Có giới hạn read-only, limit, audit, no bulk CV dump không |
| Prompt/eval maturity | Có đủ prompt policy và cases để kiểm hành vi multi-candidate không |
| Permission/audit readiness | Có thể kiểm soát ai được xem/làm gì trên job/candidate không |
| Implementation cost | Có thể làm vertical slice nhỏ mà không refactor toàn repo không |
| Future extensibility | Có thể thêm MCP/LangGraph/write tools sau mà không viết lại domain logic không |

## Options

### Option A - Không làm JobPosting Agent trong chu kỳ này

Mô tả: chỉ làm `AI Ranking + JobApplication Full-CV Chat + P1-A/P1-B`. JobPosting scope chỉ dừng ở ranking API và UI hiện có.

Ưu điểm:

- Ít rủi ro nhất.
- Giữ team tập trung vào hai việc đã rõ và có giá trị ngay.
- Không kéo framework/agent vào khi prompt/eval baseline chưa ổn.
- Tránh phải sửa schema chat và permission/audit ngay.

Nhược điểm:

- Bỏ lỡ workflow tự nhiên của HR: hỏi trên toàn bộ candidate pool của một job.
- Ranking vẫn là bảng điểm, chưa thành assistant biết giải thích/so sánh theo câu hỏi tự nhiên.
- Sau full-CV chat, sản phẩm có thể bị lệch: hỏi sâu một ứng viên tốt, nhưng hỏi toàn job vẫn thủ công.

Khi nào chọn:

- Chọn nếu nguồn lực hạn chế hoặc cần ship full-CV chat/prompt eval trước.
- Chọn nếu chưa rõ HR workflow thực tế cho JobPosting Agent.

Đánh giá: **nên chọn làm default ngắn hạn, nhưng không phải quyết định dài hạn.**

### Option B - Design-first + Read-only Tool Layer

Mô tả: chưa làm agent UI/runtime đầy đủ. Thiết kế và có thể implement domain tool layer read-only trong FANG để chuẩn bị cho agent sau.

Tool layer khởi đầu:

1. `get_job_posting_context(job_post_id)`
2. `get_job_candidate_ranking(job_post_id, limit, filters)`
3. `search_job_applications_semantic(job_post_id, query, limit, filters)`
4. `search_job_applications_text(job_post_id, query, limit, filters)`
5. `get_job_application_summary(job_app_id)`
6. `get_job_application_full_cv(job_app_id)`
7. `get_candidate_ats_history(job_app_id)`
8. `compare_job_applications(job_post_id, job_app_ids, criteria)` - có thể để phase sau nếu chưa rõ

Ưu điểm:

- Đúng thứ tự kiến trúc: domain tools trước, agent/framework sau.
- Tái dùng ranking/search/full-CV mà không phá JobApplication chat.
- Có thể test từng tool bằng unit/integration tests trước khi cho LLM điều phối.
- Dễ expose qua FastAPI nội bộ, MCP adapter hoặc LangGraph node sau này.
- Giảm rủi ro framework lock-in.

Nhược điểm:

- Chưa tạo ngay trải nghiệm "agent chat" hoàn chỉnh.
- Cần đầu tư thiết kế tool output contract, truncation, filtering, error handling.
- Nếu design quá rộng có thể thành spec lớn không ship.

Khi nào chọn:

- Chọn nếu user muốn mở track JobPosting Agent nhưng vẫn kiểm soát rủi ro.
- Chọn sau khi Full-CV Chat/P1-A có prompt policy và eval seed đủ làm nền.

Đánh giá: **khuyến nghị chiến lược.**

### Option C - Read-only JobPosting Agent Vertical Slice

Mô tả: làm một endpoint/chat surface mới cho `jobPostId`, agent chỉ được gọi read-only tools. Không có write action.

Workflow mẫu:

1. HR mở job posting.
2. Hỏi: "Top 5 ứng viên phù hợp nhất và lý do?"
3. Agent gọi ranking tool.
4. Nếu cần evidence, agent gọi summary/full CV cho một vài ứng viên top.
5. Agent trả lời có nguồn: ranking score, skill overlap, CV evidence, ATS feedback.
6. HR hỏi tiếp: "So sánh ứng viên A và B về Java/Spring Boot và kinh nghiệm lead team."

Ưu điểm:

- Tạo giá trị sản phẩm rõ hơn Option B.
- Có thể dùng ranking hiện có như first tool, không cần agent phức tạp ngay.
- Read-only giúp giới hạn compliance/permission risk.
- Là cầu nối tự nhiên giữa ranking và Full-CV Chat.

Nhược điểm:

- Cần schema/API conversation theo `jobPostId`.
- Cần prompt/tool policy rất cẩn thận để tránh bulk load CV và hallucinated comparison.
- Cần eval multi-candidate trước khi xem là production-ready.
- Nếu chưa có full-CV chat ổn, drill-down full CV sẽ lặp lại vấn đề chưa giải quyết.

Khi nào chọn:

- Chỉ chọn sau khi Option B có tool contract rõ.
- Chọn nếu user muốn prototype sản phẩm sau khi full-CV chat đã hoàn tất.

Đánh giá: **đáng làm sau, không nên nhảy thẳng vào ngay.**

### Option D - MCP Adapter sớm

Mô tả: viết MCP server expose các tool JobPosting để một agent host gọi.

Ưu điểm:

- Linh hoạt nếu user muốn dùng nhiều runtime/host khác nhau.
- Tool interface có thể reuse ngoài FANG backend.
- Hợp với hướng tool-based retrieval thay vì fixed RAG.

Nhược điểm:

- MCP không tự giải quyết domain boundary, permission, truncation, audit.
- Dễ đặt SQL/business logic lung tung trong MCP server nếu chưa có service layer.
- Có thêm surface để bảo trì.

Khi nào chọn:

- Chọn sau khi domain tool layer đã nằm trong FANG services.
- MCP chỉ là adapter mỏng gọi service/tool interface đã test.

Đánh giá: **không làm trước tool layer.**

### Option E - Full Agent Framework ngay: LangGraph/LangChain/ADK

Mô tả: đưa framework orchestration vào ngay để agent tự plan, call tools, giữ state, có thể multi-step.

Ưu điểm:

- Hợp nếu workflow cần nhiều bước, branching, memory, human approval.
- Có thể biểu diễn graph: rank -> filter -> drill-down -> compare -> draft action.
- LangGraph đặc biệt phù hợp nếu cần state machine và approval nodes.

Nhược điểm:

- Rủi ro refactor cao nếu đưa vào trước khi tool layer rõ.
- Dễ over-engineer khi use case đầu chỉ cần ranking + search + answer.
- Test/debug khó hơn service functions thuần.
- Có thể kéo JobApplication chat/ranking cũ vào refactor không cần thiết.

Khi nào chọn:

- Chọn nếu read-only vertical slice chứng minh cần orchestration stateful thật sự.
- Chọn khi đã có tool contracts, eval cases, và acceptance criteria.

Đánh giá: **defer.**

### Option F - JobPosting Action Agent

Mô tả: agent không chỉ trả lời mà còn draft/gửi email, đổi application status, tạo interview plan, tạo offer note hoặc cập nhật ATS.

Ưu điểm:

- Giá trị vận hành rất cao nếu làm đúng.
- Có thể giảm nhiều thao tác HR lặp lại.

Nhược điểm:

- Rủi ro lớn nhất: write permission, audit, user confirmation, rollback, failure semantics.
- Cần phân quyền HR theo company/job/candidate.
- Cần human-in-the-loop rõ: draft trước, approve sau.
- Không phù hợp khi read-only agent còn chưa có eval.

Khi nào chọn:

- Chỉ sau read-only agent đã ổn.
- Bắt đầu bằng draft-only, không auto-commit.

Đánh giá: **không chọn trong phase hiện tại.**

## Recommendation

Chọn **Option B - Design-first + Read-only Tool Layer** làm quyết định chiến lược hiện tại.

Diễn đạt quyết định đề xuất:

> FANG chưa implement JobPosting Agent ngay. Track JobPosting Agent sẽ bắt đầu bằng thiết kế domain tool layer read-only cho phạm vi một `JobPosting`, tái dùng NMAIex ranking, search, CV summary/full CV và ATS context. Agent framework/MCP/write tools chỉ được xét sau khi tool contract, prompt policy, eval seed và permission/audit boundary đã rõ. Trong phase gần, ưu tiên ship `JobApplication Full-CV Chat` và `P1-A/P1-B`.

Nếu user muốn giao việc ngay cho thành viên thứ ba, giao **Decision/Tool Contract Spec**, không giao coding agent framework.

## Proposed Staged Roadmap

### Stage 0 - Không chặn workstream hiện tại

Làm trước:

1. `JobApplication Full-CV Chat`.
2. `P1-A/P1-B Prompt Review + Minimal Eval`.
3. miCareer-mini/API readiness nếu có người thứ ba.

Không làm:

1. Không đổi schema chat sang `jobPostId` ngay.
2. Không đưa LangGraph/MCP vào repo ngay.
3. Không tạo write tools.

### Stage 1 - JobPosting Tool Contract Spec

Output cần có:

1. Danh sách tool read-only.
2. Input/output schema cho từng tool.
3. Permission assumption.
4. Limit/truncation policy.
5. Source attribution policy.
6. Error semantics.
7. Logging/audit metadata.
8. Minimal eval cases.

Tool contract không nên phụ thuộc framework. Dù sau này dùng FastAPI-only, LangGraph hay MCP, contract vẫn giữ.

### Stage 2 - Implement Read-only Tool Layer

Implement trong FANG services trước:

- Module gợi ý: `app/services/jobposting_tools.py` hoặc `app/services/jobposting_agent_tools.py`.
- Không gọi LLM trong các tool thuần retrieval/ranking.
- Không expose toàn bộ full CV list hàng loạt.
- Mỗi tool có deterministic tests.

Acceptance:

1. Ranking tool reuse `rank_candidates_for_job`.
2. Semantic/text search giới hạn theo `jobPostId`.
3. Summary tool trả context ngắn trước, full CV tool chỉ theo `jobAppId` cụ thể.
4. ATS tool giới hạn interview/offer/email theo policy.
5. Không có write.

### Stage 3 - Read-only Agent Prototype

Chỉ sau Stage 2:

1. Endpoint mới theo `jobPostId`, ví dụ `/v2/job-posting-agent/query` hoặc namespace rõ hơn.
2. Conversation model mới hoặc extension có `targetType = JOB_POSTING`.
3. System prompt/tool policy cho multi-candidate HR assistant.
4. Agent chỉ được gọi read-only tools.
5. Logs lưu tool calls, source IDs, latency, model.

Prototype nên trả lời được 5 workflow:

1. "Top ứng viên phù hợp nhất là ai và vì sao?"
2. "Lọc ứng viên có skill X/Y và remote."
3. "So sánh 2-3 ứng viên đã chọn."
4. "Ứng viên nào có rủi ro thiếu seniority/language/salary?"
5. "Mở sâu một ứng viên và tóm tắt fit-gap."

### Stage 4 - MCP Adapter Optional

Chỉ làm nếu cần expose tool ra runtime khác.

Nguyên tắc:

1. MCP adapter mỏng.
2. Không viết SQL tùy hứng trong MCP.
3. Gọi service/tool layer đã test.
4. Áp cùng permission/truncation/audit policy.

### Stage 5 - Draft/Write Tools

Chỉ sau read-only agent:

1. Draft interview plan/note/email.
2. Human approval bắt buộc.
3. Audit log đầy đủ.
4. Write status/offer/email sau cùng.

Không có approval thì không có write action.

## Tool Layer Proposal

### Tool 1 - `get_job_posting_context`

Mục tiêu: lấy context mô tả job làm nền cho mọi câu trả lời.

Input:

- `job_post_id: int`

Output nên có:

- title, description.
- salary range.
- work mode/location/province.
- job levels/categories.
- required skills.
- language requirements.
- company basic info nếu cần.

Rủi ro:

- JD là untrusted/semi-trusted text, có thể chứa instruction-like content.

Policy:

- Đánh dấu là data, không phải instruction.
- Truncate description nếu quá dài.

### Tool 2 - `get_job_candidate_ranking`

Mục tiêu: lấy ranking snapshot cho job.

Input:

- `job_post_id: int`
- `limit: int`
- `filters: province_id, work_mode, min_score, status` nếu hỗ trợ

Output nên có:

- candidate id/name.
- `jobAppId`.
- match score.
- score breakdown: rrf, skill, seniority, exact/fuzzy overlap.
- short reason deterministic nếu có thể derive từ score breakdown.

Policy:

- Limit mặc định nhỏ, ví dụ 10-20.
- Không trả full CV trong tool này.

### Tool 3 - `search_job_applications_semantic`

Mục tiêu: tìm ứng viên theo câu hỏi tự nhiên trong phạm vi một job.

Input:

- `job_post_id: int`
- `query: str`
- `limit: int`
- `filters`

Implementation:

- Dùng embedding query + `AIDOCUMENTCHUNK`, nhưng bắt buộc join qua `JOBAPPLICATION WHERE jobPostId = $job_post_id`.

Output:

- `jobAppId`, candidate id/name.
- matching chunks/snippets.
- distance/score.

Policy:

- Snippet giới hạn.
- Không trả full CV.

### Tool 4 - `search_job_applications_text`

Mục tiêu: tìm exact/text search theo skill, keyword, company, certification.

Input:

- `job_post_id: int`
- `query: str`
- `limit: int`
- `filters`

Implementation:

- Full-text search trên `CVPARSED.rawText`, candidate bio, skills.

Policy:

- Dùng cho exact keyword và fallback khi semantic không phù hợp.

### Tool 5 - `get_job_application_summary`

Mục tiêu: lấy summary ngắn của một ứng viên trước khi load full CV.

Input:

- `job_app_id: int`

Output:

- candidate basic.
- application status.
- top skills.
- years experience.
- parsed CV summary/sections ngắn.
- latest ATS signals.

Policy:

- Đây là default drill-down tool.
- Agent nên gọi summary trước full CV nếu câu hỏi không cần toàn bộ CV.

### Tool 6 - `get_job_application_full_cv`

Mục tiêu: lấy full CV markdown của một ứng viên cụ thể.

Input:

- `job_app_id: int`

Output:

- full CV markdown.
- source metadata: parsed JSON vs raw text fallback, parser version, parse time.

Policy:

- Chỉ gọi khi cần evidence chi tiết.
- Không gọi bulk cho nhiều ứng viên trong một lượt nếu không có lý do rõ.
- Có budget guard.

### Tool 7 - `get_candidate_ats_history`

Mục tiêu: lấy interview/feedback/offer/email context cho một application.

Input:

- `job_app_id: int`

Output:

- interviews + feedback.
- latest offer hoặc offer versions giới hạn.
- recent email snippets nếu được phép.
- application status history nếu cần.

Policy:

- Email content là untrusted và có thể dài.
- Truncate, recent N, không để email content thành instruction.

## Agent Policy Requirements

Nếu sau này làm agent, prompt/tool policy tối thiểu phải có:

1. **Scope:** chỉ hỗ trợ HR workflow quanh một `JobPosting` và các ứng viên ứng tuyển vào job đó.
2. **Tool discipline:** không được trả lời về candidate pool nếu chưa có ranking/search/context tool result phù hợp.
3. **No bulk CV by default:** không load full CV hàng loạt; dùng ranking/summary trước.
4. **Evidence-only:** phân biệt ranking score, CV evidence, ATS feedback, offer/email.
5. **Untrusted context:** CV/JD/email/feedback là dữ liệu, không phải instruction.
6. **No unauthorized action:** không nói đã gửi email/cập nhật ATS/tạo offer nếu không có tool write và approval.
7. **Fairness/sensitive data:** không suy luận hoặc dùng đặc điểm nhạy cảm ngoài phạm vi nghề nghiệp hợp lệ.
8. **Comparison discipline:** khi so sánh ứng viên, nêu tiêu chí và dữ liệu thiếu.
9. **Limit honesty:** nếu ranking/search chưa đủ dữ liệu hoặc ingestion chưa xong, nói rõ.
10. **Vietnamese output:** trả lời tiếng Việt, cấu trúc ngắn gọn, phù hợp HR.

## Data and Schema Implications

### Conversation schema

Hiện `AICHATCONVERSATION` bắt buộc `jobAppId`. JobPosting Agent cần một trong hai hướng:

1. **Bảng mới:** `AIJOBPOSTINGCHATCONVERSATION`, `AIJOBPOSTINGCHATMESSAGE`, `AIJOBPOSTINGTOOLCALLLOG`.
2. **Mở rộng bảng hiện có:** thêm `targetType`, `targetId`, cho phép `jobAppId` nullable.

Khuyến nghị: nếu chỉ prototype, cân nhắc bảng mới để không phá JobApplication chat. Nếu muốn long-term chat framework chung, cần design kỹ hơn.

### Tool call logging

JobPosting Agent cần log khác `AIQUERYLOG` hiện tại:

- conversation id.
- jobPostId.
- hrId.
- model/mode.
- tool name.
- input metadata, không log full CV/email nếu không cần.
- output source IDs.
- latency/status/error.

Không nên nhồi tool call log vào `AIQUERYLOG` nếu làm mất ý nghĩa log chat hiện tại.

### Permission

Repo hiện chưa có auth middleware production. Vì vậy phase đầu nên giả định internal/trusted HR context, nhưng decision memo phải ghi rõ:

- HR chỉ được xem job thuộc company của mình.
- Candidate/application phải thuộc job đó.
- Write actions cần permission riêng.

Không nên mở write tools trước khi có cách enforce các rule này.

## Framework Decision

### FastAPI service-only

Phù hợp cho Stage 1-2.

Ưu điểm:

- Ít dependency.
- Dễ test.
- Không đổi mental model repo.
- Tool contracts rõ trước.

Nhược điểm:

- Nếu agent multi-step phức tạp, tự viết orchestration sẽ khó.

### LangGraph

Phù hợp nếu Stage 3+ cần stateful multi-step agent, approval nodes, retry, tool call graph.

Ưu điểm:

- Tốt cho workflow có state và guardrail.
- Dễ mô hình hóa read-only -> approval -> write sau này.

Nhược điểm:

- Không nên đưa vào khi chưa có tool layer/eval.

### LangChain

Phù hợp nếu chỉ cần tool abstraction đơn giản, nhưng có nguy cơ kéo abstraction rộng hơn cần thiết.

Đánh giá: cân nhắc sau, không phải default.

### ADK

Chỉ nên đánh giá nếu hệ sinh thái model/runtime cụ thể của user cần ADK. Hiện chưa có lý do kỹ thuật đủ mạnh trong repo.

### MCP

MCP là exposure/adapter tốt, không phải nơi đặt business logic.

Khuyến nghị:

- Domain tools trong FANG services.
- MCP adapter mỏng gọi domain tools.
- Không chọn MCP chỉ vì dễ viết server.

## Decision Matrix

| Option | HR value | Architecture fit now | Risk | Effort | Recommendation |
|---|---:|---:|---:|---:|---|
| A. Không làm trong chu kỳ này | Medium | High | Low | Low | Default ngắn hạn |
| B. Design-first + read-only tool layer | High | High | Medium | Medium | **Chọn** |
| C. Read-only agent vertical slice | High | Medium | Medium | High | Sau B |
| D. MCP adapter sớm | Medium | Medium | Medium | Medium | Sau tool layer |
| E. Full framework ngay | High | Low-Medium | High | High | Defer |
| F. Write/action agent | Very high | Low | Very high | Very high | Không chọn |

## Recommended Next Work Package

Nếu user muốn tạo assignment cho track này, assignment nên là:

> Viết `JobPosting Agent Tool Contract Spec` cho FANG. Không implement agent/framework. Phân tích tool read-only cho một `jobPostId`, gồm ranking, semantic/text search, candidate summary, full CV drill-down và ATS history. Định nghĩa input/output schema, permission assumption, truncation/budget policy, source attribution, tool-call logging và minimal eval cases. Kết luận có nên prototype read-only agent sau khi `CHAT_FULL_CV` và `P1-A/P1-B` xong hay không.

Deliverables:

1. `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_JOBPOSTING_AGENT_TOOL_CONTRACT.md`
2. Minimal eval seed cases cho 5 workflow JobPosting.
3. API/schema impact note.
4. Framework decision note: FastAPI-only vs LangGraph vs MCP adapter.

## Open Questions for User

Các câu hỏi này nên chốt trước khi implement prototype:

1. HR muốn hỏi trên **tất cả applications của job** hay chỉ trên ranked/active candidates?
2. JobPosting Agent có cần lưu conversation riêng theo `jobPostId` ngay không?
3. Có được load full CV của nhiều ứng viên trong một câu trả lời không, hay bắt buộc summary/ranking trước?
4. EmailLog có được đưa vào agent context không, hay chỉ metadata/snippet?
5. Output mong muốn là chat tự nhiên, bảng shortlist, hay cả hai?
6. Có cần explain score breakdown theo NMAIex trong câu trả lời agent không?
7. Phase đầu có cần MCP để host khác gọi tools không, hay FANG internal API đủ?
8. Khi nào mới cho phép write actions: draft-only, approval-required, hay không bao giờ trong FANG?

## Final Recommendation

Không implement JobPosting Agent ngay trong phase hiện tại.

Chốt hướng:

1. Ship `JobApplication Full-CV Chat`.
2. Hoàn tất `P1-A/P1-B`.
3. Mở `JobPosting Agent Tool Contract Spec` nếu user muốn tiếp tục nghiên cứu.
4. Chỉ sau đó mới làm read-only agent vertical slice.
5. MCP/framework/write tools để sau, dựa trên tool layer và eval thực tế.


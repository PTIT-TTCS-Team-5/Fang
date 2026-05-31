# JobPosting Agent C3 Deep Advisory

Ngày lập: 2026-05-27  
Phạm vi: tư vấn sâu cho hướng **Option C3 + Dedicated JobPosting Conversation Tables**

## Executive Summary

**Câu trả lời ngắn: có, mục tiêu cuối cùng bạn mô tả là khả thi.** HR hoàn toàn có thể đứng ở màn hình `JobPosting`, bên phải có cửa sổ chat, và chat trong phạm vi một `JobPosting`. LLM có thể nhớ ngữ cảnh hội thoại, tự gọi tool hệ thống, biết phân tích top N ứng viên, biết lọc tiếp theo ràng buộc mới, và biết từ chối những yêu cầu quá lớn như "so sánh tất cả 789 ứng viên" bằng cách hướng HR quay lại ranking/filtering.

Nhưng để đạt đúng hành vi đó, **C3 không chỉ là thêm bảng conversation**. Nó thực chất là 4 lớp cùng lúc:

1. **Job-scoped chat surface**: chat gắn với `jobPostId`, không phải `jobAppId`.
2. **Dedicated memory/persistence**: conversation/message/tool-call log riêng cho JobPosting.
3. **Read-only tool layer đủ mạnh**: ranking, filter/search, summary, full CV, ATS history, count/guardrail.
4. **Agent runtime/controller**: lớp điều phối cho phép LLM chọn tool, nhận tool result, nhớ ngữ cảnh, rồi trả lời.

**Điểm quan trọng nhất cần nhìn rõ trước khi code:** code hiện tại **chưa có native tool-calling runtime**. `invoke_generation()` và `rag_model_adapters.py` mới chỉ là text generation/fallback, chưa có cơ chế "LLM tự gọi hàm" theo đúng nghĩa. Vì vậy nếu chọn C3, bạn đang chấp nhận làm thêm một lớp mới: `jobposting_agent_runtime`.

**Khuyến nghị chiến lược:** nếu đi C3, hãy chốt một phiên bản rất cụ thể:

- Dedicated conversation tables: **nên làm**.
- Read-only tools: **bắt buộc**.
- Agent runtime: **bắt buộc**.
- Multi-provider tool calling: **không nên làm ngay**.
- Chỉ support 3-4 workflow đầu tiên thật chắc.

**Khuyến nghị kỹ thuật cụ thể:** làm theo **C3.1 - Dedicated tables + single-agent runtime + minimal tool set**. Không cố support toàn bộ `7 modelMode` cho agent phase đầu. Agent mode nên dùng **một provider/model agent chính** trước, còn chat generation cũ vẫn giữ nguyên cho các flow khác.

## Direct Answer To Your Desired End State

### Bạn muốn gì

Bạn muốn:

1. HR đứng ở màn hình `JobPosting`.
2. Bên phải có khung chat.
3. HR chat trên phạm vi một job.
4. LLM được "dạy skill" và các nguyên tắc dùng tool.
5. LLM nhớ ngữ cảnh hội thoại trước đó.
6. LLM tự biết khi nào gọi tool rank, filter, summary, full CV, ATS history.
7. LLM biết guardrail:
   - "phân tích 10 ứng viên top đầu" -> gọi rank limit 10.
   - "lọc tiếng Anh từ C trở lên" -> nhớ 10 ứng viên trước, lọc hoặc gọi tool phù hợp.
   - "so sánh tất cả ứng viên" -> phát hiện tập quá lớn, không làm ngu, mà tư vấn cách tốt hơn.

### Câu trả lời thẳng

**Có, nhưng đó là một agent runtime thật sự, không còn là "RAG chat mở rộng nhẹ" nữa.**

Muốn có hành vi này, bạn cần 3 thứ đồng thời:

1. **Conversation memory**:
   - lưu các message trước;
   - lưu tool outputs quan trọng;
   - có summary/compressed state khi hội thoại dài.

2. **Tool-use policy**:
   - model phải biết workflow nào thì gọi tool gì;
   - model phải biết giới hạn số lượng ứng viên có thể phân tích/so sánh;
   - model phải biết không load full CV hàng loạt.

3. **Controller loop**:
   - model đưa ra action/tool call;
   - backend thực thi tool;
   - backend trả tool result lại vào context;
   - model tiếp tục hoặc kết luận.

Nếu thiếu controller loop, model không thực sự "tự gọi tool". Nó chỉ "được prompt để tưởng tượng" rằng có tool, và đó là thiết kế sai.

## The Key Architecture Gap In Current Code

### Current state

Code hiện tại có:

- `app/services/rag_orchestrator.py`
- `app/services/rag_model_adapters.py`
- `invoke_generation(messages, model_mode)`

Nhưng lớp này chỉ làm:

1. nhận messages,
2. gọi một model text generation,
3. trả về text response.

Nó **không có**:

1. tool schema/registry,
2. tool call plan/result loop,
3. structured tool invocation protocol,
4. conversation state machine cho agent,
5. tool execution budget/step budget.

### What this means

Nếu bạn chọn C3, bạn sẽ cần **một runtime mới**, ví dụ:

- `app/services/jobposting_agent_runtime.py`

Nó không thay thế `invoke_generation()`, mà dùng `invoke_generation()` hoặc provider-specific calls như một phần của agent loop.

## Recommended C3 Shape

### C3.1 - Dedicated tables + single-agent runtime + minimal tools

Đây là hướng tôi khuyên.

#### Thành phần

1. **Dedicated tables**
   - `AIJOBPOSTINGCHATCONVERSATION`
   - `AIJOBPOSTINGCHATMESSAGE`
   - `AIJOBPOSTINGTOOLCALLLOG`
   - optional: `AIJOBPOSTINGCHATSTATE`

2. **Minimal read-only tools**
   - `get_job_posting_context(job_post_id)`
   - `get_job_candidate_ranking(job_post_id, limit, filters)`
   - `search_job_applications_text(job_post_id, query, limit, filters)`
   - `get_job_application_summary(job_app_id)`
   - `get_job_application_full_cv(job_app_id)`
   - `get_candidate_ats_history(job_app_id)`
   - `count_job_applications(job_post_id, filters)` hoặc count embedded trong ranking/search

3. **Agent runtime/controller**
   - receive user message
   - load conversation memory
   - ask model for next action
   - execute tool
   - append tool result
   - repeat up to max steps
   - ask model for final answer

4. **Guardrails**
   - max tool steps
   - max candidates analyzed deeply
   - max full CV loads per turn
   - max comparison set size

### Tại sao phải có count/limit guardrail

Ví dụ "so sánh tất cả ứng viên" là test rất hay.

Hệ thống nên làm:

1. xác định hoặc gọi tool biết số lượng ứng viên trong phạm vi;
2. nếu số lượng quá lớn, **không cố phân tích**;
3. trả lời:
   - số lượng hiện tại quá lớn để so sánh chi tiết một cách hữu ích;
   - đề xuất dùng top N, ranking, hoặc bộ lọc cụ thể như skill/language/experience/status.

Đó là behavior đúng của agent production-minded.

## Dedicated Tables Design

### 1. `AIJOBPOSTINGCHATCONVERSATION`

Fields nên có:

- `conversationId UUID PK`
- `jobPostId INT NOT NULL`
- `hrId INT NOT NULL`
- `createdAt`
- `lastMessageAt`
- optional `status`
- optional `summaryVersion`

Mục đích:

- gắn một conversation vào đúng một `jobPostId`;
- tách hẳn khỏi `AICHATCONVERSATION` theo `jobAppId`.

### 2. `AIJOBPOSTINGCHATMESSAGE`

Fields nên có:

- `messageId SERIAL PK`
- `conversationId UUID`
- `role` = user | assistant | system | tool
- `content TEXT`
- `model`
- `modelMode`
- `latencyMs`
- `fallbackPath`
- `summarized BOOLEAN`
- `createdAt`

Điểm khác:

- `tool` nên là role hợp lệ hoặc lưu thành message type riêng.
- Message tool giúp reconstruct context.

### 3. `AIJOBPOSTINGTOOLCALLLOG`

Fields gợi ý:

- `toolCallId SERIAL PK`
- `conversationId UUID`
- `messageId INT NULL`
- `jobPostId INT`
- `hrId INT`
- `toolName`
- `toolInput JSONB`
- `toolOutputMeta JSONB`
- `status`
- `latencyMs`
- `createdAt`

Không nên log full CV/email content raw nếu không thật sự cần.

### 4. Optional `AIJOBPOSTINGCHATSTATE`

Nếu bạn muốn memory tốt hơn:

- `conversationId`
- `stateJson`
- `updatedAt`

State có thể chứa:

- working set hiện tại, ví dụ top 10 `jobAppId`;
- active filters, ví dụ `english >= C`;
- last ranking result ids;
- comparison target ids;
- summary of prior turns.

Đây là điểm rất hữu ích cho các câu kiểu "trong 10 ông này..." mà bạn vừa mô tả.

## Memory Design

### "Bộ nhớ" bạn muốn không nên hiểu là gì

Không nên hiểu memory là:

- fine-tune model;
- nhồi toàn bộ lịch sử chat dài vô hạn vào prompt;
- để model tự nhớ theo cảm giác.

### Memory đúng cho use case này là

1. **Short-term message history**
   - vài lượt chat gần nhất.

2. **Structured conversation state**
   - ví dụ:
     - current candidate set = `[101, 205, ...]`
     - current ranking scope = top 10 of job 55
     - current filters = english >= C

3. **Optional summary**
   - khi hội thoại dài, summarize old turns.

### Điều này giải quyết đúng ví dụ của bạn

Turn 1:

- HR: "Phân tích 10 ứng viên rank cao nhất"
- system:
  - gọi ranking tool limit 10
  - lưu working set top10 vào `stateJson`

Turn 2:

- HR: "Trong 10 ông này lọc ra tiếng anh hạng C trở lên"
- system:
  - đọc `stateJson`
  - biết "10 ông này" là working set trước
  - áp thêm filter hoặc gọi tool phù hợp
  - cập nhật working set mới

Turn 3:

- HR: "So sánh tất cả ứng viên"
- system:
  - biết scope hiện tại là job-level hay current set;
  - nếu user ám chỉ toàn bộ ứng viên của job, gọi count hoặc read count;
  - nếu 789, refuse politely and redirect to narrower workflow.

## Tooling You Actually Need For Your Examples

### Example 1 - "Phân tích 10 ứng viên rank cao nhất"

Tool path:

1. `get_job_posting_context(job_post_id)`
2. `get_job_candidate_ranking(job_post_id, limit=10, filters={})`
3. For top subset only:
   - `get_job_application_summary(job_app_id)` for each selected candidate
4. Optional:
   - if one candidate needs deep evidence -> `get_job_application_full_cv(job_app_id)`

System behavior:

- Không nên load full CV cho cả 10 ngay.
- Dùng ranking + summary làm default.

### Example 2 - "Trong 10 ông này phải có tiếng Anh hạng C trở lên"

Đây là ví dụ cho thấy bạn nên có **structured state**.

Bạn có 2 đường:

1. **Tool filter trực tiếp**
   - `filter_candidate_set_by_language(candidate_set, min_level)`

2. **Agent composition**
   - đọc working set top10;
   - gọi summary/structured candidate data;
   - lọc theo language field.

Khuyến nghị:

- Phase đầu đừng làm tool quá generic như `filter_anything`.
- Hãy có structured data trong summary để agent lọc được một số điều phổ biến.

Nếu ranking/enrichment hiện chưa normalize language đủ tốt, đây là dependency/risk thật.

### Example 3 - "So sánh tất cả ứng viên"

Đây là nơi cần **guardrail + count + UX policy**.

Agent phải làm:

1. xác định tập mục tiêu là gì;
2. gọi count hoặc ranking metadata;
3. nếu quá lớn:
   - từ chối so sánh chi tiết tất cả;
   - đề xuất:
     - top 10/top 20,
     - lọc theo skill,
     - lọc theo level/language/status.

Muốn làm được vậy, system prompt cần explicit rule:

- nếu set size vượt threshold X, không so sánh chi tiết; chuyển người dùng sang refine/filer/rank flow.

## Tool-Calling Runtime Options

### Option R1 - Fake tool calling bằng text JSON loop

Mô tả:

- prompt model trả JSON như:
  - `{"action":"call_tool","tool":"get_job_candidate_ranking","args":{...}}`
- backend parse JSON
- execute tool
- feed back result

Ưu điểm:

- Có thể reuse layer generation hiện tại.
- Không cần native tool-calling SDK ngay.

Nhược điểm:

- Dễ brittle hơn.
- Parse fail/rule fail nhiều hơn native tool calling.

### Option R2 - Native tool calling, single provider first

Mô tả:

- agent runtime dùng một provider/model chuyên cho JobPosting Agent hỗ trợ tool/function calling.
- chat cũ vẫn dùng `invoke_generation()`.

Ưu điểm:

- Hành vi "tự gọi tool" chắc hơn.
- Dễ scale logic agent hơn.

Nhược điểm:

- Bỏ tính đồng nhất `7 modelMode` cho flow agent phase đầu.
- Cần code path riêng cho provider đó.

### Khuyến nghị

Nếu mục tiêu của bạn là **prototype đáng tin**, tôi nghiêng về:

**R2 cho agent mode**, nhưng chỉ với **một model/provider** trước.

Nếu mục tiêu là spike kỹ thuật nhanh:

**R1** có thể đủ để prove concept.

Điểm tôi không khuyên:

- cố support tool calling đồng thời cho toàn bộ registry multi-provider hiện có ngay từ đầu.

## Skills, Prompting, And "Teaching The Model"

### "Dạy skill" nên hiểu đúng

Không phải fine-tune weights.

Nên tách thành:

1. **System rules**
   - scope, grounding, no-bulk-CV, no huge compare.

2. **Tool affordance descriptions**
   - mỗi tool làm gì, input gì, giới hạn gì.

3. **Few-shot examples**
   - top 10 -> rank tool.
   - refine within previous set -> use memory/state.
   - huge compare -> refuse + suggest narrow.

4. **Output contract**
   - format phân tích cho HR.

5. **Guardrails in controller**
   - model không được tự phá giới hạn, dù prompt có tệ.

### Bạn muốn model "tự biết"

Thực tế production:

- model "tự biết" một phần nhờ prompt/examples;
- backend "ép biết" phần còn lại qua controller rules và hard limits.

Đây là khác biệt giữa demo agent và hệ thống dùng được.

## What You Will Likely Need To Build

Nếu chọn C3 như bạn nói, khối lượng việc dự tính gồm:

### 1. Schema

- migration cho 3 bảng dedicated tables
- indexes
- maybe state table

### 2. Models

- request/response model mới cho JobPosting agent
- message/tool-call models
- state model

### 3. Tool layer

- ít nhất 5-6 tools usable
- source metadata + warnings
- count/guardrail support

### 4. Agent runtime

- tool registry
- tool selection loop
- step budget
- memory/state update
- final answer step

### 5. Prompt assets

- system prompt
- tool descriptions
- maybe few-shot examples

### 6. API route

- query endpoint
- get conversation/messages endpoint nếu muốn UI chat

### 7. Tests

- unit tests tool layer
- unit tests runtime/controller
- API tests
- some eval-lite/manual scenarios

### 8. UI contract

Nếu muốn pane chat bên phải:

- frontend sẽ cần conversation id
- message list
- maybe tool/debug status if useful
- handling long-running multi-step responses

## What The Outcome Looks Like If Done Well

### Outcome giai đoạn đầu

Sau C3 phase đầu làm tốt, bạn sẽ có:

1. HR có thể chat trên phạm vi `jobPostId`.
2. Chat nhớ ngữ cảnh hội thoại trước qua message history + state.
3. Hệ thống biết làm top N analysis, refine set, drill-down một ứng viên.
4. Hệ thống biết từ chối những yêu cầu quá lớn theo cách hữu ích.
5. Mọi câu trả lời có grounding tốt hơn vì dựa trên tool outputs.

### Outcome chưa nên kỳ vọng ngay

Bạn chưa nên kỳ vọng:

1. multi-provider tool calling hoàn chỉnh;
2. compare 100 ứng viên đẹp và rẻ;
3. write-back ATS/email/offer;
4. perfect memory vô hạn;
5. no-hallucination tuyệt đối.

## Suggested Phased Build

### Phase 1 - C3 foundation

- dedicated conversation tables
- minimal tool layer
- count + working set state
- one-shot plus follow-up turns

### Phase 2 - thin runtime

- query route
- tool-call loop
- summary-first/full-CV-last rule
- topN/refine/too-large guardrails

### Phase 3 - usability hardening

- state compression/summarization
- language/filter improvements
- richer tool-call logging
- frontend chat pane integration

### Phase 4 - optional sophistication

- compare flow
- better tool planner
- MCP or framework adapter
- maybe write actions much later

## Open Questions You Should Decide Before Coding

1. Agent mode phase đầu dùng **một provider/model riêng** hay cố dùng lại toàn bộ `modelMode` hiện tại?
2. Bạn có muốn tool calling native ngay không, hay chấp nhận JSON-loop controller trước?
3. Có cần `AIJOBPOSTINGCHATSTATE` không? Tôi nghiêng về **có**.
4. `working set` mặc định lưu theo `jobAppId[]` hay candidate id? Tôi nghiêng về **jobAppId[]**.
5. Limit mặc định cho "phân tích top N" là bao nhiêu nếu HR không chỉ rõ?
6. Threshold nào thì refuse compare? Ví dụ > 20 hoặc > 30.
7. Language filter có cần normalized field đáng tin ngay bây giờ không, hay chấp nhận heuristic/raw parsed data phase đầu?
8. UI phase đầu có cần show "agent đang lọc/ranking/đọc CV" không, hay chỉ show final answer?
9. Có cần route lấy conversation history/messages cho frontend không?
10. Có chấp nhận agent phase đầu chỉ support `auto-pro` hoặc một `agent-pro` mode riêng không?

## Recommended Final Call

Nếu bạn thực sự nghiêng về **C3 + Dedicated JobPosting conversation tables**, tôi khuyên chốt như sau:

1. **Có**, đó là nền đúng nếu bạn muốn một chat pane thật sự theo `JobPosting`.
2. **Nhưng** hãy coi đây là một mini-agent system, không phải chỉ là thêm table và prompt.
3. Phase đầu nên làm:
   - dedicated tables,
   - working-set/state memory,
   - minimal tool set,
   - one agent runtime riêng,
   - 3 workflow đầu tiên thật chắc.
4. Không nên phase đầu:
   - hỗ trợ full compare trên tập lớn,
   - multi-provider tool calling,
   - write actions,
   - generalized chat refactor.

Nếu bạn muốn, bước tiếp theo hợp lý nhất là tôi viết tiếp cho bạn một **implementation blueprint cực cụ thể** cho C3: file/schema nào tạo trước, route nào, runtime loop nào, state JSON nên có gì, và thứ tự code 1-2-3-4 để bạn bắt tay vào làm luôn.


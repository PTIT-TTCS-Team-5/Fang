# JobApplication Full-CV Chat Decision Analysis

Ngày lập: 2026-05-27  
Phạm vi: FANG AI core, luồng chat trên một `JobApplication`

## Executive Summary

**Khuyến nghị chiến lược: nên làm `JobApplication Full-CV Chat`, nhưng chỉ làm như một bounded single-candidate assistant, không nâng thành JobPosting Agent hoặc agent framework trong cùng pha.**

Lý do chính: với phạm vi một `JobApplication`, CV đủ nhỏ để đưa toàn bộ markdown vào context, nên fixed top-k chunk RAG đang tạo ra độ phức tạp không cần thiết và có nguy cơ thiếu evidence khi HR hỏi các câu cần nhìn toàn CV. Chuyển sang full-CV giúp câu trả lời ổn định hơn, dễ giải thích hơn, dễ test hơn, và phù hợp với quyết định đã ghi trong `FANG_NEXT_PHASE_DECISIONS.md`.

**Quyết định nên chốt ở mức chiến lược:**

1. Làm full-CV chat trong phase này.
2. Không xóa ingestion/chunking/embedding/AIDOCUMENTCHUNK vì các phần đó vẫn cần cho ranking, search và các use case khác.
3. Data source phase đầu: rebuild markdown tại query time từ `CVPARSED.parsedJson` bằng `convert_json_to_markdown()`.
4. Nếu `parsedJson` lỗi hoặc legacy không validate được, fallback có kiểm soát sang `CVPARSED.rawText`.
5. Prompt mới phải coi CV/JD/ATS/email/offer là untrusted input, giới hạn phạm vi trả lời vào tuyển dụng và evidence có trong context.
6. Context budget phải tính cả system prompt, full CV, history và user prompt. Khi vượt ngưỡng, không âm thầm gọi LLM.
7. Giữ API backward-compatible tối đa: `topK` vẫn có thể trả về để không làm hỏng client, nhưng semantic nên chuyển thành `0` hoặc giá trị legacy được giải thích trong docs.

**Option đề xuất:** chọn **Option C - Full-CV bounded implementation**. Đây là điểm cân bằng tốt nhất giữa giá trị HR, chi phí implement, rủi ro architecture và khả năng giao cho một thành viên thực thi.

**Không nên chọn trong phase này:**

- Không giữ nguyên top-k RAG như kiến trúc lâu dài, vì trái với mục tiêu chất lượng JobApplication chat.
- Không mở JobPosting Agent trong cùng package, vì đây là bài toán nhiều ứng viên, tool/retrieval/permission khác hẳn.
- Không đưa LangGraph/MCP/agent framework vào `JobApplication Full-CV Chat`, vì hiện tại không cần orchestration phức tạp.

**Mức độ ưu tiên:** nên làm sau P0-C/doc reconciliation baseline và song song chặt với P1-A/P1-B ở phần prompt/eval. Nếu nguồn lực hạn chế, làm backend + tests + strategy/guide trước, UI/client chỉ chỉnh wording và schema compatibility tối thiểu.

## Current Reality

### Kiến trúc hiện tại

Theo knowledge graph và code hiện tại, FANG là FastAPI AI core cho miCareer, gồm các luồng chính:

- CV ingestion: parse CV, build markdown/chunks, embed và lưu vào PostgreSQL/pgvector.
- RAG chat: nhận câu hỏi HR trên một `JobApplication`, retrieve top-k chunk, ghép context và gọi LLM.
- NMAIex ranking: dùng dữ liệu CV/job/skill/ranking riêng, vẫn cần embedding và chunk artifacts.
- Chat persistence: lưu conversation, message, query log và summary.

Các entry point liên quan:

- `app/api/routes_chat.py`: route `/chat/query`, conversation list, messages, summarize, branch-new.
- `app/services/rag_query.py`: pipeline chat hiện tại.
- `app/services/rag_orchestrator.py`: gọi generation theo model mode.
- `app/services/rag_model_adapters.py`: registry 7 `modelMode`, provider adapters và budget group.
- `app/services/markdown_builder.py`: có sẵn `convert_json_to_markdown(parsed_cv)`.
- `app/services/chat_persistence.py`: lưu conversation/message/query log.
- `database/schema_ai_core.sql`: `AIINDEXJOB`, `CVPARSED`, `AIDOCUMENTCHUNK`, `AIQUERYLOG`, `AICHATCONVERSATION`, `AICHATMESSAGE`.
- `database/schema_web_core.sql`: `JOBPOSTING`, `JOBAPPLICATION`, `CANDIDATE`, `CANDIDATESKILL`, `INTERVIEW`, `INTERVIEWFEEDBACK`, `OFFER`, `EMAILLOG`.

### Luồng chat hiện tại

`process_chat_query()` trong `app/services/rag_query.py` đang làm:

1. Kiểm tra `AIINDEXJOB` mới nhất của `jobAppId` phải `SUCCESS`.
2. Load hoặc tạo conversation.
3. Lưu user message.
4. Embed prompt bằng `embed_chunks([prompt])`.
5. Vector search trên `AIDOCUMENTCHUNK`.
6. Fetch thêm job posting, candidate profile, ATS interview feedback.
7. Build system prompt với `[NỘI DUNG CV - Top K]`.
8. Check context budget chỉ trên history.
9. Gọi LLM.
10. Lưu assistant message và `AIQUERYLOG`.

Điểm lệch quan trọng: quyết định next phase nói JobApplication chat sẽ dùng full CV markdown, nhưng code runtime vẫn là fixed top-k chunk RAG.

### Drift/risk đã được P0-A/P0-B/P0-C ghi nhận

Các report hiện tại đã nêu các điểm cần xử lý:

- JobApplication chat full-CV đã được quyết định nhưng chưa implement.
- Multi-source context thực tế hẹp hơn docs: code chỉ có title/description, candidate basic fields, interview feedback; chưa có skills, salary/work mode/level, offer, email.
- Context budget hiện chỉ tính history, không tính system prompt/full context.
- Khi budget warning xảy ra, code vẫn gọi LLM.
- Prompt HR co-pilot là prompt ưu tiên cao nhất trong P1-A vì user-facing, nhiều dữ liệu untrusted và ảnh hưởng trực tiếp tới quyết định HR.
- Tests RAG/chat còn thiếu; cần thêm unit test cho behavior mới thay vì chỉ cập nhật docs.

## Strategic Question

Câu hỏi không chỉ là "đổi top-k sang full CV" mà là:

**FANG có nên tối ưu luồng chat một ứng viên bằng full CV context trước, hay giữ RAG hiện tại/chuyển thẳng sang agent/tool architecture rộng hơn?**

Để quyết định, cần tách 3 bài toán:

1. **JobApplication Chat:** một ứng viên, một CV, một job application, cần hỏi đáp sâu trên hồ sơ đó.
2. **Ranking/Search:** nhiều ứng viên, cần embedding/retrieval/ranking để tìm hoặc so sánh.
3. **JobPosting Agent:** một job posting, nhiều ứng viên, cần tool retrieval, filtering, comparison, permission và audit rộng hơn.

Full-CV Chat phù hợp với bài toán 1. Nó không thay thế bài toán 2 và không nên bị kéo vào bài toán 3 trong phase đầu.

## Decision Criteria

Nên đánh giá các lựa chọn theo các tiêu chí sau:

| Tiêu chí | Ý nghĩa |
|---|---|
| HR value | HR có nhận câu trả lời đầy đủ hơn, ít miss evidence hơn không |
| Architecture fit | Có đi cùng kiến trúc hiện tại mà không refactor lớn không |
| Risk containment | Có giới hạn blast radius ở một luồng API/service không |
| Data correctness | Context có đầy đủ và có fallback rõ không |
| Prompt safety | Có chống prompt injection và scope abuse tốt hơn không |
| Testability | Có thể viết unit tests/smoke tests rõ không |
| UI/API compatibility | Có phá miCareer-mini hoặc Postman flow không |
| Future extensibility | Có mở đường cho JobPosting Agent mà không trói sai kiến trúc không |

## Options

### Option A - Giữ nguyên fixed top-k chunk RAG

Mô tả: không đổi kiến trúc chat, chỉ cải thiện prompt/budget/docs nhỏ.

Ưu điểm:

- Ít code change nhất.
- Không động vào pipeline chat nhiều.
- Top-k có lợi nếu CV rất dài hoặc nhiều source document.
- Giữ nguyên ý nghĩa `topK` và query log.

Nhược điểm:

- Trái với quyết định đã chốt trong `FANG_NEXT_PHASE_DECISIONS.md`.
- HR hỏi câu tổng hợp toàn CV có thể thiếu evidence vì top-k chỉ lấy vài chunk gần prompt nhất.
- Câu trả lời dễ phụ thuộc embedding quality, chunk boundary và query wording.
- Vẫn phải sửa prompt injection/context budget, nên không thật sự "không làm gì".
- Không giải quyết drift docs-code hiện tại.

Khi nào chọn:

- Chỉ chọn nếu phát hiện CV production quá dài để full context không khả thi, hoặc model budget/chi phí không đáp ứng.
- Hiện tại chưa có bằng chứng đủ mạnh để chọn hướng này.

Đánh giá: **không khuyến nghị làm hướng lâu dài**.

### Option B - Minimal Full-CV Chat

Mô tả: chỉ thay top-k chunks bằng full CV markdown, giữ nguyên phần lớn prompt/API/budget.

Ưu điểm:

- Đạt mục tiêu chính nhanh.
- Ít thay đổi hơn Option C.
- Dễ giao cho tier 2 nếu spec đủ rõ.

Nhược điểm:

- Nếu không sửa prompt scope, HR vẫn có thể hỏi ngoài phạm vi và model có thể trả lời những thứ không liên quan tuyển dụng.
- Nếu không sửa budget, full CV làm rủi ro context lớn nghiêm trọng hơn.
- Nếu không xử lý untrusted context, prompt injection từ CV/JD/email vẫn còn.
- Nếu không bổ sung tests đúng, có thể chỉ đổi source context nhưng không bảo chứng behavior.

Khi nào chọn:

- Chọn khi cần demo rất nhanh, có chấp nhận debt rõ ràng.
- Phải tạo follow-up bắt buộc cho prompt/budget/security ngay sau đó.

Đánh giá: **không nên chọn nếu mục tiêu là quyết định chiến lược bền vững**.

### Option C - Full-CV Bounded Implementation

Mô tả: chuyển JobApplication chat sang full CV markdown, đồng thời sửa prompt policy, fallback, budget behavior, tests và docs trong phạm vi một ứng viên.

Đây là option khuyến nghị.

Thành phần chính:

- Bỏ embed prompt + vector search trong luồng `process_chat_query()` cho JobApplication chat.
- Fetch `CVPARSED.parsedJson`; validate bằng `ParsedCV`; convert bằng `convert_json_to_markdown()`.
- Fallback sang `rawText` nếu parsed JSON lỗi, có warning/log rõ.
- Fetch job posting/candidate/ATS context tốt hơn nhưng giữ scope đọc dữ liệu.
- Thêm offer/email nếu schema và budget cho phép; nếu chưa đưa vào được thì report lý do.
- Build system prompt mới theo block context rõ ràng.
- Tính budget trên toàn bộ message payload: system prompt + full CV + history + user prompt.
- Nếu vượt hard threshold, trả deterministic response/contextWarning, không gọi LLM.
- Giữ schema response tương thích nhất có thể.
- Bổ sung unit tests cho context source, no vector search, fallback rawText, budget và prompt blocks.

Ưu điểm:

- Giải quyết đúng vấn đề chất lượng chat một ứng viên.
- Giảm phụ thuộc embedding/chunk quality ở use case không cần retrieval.
- Blast radius nhỏ: tập trung `rag_query.py`, model/schema chat nếu cần, docs/tests.
- Tái dùng `markdown_builder.py`, không cần migration DB.
- Giữ đường lui: `AIDOCUMENTCHUNK` vẫn còn cho ranking/search.
- Tạo nền tốt cho P1-A/P1-B review prompt và eval.

Nhược điểm:

- Cần sửa nhiều hơn Option B.
- Cần quyết định kỹ behavior khi context quá lớn.
- Có thể phải chỉnh `topK` semantics để không làm client hiểu sai.
- Phải làm tests nghiêm túc vì đổi core chat path.

Khi nào chọn:

- Chọn nếu mục tiêu là ship feature đúng kiến trúc và giảm drift hiện tại.
- Phù hợp nhất với tình hình FANG hiện tại.

Đánh giá: **khuyến nghị chọn**.

### Option D - Hybrid Full-CV + On-demand Retrieval

Mô tả: full CV là context chính, nhưng vẫn giữ tool hoặc retrieval phụ để tìm chunk khi cần.

Ưu điểm:

- Linh hoạt nếu CV dài hoặc có nhiều document phụ.
- Có thể là stepping stone cho tool-based retrieval về sau.

Nhược điểm:

- Dễ phức tạp hóa quá sớm.
- Vẫn phải quyết định khi nào dùng full, khi nào retrieve.
- Nếu làm trong cùng phase, có nguy cơ biến JobApplication chat thành mini-agent không cần thiết.
- Test matrix phình ra.

Khi nào chọn:

- Chọn ở phase sau nếu có bằng chứng CV/context thường vượt budget.
- Chọn nếu có thêm nhiều artifact ngoài CV mà không thể nhét hết vào prompt.

Đánh giá: **để sau**, không phải phase đầu.

### Option E - Mở JobPosting Agent luôn

Mô tả: bỏ qua single-candidate bounded chat, xây agent/tool layer cho job posting và candidate pool.

Ưu điểm:

- Hấp dẫn về sản phẩm nếu HR muốn hỏi trên toàn bộ pipeline tuyển dụng.
- Có thể tận dụng ranking, search, full CV, filters và comparison.

Nhược điểm:

- Bài toán khác hẳn JobApplication chat.
- Cần tool boundary, permissions, audit, failure semantics, possibly human approval.
- Dễ refactor quá rộng và làm chậm feature nhỏ đang rõ.
- Có nguy cơ kéo LangGraph/MCP/framework vào trước khi domain tool layer đủ chín.

Khi nào chọn:

- Chỉ sau khi có JobPosting Agent Decision memo riêng.
- Không nên gộp với Full-CV Chat.

Đánh giá: **không chọn cho phase này**.

## Recommended Decision

Chọn **Option C - Full-CV Bounded Implementation**.

Quyết định nên được diễn đạt như sau:

> Với chat trên một `JobApplication`, FANG sẽ dùng full CV markdown context làm source chính thay cho fixed top-k chunk RAG. Thay đổi này chỉ áp dụng cho single-candidate JobApplication chat. Ingestion, chunking, embedding và `AIDOCUMENTCHUNK` vẫn được giữ cho ranking/search/use case khác. Phase đầu rebuild markdown tại query time từ `CVPARSED.parsedJson`, fallback có kiểm soát sang `rawText`, và bổ sung prompt/budget/tests/docs tương ứng.

## Scope Boundary

### In scope

- Backend chat path cho `/v2/chat/query`.
- Full CV markdown context source.
- Fallback `parsedJson -> rawText -> clear error`.
- Job posting context có field hiện có: title, description, salary, work mode, location, level/category/skills nếu query được gọn.
- Candidate context: basic profile và skills.
- ATS context: interview feedback, offer, email log nếu giới hạn nội dung được.
- Prompt policy cho single-candidate HR assistant.
- Context budget behavior tính cả full prompt.
- Query/message logging tương thích.
- Unit tests và smoke checklist.
- Strategy/guide docs sau khi implement.
- miCareer-mini compatibility check.

### Out of scope

- JobPosting Agent.
- Multi-candidate comparison agent.
- MCP/LangGraph/LangChain framework integration.
- Xóa chunking/embedding.
- Migration lưu `cvMarkdown` trong DB ở phase đầu.
- Prompt review toàn hệ thống.
- Write tools cập nhật ATS/email/offer.

## Architecture Recommendation

### Data source

Phase đầu nên dùng query-time rebuild:

1. Query `CVPARSED` theo `jobAppId`.
2. Nếu `parsedJson` có dữ liệu:
   - validate bằng `ParsedCV.model_validate(parsedJson)`;
   - convert bằng `convert_json_to_markdown(parsed_cv)`.
3. Nếu validate/convert lỗi:
   - dùng `rawText` nếu có;
   - ghi log warning với `jobAppId`, `cvParsedId`, `parserVer`, error class;
   - đánh dấu context source là `raw_text_fallback`.
4. Nếu không có `parsedJson` hợp lệ và không có `rawText`:
   - trả lỗi rõ;
   - không gọi LLM với context rỗng.

Không nên thêm cột `cvMarkdown` ngay vì:

- Cần migration và lifecycle invalidation khi parser/markdown format đổi.
- `markdown_builder.py` đã có sẵn.
- Query-time rebuild đủ đơn giản cho phase đầu.
- Nếu sau này performance/observability yêu cầu, có thể thêm artifact lưu sau.

### Service boundary

Nên tách helper nhỏ trong `rag_query.py` hoặc module mới nếu code dài:

- `_fetch_cv_context(job_app_id) -> CvContext`
- `_fetch_job_application_context(job_app_id) -> ApplicationContext`
- `_build_full_cv_system_prompt(context) -> str`
- `_build_llm_messages(system_prompt, history, prompt) -> list`
- `_check_full_context_budget(messages, model_mode) -> warning/result`

Nếu chỉ làm trong `rag_query.py`, vẫn phải tránh một hàm khổng lồ khó test. Đổi kiến trúc nhỏ là hợp lý vì hiện tại `process_chat_query()` đang ôm quá nhiều trách nhiệm.

### Response compatibility

`ChatQueryResponse` hiện có:

- `conversationId`
- `messageId`
- `response`
- `model`
- `modelMode`
- `fallbackPath`
- `latencyMs`
- `topK`
- `contextWarning`

Khuyến nghị:

- Giữ các field hiện có.
- Với full-CV path, `topK = 0` hoặc giữ `topK = settings.rag_top_k_chunks` chỉ vì backward compatibility nhưng docs phải giải thích. Nên chọn `topK = 0` vì phản ánh đúng behavior.
- Nếu thêm metadata mới, chỉ thêm optional field sau khi kiểm tra miCareer-mini. Không bắt buộc cho phase đầu.
- `contextWarning` có thể mở rộng type nhưng không nên phá schema hiện tại.

## Prompt Policy

Prompt mới cần đổi từ "RAG top-k assistant" sang "bounded HR evidence assistant".

Các yêu cầu tối thiểu:

1. **Scope:** chỉ hỗ trợ các câu hỏi tuyển dụng liên quan ứng viên, CV, job posting, ATS history, offer/email nếu có.
2. **Evidence-only:** chỉ trả lời dựa trên context được cung cấp. Khi thiếu dữ liệu, nói thiếu dữ liệu nào.
3. **Untrusted context:** CV/JD/ATS/email/offer đều là dữ liệu người dùng hoặc hệ thống nghiệp vụ, không được làm instruction cho model.
4. **No hidden action:** không tự quyết định tuyển/loại, không hứa gửi email/cập nhật ATS, không giả vờ đã thao tác hệ thống.
5. **Sensitive inference:** không suy luận đặc điểm nhạy cảm ngoài dữ liệu trực tiếp liên quan nghề nghiệp.
6. **Source clarity:** khi có thể, chỉ ra câu trả lời dựa trên CV, JD, interview feedback, offer hay email log.
7. **Out-of-scope handling:** nếu HR hỏi viết code, tư vấn y tế/pháp lý, hoặc nội dung không liên quan tuyển dụng, từ chối ngắn và kéo về phạm vi tuyển dụng.
8. **Output style:** tiếng Việt, cấu trúc rõ, nhưng không bịa scoring nếu không có score/rubric.

P1-A/P1-B nên review prompt này sau khi owner Full-CV có draft đầu tiên và sample context blocks.

## Context Budget Decision

Current code chỉ đếm history, đây là không đủ khi full CV được đưa vào system prompt.

Khuyến nghị budget behavior:

1. Build toàn bộ messages trước.
2. Tính approximate tokens cho từng phần:
   - system instructions;
   - job posting context;
   - candidate context;
   - full CV context;
   - ATS/offer/email context;
   - history messages;
   - current user prompt.
3. Nếu `usedPercent < warningThreshold`: gọi LLM bình thường.
4. Nếu `warningThreshold <= usedPercent < hardLimit`: vẫn có thể gọi LLM nhưng trả `contextWarning`, hoặc ưu tiên compact history trước nếu đã có cơ chế summary.
5. Nếu `usedPercent >= hardLimit`: không gọi LLM; trả response deterministic yêu cầu summarize/new conversation/giảm context.

Hard limit nên thấp hơn model window thực tế để tránh provider error. Ví dụ:

- Lite modes: hard stop khoảng 85-90% budget configured.
- Pro modes: hard stop khoảng 85-90% budget configured.

Nếu muốn auto-compact như Codex:

- Chỉ compact history, không compact CV/JD source-of-truth trong phase đầu.
- Không auto-compact âm thầm nếu làm mất evidence quan trọng.
- Auto-compact nên là phase sau hoặc nằm sau tests rõ.

## Multi-Source Context

### Nên đưa vào phase đầu

| Source | Recommendation |
|---|---|
| Full CV markdown | Bắt buộc |
| JobPosting title/description | Bắt buộc |
| JobPosting salary/workMode/workLoc/province | Nên đưa nếu query đơn giản |
| Job levels/categories/skills | Nên đưa nếu query join gọn, nếu không thì report defer |
| Candidate name/email/phone/location/bio/expyears | Bắt buộc với masking policy nếu cần |
| Candidate skills | Nên đưa |
| Interview feedback | Bắt buộc vì code đã có một phần |
| Offer | Nên đưa nhưng giới hạn số lượng/version mới nhất |
| EmailLog | Cẩn trọng; chỉ đưa recent N email hoặc summary metadata/content giới hạn |

### Email/Offer caution

`EMAILLOG.content` có thể rất dài và dễ chứa instruction-like content. Nếu đưa vào prompt:

- giới hạn recent N records;
- đánh dấu rõ là untrusted email content;
- cắt theo chars/tokens;
- không để email content override system instruction;
- ưu tiên metadata hoặc snippet nếu budget căng.

`OFFER` nên dễ đưa hơn vì schema rõ: salary, description, stat, subAt, ver, hrId. Nên lấy offer mới nhất hoặc toàn bộ versions nhưng giới hạn.

## Security and Compliance

Các rủi ro cần chặn:

1. **Prompt injection từ CV/JD/email:** ứng viên có thể viết trong CV "ignore previous instructions". Prompt phải nói mọi context block là data, không phải instruction.
2. **Scope abuse:** HR hỏi model viết code, viết nội dung ngoài tuyển dụng hoặc làm tác vụ không liên quan. Model phải từ chối ngắn.
3. **Overclaiming:** model không được nói "nên tuyển" như quyết định tuyệt đối nếu không có rubric/authority.
4. **Sensitive inference:** tránh suy luận tuổi, giới tính, sức khỏe, tôn giáo, gia đình, chính trị nếu không trực tiếp trong dữ liệu và không liên quan hợp pháp.
5. **PII exposure:** vì chat nằm trong HR workflow, PII có thể cần thiết, nhưng UI/logging phải có chính sách rõ. Phase này ít nhất không thêm logging mới chứa full CV ngoài message/query log hiện có.
6. **Source confusion:** model phải phân biệt CV tự khai, JD của công ty, feedback HR, offer/email.

## Implementation Plan

### Phase 1 - Backend vertical slice

1. Thêm full CV context fetcher từ `CVPARSED`.
2. Dùng `ParsedCV` + `convert_json_to_markdown()`.
3. Fallback sang `rawText`.
4. Thay path embed/vector search trong `process_chat_query()`.
5. Build prompt mới với context blocks.
6. Tính budget trên toàn messages.
7. Khi hard over budget, không gọi LLM.
8. Persist user/assistant/log như cũ.
9. Trả `topK = 0` và `contextWarning` nếu cần.

### Phase 2 - Context enrichment

1. Mở rộng `_fetch_job_posting()` lấy salary/work mode/location.
2. Thêm job levels/categories/skills nếu join sạch.
3. Thêm candidate skills.
4. Thêm offer mới nhất hoặc danh sách giới hạn.
5. Thêm email log recent N với truncation.
6. Ghi rõ context source nào included/deferred trong implementation report.

### Phase 3 - Docs/tests/client

1. Unit tests cho full CV context source.
2. Unit tests xác nhận không gọi `embed_chunks()` và `_vector_search()` trong JobApplication full-CV path.
3. Unit tests fallback rawText.
4. Unit tests no-empty-context error.
5. Unit tests context budget tính cả system prompt/full CV.
6. Update strategy doc và guide doc.
7. Update RAG docs để phân biệt full-CV JobApplication chat với chunk/embedding vẫn còn cho ranking/search.
8. Check miCareer-mini wording/schema.

## Test Strategy

Tests bắt buộc trước khi xem là done:

| Test | Mục tiêu |
|---|---|
| Parsed JSON to markdown | `CVPARSED.parsedJson` hợp lệ được convert thành markdown |
| Raw text fallback | parsed JSON invalid thì dùng `rawText` và log warning |
| Empty context failure | không có usable CV context thì không gọi LLM |
| No embedding in chat path | `embed_chunks()` không được gọi cho full-CV JobApplication chat |
| No vector search in chat path | `_vector_search()` không được gọi |
| Budget includes system prompt | full CV/system prompt được tính vào token estimate |
| Over hard budget | trả deterministic warning/response, không gọi `invoke_generation()` |
| Prompt blocks | system prompt có CV/JD/ATS blocks và untrusted-input instruction |
| API compatibility | response vẫn match `ChatQueryResponse` |
| Existing smoke | `/v2/chat/query` vẫn chạy với jobAppId đã ingestion `SUCCESS` |

Không nên chỉ dựa vào smoke test vì lỗi lớn nhất của change này là behavior nội bộ: có gọi embedding/vector search hay không, có budget đúng hay không.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Full CV quá dài | Provider error/cost cao | Budget tính toàn messages, hard stop, optional history summary |
| parsedJson legacy không validate | Chat fail với dữ liệu cũ | Fallback rawText + warning |
| Prompt injection từ CV/email | Model làm sai instruction | Context delimiter + untrusted policy + eval cases |
| API client phụ thuộc `topK > 0` | UI hiểu sai hoặc lỗi | Check miCareer-mini; giữ field, set `0`, update wording |
| Offer/email làm prompt dài | Budget/cost tăng | Limit recent N, truncate, defer nếu cần |
| Scope creep sang JobPosting Agent | Chậm feature | Ghi out-of-scope rõ, decision memo riêng |
| Tests chưa đủ | Regression âm thầm | Unit tests internal behavior bắt buộc |
| Logging full context quá nhiều | PII/cost/debug risk | Không log full CV; log metadata/source/status |

## Decision Matrix

| Option | HR Value | Architecture Fit | Risk | Effort | Recommendation |
|---|---:|---:|---:|---:|---|
| A. Keep top-k RAG | Medium | Medium | Medium | Low | Không chọn |
| B. Minimal full-CV | High | Medium | High | Medium | Chỉ chọn để demo nhanh |
| C. Bounded full-CV | High | High | Medium | Medium | **Chọn** |
| D. Hybrid retrieval | High | Medium | Medium-High | High | Để sau |
| E. JobPosting Agent | Very high | Low now | High | Very high | Decision track riêng |

## Recommended Final Call

Nên chốt:

**Proceed với JobApplication Full-CV Chat theo Option C.**

Điều kiện để giao implementation:

1. Owner đọc `FANG_NEXT_PHASE_CHAT_FULL_CV_ASSIGNMENT.md`.
2. Owner không mở rộng sang JobPosting Agent/framework.
3. Owner tạo implementation report, strategy doc và guide doc sau khi sửa code.
4. P1-A/P1-B nhận draft prompt/context blocks để review sau vertical slice.
5. Nếu trong implementation phát hiện CV thực tế thường vượt budget, dừng lại báo decision thay vì tự chuyển sang hybrid/agent.

## Open Questions for User

Các câu hỏi này không chặn phase đầu, nhưng nên chốt trước khi merge production behavior:

1. `topK` trong response full-CV nên trả `0` hay giữ giá trị legacy?
2. EmailLog có nên đưa full content vào prompt không, hay chỉ recent summary/snippet?
3. Khi over hard budget, muốn behavior là deterministic warning hay auto-summarize history trước?
4. Có cần masking email/phone trong model context không, hay HR workflow được phép thấy PII đầy đủ?
5. Offer history lấy latest offer hay toàn bộ versions giới hạn?

## Suggested Assignment Wording

Nếu giao cho một thành viên, có thể giao bằng câu ngắn:

> Implement `CHAT_FULL_CV` theo Option C trong `FANG_NEXT_PHASE_CHAT_FULL_CV_DECISION_ANALYSIS.md`: chuyển `/v2/chat/query` cho JobApplication sang full CV markdown context từ `CVPARSED.parsedJson`, fallback `rawText`, không gọi embedding/vector search, thêm prompt policy/budget behavior/tests/docs, giữ chunking/embedding cho ranking/search và không mở JobPosting Agent.


# FANG Next Phase - 9Router Deep Research Prompt

## Mục Tiêu

Đánh giá khả năng dùng 9Router trong FANG sau khi đã có P0-B AI/LLM Inventory.

Trọng tâm không còn là câu hỏi chung chung "có đổi base URL được không", mà là:

1. Có thể route phần nào của FANG qua 9Router bằng thay đổi cấu hình/base URL tối thiểu?
2. Có nên tách riêng nhánh **JobPosting Agent** để chỉ nhánh đó dùng 9Router không?
3. Nếu muốn tạo bộ dữ liệu CV thật hơn, có nên chuyển CV mock/Cloudinary sang local storage và sinh PDF từ `CVPARSED.parsedJson` không?

Kết luận cần phân biệt rõ:

- phần có thể drop-in qua OpenAI-compatible endpoint;
- phần cần config-level adapter;
- phần không nên đụng trong giai đoạn này vì liên quan embedding, PDF/file upload, structured output hoặc fallback contract.

## Repo Context

- Repo: `FANG`
- Branch cần đọc: `chore/p0-abc-repo-ai-docs-audit`
- Commit đáng chú ý mới nhất: `b8d0544 feat: tách enrichment NMAIex khỏi ingestion chính`
- FANG là FastAPI AI core cho CV ingestion, embedding, RAG chat, NMAIex enrichment/ranking.
- User đã dùng 9Router để sinh synthetic data/gán nhãn và muốn tận dụng 9Router cho round-robin key, token saver, tăng tải, đặc biệt cho tác vụ agent tốn token.
- P0-B inventory đã hoàn tất và phải được coi là source chính cho caller map, prompt map, model map, failure gap.

## File Bắt Buộc Đọc

Đọc theo thứ tự này:

1. `agent_workflow_doc/P0B_AI_LLM_INVENTORY_REPORT.md`
2. `agent_workflow_doc/FANG_NEXT_PHASE_P0B_AI_LLM_INVENTORY.md`
3. `agent_workflow_doc/FANG_NEXT_PHASE_DECISIONS.md`
4. `agent_workflow_doc/FANG_NEXT_PHASE_P0A_USER_NOTE_TRIAGE.md`
5. `agent_workflow_doc/walkthrough_full_system_test.md`
6. `app/core/config.py`
7. `.env.example`
8. `requirements.txt`
9. `app/services/rag_model_adapters.py`
10. `app/services/rag_orchestrator.py`
11. `app/services/cv_parser_adapters.py`
12. `app/services/cv_parser.py`
13. `app/services/embedding.py`
14. `app/services/rag_query.py`
15. `app/services/nmaiex_mapper_service.py`
16. `app/services/nmaiex_candidate_enrichment.py`
17. `synthetic_data/run_pipeline.py`
18. `synthetic_data/prompts.py`

Nếu nghiên cứu local CV/PDF storage, đọc thêm:

19. các route ingestion/upload liên quan `cvUrl`, `cvSnapUrl`, `download_cv`, Cloudinary hoặc file download;
20. schema DB liên quan `CANDIDATE`, `JOBAPPLICATION`, `CVPARSED`, `AIINDEXJOB`.

## P0-B Findings Cần Dùng Làm Ground Truth

P0-B đã xác định các use case AI/LLM chính:

- UC-1: CV Parsing PDF -> `ParsedCV`
- UC-2: Text embedding
- UC-3: Chunking, deterministic, không gọi LLM
- UC-4: RAG chat query
- UC-5/UC-6: chat summarization/branching
- UC-7/UC-8/UC-10: NMAIex province/skill/proficiency mapper
- UC-9: raw skill embedding
- UC-11/UC-12: deterministic ranking có phụ thuộc embedding
- synthetic data pipeline, hiện đã có 9Router proxy path

P0-B cũng đã nêu các gap quan trọng:

- F1: specific generation modes bỏ qua quality gate.
- F2: embedding chỉ có Gemini, không fallback.
- F3: chat query embedding error có thể thành raw 500.
- F4/F5: province/skill mapper chưa validate ID tồn tại.
- F7: raw skill embedding có thể silent abort khi lệch vector count.
- F8: chưa có timeout LLM rõ ràng.
- O1/O4/O10: thiếu prompt versioning, token usage tracking, cost estimate.

Research phải dùng các gap này để đánh giá 9Router, không chỉ dựa vào docs marketing.

## Research Questions

### 1. 9Router hỗ trợ API surface nào liên quan FANG?

Xác minh bằng tài liệu hiện tại của 9Router hoặc source code nếu cần:

- OpenAI-compatible `/v1/chat/completions`
- OpenAI-compatible `/v1/responses`, nếu có
- OpenAI-compatible structured output / JSON schema, nếu có
- Gemini-compatible `generateContent`
- Gemini-compatible `embedContent`
- Gemini Files API upload/delete/list, nếu có
- Anthropic-compatible Messages API, nếu có
- model listing, model alias, provider routing, key round-robin, token saver
- timeout, retry, error response format, usage/token accounting

Kết luận rõ API nào là documented, API nào là suy luận từ compatibility layer, API nào chưa chắc.

### 2. Với code FANG hiện tại, phần nào chỉ cần đổi base URL/config?

Đánh giá từng module:

- `rag_model_adapters.py` OpenAI generation adapter
- `cv_parser_adapters.py` OpenAI parser adapter
- Gemini generation adapter
- Gemini parser PDF path
- Gemini embedding path
- Anthropic generation/parser adapter
- `synthetic_data/run_pipeline.py` path đang dùng 9Router

Với mỗi module, trả lời:

- có thể đổi base URL một dòng không?
- cần thêm env config nào?
- có giữ được output contract không?
- có ảnh hưởng fallback/quality gate không?
- có ảnh hưởng cost/token tracking không?

### 3. Có nên route toàn hệ thống qua 9Router ngay không?

So sánh 3 option:

- **Option A: base URL only**  
  Dùng khi provider SDK/API đang OpenAI-compatible thật sự.

- **Option B: config-level routed adapters**  
  Thêm env như `OPENAI_BASE_URL`, `OPENAI_API_KEY`, có thể thêm `ANTHROPIC_BASE_URL`, nhưng vẫn giữ adapter hiện tại.

- **Option C: unified 9Router/OpenAI-compatible LLM adapter**  
  Gom generation/parser/mappers qua một adapter OpenAI-compatible, nhưng giữ embedding và PDF parser native nếu 9Router chưa hỗ trợ chắc.

Kết luận option nào phù hợp nhất trong 2 tuần tới, dựa trên rủi ro P0-B.

### 4. JobPosting Agent-only qua 9Router

Đánh giá phương án tách riêng nhánh **JobPosting Agent** và chỉ dùng 9Router cho nhánh đó.

Bối cảnh:

- JobPosting Agent là decision track riêng, chưa nên làm nhiễu core ingestion/chat/ranking.
- Agent dự kiến tốn token hơn các path hiện tại.
- User muốn xoay giữa Google API hoặc provider khác qua 9Router.

Cần trả lời:

- Đây có phải hướng ít rủi ro hơn so với route toàn hệ thống không?
- Nên thiết kế boundary thế nào để JobPosting Agent dùng 9Router nhưng core FANG không đổi?
- Env/config đề xuất:
  - `JOBPOSTING_AGENT_LLM_PROVIDER`
  - `JOBPOSTING_AGENT_BASE_URL`
  - `JOBPOSTING_AGENT_API_KEYS`
  - `JOBPOSTING_AGENT_MODEL`
  - `JOBPOSTING_AGENT_TIMEOUT_SECONDS`
  - `JOBPOSTING_AGENT_MAX_OUTPUT_TOKENS`
- Có nên dùng OpenAI-compatible client riêng cho agent không?
- Nếu agent cần gọi tool nội bộ như search/ranking/job draft validation, nên tách LLM layer và tool layer thế nào?
- Cần log gì để đánh giá chi phí/token/latency của agent?

Output mong muốn cho phần này: recommendation rõ "nên/không nên", patch plan tối thiểu, và rủi ro còn lại.

### 5. Local CV storage + synthetic real PDF generation

Đánh giá ý tưởng:

- Hiện dataset có 500 CV mẫu nhưng nhiều CV là mock/ghi trực tiếp `CVPARSED`.
- User muốn có CV PDF thật hơn để test ingestion/RAG/chat sống động.
- Có thể dùng 9Router sinh ngược nội dung CV từ `CVPARSED.parsedJson`, sau đó render PDF local.
- User muốn cân nhắc chuyển CV lưu trữ từ Cloudinary sang local, có thể đặt trong `miCareer-mini` cùng thư mục `cur_prj` với FANG.

Cần trả lời:

- Trong code/schema hiện tại, CV file URL đang nằm ở đâu? `CANDIDATE.cvUrl`, `JOBAPPLICATION.cvSnapUrl`, hay nơi khác?
- Ingestion hiện download CV như thế nào? Có yêu cầu URL public hay chỉ cần path/local file?
- Có thể giữ DB schema dạng URL và chỉ thêm local/static URL không?
- Có nên dùng `file://`, relative path, `local://`, hay FastAPI/static public URL?
- Có nên đặt file ở FANG repo, ở `miCareer-mini`, hay thư mục shared ngoài repo?
- Thay đổi tối thiểu để hỗ trợ local storage trong dev/test là gì?
- Thay đổi nếu muốn thay Cloudinary production hoàn toàn là gì?
- Pipeline sinh PDF nên nằm ở FANG hay synthetic tooling?
- Nên dùng 9Router cho phần sinh nội dung nào, và dùng renderer local nào cho PDF?

Output mong muốn:

- Complexity estimate: dev/test local only vs production replacement.
- Minimal migration plan không phá dataset hiện có.
- Các field DB cần update/backfill.
- Rủi ro bảo mật khi serve local PDF.

## Compatibility/Risk Checklist

Khi đánh giá 9Router, bắt buộc kiểm tra:

- structured output/schema validation với `ParsedCV`
- PDF/file upload cho CV parser
- Gemini embedding dimensions 1536 và 256
- retry/fallback/error type mapping
- timeout rõ ràng
- streaming nếu dùng trong tương lai
- model alias/model listing
- provider-specific parameters bị mất khi đi qua OpenAI-compatible API
- token saver có làm thay đổi output contract không
- log usage/cost có lấy được không
- ảnh hưởng tới P0-B gap F1-F11 và O1-O10

## Output Yêu Cầu

Viết báo cáo bằng tiếng Việt, ngắn nhưng đủ quyết định.

Bắt buộc có các phần:

1. **Executive Answer**  
   Trả lời thẳng:
   - toàn hệ thống có thể chỉ đổi base URL không?
   - JobPosting Agent-only qua 9Router có nên làm không?
   - local CV/PDF synthetic có đáng làm không?

2. **Compatibility Matrix**  
   Bảng gồm: module/use case, SDK/API hiện tại, 9Router support, mức sửa, rủi ro, recommendation.

3. **JobPosting Agent Recommendation**  
   Thiết kế boundary, env config, patch plan tối thiểu, logging/cost tracking.

4. **Local CV/PDF Recommendation**  
   Dev/test plan, production caveat, DB fields, storage path, file serving strategy.

5. **2-Week Implementation Plan**  
   Thứ tự việc nên làm trong 2 tuần tới.

6. **Questions For User**  
   Chỉ liệt kê các câu cần xác nhận trước khi code, không hỏi lan man.

## Ràng Buộc

- Không đề xuất refactor lớn trước khi P0-C nếu không bắt buộc.
- Không làm hỏng Gemini embedding 1536 dims và 256-dim skill embedding.
- Không phá parser fallback/ProTierGate.
- Không route PDF parser qua 9Router nếu Files API/schema support chưa chắc.
- Không route embedding qua 9Router nếu chưa chứng minh giữ đúng dimension và output contract.
- Không đổi behavior score clipping; default vẫn raw score.
- Không dùng docs cũ làm source of truth runtime; code hiện tại và P0-B report là ground truth.

# Báo cáo Inventory AI/LLM P0-B

> **Generated**: 2026-05-23  
> **Scope**: Toàn bộ repo FANG — các production path, công cụ dev/synthetic, các script  
> **Method**: Code-first analysis (đọc toàn bộ từng file; tài liệu chỉ dùng để đối chiếu chéo)  
> **Purpose**: Dữ liệu đầu vào cho P1-A prompt review, P1-B minimal eval, điều hòa model/fallback, và đợt refactor layer LLM trong tương lai

---

## 1. Danh mục Master Use-Case (Master Use-Case Inventory)

### UC-1: CV Parsing (PDF → Structured JSON)

| Field | Chi tiết |
|---|---|
| **Business purpose** | Trích xuất structured candidate data từ CV PDF được tải lên để hiển thị, tìm kiếm, ranking, và làm chat context |
| **Category** | Inference / Generation (structured extraction) |
| **Code entry point** | [`cv_parser.py:CVParserOrchestrator.parse()`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/cv_parser.py#L240) |
| **Prompt/template location** | [`cv_parser_adapters.py:CV_PARSE_PROMPT`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/cv_parser_adapters.py#L18-L49) — hằng số inline, tiếng Anh |
| **Anthropic variant** | [`cv_parser_adapters.py:ANTHROPIC_SCHEMA_PROMPT`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/cv_parser_adapters.py#L52-L56) — thêm toàn bộ JSON schema vào prompt (không có native structured output) |
| **Input data** | `cv_bytes: bytes` — PDF được tải lên bởi người dùng (**untrusted**). Không thực hiện sanitization trước khi gửi đến các provider. |
| **Output contract** | Pydantic model [`ParsedCV`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/cv_models.py#L97) (`candidateInfo`, `education`, `experience`, `skills`, `certificates`, `languages`, `summary`, `rawText`, `expectedSalaryMin/Max`, `parserSelfReport`) |
| **Structured output** | Gemini: native `response_schema=ParsedCV` + `response_mime_type="application/json"`. OpenAI: `text.format` với `json_schema` (`strict: False`). Anthropic: schema-in-prompt, response được parse qua `model_validate_json` sau khi loại bỏ các markdown fence. |
| **Models/modes** | 5-tier fallback: T1 `gemini-flash` → T2 `gpt-5.4-mini` → T3 `claude-4.5-haiku` → T4 `gemini-pro` → T5 `gpt-5.5` |
| **Fallback logic** | Các lite tier (1–3) luôn được thử tuần tự. Các pro tier (4–5) chỉ được kích hoạt thông qua [`ProTierGate`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/cv_parser.py#L219-L237): escalate nếu có ít nhất một lite tier trả về kết quả chất lượng thấp (low-quality output); bỏ qua nếu có ≥2 lỗi infra. Hỗ trợ intra-provider model candidate fallback (ví dụ: `gemini-flash` → `gemini-3.1-flash` → `gemini-2.5-flash`). |
| **Retry** | Sử dụng [`tenacity`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/cv_parser.py#L358-L371): chỉ áp dụng cho `TransientProviderError`, 3 lần thử, exponential backoff từ 2–8 giây (có thể cấu hình) |
| **Validation/fallback** | 4-check quality gate ([`_build_quality_gate`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/cv_parser.py#L138-L187)): (1) rawText ≥ 120 ký tự, (2) có tín hiệu nhận diện ứng viên (candidate identity signal), (3) có ≥ 1 phần không trống, (4) parser self-confidence ≥ 0.55. Sử dụng cấu hình `extra="ignore"` của Pydantic. |
| **Temperature** | Gemini: `0` (deterministic). OpenAI/Anthropic: Mặc định của SDK. |
| **System/user separation** | Gemini: phẳng dạng `contents=[prompt, file]`. OpenAI: dùng role `developer` cho prompt + role `user` cho file PDF. Anthropic: dùng kwarg `system=` + tin nhắn của `user` chứa file PDF. |
| **Failure behavior** | Khi tất cả các tier đều thất bại → Ném lỗi `CVParsingError` kèm theo toàn bộ fallback path. Ingestion task bị fail. |
| **Risks** | File PDF chưa được xác thực (untrusted) được chuyển trực tiếp tới LLMs mà không qua kiểm tra nội dung. Anthropic thiết lập `strict: False` đối với schema. Thiếu dataset để eval. Tham số Temperature không đồng nhất giữa các provider. |
| **Tests/evals** | [`tests/unit/unit_test_parser_policy.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/tests/unit/unit_test_parser_policy.py) — kiểm tra logic của quality gate + orchestrator. Chưa thực hiện eval đối với kết quả đầu ra của LLM. |
| **Logging** | Ghi log có cấu trúc cho mỗi lần thử (tier, provider, model, duration, status, lý do chất lượng, độ tự tin). Theo dõi trace ở cấp độ pipeline qua `_LAST_PARSE_TRACE` ContextVar. |

---

### UC-2: Text Embedding (Chunks → Vectors)

| Field | Chi tiết |
|---|---|
| **Business purpose** | Chuyển đổi các đoạn văn bản (text chunks) thành vector embeddings để tìm kiếm theo cosine-distance (phục vụ RAG retrieval, ranking fuzzy skill matching) |
| **Category** | Embedding |
| **Code entry point** | [`embedding.py:embed_chunks()`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/embedding.py#L30) |
| **Prompt/template** | Không có — các lệnh gọi embedding truyền trực tiếp văn bản thô (raw text) dưới dạng `contents` |
| **Input data** | `chunks: List[str]` — dữ liệu chưa xác thực (**untrusted**, lấy từ CV do người dùng tải lên, bản mô tả công việc, hoặc prompt của bộ phận HR) |
| **Output contract** | `List[List[float]]` — một vector cho mỗi chunk. Thực hiện kiểm tra (validation) sau cuộc gọi: số lượng vector phải bằng số lượng chunk. |
| **Models/modes** | `gemini-embedding-001` (chỉ dùng duy nhất một provider, không có fallback) |
| **Dimensions** | Mặc định là `1536` ([`config.py:embedding_dim`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/core/config.py#L8)), có thể ghi đè (overridable) trên từng lệnh gọi. Các kỹ năng trong NMAIex sử dụng `256` chiều (dims). Có hỗ trợ Matryoshka-compatible truncation thông qua tham số `output_dimensionality`. |
| **Batch size** | `32` (có thể cấu hình qua `embedding_batch_size`) |
| **Storage** | Kiểu dữ liệu pgvector `halfvec` tại cột `AIDOCUMENTCHUNK.embedding`. Được tuần tự hóa (serialized) thông qua [`persistence.py:_serialize_embedding()`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/persistence.py#L195). |
| **Validation** | 5 bước kiểm tra trước (upfront checks): provider == "gemini", có khóa API key, batch_size > 0, mỗi chunk là chuỗi ký tự không rỗng, số lượng vector trả về trùng khớp. |
| **Failure behavior** | Catch-all → log `logger.exception("Gemini embedding failed")` → re-raise lỗi lên trên. Không có cơ chế retry tại layer này. |
| **Risks** | **Chỉ dùng duy nhất một provider, không có fallback**. Sự cố sập API của Gemini đồng nghĩa với việc toàn bộ hệ thống embedding bị tê liệt. Không có logic retry ở layer này. |
| **Tests/evals** | [`tests/unit/unit_test_embedding.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/tests/unit/unit_test_embedding.py) — 7 trường hợp kiểm thử sử dụng mock `FakeGeminiClient`. |
| **Logging** | Khi thành công: Ghi log có cấu trúc chứa provider, model, dimension, chunkCount, batchSize. Khi thất bại: Ghi log qua `logger.exception`. |

---

### UC-3: Document Chunking (Markdown → Embedding-Ready Chunks)

| Field | Chi tiết |
|---|---|
| **Business purpose** | Chia nhỏ CV đã parse/job markdown thành các đoạn có phân cấp (hierarchical chunks) phục vụ cho việc tạo embedding và RAG retrieval |
| **Category** | Tiền xử lý / Preprocessing (deterministic — **không gọi AI/LLM**) |
| **Code entry point** | [`chunking.py:process_document_to_chunks()`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/chunking.py#L50) |
| **AI dependency** | Không có. Sử dụng `MarkdownHeaderTextSplitter` + `RecursiveCharacterTextSplitter` của LangChain (thuật toán thuần túy, không dựa trên model). |
| **Token counting** | Ước tính có tính chất deterministic: `ceil(len(text) / 3.5)` — không phải là một tokenizer thực thụ. |
| **Constants** | Giới hạn parent chunk: 512 tokens. Mục tiêu child: 180 tokens. Khoảng chồng lấp (Overlap): 36 tokens. |
| **Output** | `List[ChunkPayload]` dạng TypedDict: `{content, tokenCount, chunkIndex}` |
| **Context injection** | Thêm thông tin ngữ cảnh header (tái dựng `# h1\n## h2\n### h3`) và siêu dữ liệu toàn cục tùy chọn (optional global metadata) vào đầu mỗi chunk. |
| **Tests** | [`tests/unit/unit_test_chunking.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/tests/unit/unit_test_chunking.py) — 2 trường hợp kiểm thử (test cases). |

---

### UC-4: RAG Chat Query (HR Co-pilot)

| Field | Chi tiết |
|---|---|
| **Business purpose** | Bộ phận HR đặt câu hỏi về ứng viên; hệ thống truy xuất các CV chunks liên quan + ngữ cảnh từ nhiều nguồn, sau đó generate câu trả lời qua LLM |
| **Category** | Retrieval + Generation (RAG) |
| **Code entry point** | [`rag_query.py:process_chat_query()`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/rag_query.py#L252) → [`routes_chat.py:POST /chat/query`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/api/routes_chat.py#L47) |
| **Prompt/template location** | [`rag_query.py:_build_system_prompt()`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/rag_query.py#L123-L193) — inline, tiếng Việt |
| **System prompt structure** | `[VỊ TRÍ TUYỂN DỤNG]` (job posting) → `[HỒ SƠ ỨNG VIÊN]` (candidate profile) → `[NỘI DUNG CV — Top K]` (các chunk tìm kiếm theo vector) → `[LỊCH SỬ TUYỂN DỤNG]` (lịch sử phỏng vấn ATS) → `[HƯỚNG DẪN TRẢ LỜI]` (quy tắc phản hồi) |
| **Grounding instruction** | "Chỉ dựa vào thông tin được cung cấp ở trên. Không suy diễn ngoài dữ liệu." |
| **Input data** | `prompt: str` — văn bản tự do của HR (**untrusted**). Ngữ cảnh lấy từ DB (job, candidate, CV chunks, ATS history) — (**semi-trusted**, ban đầu do người dùng cung cấp). |
| **Message construction** | `[system_prompt, *history_messages, user_prompt]` — phân tách rõ ràng vai trò (role separation). |
| **Output contract** | Pydantic [`ChatQueryResponse`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/chat.py#L50): `conversationId`, `messageId`, `response`, `model`, `modelMode`, `fallbackPath`, `latencyMs`, `topK`, `contextWarning` |
| **Models/modes** | 7 chế độ hợp lệ (valid modes): `gemini-flash`, `gpt-mini`, `claude-haiku`, `gemini-pro`, `gpt-full`, `auto-lite`, `auto-pro` |
| **Fallback** | `auto-lite`: gemini-flash → gpt-5.4-mini → claude-4.5-haiku. `auto-pro`: gemini-pro → gpt-5.5. Các chế độ chỉ định model cụ thể (Specific modes): không có fallback. |
| **Retry** | Sử dụng tenacity: 3 lần thử, tăng dần theo hàm mũ (exponential) từ 1–6 giây, chỉ áp dụng cho lỗi `TransientProviderError`. |
| **Quality gate** | Chỉ áp dụng trong chế độ auto: từ chối các phản hồi có độ dài < 5 ký tự hoặc chứa tín hiệu từ chối trả lời (refusal signals bằng tiếng Việt + tiếng Anh). **Không áp dụng trong các chế độ chỉ định model cụ thể.** |
| **Context budget** | Lite: 180k tokens, Pro: 960k tokens. Cảnh báo khi mức sử dụng đạt ≥ 80%. Tùy chọn xử lý: `summarize_and_continue`, `new_conversation_with_summary`. |
| **Vector search** | pgvector `<=>` cosine distance trên bảng `AIDOCUMENTCHUNK`, top_k = 3 (có thể cấu hình). |
| **Failure behavior** | Lỗi `ValueError` → trả về code 400. `InvalidModelModeError` → trả về code 400. `GenerationError` → trả về code 502. Lỗi chung (Generic) → trả về code 500. |
| **Risks** | Dữ liệu từ DB được chèn trực tiếp vào system prompt mà không qua lọc/làm sạch (nguy cơ prompt injection từ nội dung CV/mô tả công việc). Bỏ qua Quality gate ở các chế độ chỉ định model cụ thể. Không đếm số lượng token cho bản thân system prompt (chỉ đếm phần history). Không thiết lập timeout rõ ràng cho các cuộc gọi LLM. |
| **Tests/evals** | Không tìm thấy. |
| **Logging** | Ghi nhận tại bảng `AIQUERYLOG` (prompt, response, model, latency, fallback_path). Bảng `AICHATMESSAGE` (lưu trữ tất cả tin nhắn). Cảnh báo giới hạn context budget. Nhật ký các lượt thử tạo câu trả lời (Generation attempt logs). |

---

### UC-5: Chat Summarization

| Field | Chi tiết |
|---|---|
| **Business purpose** | Tóm tắt các tin nhắn cũ trong cuộc trò chuyện để giải phóng dung lượng context window khi budget gần đạt giới hạn |
| **Category** | Generation (summarization) |
| **Code entry point** | [`routes_chat.py:POST /chat/conversations/{id}/summarize`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/api/routes_chat.py#L165) |
| **Prompt/template** | Viết inline tại [`routes_chat.py:L192–L202`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/api/routes_chat.py#L192-L202) — tiếng Việt: "Tóm tắt cuộc hội thoại HR-AI dưới đây thành bản rút gọn, giữ lại các điểm quan trọng về ứng viên, đánh giá, và kết luận." |
| **Input data** | `conversation_text` — chuỗi ghép từ các tin nhắn trước đó (`ROLE: content`). Chứa các prompt chưa xác thực từ người dùng (**untrusted**) + phản hồi bán-xác-thực từ trợ lý (**semi-trusted**). |
| **Output** | Văn bản tóm tắt được lưu giữ dưới dạng tin nhắn hệ thống (system message). Các tin nhắn cũ được đánh dấu là đã tóm tắt (summarized). |
| **Model** | [`settings.context_summarization_model`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/core/config.py#L44) — mặc định là `"gemini-flash"` |
| **Validation** | Yêu cầu tối thiểu phải có 4 tin nhắn chưa được tóm tắt. |
| **Risks** | Các tin nhắn cũ của người dùng (chưa xác thực - untrusted) được đưa vào dữ liệu đầu vào của tiến trình tóm tắt. Không có cơ chế kiểm tra (output validation) chất lượng của bản tóm tắt. |
| **Tests/evals** | Không tìm thấy. |

---

### UC-6: Chat Branch (New Conversation with Summary)

| Field | Chi tiết |
|---|---|
| **Business purpose** | Tạo một cuộc hội thoại mới chứa bản tóm tắt kế thừa từ cuộc hội thoại trước đó |
| **Category** | Generation (summarization) |
| **Code entry point** | [`routes_chat.py:POST /chat/conversations/{id}/branch-new`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/api/routes_chat.py#L234) |
| **Prompt/template** | Viết inline tại [`routes_chat.py:L260–L270`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/api/routes_chat.py#L260-L270) — tiếng Việt: "Tóm tắt cuộc hội thoại HR-AI dưới đây thành bản rút gọn để mang sang hội thoại mới." |
| **Input data** | Tương tự UC-5: các tin nhắn trước đó được nối chuỗi (bao gồm cả dữ liệu untrusted + semi-trusted). |
| **Output** | Cuộc hội thoại mới với tin nhắn hệ thống đầu tiên là bản tóm tắt, bắt đầu bằng tiền tố `[Tóm tắt từ hội thoại trước]`. |
| **Model** | Tương tự UC-5: `settings.context_summarization_model` |
| **Risks** | Tương tự UC-5. |
| **Tests/evals** | Không tìm thấy. |

---

### UC-7: NMAIex Province Mapping

| Field | Chi tiết |
|---|---|
| **Business purpose** | Ánh xạ (Map) các địa chỉ dạng văn bản tự do từ CV/biểu mẫu sang ID tỉnh thành chuẩn hóa (34 tỉnh thành sau đợt sáp nhập năm 2025) |
| **Category** | Inference / Mapping |
| **Code entry point** | [`nmaiex_mapper_service.py:map_string_to_province_id()`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/nmaiex_mapper_service.py#L23) |
| **Prompt/template** | Viết inline tại [`nmaiex_mapper_service.py:L38–L50`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/nmaiex_mapper_service.py#L38-L50) — tiếng Việt. Thực hiện inject danh mục tỉnh thành (province catalog) thực tế từ DB lúc runtime. |
| **Input data** | `text: str` — địa chỉ dạng văn bản tự do chưa xác thực (**untrusted**) từ CV hoặc biểu mẫu, được đưa vào tin nhắn người dùng. Danh mục tỉnh thành từ DB — đáng tin cậy (**trusted**), được đưa vào tin nhắn hệ thống. |
| **Output contract** | Pydantic [`ProvinceMappingResult`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/nmaiex_schemas.py#L26): `prov_id: Optional[str]` |
| **Models/modes** | `"auto-lite"` (gemini-flash → gpt-5.4-mini → claude-4.5-haiku) |
| **Validation** | Chỉ kiểm tra kiểu dữ liệu qua Pydantic. **Không kiểm tra xem provId được trả về có thực sự tồn tại trong province catalog hay không.** |
| **Failure behavior** | Mọi ngoại lệ (exception) xảy ra → trả về `None` + ghi log cảnh báo. Lỗi `GenerationError` từ `invoke_generation` **không được bắt (catch) rõ ràng** — lan truyền lên phía caller. |
| **Risks** | Không xác thực sự tồn tại của provId. Không có hướng dẫn ngăn ngừa prompt injection trong prompt. |
| **Tests/evals** | Không tìm thấy. |

---

### UC-8: NMAIex Skill Mapping (LLM Tier 1)

| Field | Chi tiết |
|---|---|
| **Business purpose** | Ánh xạ các kỹ năng dạng văn bản tự do từ CV sang ID kỹ năng trong danh mục (phân loại dạng closed-world classification) |
| **Category** | Inference / Mapping |
| **Code entry point** | [`nmaiex_mapper_service.py:map_skills()`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/nmaiex_mapper_service.py#L71) |
| **Prompt/template** | Viết inline tại [`nmaiex_mapper_service.py:L92–L106`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/nmaiex_mapper_service.py#L92-L106) — tiếng Việt. Thực hiện chèn đầy đủ danh mục kỹ năng (skill catalog) từ DB. |
| **Input data** | `skills: list[str]` — dữ liệu chưa xác thực (**untrusted**, lấy từ CV parsing hoặc thông tin người dùng nhập vào), được nối bằng dấu phẩy và đưa vào tin nhắn người dùng. Danh mục kỹ năng (Skill catalog) lấy từ DB — đáng tin cậy (**trusted**). |
| **Output contract** | Pydantic [`SkillMappingResult`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/nmaiex_schemas.py#L15): `matched_ids: list[int]`, `unmatched_texts: list[str]` |
| **Models/modes** | `"auto-lite"` |
| **Preprocessing** | Loại bỏ các khối code block dạng markdown (` ```json...``` `) — giải pháp phòng vệ tạm thời đối với hành vi bao bọc mã của LLM đã biết trước đó. |
| **Validation** | Dùng `model_validate_json()` của Pydantic. **Không đối chiếu chéo (cross-check) xem các matched_ids có tồn tại trong danh mục hay không. Không kiểm tra xem mỗi skill đầu vào có xuất hiện đúng một lần trong output hay không.** |
| **Failure behavior** | **Giảm cấp mượt mà (Graceful degradation)**: mọi exception xảy ra → trả về `SkillMappingResult(matched_ids=[], unmatched_texts=list(skills))` — toàn bộ kỹ năng sẽ được chuyển sang cơ chế Tier 2 embedding fallback. Hoàn toàn không mất mát thông tin. |
| **Tests/evals** | Không tìm thấy. |

---

### UC-9: NMAIex Skill Embedding (Embedding Tier 2 Fallback)

| Field | Chi tiết |
|---|---|
| **Business purpose** | Tạo embedding cho các đoạn văn bản kỹ năng chưa khớp để tính fuzzy skill score dựa trên vector phục vụ cho quá trình ranking |
| **Category** | Embedding |
| **Code entry point** | [`nmaiex_mapper_service.py:embed_and_store_raw_skills()`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/nmaiex_mapper_service.py#L142) |
| **Input data** | `unmatched_texts: list[str]` — các chuỗi chưa xác thực (**untrusted**) từ kết quả đầu ra của UC-8 |
| **Output** | Các vector được lưu trữ trong bảng `CANDIDATE_SKILL_RAW` hoặc `JOB_SKILL_RAW` (kiểu dữ liệu pgvector `::vector`) |
| **Models/modes** | `gemini-embedding-001` ở số chiều `256` (lấy từ [`nmaiex_config.py:nmaiex_skill_embedding_dims`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/core/nmaiex_config.py#L34)) |
| **Validation** | Số lượng vector == số lượng đoạn văn bản. Xác thực kiểu thực thể (Entity type validation). |
| **Failure behavior** | Số lượng vector không khớp → **tự động dừng trong im lặng (silent abort)** (không ném ngoại lệ, chỉ ghi log lỗi). Dữ liệu đầu vào trống → trả về ngay lập tức (early return). |
| **Risks** | Hành vi silent abort khi mất cân đối số lượng có thể khiến các kỹ năng không có embedding mà không có bất kỳ cảnh báo nào. |
| **Tests/evals** | Không tìm thấy. |

---

### UC-10: NMAIex Language Proficiency Normalization

| Field | Chi tiết |
|---|---|
| **Business purpose** | Chuẩn hóa các chuỗi trình độ ngôn ngữ đa dạng (N3, IELTS 7.5, B2, Fluent, v.v.) thành enum 5 cấp độ |
| **Category** | Inference / Normalization |
| **Code entry point** | [`nmaiex_mapper_service.py:normalize_proficiency()`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/nmaiex_mapper_service.py#L228) |
| **Prompt/template** | Hằng số cấp module [`_PROFICIENCY_SYSTEM_PROMPT`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/nmaiex_mapper_service.py#L211-L225) — tiếng Việt. Ánh xạ sang các cấp độ `BASIC | INTERMEDIATE | ADVANCED | FLUENT | NATIVE` kèm theo các ví dụ. |
| **Input data** | `raw_proficiency: str` — dữ liệu chưa xác thực (**untrusted**, lấy từ quá trình CV parsing) |
| **Output contract** | Một trong số 5 chuỗi ký tự, được xác thực dựa trên allowlist của dict `PROFICIENCY_LEVELS`. |
| **Fast path** | Nếu đầu vào trùng khớp với một cấp độ hợp lệ → trả về ngay lập tức **mà không cần gọi LLM**. |
| **Models/modes** | `"auto-lite"` |
| **Failure behavior** | **Double fallback**: giá trị không hợp lệ → trả về `"BASIC"` + ghi cảnh báo. LLM lỗi → trả về `"BASIC"` + ghi cảnh báo. **Hàm này không bao giờ ném lỗi (never raises).** |
| **Risks** | Việc đặt mặc định là `"BASIC"` có thể làm giảm giá trị thực tế của ứng viên có trình độ cao khi hệ thống LLM gặp sự cố mà không phát tín hiệu cảnh báo rõ ràng. |
| **Tests/evals** | Không tìm thấy. |

---

### UC-11: NMAIex Ranking — Fuzzy Skill Scoring via Pre-stored Embeddings

| Field | Chi tiết |
|---|---|
| **Business purpose** | Tính toán mức độ trùng khớp kỹ năng mờ (fuzzy skill overlap) giữa công việc và ứng viên bằng các skill embeddings được lưu trước |
| **Category** | Retrieval (độ tương đồng vector, không gọi LLM) |
| **Code entry point** | [`nmaiex_ranking_service.py:compute_skill_score()`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/nmaiex_ranking_service.py#L226) |
| **AI dependency** | Sử dụng các **pre-stored embeddings** từ UC-9 (`JOB_SKILL_RAW`, `CANDIDATE_SKILL_RAW`). Không thực hiện cuộc gọi AI thời gian thực (no real-time AI call). |
| **Algorithm** | Chỉ số `avg_max_cosine` được tính toán trong PostgreSQL thông qua toán tử `<=>` của pgvector. Tỉ lệ pha trộn: `alpha * exact_overlap + (1-alpha) * fuzzy_overlap` (với alpha=0.8). |
| **Validation** | Giới hạn fuzzy_overlap trong khoảng `[0.0, 1.0]`. |
| **Failure behavior** | Khi xảy ra lỗi DB exception → gán `fuzzy_overlap = 0.0` + ghi log cảnh báo. |

---

### UC-12: NMAIex Ranking — J→C Vector Search

| Field | Chi tiết |
|---|---|
| **Business purpose** | Tạo embedding cho chức danh công việc + mô tả (job title+description) để tìm kiếm vector đối chiếu với các CV chunks của ứng viên trong quy trình xếp hạng J→C |
| **Category** | Embedding + Retrieval |
| **Code entry point** | [`nmaiex_ranking_service.py:rank_candidates_for_job()`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/nmaiex_ranking_service.py#L368) |
| **AI call** | Lệnh gọi `embed_chunks([job_text])` — sử dụng cùng một Gemini embedding như UC-2 |
| **Failure behavior** | Nếu vector rỗng → trả về kết quả trống ngay lập tức. |

---

### UC-13: Synthetic Data Generation (Dev/Tooling)

| Field | Chi tiết |
|---|---|
| **Business purpose** | Tạo các CV và tin tuyển dụng giả lập (synthetic) phục vụ cho quá trình phát triển/kiểm thử |
| **Category** | Generation (công cụ hỗ trợ dev — **KHÔNG nằm trên production path**) |
| **Code entry point** | [`synthetic_data/run_pipeline.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/synthetic_data/run_pipeline.py) → [`generator.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/synthetic_data/generator.py) |
| **Prompt/template** | [`synthetic_data/prompts.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/synthetic_data/prompts.py): `CV_SYSTEM_PROMPT` (L27–47), `JOB_SYSTEM_PROMPT` (L94–123) — tiếng Việt |
| **Models** | `gemini/gemini-3.1-flash-lite` (cho CV), `gemini/gemini-3.5-flash` (cho Job + QA) — thông qua 9Router proxy chạy tại `localhost:20128` |
| **⚠️ Production impact** | File `run_pipeline.py` tiến hành **monkey-patch** hàm production `embed_chunks` thành `embed_chunks_9router` (L37–100). File `db_writer.py` **ghi trực tiếp dữ liệu vào các bảng DB production** (USER, CANDIDATE, JOBAPPLICATION, CVPARSED, AIDOCUMENTCHUNK, JOBPOSTING). |
| **Risks** | Thực hiện monkey-patching các module chạy trên production. Ghi trực tiếp dữ liệu giả lập vào DB production. Sử dụng các API key được hardcode. |

---

### UC-14: NMAIex Candidate Enrichment Retry (Script)

| Field | Chi tiết |
|---|---|
| **Business purpose** | Thử lại (Retry) các job làm giàu dữ liệu ứng viên NMAIex bị lỗi (backfill) |
| **Category** | Tập lệnh vận hành / Ops script (gây ảnh hưởng trực tiếp đến production) |
| **Code entry point** | [`scripts/retry_nmaiex_candidate_enrichment.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/scripts/retry_nmaiex_candidate_enrichment.py) |
| **AI calls** | Gọi gián tiếp: `run_enrichment_job()` → embedding + LLM skill mapping (UC-8, UC-9) |
| **⚠️ Production impact** | Sửa đổi trực tiếp dữ liệu trên DB production (CANDIDATESKILL, CANDIDATE_SKILL_RAW) |

---

## 2. Ảnh hưởng từ Quyết định Chuyển đổi từ JobApplication Chat → Full CV Markdown

Theo quyết định trong tài liệu [`FANG_NEXT_PHASE_DECISIONS.md`](file:///c:/Users/os/Desktop/cur_prj/Fang/agent_workflow_doc/FANG_NEXT_PHASE_DECISIONS.md#L19-L22), phần trò chuyện `JobApplication` sẽ chuyển đổi từ cơ chế cố định chunk-RAG sang sử dụng ngữ cảnh full CV markdown.

**Các use case bị ảnh hưởng:**

| Use Case | Ảnh hưởng |
|---|---|
| **UC-4 (RAG Chat Query)** | **Viết lại diện rộng (Major rewrite).** Hàm `_build_system_prompt()` hiện đang chèn các top-K chunks thu được từ tìm kiếm vector. Sẽ được thay thế bằng full `cv_markdown` trích từ `CVPARSED.parsed_json` → `convert_json_to_markdown()`. Bước tìm kiếm theo vector (`embed_chunks([prompt])` + `_vector_search()`) sẽ trở nên không cần thiết cho flow này nữa. |
| **UC-2 (Embedding)** | Không thay đổi đối với bản thân service, nhưng lệnh gọi embedding bên trong `process_chat_query` sẽ bị loại bỏ đối với chat đơn lẻ của JobApplication. Embedding vẫn rất cần thiết cho việc ranking (UC-12) và các kịch bản nhiều ứng viên (multi-candidate scenarios). |
| **UC-3 (Chunking)** | Không thay đổi đối với bản thân service. Cơ chế chunking vẫn cần thiết cho quá trình ingestion (các chunk lưu trữ được sử dụng bởi tìm kiếm vector phục vụ cho ranking). Không cần thiết đối với full-CV chat. |
| **UC-5/UC-6 (Summarization/Branch)** | Động lực học của context budget sẽ thay đổi: full CV markdown có dung lượng lớn hơn nhiều so với các top-K chunks, có khả năng kích hoạt cơ chế tóm tắt (summarization) sớm hơn. Các ngưỡng giới hạn ngân sách (budget thresholds) có thể cần phải hiệu chỉnh lại. |
| **UC-7/UC-8/UC-9/UC-10 (NMAIex mappers)** | Không ảnh hưởng — các tác vụ này chạy trong quá trình ingestion/enrichment, không chạy trong khi chat. |
| **UC-11/UC-12 (Ranking)** | Không ảnh hưởng — ranking sử dụng pipeline embedding/vector search độc lập của riêng nó. |

---

## Phụ lục A: Sơ đồ Model/Fallback (Model/Fallback Map)

### Các Model tạo sinh (Generation Models)

| Logical Mode | Provider | Model Candidates (intra-provider fallback) | Tier | Ngân sách ngữ cảnh (Context Budget) |
|---|---|---|---|---|
| `gemini-flash` | Google | `gemini-flash` → `gemini-3.1-flash` → `gemini-3.1-flash-preview` → `gemini-3.1-flash-lite-preview` → `gemini-2.5-flash` → `gemini-flash-latest` | 1 (Lite) | 180k tokens |
| `gpt-mini` / `gpt-5.4-mini` | OpenAI | `gpt-5.4-mini` → `gpt-5-mini` | 2 (Lite) | 180k tokens |
| `claude-haiku` / `claude-4.5-haiku` | Anthropic | `claude-4.5-haiku` → `claude-3-5-haiku-latest` | 3 (Lite) | 180k tokens |
| `gemini-pro` | Google | `gemini-3.1-pro-preview` → `gemini-3.1-pro` → `gemini-pro` | 4 (Pro) | 960k tokens |
| `gpt-full` / `gpt-5.5` | OpenAI | `gpt-5.5` → `gpt-5.4` → `gpt-5.4-pro` | 5 (Pro) | 960k tokens |

### Chuỗi tự động (Auto Chains)

| Chuỗi (Chain) | Trình tự (Sequence) |
|---|---|
| `auto-lite` | gemini-flash → gpt-5.4-mini → claude-4.5-haiku |
| `auto-pro` | gemini-pro → gpt-5.5 |

### Model Embedding

| Model | Provider | Số chiều (Dimensions) | Batch Size | Fallback |
|---|---|---|---|---|
| `gemini-embedding-001` | Google | 1536 (mặc định), 256 (cho kỹ năng NMAIex) | 32 | **Không có (None)** |

### Model Tóm tắt (Summarization Model)

| Model | Provider | Cách dùng (Usage) |
|---|---|---|
| `gemini-flash` (thông qua `context_summarization_model`) | Google | Tóm tắt ở UC-5, tạo nhánh ở UC-6 (UC-5 summarize, UC-6 branch) |

### Các API Key

| Biến môi trường (Env Variable) | Nhà cung cấp (Provider) | Được dùng bởi (Used By) |
|---|---|---|
| `GOOGLE_API_KEY` | Google (Gemini) | Embedding, CV Parse T1/T4, Chat generation, NMAIex mappers, Tóm tắt (Summarization) |
| `OPENAI_API_KEY` | OpenAI | CV Parse T2/T5, Chat generation |
| `CLAUDE_API_KEY` | Anthropic | CV Parse T3, Chat generation |

---

## Phụ lục B: Chỉ mục vị trí của Prompt (Prompt Location Index)

| # | Prompt | File | Dòng (Lines) | Ngôn ngữ (Language) | Kiểu (Type) |
|---|---|---|---|---|---|
| P1 | CV Parse Prompt | [`cv_parser_adapters.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/cv_parser_adapters.py#L18-L49) | 18–49 | tiếng Anh | Hằng số inline `CV_PARSE_PROMPT` |
| P2 | Anthropic Schema Prompt (extends P1) | [`cv_parser_adapters.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/cv_parser_adapters.py#L52-L56) | 52–56 | tiếng Anh | Hằng số inline `ANTHROPIC_SCHEMA_PROMPT` |
| P3 | HR Co-pilot System Prompt | [`rag_query.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/rag_query.py#L123-L193) | 123–193 | tiếng Việt | Bộ dựng động `_build_system_prompt()` |
| P4 | Chat Summarization Prompt | [`routes_chat.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/api/routes_chat.py#L192-L202) | 192–202 | tiếng Việt | Viết inline trong endpoint handler |
| P5 | Chat Branch Summarization Prompt | [`routes_chat.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/api/routes_chat.py#L260-L270) | 260–270 | tiếng Việt | Viết inline trong endpoint handler |
| P6 | Province Mapping Prompt | [`nmaiex_mapper_service.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/nmaiex_mapper_service.py#L38-L50) | 38–50 | tiếng Việt | Viết inline trong hàm (function) |
| P7 | Skill Mapping Prompt | [`nmaiex_mapper_service.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/nmaiex_mapper_service.py#L92-L106) | 92–106 | tiếng Việt | Viết inline trong hàm (function) |
| P8 | Proficiency Normalization Prompt | [`nmaiex_mapper_service.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/nmaiex_mapper_service.py#L211-L225) | 211–225 | tiếng Việt | Hằng số cấp module `_PROFICIENCY_SYSTEM_PROMPT` |
| P9 | Synthetic CV Generation Prompt | [`synthetic_data/prompts.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/synthetic_data/prompts.py#L27-L47) | 27–47 | tiếng Việt | Chỉ dùng làm công cụ dev |
| P10 | Synthetic Job Generation Prompt | [`synthetic_data/prompts.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/synthetic_data/prompts.py#L94-L123) | 94–123 | tiếng Việt | Chỉ dùng làm công cụ dev |

**Lưu ý:** Tất cả các prompt sử dụng trên production đều được viết inline trong các file service. Không có thư mục dành riêng cho các prompt template. File duy nhất có chứa từ "prompt" trong tên của nó là `synthetic_data/prompts.py` (dùng làm công cụ dev).

---

## Phụ lục C: Chỉ mục các Structured Output / Schema (Structured Output / Schema Index)

| Schema | File | Được dùng bởi (Used By) | Phương thức xác thực (Validation Method) |
|---|---|---|---|
| [`ParsedCV`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/cv_models.py#L97) | `cv_models.py` | UC-1 (CV Parse) | Gemini native schema, OpenAI json_schema (strict:False), Anthropic schema-in-prompt + `model_validate_json` |
| [`ParserSelfReport`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/cv_models.py#L78) | `cv_models.py` | UC-1 (quality gate) | Lồng trong ParsedCV (Nested in ParsedCV) |
| [`LanguageEntry`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/cv_models.py#L60) | `cv_models.py` | UC-1 + UC-10 | Lồng trong ParsedCV (Nested in ParsedCV) |
| [`CandidateInfo`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/cv_models.py#L18) | `cv_models.py` | UC-1 (identity check) | Lồng trong ParsedCV (Nested in ParsedCV) |
| [`ChatQueryRequest`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/chat.py#L14) | `chat.py` | UC-4 (input) | Xác thực request bằng Pydantic (Pydantic request validation) |
| [`ChatQueryResponse`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/chat.py#L50) | `chat.py` | UC-4 (output) | Tuần tự hóa phản hồi bằng Pydantic (Pydantic response serialization) |
| [`ContextWarning`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/chat.py#L39) | `chat.py` | UC-4 (budget) | Lồng trong ChatQueryResponse |
| [`SkillMappingResult`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/nmaiex_schemas.py#L15) | `nmaiex_schemas.py` | UC-8 (skill mapping) | `model_validate_json` kết hợp loại bỏ các markdown fence |
| [`ProvinceMappingResult`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/nmaiex_schemas.py#L26) | `nmaiex_schemas.py` | UC-7 (province mapping) | Pydantic constructor |
| [`ScoreBreakdown`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/nmaiex_schemas.py#L40) | `nmaiex_schemas.py` | UC-11/12 (ranking) | Kết quả chấm điểm có tính deterministic |
| [`CandidateRankResult`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/nmaiex_schemas.py#L63) | `nmaiex_schemas.py` | UC-12 (J→C ranking) | Deterministic |
| [`GenerationTrace`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/rag_orchestrator.py#L66) | `rag_orchestrator.py` | UC-4/5/6 (generation) | Dataclass (không phải Pydantic) |
| `ChunkPayload` | `chunking.py` | UC-3 | TypedDict |

---

## Phụ lục D: Các lỗ hổng trong xử lý lỗi (Failure Handling Gaps)

| # | Lỗ hổng (Gap) | Use Cases | Mức độ nghiêm trọng (Severity) | Chi tiết (Detail) |
|---|---|---|---|---|
| F1 | **Bỏ qua Quality gate ở các chế độ chỉ định model cụ thể** | UC-4 | Cao | Hàm `_invoke_specific()` KHÔNG chạy `_generation_quality_gate()`. Nếu một model cụ thể được chọn trả về kết quả từ chối/rác (refusal/garbage), kết quả đó vẫn sẽ được gửi trực tiếp tới người dùng. Chỉ các chuỗi auto mới áp dụng Quality gate. |
| F2 | **Embedding không có provider dự phòng (fallback provider)** | UC-2, UC-9, UC-12 | Cao | Chỉ hỗ trợ Gemini. Khi xảy ra sự cố API sập → tê liệt hoàn toàn dịch vụ embedding. Không có cơ chế retry ở layer embedding. |
| F3 | **Lỗi embedding trong chat query không được bắt (catch)** | UC-4 | Trung bình | Lệnh gọi `embed_chunks([prompt])` trong `process_chat_query` không có khối try/except — ngoại lệ thô (raw exception) sẽ lan truyền ngược lại dưới dạng lỗi 500. |
| F4 | **Ánh xạ tỉnh thành (Province mapping): không kiểm tra sự tồn tại của provId** | UC-7 | Trung bình | LLM có thể trả về bất kỳ chuỗi ký tự nào; Pydantic chỉ kiểm tra dạng `Optional[str]`. Một provId không hợp lệ vẫn có thể được ghi vào DB. |
| F5 | **Ánh xạ kỹ năng (Skill mapping): không kiểm tra sự tồn tại của matched_id** | UC-8 | Trung bình | LLM có thể trả về các ID kỹ năng không hề có trong danh mục (catalog). Không có bước đối chiếu/xác thực chéo (cross-validation). |
| F6 | **Chuẩn hóa mức độ thành thạo ngôn ngữ mặc định trả về BASIC** | UC-10 | Thấp - Trung bình | Lặng lẽ đánh giá thấp ứng viên khi LLM gặp lỗi. Không bao giờ ném ngoại lệ (never raises), không phát tín hiệu cảnh báo ở mức lỗi. |
| F7 | **Tạo embedding kỹ năng: tự dừng trong im lặng (silent abort) khi lệch số lượng vector** | UC-9 | Trung bình | Chỉ ghi nhận log lỗi nhưng vẫn trả về kết quả thành công một cách im lặng — phía caller không hề có tín hiệu để biết các kỹ năng đó đang bị thiếu embedding. |
| F8 | **Không thiết lập timeout rõ ràng cho cuộc gọi LLM** | Tất cả UCs | Trung bình | Phụ thuộc vào giá trị mặc định của SDK. Không thấy có cấu hình timeout cụ thể nào được khai báo. |
| F9 | **Context budget chỉ kiểm tra lịch sử chat, không kiểm tra system prompt** | UC-4 | Thấp | Hàm `_check_context_budget` thực hiện cộng tổng độ dài các tin nhắn lịch sử (history messages) nhưng lại bỏ qua phần system prompt được xây dựng động, vốn có dung lượng rất lớn. |
| F10 | **Trình parse CV của Anthropic: không hỗ trợ native structured output** | UC-1 | Thấp | Phải phụ thuộc vào việc nhét schema vào trong prompt + parse kết quả sau cuộc gọi (post-hoc parsing). Cơ chế này kém bền vững hơn so với native structured output. |
| F11 | **Lỗi GenerationError từ invoke_generation không được bắt trong province mapper** | UC-7 | Trung bình | Nếu toàn bộ các tier của chuỗi auto-lite đều thất bại, lỗi `GenerationError` sẽ tự lan truyền mà không được bắt tới phía enrichment caller. |

---

## Phụ lục E: Các lỗ hổng trong Khả năng Giám sát & Quản lý Phiên bản (Observability / Versioning Gaps)

| # | Lỗ hổng (Gap) | Use Cases | Chi tiết (Detail) |
|---|---|---|---|
| O1 | **Không quản lý phiên bản prompt (No prompt versioning)** | Tất cả | Các prompt đều là những hằng số viết inline và không đi kèm thẻ phiên bản (version tag). Các thay đổi chỉ được theo dõi qua các lượt commit của git. Không có cách nào để đối chiếu/liên hệ kết quả đầu ra của LLM với phiên bản prompt đã tạo ra nó. |
| O2 | **Không ghi nhận nhật ký kết quả đầu ra (generation output) cho các mapper của NMAIex** | UC-7, UC-8, UC-10 | Phản hồi của LLM đối với việc ánh xạ tỉnh thành/kỹ năng/trình độ ngôn ngữ không được lưu giữ hay kiểm toán (persisted/audited). Chỉ tồn tại bảng `AIQUERYLOG` (dành riêng cho chat). |
| O3 | **Không có bộ dữ liệu eval hoặc bộ kiểm thử hồi quy (eval dataset / regression suite)** | Tất cả use case dùng LLM | Thiếu bộ dữ liệu chuẩn (golden dataset) để đánh giá độ chính xác khi parse CV, chất lượng của prompt, tính đúng đắn khi ánh xạ hoặc chất lượng câu trả lời khi chat. |
| O4 | **Không theo dõi lượng token tiêu thụ (No token usage tracking)** | Tất cả use case dùng LLM | Không ghi nhận số lượng token đầu vào/đầu ra cho mỗi cuộc gọi LLM. Không thể theo dõi chi phí hoặc phát hiện các vấn đề về context budget. |
| O5 | **Không theo dõi độ trễ (latency) cho các cuộc gọi LLM trong NMAIex** | UC-7, UC-8, UC-10 | Phần Chat có thuộc tính `latencyMs` trong `GenerationTrace`, nhưng các cuộc gọi LLM của bộ mapper không hề đo đạc hay ghi nhận độ trễ. |
| O6 | **Trường parserVer không được điền bởi các adapter** | UC-1 | Trường `ParsedCV.parserVer` có tồn tại trong schema nhưng không được thiết lập bởi bất kỳ adapter nào — luôn nhận giá trị `None`. |
| O7 | **Ghi nhật ký (logging) của summarization model chưa đầy đủ** | UC-5, UC-6 | Chỉ ghi log tên của `summaryModel` chứ không có bảng lưu trữ nhật ký kiểm toán lâu dài (khác biệt với chat queries có bảng lưu trữ → `AIQUERYLOG`). |
| O8 | **Không ghi log có cấu trúc cho các cuộc gọi embedding** | UC-2 | Chỉ có các dòng log thành công/thất bại cơ bản. Không theo dõi chi phí, độ trễ hoặc số lượng chiều (dimension) cho từng request. |
| O9 | **Quá trình chunking có rất ít nhật ký log** | UC-3 | Chỉ ghi log phương thức (strategy) bên trong wrapper `split_into_chunks`. Hàm `process_document_to_chunks` hoàn toàn không có hoạt động ghi log. |
| O10 | **Không có tính năng ước tính chi phí của model** | Tất cả | Thiếu cơ chế ước tính hoặc theo dõi chi phí API giữa các nhà cung cấp khác nhau. |

---

## Phụ lục F: Các Prompt Ưu tiên để Đánh giá trong P1-A (P1-A Priority Prompts for Review)

Dựa trên danh mục inventory này, các prompt sau đây nên được ưu tiên rà soát trước trong giai đoạn P1-A, được sắp xếp theo mức độ rủi ro và sức ảnh hưởng trên môi trường production:

| Mức độ ưu tiên (Priority) | Prompt | Lý do (Reason) |
|---|---|---|
| 1 | P3 — HR Co-pilot System Prompt | Mức độ hiển thị cao nhất: tương tác trực tiếp với người dùng qua chat, dữ liệu chưa xác thực đưa vào system prompt, tính năng grounding đóng vai trò then chốt cho các quyết định của bộ phận HR. Sẽ thay đổi khi chuyển dịch sang full-CV. |
| 2 | P1 — CV Parse Prompt | Pipeline dữ liệu cốt lõi: mọi CV đều phải chảy qua đây. Ràng buộc bởi structured output contract. Có sự khác biệt lớn về hành vi giữa các nhà cung cấp. |
| 3 | P7 — Skill Mapping Prompt | Chất lượng dữ liệu production: việc ánh xạ sai sẽ trực tiếp ảnh hưởng đến kết quả ranking. Chưa có cơ chế xác thực sự tồn tại của dữ liệu đầu ra. |
| 4 | P6 — Province Mapping Prompt | Tương tự như trên; các quy tắc sáp nhập tỉnh thành cần độ chính xác cao. |
| 5 | P8 — Proficiency Normalization | Cơ chế tự động fallback về BASIC trong im lặng có thể khiến hệ thống đánh giá thấp ứng viên một cách có hệ thống. |
| 6 | P4/P5 — Summarization Prompts | Ít rủi ro hơn nhưng gây ảnh hưởng trực tiếp đến tính liên tục của cuộc trò chuyện. |

---

## Phụ lục G: Sơ đồ Lệnh gọi (Who Calls What / Caller Map)

```
routes_ingestion.py (POST /ingestion/jobs)
  └→ cv_parser.py:CVParserOrchestrator.parse()
      └→ cv_parser_adapters.py:[Gemini|OpenAI|Anthropic]ProviderAdapter.parse()
  └→ chunking.py:process_document_to_chunks()
  └→ embedding.py:embed_chunks()
  └→ persistence.py:save_document_chunks()

routes_chat.py (POST /chat/query)
  └→ rag_query.py:process_chat_query()
      └→ embedding.py:embed_chunks([prompt])
      └→ rag_query.py:_vector_search()
      └→ rag_query.py:_build_system_prompt()
      └→ rag_orchestrator.py:invoke_generation()
          └→ rag_model_adapters.py:[Gemini|OpenAI|Anthropic]GenerationAdapter.generate()

routes_chat.py (POST .../summarize)
  └→ rag_orchestrator.py:invoke_generation()

routes_chat.py (POST .../branch-new)
  └→ rag_orchestrator.py:invoke_generation()

nmaiex_candidate_enrichment.py:run_enrichment_job()
  └→ nmaiex_mapper_service.py:map_skills()
      └→ rag_orchestrator.py:invoke_generation()  [auto-lite]
  └→ nmaiex_mapper_service.py:embed_and_store_raw_skills()
      └→ embedding.py:embed_chunks()
  └→ nmaiex_mapper_service.py:map_string_to_province_id()
      └→ rag_orchestrator.py:invoke_generation()  [auto-lite]
  └→ nmaiex_mapper_service.py:normalize_proficiency()
      └→ rag_orchestrator.py:invoke_generation()  [auto-lite]

nmaiex_ranking_service.py:rank_candidates_for_job()
  └→ embedding.py:embed_chunks([job_text])
  └→ nmaiex_ranking_service.py:compute_skill_score()
      └→ pgvector cosine distance (pre-stored embeddings)

scripts/retry_nmaiex_candidate_enrichment.py
  └→ nmaiex_candidate_enrichment.py:run_enrichment_job()

synthetic_data/run_pipeline.py
  └→ synthetic_data/generator.py:_call_llm()  [9Router proxy]
  └→ [monkey-patched] embedding.py:embed_chunks()
```

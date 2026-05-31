# Hướng dẫn Module Embedding (`embedding.py` & persistence liên quan)

Tài liệu này giải thích cách sử dụng và cách hoạt động của Embedding Layer trong FANG. Nếu `embedding_strategy.md` tập trung vào quyết định kiến trúc, tài liệu này tập trung vào cách code hiện tại vận hành.

> [!NOTE]
> Phiên bản trước của tài liệu này mô tả OpenAI `text-embedding-3-small`. Phiên bản cũ đã được archive tại `docs/archive/embedding_guide_openai_legacy.md`.

## 1. Luồng hoạt động

Quá trình nhúng vector hiện tại gồm các bước:

1. Nhận danh sách chunk văn bản đã được chuẩn hóa.
2. Kiểm tra cấu hình: provider phải là `gemini`, có `GOOGLE_API_KEY`, `batch_size > 0`.
3. Validate từng chunk: phải là chuỗi không rỗng.
4. Chia danh sách đầu vào thành các batch nhỏ theo `EMBEDDING_BATCH_SIZE` (mặc định 32).
5. Gọi Gemini Embedding API qua `google.genai` SDK — `genai.Client.models.embed_content()` với `output_dimensionality`.
6. Ghép vector trả về lại theo đúng thứ tự chunk ban đầu.
7. Validate: số vector == số chunk.
8. Chuyển vector sang định dạng chuỗi pgvector để lưu DB.

## 2. Các file chính

* `app/services/embedding.py`
  * chịu trách nhiệm gọi Gemini Embedding API
  * validate đầu vào (5 bước kiểm tra)
  * batch và gom kết quả trả về
  * dùng `asyncio.to_thread()` để wrap synchronous SDK call

* `app/services/persistence.py`
  * `_serialize_embedding()` — serialize vector sang định dạng pgvector
  * `_resolve_pgvector_type()` — quyết định cast kiểu `halfvec` hoặc `vector`
  * insert vào `AIDOCUMENTCHUNK`

* `app/core/config.py`
  * định nghĩa các cấu hình embedding dùng ở runtime

* `app/core/nmaiex_config.py`
  * `NMAIEX_SKILL_EMBEDDING_DIM` — dimension riêng cho NMAIex skill embedding (mặc định 256)

## 3. Cấu hình cần thiết

Các biến môi trường quan trọng:

* `GOOGLE_API_KEY` — API key cho Gemini
* `EMBEDDING_PROVIDER` — provider embedding (hiện chỉ hỗ trợ `gemini`)
* `EMBEDDING_MODEL` — tên model (mặc định `gemini-embedding-001`)
* `EMBEDDING_DIM` — dimension mặc định (mặc định `1536`)
* `EMBEDDING_BATCH_SIZE` — kích thước batch (mặc định `32`)
* `EMBEDDING_VECTOR_TYPE` — kiểu lưu trữ pgvector (`halfvec` hoặc `vector`)

Giá trị mặc định hiện tại trong code:

* `EMBEDDING_PROVIDER=gemini`
* `EMBEDDING_MODEL=gemini-embedding-001`
* `EMBEDDING_DIM=1536`
* `EMBEDDING_BATCH_SIZE=32`
* `EMBEDDING_VECTOR_TYPE=halfvec`

## 4. Hợp đồng đầu vào / đầu ra

### Đầu vào của `embed_chunks`

`embed_chunks(chunks: List[str], dimensions: Optional[int] = None) -> List[List[float]]`

Ràng buộc:

* mỗi phần tử phải là chuỗi không rỗng
* danh sách rỗng thì trả về danh sách rỗng
* provider hiện chỉ hỗ trợ `gemini`
* `dimensions` cho phép override dimension — dùng cho NMAIex skill embedding (256 dims)

### Đầu ra

* số vector trả về phải bằng số chunk đầu vào
* chiều của từng vector khớp với `dimensions` (hoặc `EMBEDDING_DIM` nếu không truyền)

Nếu API trả về thiếu vector hoặc sai số lượng, hàm sẽ ném `RuntimeError` thay vì âm thầm bỏ qua.

## 5. Cách lưu vào PostgreSQL

`persistence.py` dùng hai bước:

1. `_serialize_embedding`
   * biến list float thành chuỗi dạng `[0.1,0.2,...]`
2. `_resolve_pgvector_type`
   * xác định runtime đang cast sang `halfvec` hay `vector`

Insert cuối cùng sẽ có dạng logic:

```sql
INSERT ... VALUES (..., $7::halfvec)
```

hoặc:

```sql
INSERT ... VALUES (..., $7::vector)
```

tùy theo `EMBEDDING_VECTOR_TYPE`.

## 6. Kiểm thử hiện có

Các lớp kiểm thử đã có trong repo:

* `tests/unit/unit_test_embedding.py`
  * mock `FakeGeminiClient` (Gemini SDK)
  * kiểm tra model, batching, dimension
  * kiểm tra validation (empty chunks, invalid provider)
  * 7 test cases, tất cả pass

* `tests/unit/unit_test_persistence.py`
  * kiểm tra serialize vector
  * kiểm tra lựa chọn `halfvec` / `vector`

* `tests/unit/unit_test_ingestion_flow.py`
  * kiểm tra tích hợp route ingestion với chunking và embedding bằng mock

* `smoke_tests/test_e2e_pipeline.py`
  * chạy pipeline thật với parser + embedding + DB
  * expected dimension: 1536

## 7. Những lỗi thường gặp

### Lệch dimension giữa runtime và DB

Đây là lỗi dễ gặp nhất.

Ví dụ:

* runtime đang dùng `EMBEDDING_DIM=1536`
* schema DB lại đang là `halfvec(256)`

Khi đó insert sẽ lỗi do vector không khớp chiều. Không reset DB trong test
thông thường; cần lập kế hoạch migration/schema rebuild riêng nếu đổi embedding
dimension hoặc vector storage type.

### Lệch kiểu vector

Ví dụ:

* runtime cast `::vector`
* schema DB lại đang là `halfvec(1536)`

Lúc đó insert hoặc index sẽ không khớp với thiết kế schema hiện tại.

### Thiếu API key

* `GOOGLE_API_KEY` không được set → `embed_chunks()` raise `ValueError` ngay ở bước validation
* Parser có thể chạy (dùng key khác) nhưng embedding fail nếu Gemini key thiếu

### Gemini API outage

* Không có fallback provider — toàn bộ embedding bị tê liệt
* Ingestion task sẽ fail, cần manual re-run

## 8. Cách chạy nhanh để kiểm chứng

Chạy unit test:

```bash
venv\Scripts\python -m unittest discover -s tests/unit -p "unit_test_embedding*"
```

Chạy script E2E (cần DB + Gemini API key):

```bash
python smoke_tests/test_e2e_pipeline.py
```

Mục tiêu mong đợi:

* parse thành công
* sinh ra chunk
* gọi Gemini embedding thành công
* lưu đủ số chunk và vector vào `AIDOCUMENTCHUNK`

## 9. Tài Liệu Liên Quan

* `docs/strategy/embedding_strategy.md` — Quyết định kiến trúc embedding
* `agent_workflow_doc/P0B_AI_LLM_INVENTORY_REPORT.md` — UC-2 (Text Embedding), UC-9 (Skill Embedding)

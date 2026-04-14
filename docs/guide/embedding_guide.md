# Hướng dẫn Module Embedding (`embedding.py` & persistence liên quan)

Tài liệu này giải thích cách sử dụng và cách hoạt động của Embedding Layer trong FANG. Nếu `embedding_strategy.md` tập trung vào quyết định kiến trúc, tài liệu này tập trung vào cách code hiện tại vận hành.

## 1. Luồng hoạt động

Quá trình nhúng vector hiện tại gồm các bước:

1. Nhận danh sách chunk văn bản đã được chuẩn hóa.
2. Kiểm tra cấu hình provider/model/dimension.
3. Chia danh sách đầu vào thành các batch nhỏ theo `EMBEDDING_BATCH_SIZE`.
4. Gọi OpenAI Embeddings API bằng `text-embedding-3-small`.
5. Ghép vector trả về lại theo đúng thứ tự chunk ban đầu.
6. Chuyển vector sang định dạng chuỗi pgvector để lưu DB.

## 2. Các file chính

* `app/services/embedding.py`
  * chịu trách nhiệm gọi OpenAI API
  * validate đầu vào
  * batch và gom kết quả trả về

* `app/services/persistence.py`
  * serialize vector sang định dạng pgvector
  * quyết định cast kiểu `halfvec` hoặc `vector`
  * insert vào `AIDOCUMENTCHUNK`

* `app/core/config.py`
  * định nghĩa các cấu hình embedding dùng ở runtime

## 3. Cấu hình cần thiết

Các biến môi trường quan trọng:

* `OPENAI_API_KEY`
* `EMBEDDING_PROVIDER`
* `EMBEDDING_MODEL`
* `EMBEDDING_DIM`
* `EMBEDDING_BATCH_SIZE`
* `EMBEDDING_VECTOR_TYPE`

Giá trị mặc định hiện tại trong repo:

* `EMBEDDING_PROVIDER=openai`
* `EMBEDDING_MODEL=text-embedding-3-small`
* `EMBEDDING_DIM=1024`
* `EMBEDDING_BATCH_SIZE=32`
* `EMBEDDING_VECTOR_TYPE=halfvec`

## 4. Hợp đồng đầu vào / đầu ra

### Đầu vào của `embed_chunks`

`embed_chunks(chunks: List[str]) -> List[List[float]]`

Ràng buộc:

* mỗi phần tử phải là chuỗi không rỗng
* danh sách rỗng thì trả về danh sách rỗng
* provider hiện chỉ hỗ trợ `openai`

### Đầu ra

* số vector trả về phải bằng số chunk đầu vào
* chiều của từng vector phải khớp với `EMBEDDING_DIM`

Nếu API trả về thiếu vector hoặc sai số lượng, hàm sẽ ném lỗi thay vì âm thầm bỏ qua.

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

* `test_embedding.py`
  * mock OpenAI client
  * kiểm tra model, batching, dimension

* `test_persistence.py`
  * kiểm tra serialize vector
  * kiểm tra lựa chọn `halfvec` / `vector`

* `test_ingestion_flow.py`
  * kiểm tra tích hợp route ingestion với chunking và embedding bằng mock

* `test_e2e_pipeline.py`
  * chạy pipeline thật với parser + embedding + DB

## 7. Những lỗi thường gặp

### Lệch dimension giữa runtime và DB

Đây là lỗi dễ gặp nhất.

Ví dụ:

* runtime đang dùng `EMBEDDING_DIM=1536`
* schema DB lại đang là `halfvec(1024)`

Khi đó insert sẽ lỗi do vector không khớp chiều.

### Lệch kiểu vector

Ví dụ:

* runtime cast `::vector`
* schema DB lại đang là `halfvec(1024)`

Lúc đó insert hoặc index sẽ không khớp với thiết kế schema hiện tại.

### Thiếu credit hoặc key API

* parser có thể chạy nhưng embedding fail
* hoặc embedding thành công nhưng DB fail nếu schema cũ chưa được apply lại

## 8. Cách chạy nhanh để kiểm chứng

Chạy script E2E:

```bash
python test_e2e_pipeline.py
```

Khi cần ép đúng cấu hình runtime:

```bash
EMBEDDING_DIM=1024
EMBEDDING_VECTOR_TYPE=halfvec
python test_e2e_pipeline.py
```

Mục tiêu mong đợi:

* parse thành công
* sinh ra chunk
* gọi OpenAI embeddings thành công
* lưu đủ số chunk và vector vào `AIDOCUMENTCHUNK`

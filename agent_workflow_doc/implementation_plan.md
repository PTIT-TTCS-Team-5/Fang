# Mục Tiêu

Bản thiết kế kiến trúc và đặc tả kỹ thuật cho Phase Embedding của hệ thống AI Core (dự án FANG), nhằm chuyển hóa CV từ dạng JSON (sau parse) thành các vector embedding và lưu trữ vào pgvector. Tài liệu này đóng vai trò là bản bàn giao (handoff spec) chuyển cho Chat B (model thực thi) tiến hành gõ code.

## User Review Required

> [!IMPORTANT]
> Đây là bản thiết kế kiến trúc. Người dùng cần duyệt qua các quyết định về lưu trữ (halfvec vs vector), dimension (1024), model embedding (`text-embedding-3-small`), và thứ tự triển khai trước khi agent chuyển sang phase lập trình thực tế (Chat B).

## 1. Đánh giá kiến trúc hiện tại và khoảng trống (Gap Analysis)

**Kiến trúc hiện hành:**
- Phase Parser đã hoàn thiện với kiến trúc 3-tier (Gemini Flash -> GPT-4o-mini -> Claude Haiku), retry policy với `tenacity` và quality gate.
- Đầu ra của parser (`ParsedCV`) đã ổn định, chứa văn bản thô `raw_text` và structured JSON, được lưu tại bảng `CVPARSED`.
- Luồng `POST /v1/ingestion/jobs` đã có khung nhưng mới dừng ở đoạn parse thành công. Các hàm stub cho đoạn lưu `AIDOCUMENTCHUNK` (`save_document_chunks`) đang chưa tích hợp với module chunking và embedding thực tế.

**Khoảng trống cần bù đắp (Gaps cho Phase Embedding):**
1. Gọi thực tế hàm `convert_json_to_markdown` và `process_document_to_chunks` trong handler/service luồng ingestion.
2. Tích hợp OpenAI client để gọi `text-embedding-3-small` (dimension 1024) thực tế bên trong `app/services/embedding.py` (hiện tại đang là stub trả về vector 0.0).
3. Triển khai schema DB `AIDOCUMENTCHUNK` bao gồm setup `vector`/`halfvec` plugin trên PostgreSQL.
4. Cập nhật `app/services/persistence.py` để xử lý insert embedding data đúng chuẩn pgvector.

## 2. Thiết kế Kiến trúc Embedding End-to-End

Luồng xử lý (Ingestion Pipeline) cụ thể như sau:
1. **Ingestion Trigger**: Lấy kết quả `ParsedCV` (JSON) vừa thành công từ bước Parse.
2. **Flatten**: Sử dụng `markdown_builder.py` để làm phẳng cấu trúc JSON thành văn bản Markdown phân cấp theo Heading, đồng thời trích xuất siêu dữ liệu (Global Context) thông qua `extract_global_metadata`.
3. **Chunking**: Truyền nội dung Markdown và Context vào `process_document_to_chunks` (trong `chunking.py`). 
    - Thực thi Zero-LLM chunking với `MarkdownHeaderTextSplitter`.
    - Áp dụng cấu trúc Small-to-Big Retrieval: Block > 512 tokens sẽ bị chia đệ quy ở mức 180 tokens/chunk (overlap 36 tokens, ~20%).
    - Tiêm Section-Pinning (Bối cảnh): Gắn Metadata vào đầu prefix mỗi child chunk.
4. **Embed**: Gửi batch danh sách các chunk đã tiêm bối cảnh lên OpenAI API (`text-embedding-3-small`) sử dụng tham số `dimensions=1024`.
5. **Persist**: Lưu cục bộ chunk (content, tokenCount, metadata) cùng vector vào `AIDOCUMENTCHUNK`. Cấu hình kiểu dữ liệu **`halfvec`** để tối ưu dung lượng.
6. **Retrieve**: Khi query tìm kiếm, sử dụng Index **`HNSW`** (Cosine) trên bảng PG để trích xuất chunk liên quan.

## 3. Chiến lược Chunking Chi Tiết

- **Ngưỡng an toàn block gốc (Threshold):** `PARENT_CHUNK_TOKEN_LIMIT = 512` tokens. 
- **Độ phân giải Child Chunk:** `CHILD_CHUNK_TARGET_TOKENS = 180` tokens.
- **Chồng chéo (Overlap):** `CHILD_CHUNK_OVERLAP_TOKENS = 36` tokens (~20%).
- **Metadata Injection:** Prefix cho từng chunk áp dụng cấu trúc tĩnh:
  `[Candidate: {Tên} | Total Exp: {Số năm} | Target Role: {Vị trí tiềm năng} | Core Skills: {Kỹ năng}] \n\n {Nội dung khối}`
- **Chuẩn hóa token:** Tiếp tục sử dụng `approx_token_count` (`CHARS_PER_TOKEN = 3.5`) hiện có nhưng xác nhận log token thực tế trả về từ OpenAI API để tinh chỉnh sau.

## 4. Thiết kế Schema Khởi Tạo DB và Chỉ Mục

### Bảng `AIDOCUMENTCHUNK`
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS AIDOCUMENTCHUNK (
    chunkId SERIAL PRIMARY KEY,
    jobAppId INTEGER NOT NULL,
    sourceType VARCHAR(50) NOT NULL, -- 'CV', 'JD', 'COVER_LETTER'
    content TEXT NOT NULL,
    chunkIndex INTEGER NOT NULL,
    tokenCount INTEGER NOT NULL,
    metadata JSONB,
    embedding halfvec(1024), -- Lượng tử hóa vô hướng để giảm 50% RAM In-memory
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### HNSW Index (Môi trường DEV)
```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_aidocchunk_hnsw_cosine
ON AIDOCUMENTCHUNK
USING hnsw (embedding halfvec_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

> [!TIP]
> Sử dụng `halfvec(1024)` cho môi trường DEV kết hợp model OpenAI `text-embedding-3-small` là chiến lược cực kỳ tốt theo bản R&D. Cho phép duy trì mức giá rất rẻ nhưng giữ RAM index siêu thấp, trong khi recall vẫn đảm bảo ~94%. 

## 5. Kế hoạch Kiểm thử (Test Plan)

### Smoke Tests
- `test_chunking.py`: Sử dụng 1 CV dạng JSON truyền vào, theo dõi đầu ra đảm bảo list chunk có tiền tố "Candidate...", không vượt token size.
- `test_embedding.py`: Mock test để kiểm chứng API client, config model và tham số dimensions có được load đúng từ biến môi trường.

### Integration / Quality Checks
- Viết integration test `test_ingestion_flow.py`: Đi qua từ Mock ParsedCV -> Markdown -> Chunking -> Mock Embedding -> SQLite hoặc Postgres test container. Sau khi insert, verify dòng dữ liệu trong bảng.
- Kiểm thử cơ chế "Replace Existing": Giả lập chạy re-ingest CV cho cùng một `jobAppId` để confirm chunk cũ bị xóa và thay thế bằng tập mới hoàn toàn mà không duplicate dòng.

## Proposed Changes (Đặc Tả Bàn Giao Cho Chat B)

**Phạm vi File Cần Cập Nhật & Thứ tự:**

### 1. File Cấu Hình & Database Schema
#### [MODIFY] [config.py](file:///c:/Users/os/Desktop/cur_prj/Fang/app/core/config.py)
- Khai báo mapping/struct lấy `OPENAI_API_KEY`, chuyển tham số `EMBEDDING_PROVIDER` sang `openai`, gán `EMBEDDING_DIM` mặc định là `1024`.
#### [MODIFY] `db/init.sql` (hoặc nơi quản lý schema DB)
- Thêm script cài extension `vector` và tạo bảng `AIDOCUMENTCHUNK` với type `halfvec(1024)`. Thêm script tạo index HNSW.

### 2. Lõi Embedding
#### [MODIFY] [embedding.py](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/embedding.py)
- Setup SDK OpenAI (`import openai`, khởi tạo AsyncClient). 
- Replace hàm `embed_chunks` hiện tại để gọi API `embeddings.create(model=..., input=..., dimensions=1024)`. Thêm xử lý batching nếu file PDF quá lớn (nhưng với CV ~5 chunks thì call 1 batch là đủ).

### 3. Tích Hợp Luồng
#### [MODIFY] [routes_ingestion.py](file:///c:/Users/os/Desktop/cur_prj/Fang/app/api/routes_ingestion.py)
- Bổ sung việc trigger `convert_json_to_markdown` và `process_document_to_chunks` thay vi chỉ dừng lại ở Parse.
- Map trả về danh sách payloads và gọi `embed_chunks`.
#### [MODIFY] [persistence.py](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/persistence.py)
- Cập nhật hàm `save_chunk_payloads` và format lưu mảng array vào kiểu Postgres Vector.

---

## 6. Rủi Ro & Rollback Plan

- **Rủi ro 1**: System Postgres cục bộ hiện tại chưa enable extension pgvector, tạo bảng `halfvec` gây lỗi crash luồng DB.
  *Mitigation*: Kiểm tra kỹ requirement và script `init.sql` chạy đúng thứ tự `CREATE EXTENSION IF NOT EXISTS vector;` trước CREATE TABLE.
- **Rủi ro 2**: Rate limit của OpenAI API (dù CV ít nhưng nếu ingest bulk lượng lớn).
  *Mitigation*: Sử dụng cơ chế retry `tenacity` (tương tự như Phase 1 - parser) áp dụng quanh hàm `embed_chunks`.
- **Kế hoạch Rollback**: Nhánh `feat/embedding-phase` đang biệt lập hoàn toàn. Nếu có bug rớt DB, có thể drop index/bảng `AIDOCUMENTCHUNK` và reset head không làm ảnh hưởng nhánh parser.

## Open Questions
- Hình thức setup DB Postgres hiện tại của người dùng là qua Docker Container? Nếu đúng thì cần nhắc nhở dev (Chat B hoặc User) cấu hình dùng image hỗ trợ `pgvector` (ví dụ: `pgvector/pgvector:pg16`).
- File `init.sql` thực tế nằm ở đâu trong repo để Chat B cập nhật? (Agent B sẽ phải quét dự án để tìm file chạy init hoặc migration tool nếu có).

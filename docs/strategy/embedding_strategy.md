# Chiến Lược Embedding (AI Core)

Tài liệu này mô tả các quyết định kiến trúc cốt lõi cho giai đoạn Embedding trong FANG, nơi các chunk văn bản đã qua parse và chunking được biến đổi thành vector để lưu vào PostgreSQL `pgvector`.

> [!NOTE]
> Phiên bản trước của tài liệu này mô tả OpenAI `text-embedding-3-small` 1024 dims. Phiên bản cũ đã được archive tại `docs/archive/embedding_strategy_openai_legacy.md`.

## 1. Mục Tiêu

Giai đoạn Embedding có ba mục tiêu chính:

* Chuẩn hóa toàn bộ chunk đầu vào thành vector cùng số chiều.
* Lưu vector theo cách tối ưu cho môi trường local/DEV nhưng vẫn dễ nâng cấp về sau.
* Giữ cho pipeline parse → chunking → embedding → database chạy được end-to-end với chi phí thấp.

## 2. Mô Hình và Cấu Hình Hiện Tại

Các quyết định đang được dùng trong codebase hiện tại:

* **Provider:** Google (Gemini)
* **Model:** `gemini-embedding-001`
* **Dimension mặc định:** `1536` (cấu hình qua `EMBEDDING_DIM` trong `.env`)
* **NMAIex skill embedding:** `256` dims (cấu hình qua `NMAIEX_SKILL_EMBEDDING_DIM` trong `.env.nmaiex`)
* **Batching:** `32` (cấu hình qua `EMBEDDING_BATCH_SIZE`)
* **Storage mặc định:** `halfvec(1536)` cho document chunks, `vector(256)` cho NMAIex skill embeddings
* **SDK:** `google.genai` — gọi qua `genai.Client.models.embed_content()`
* **API Key:** `GOOGLE_API_KEY`

Lý do chọn cấu hình này:

* `gemini-embedding-001` hỗ trợ native `output_dimensionality` (Matryoshka-compatible truncation) — cho phép dùng dims khác nhau cho use case khác nhau mà không cần post-process.
* `dimensions=1536` là native dimension mặc định, cho semantic depth tốt nhất cho document chunks dài.
* `dimensions=256` cho NMAIex skill embedding — text kỹ năng rất ngắn (1–5 từ), 256 dims đủ chất lượng và giảm chi phí lưu trữ/compute đáng kể.
* `halfvec` giảm chi phí RAM/index rõ rệt cho môi trường local và DEV.

### 2.1 Fallback và Retry

* **Không có fallback provider** — chỉ dùng Gemini. Sự cố API Gemini sẽ làm tê liệt toàn bộ embedding.
* **Không có retry** ở layer embedding — lỗi được re-raise lên caller. Caller (ingestion pipeline) có thể retry toàn bộ task.
* Đây là risk đã ghi nhận (P0-B F2). Khi cần, có thể thêm fallback provider hoặc retry tại layer này.

## 3. Quy Tắc Thiết Kế

### 3.1. Embedding chỉ nhận văn bản đã chuẩn hóa

Embedding Layer không làm sạch hay phân tích ngữ nghĩa đầu vào. Nó chỉ nhận:

* nội dung chunk đã được tiêm `global_context`
* header cha đã được bảo toàn từ giai đoạn chunking

Điều này giúp phân tầng trách nhiệm rõ ràng:

* Parser chịu trách nhiệm tạo dữ liệu có cấu trúc.
* Chunking chịu trách nhiệm tối ưu đơn vị ngữ nghĩa để truy xuất.
* Embedding chỉ chịu trách nhiệm ánh xạ văn bản thành vector.

### 3.2. Validation trước khi embed

`embed_chunks()` thực hiện 5 bước kiểm tra upfront:

1. `provider == "gemini"` — từ chối provider không hỗ trợ.
2. `GOOGLE_API_KEY` tồn tại — tránh lỗi auth muộn.
3. `batch_size > 0` — tránh infinite loop.
4. Mỗi chunk phải là chuỗi ký tự không rỗng.
5. Số lượng vector trả về == số lượng chunk — phát hiện mismatch ngay.

### 3.3. Không khóa cứng chiến lược lưu trữ vector

FANG hiện mặc định dùng `halfvec`, nhưng quyết định này được giữ ở mức cấu hình:

* `EMBEDDING_VECTOR_TYPE=halfvec`
* các giá trị hợp lệ hiện tại: `halfvec`, `vector`

Mục tiêu là cho phép chuyển đổi chiến lược lưu trữ mà không phải refactor pipeline ingestion.

## 4. Chiến Lược Lưu Trữ Vector

### Mặc định hiện tại: `halfvec`

* phù hợp cho local/DEV
* tiết kiệm RAM và kích thước index
* đủ tốt cho bài toán thử nghiệm RAG hiện tại

### Khi nào cân nhắc `vector`

* khi cần giữ độ chính xác số học tối đa
* khi muốn benchmark recall/latency giữa `vector` và `halfvec`
* khi môi trường hạ tầng không còn bị ràng buộc nhiều bởi RAM

### Cách đổi nhanh sang `vector`

Hiện tại việc chuyển đổi được thiết kế để khá nhẹ:

1. Đổi schema và index trong `database/schema_ai_core.sql`:
	- `embedding halfvec(1536)` → `embedding vector(1536)`
	- `halfvec_cosine_ops` → `vector_cosine_ops`
2. Đổi cấu hình runtime trong `.env` thành `EMBEDDING_VECTOR_TYPE=vector`.
3. Xác nhận logic cast/validate tương thích trong `app/services/persistence.py` (hàm `_resolve_pgvector_type` và `_serialize_embedding`) và `app/services/rag_query.py` (query cast theo `settings.embedding_vector_type`).

## 5. Cách Pipeline Tương Tác Với Embedding

Đầu vào của Embedding Layer là danh sách `ChunkPayload`:

* `content`
* `tokenCount`
* `chunkIndex`

Đầu ra là:

* danh sách vector cùng chiều (`List[List[float]]`)
* được map 1-1 trở lại vào từng chunk để lưu vào `AIDOCUMENTCHUNK`

Pipeline này hiện đã được kiểm chứng end-to-end bằng smoke test `test_e2e_pipeline.py` (1536 dims).

### 5.1 NMAIex Skill Embedding

NMAIex skill embedding dùng cùng `embed_chunks()` nhưng với `dimensions=256`:

* Entry point: `nmaiex_mapper_service.py:embed_and_store_raw_skills()`
* Lưu vào `CANDIDATE_SKILL_RAW` và `JOB_SKILL_RAW` (kiểu `::vector`, không phải `halfvec`)
* Dùng cho fuzzy skill scoring trong ranking (cosine distance trên pgvector)

## 6. Kiến Trúc Chỉ Mục

Vector được lưu trong bảng `AIDOCUMENTCHUNK` và đánh index bằng HNSW cosine.

Mục tiêu:

* tối ưu truy xuất ngữ nghĩa sau này
* giữ cấu trúc đủ đơn giản để dễ debug trong giai đoạn phát triển

## 7. Nguyên Tắc Mở Rộng Sau Này

Khi hệ thống chuyển sang giai đoạn production hoặc benchmark chuyên sâu, các hướng mở rộng hợp lý là:

* thêm fallback embedding provider (risk F2 — hiện chỉ Gemini)
* thêm retry ở layer embedding
* đổi kiểu lưu trữ `halfvec` / `vector`
* thêm logging chi tiết hơn cho usage, latency và token consumption (gap O8)
* thêm bước validate trước khi insert để phát hiện mismatch dimension với schema DB

## 8. Tài Liệu Liên Quan

* `app/services/embedding.py` — Code entry point
* `app/core/config.py` — Cấu hình `EMBEDDING_DIM`, `EMBEDDING_BATCH_SIZE`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`
* `app/core/nmaiex_config.py` — Cấu hình `NMAIEX_SKILL_EMBEDDING_DIM`
* `docs/guide/embedding_guide.md` — Hướng dẫn vận hành thực tế
* `agent_workflow_doc/P0B_AI_LLM_INVENTORY_REPORT.md` — UC-2 (Text Embedding), UC-9 (NMAIex Skill Embedding)

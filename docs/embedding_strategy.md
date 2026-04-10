# Chiến Lược Embedding (AI Core - Pha 3)

Tài liệu này mô tả các quyết định kiến trúc cốt lõi cho giai đoạn Embedding trong FANG, nơi các chunk văn bản đã qua parse và chunking được biến đổi thành vector để lưu vào PostgreSQL `pgvector`.

## 1. Mục Tiêu

Giai đoạn Embedding có ba mục tiêu chính:

* Chuẩn hóa toàn bộ chunk đầu vào thành vector cùng số chiều.
* Lưu vector theo cách tối ưu cho môi trường local/DEV nhưng vẫn dễ nâng cấp về sau.
* Giữ cho pipeline parse -> chunking -> embedding -> database chạy được end-to-end với chi phí thấp.

## 2. Mô Hình và Cấu Hình Hiện Tại

Các quyết định đang được dùng trong codebase hiện tại:

* **Provider:** OpenAI
* **Model:** `text-embedding-3-small`
* **Dimension:** `1024`
* **Batching:** cấu hình qua `EMBEDDING_BATCH_SIZE`
* **Storage mặc định:** `halfvec(1024)`

Lý do chọn cấu hình này:

* `text-embedding-3-small` có chi phí thấp và dễ tích hợp trực tiếp bằng SDK.
* `dimensions=1024` giúp giảm tải lưu trữ so với 1536 chiều nhưng vẫn phù hợp cho thử nghiệm và phát triển.
* `halfvec` giảm chi phí RAM/index rõ rệt cho môi trường local và DEV.

## 3. Quy Tắc Thiết Kế

### 3.1. Embedding chỉ nhận văn bản đã chuẩn hóa

Embedding Layer không làm sạch hay phân tích ngữ nghĩa đầu vào. Nó chỉ nhận:

* nội dung chunk đã được tiêm `global_context`
* header cha đã được bảo toàn từ giai đoạn chunking

Điều này giúp phân tầng trách nhiệm rõ ràng:

* Parser chịu trách nhiệm tạo dữ liệu có cấu trúc.
* Chunking chịu trách nhiệm tối ưu đơn vị ngữ nghĩa để truy xuất.
* Embedding chỉ chịu trách nhiệm ánh xạ văn bản thành vector.

### 3.2. Không khóa cứng chiến lược lưu trữ vector

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

1. Đổi schema từ `embedding halfvec(1024)` sang `embedding vector(1024)`.
2. Đổi index từ `halfvec_cosine_ops` sang `vector_cosine_ops`.
3. Đổi cấu hình runtime `EMBEDDING_VECTOR_TYPE=vector`.

## 5. Cách Pipeline Tương Tác Với Embedding

Đầu vào của Embedding Layer là danh sách `ChunkPayload`:

* `content`
* `tokenCount`
* `chunkIndex`

Đầu ra là:

* danh sách vector cùng chiều
* được map 1-1 trở lại vào từng chunk để lưu vào `AIDOCUMENTCHUNK`

Pipeline này hiện đã được kiểm chứng end-to-end bằng script `test_e2e_pipeline.py`.

## 6. Kiến Trúc Chỉ Mục

Vector được lưu trong bảng `AIDOCUMENTCHUNK` và đánh index bằng HNSW cosine.

Mục tiêu:

* tối ưu truy xuất ngữ nghĩa sau này
* giữ cấu trúc đủ đơn giản để dễ debug trong giai đoạn phát triển

## 7. Nguyên Tắc Mở Rộng Sau Này

Khi hệ thống chuyển sang giai đoạn production hoặc benchmark chuyên sâu, các hướng mở rộng hợp lý là:

* đổi provider embedding
* đổi dimension
* đổi kiểu lưu trữ `halfvec` / `vector`
* thêm logging chi tiết hơn cho usage và latency
* thêm bước validate trước khi insert để phát hiện mismatch dimension với schema DB

# Implementation Plan: E2E Pipeline & Embedding Architecture

Kế hoạch này nhằm hoàn thiện luồng pipeline xử lý CV từ đầu đến cuối và giải quyết vấn đề mất ngữ cảnh (loss context) khi chia nhỏ tài liệu (chunking). Đồng thời, xác định mô hình và kiến trúc Embedding sẽ được sử dụng dựa trên các tài liệu nghiên cứu.

## 1. Kết Luận Khảo Sát Mô Hình Embedding

Dựa trên báo cáo `RAG_Embedding_Research_miCareer.md`, đây là kết luận dành cho giai đoạn hiện tại:

- **Mô hình được chọn cho Môi trường DEV/Test (Giai đoạn này):** `text-embedding-3-small` của OpenAI.
- **Cấu hình Dimension:** `1024` (Sử dụng tham số `dimensions=1024` trong API OpenAI theo chiến lược Matryoshka để tối ưu RAM và Storage mờ không giảm sút nhiều về accuracy).
- **Lý do:** Rẻ, kích thước context lớn (8192 tokens), dễ tích hợp SDK trực tiếp, và tiết kiệm storage so với bản gốc 1536 chiều.

> [!NOTE]
> Cho môi trường **PROD** (sau này), hệ thống sẽ cần dịch chuyển sang `gemini-embedding-001` (với `output_dimensionality=768`) của Google vì chất lượng tiếng Việt tốt hơn hẳn (MTEB: 68.32). Nhưng hiện tại ở local E2E test, việc sử dụng `text-embedding-3-small` là hợp lý nhất.

## 2. Kế Hoạch Cập Nhật Code (Giao việc cho Agent Execute)

### [Component: Chunking Service]

#### [MODIFY] [chunking.py](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/chunking.py)
* **Goal:** Khắc phục lỗi tại Chunk 3, 4 bị mất Header `## Experience` và mất ngữ cảnh cha.
* **Thay đổi chi tiết:**
  - Trong hàm `process_document_to_chunks`, sửa `strip_headers=False` thành `strip_headers=True` khi gọi `MarkdownHeaderTextSplitter`.
  - Lúc này, LangChain sẽ loại bỏ Header khỏi `node.page_content` nhưng lưu chúng trong `node.metadata` dưới dạng dictionary (ví dụ: `{"h1": "Nguyễn Hải Hưng", "h2": "Experience"}`).
  - Trong logic chia chunk con (bằng `RecursiveCharacterTextSplitter`), trước khi phân tích, cần trích xuất tuần tự các thẻ h1, h2, h3 từ `node.metadata` để tái cấu trúc lại một chuỗi Header chuẩn (ví dụ: `# Nguyễn Hải Hưng\n## Experience`).
  - **Header Injection:** Nối chuỗi Header này vào đầu **mỗi chunk con** trước khi lưu trữ (`ChunkPayload`). Điều này đảm bảo dù `Experience` bị xé nhỏ ra nhiều mảnh, bất cứ mảnh nào cũng vẫn có tiêu đề `## Experience` nằm ở trên để Embedding Model hiểu được bối cảnh.

### [Component: Luồng End-to-End Test]

#### [NEW] [test_e2e_pipeline.py](file:///c:/Users/os/Desktop/cur_prj/Fang/test_e2e_pipeline.py)
* **Goal:** Xây dựng một script test End-to-End hoàn chỉnh, bỏ qua quy trình Mock và thay bằng luồng dữ liệu thực tế.
* **Thay đổi chi tiết:**
  1. Trỏ đến file `sample.pdf` tại thư mục gốc, hoặc cho phép truyền URL từ Cloudinary.
  2. **Bước 1 (Parse):** Đẩy qua mô hình Gemini (`google:gemini-3.1-flash-lite-preview` hoặc bản mới nhất theo API key) để trích xuất JSON (`ParsedCV`).
  3. **Bước 2 (Markdown & Convert):** Lọc metadata ứng viên, chuyển JSON thành chuỗi Markdown thông qua module `markdown_builder`.
  4. **Bước 3 (Chunking):** Chạy `process_document_to_chunks` (sau khi đã được sửa lỗi Header context như đã nêu) để lấy danh sách chunk con.
  5. **Bước 4 (Embedding):** Khởi tạo OpenAI Client. Gửi một batch yêu cầu lên API `text-embedding-3-small` (kèm theo `dimensions=1024`) chứa toàn bộ content của chunks. (Lưu ý: API Embedding chỉ nhận Input Text, không nhận Prompt truyền thống như LLM, ta chỉ cần truyền mảng text lấy về mảng vector).
  6. **Bước 5 (Database):** Cập nhật PostgreSQL scheme cho cột `embedding vector(1024)`:
     - Tạo connection pool tới DB (Sử dụng file configs chuẩn trong `/core`).
     - Lưu thông tin vào `CVPARSED` và `AIDOCUMENTCHUNK`, insert các vector trực tiếp qua kiểu `pgvector` đúng như thiết kế ở Sprint 1.

### [Component: Database Migration (Tuỳ chọn)]

#### [MODIFY] DB Scripts hoặc hướng dẫn `psql` (Tuỳ chọn)
* Mặc định hiện tại chọn `halfvec(1024)` cho môi trường DEV/Test để tiết kiệm RAM và chi phí index.
* Cần ghi chú rõ trong schema/config rằng việc đổi sang `vector(1024)` là rất dễ:
  - `embedding halfvec(1024)` -> `embedding vector(1024)`
  - `halfvec_cosine_ops` -> `vector_cosine_ops`
  - `EMBEDDING_VECTOR_TYPE=halfvec` -> `EMBEDDING_VECTOR_TYPE=vector`
* Cần đảm bảo index `hnsw` với toán tử cosine tương ứng đã được áp dụng trong cơ sở dữ liệu `test_parser_db` để chuẩn bị cho vector search (Query).

### [Note: Flexibility cho Vector Storage]

Trong giai đoạn hiện tại, `halfvec` là lựa chọn mặc định. Tuy nhiên, để tránh khóa cứng quyết định kiến trúc:

- Runtime của ứng dụng nên đọc kiểu vector từ cấu hình `EMBEDDING_VECTOR_TYPE`.
- Schema SQL cần ghi chú trực tiếp các dòng phải đổi nếu muốn chuyển sang `vector`.
- Mục tiêu là để dev có thể đổi chiến lược lưu trữ chỉ bằng vài chỉnh sửa nhỏ, không phải refactor lại pipeline embedding/persistence.

## 3. Quá trình kiểm thử (Verification Plan)

- Chạy `python test_e2e_pipeline.py`.
- Hệ thống log ra console quá trình từ PDF tải vào RAM, parsing ra JSON, số chunks con sinh ra.
- Log ra preview 2-3 chunk xem Header đã được gắn dính liền với nội dung hay chưa.
- Mở DBeaver/pgAdmin kiểm tra bảng `AIDOCUMENTCHUNK` phải thấy dữ liệu vector cột `embedding` không bị rỗng. Cột `tokenCount` và `content` chính xác.
- Xác nhận cấu hình mặc định đang là `halfvec`, nhưng tài liệu/schema đã mô tả rõ cách đổi nhanh sang `vector` nếu cần.

## Open Questions
- Bạn có muốn tự động upload `sample.pdf` lên Cloudinary thành thư viện test mặc định thông qua SDK không, hay chỉ cần dùng file đọc dạng binary ngay tại thư mục local là đủ?
- Bạn có sở hữu tài khoản OpenAI có sẵn credit/billing để API Embedding hoạt động hay ta đang sử dụng model giả lập / key trung gian nào đó?

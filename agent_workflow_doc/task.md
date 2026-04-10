- [ ] **Component: Chunking Service**
  - [ ] Sửa thuộc tính `strip_headers=True` trong module `chunking.py`.
  - [ ] Cập nhật vòng lặp xử lý `node`: Trích xuất các khoá cấu trúc (như h1, h2, h3) từ `node.metadata` thành chuỗi Markdown.
  - [ ] Chèn chuỗi Header vào đầu các chunk con được phân tách qua `RecursiveCharacterTextSplitter`.

- [ ] **Component: Luồng End-to-End Pipeline Test**
  - [ ] Khởi tạo kịch bản `test_e2e_pipeline.py`.
  - [ ] Lập trình hàm đọc file PDF giả lập hoặc lấy qua Cloudinary.
  - [ ] Lập trình bước Parsing sử dụng kết nối Gemini SDK.
  - [ ] Lập trình bước Markdown Conversion bằng thư viện nội bộ.
  - [ ] Lập trình bước Chunking với tuỳ chọn truyền `global_context`.
  - [ ] Lập trình bước Batch Embedding sử dụng `text-embedding-3-small` OpenAI API.
  - [ ] Lập trình bước Database Insertion sử dụng queries của hệ cơ sở PostgreSQL.
  - [ ] Chạy thử nghiệm và xác nhận DB `AIDOCUMENTCHUNK` ghi nhận đủ dữ liệu embedding theo cấu hình hiện tại.

- [ ] **Component: Cấu trúc cơ sở dữ liệu**
  - [ ] Giữ mặc định `AIDOCUMENTCHUNK.embedding` là `halfvec(1024)` cho DEV/Test.
  - [ ] Ghi chú rõ trong schema/config cách đổi nhanh sang `vector(1024)` khi cần.
  - [ ] Tạo / Kiểm tra index chuẩn `hnsw` tương ứng với kiểu vector đang chọn.

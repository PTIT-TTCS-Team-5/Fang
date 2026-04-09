# Chiến Lược Chunking & Ingestion (AI Core - Pha 2)

Tài liệu này định nghĩa kiến trúc **"Zero-LLM-Cost"** cho quy trình chuyển đổi dữ liệu CV đã parse dạng JSON thành các vector nhúng (Embeddings) để lưu trữ vào cơ sở dữ liệu Vector (PostgreSQL `pgvector`) 

Kiến trúc này loại bỏ hoàn toàn phương pháp cắt chuỗi cơ học (naive text splitting) trên văn bản thô, thay vào đó áp dụng chiến lược **Phân mảnh cấu trúc lai (Hybrid Structure-aware Chunking)** kết hợp **Ghim bối cảnh (Section-Pinning)** và kiến trúc **Small-to-Big Retrieval**.

## 1. Nguyên Tắc Cốt Lõi
* **Không Vector hóa JSON thô:** Việc đưa trực tiếp JSON vào mô hình nhúng làm lãng phí token cho các ký tự cú pháp và phá vỡ cơ chế attention của mô hình.
* **Bảo toàn Tính Nguyên tử (Atomicity):** Các khối thông tin logic (một kinh nghiệm làm việc, một bằng cấp) phải được duy trì trọn vẹn trong một phân mảnh.
* **Zero-LLM-Cost Ingestion:** Toàn bộ quá trình chuyển đổi cấu trúc và tiêm bối cảnh phải được thực hiện bằng mã lập trình tĩnh (code-deterministic), không gọi LLM để tóm tắt hay chia chunk nhằm tối ưu chi phí và độ trễ.
* **Tiêm Bối cảnh Toàn cục:** Mọi phân mảnh vi mô phải mang theo siêu dữ liệu vĩ mô của ứng viên.

## 2. Pipeline Xử Lý (Ingestion Pipeline) 4 Bước

### Bước 2.1: Chuyển đổi JSON sang Markdown (Programmatic Flattening)
Dữ liệu đầu vào `ParsedCV` phải được "làm phẳng" thành định dạng Markdown. Mô hình nhúng được huấn luyện để nhận diện rất tốt các cấu trúc phân cấp thông qua thẻ Heading (`#`, `##`, `###`) của Markdown.

**Quy tắc làm sạch dữ liệu (Data Cleaning Heuristics):**
* Lọc bỏ các số trang và tiêu đề lặp lại (Headers/Footers) sinh ra từ quá trình parse PDF ban đầu
* Chuẩn hóa khoảng trắng và xử lý các ký tự gạch đầu dòng (bullet points) để đảm bảo mật độ ngữ nghĩa

### Bước 2.2: Phân mảnh nhận thức Cấu trúc (Node-Based Semantic Partitioning)
Sử dụng bộ chia cắt phân tích cú pháp Markdown (ví dụ: `MarkdownHeaderTextSplitter`) để tách văn bản dựa trên các thẻ Heading
* **Ưu điểm:** Đảm bảo toàn bộ mô tả của một chức danh công việc hoặc danh sách kỹ năng không bị cắt ngang giữa chừng

### Bước 2.3: Xử lý Ngoại lệ (Long-Tail Nodes) với Kiến trúc Small-to-Big
Đối với các khối thông tin quá lớn (ví dụ: kinh nghiệm 10 năm tại một công ty), việc nhúng toàn bộ sẽ làm loãng ngữ nghĩa, trong khi cắt cứng sẽ làm mất bối cảnh. 

Hệ thống áp dụng kiến trúc **Parent-Document Retrieval**:
1.  **Ngưỡng kích hoạt (Fallback Window):** Nếu một khối cấu trúc đơn lẻ (Parent Node) vượt quá **512 tokens**.
2.  **Chia nhỏ (Child Chunks):** Kích hoạt bộ chia đệ quy (`RecursiveCharacterTextSplitter`) để cắt Parent Node thành các Child Chunks có kích thước **150-200 tokens**, với độ chồng chéo (overlap) khoảng **20%** (hoặc ~64 tokens).
3.  **Lưu trữ:** Chỉ nhúng và lưu các Child Chunks vào cơ sở dữ liệu Vector để tìm kiếm với độ phân giải cao. Gắn khóa ngoại liên kết Child Chunks về Parent Node gốc (lưu ở bảng khác) để truy xuất toàn bộ bối cảnh cho LLM khi sinh câu trả lời.

### Bước 2.4: Tiêm Bối Cảnh Xác Định (Deterministic Contextual Injection / Section-Pinning)
Trích xuất siêu dữ liệu toàn cục (Tên ứng viên, Tổng số năm kinh nghiệm, Vị trí mục tiêu, Kỹ năng cốt lõi) từ gốc của `ParsedCV` 

Trước khi gửi văn bản cho mô hình Embedding, cần nối chuỗi siêu dữ liệu này vào đầu mỗi phân mảnh. Thao tác này ép buộc mô hình nhúng gom cụm vector dựa trên cả thuộc tính cá nhân lẫn chuyên môn.

**Ví dụ một chunk sau khi tiêm bối cảnh:**
```markdown
[Candidate: Nguyễn Văn A | Total Exp: 5 Years | Core Skills: Java, Spring Boot] 
## Kinh nghiệm làm việc
### Backend Developer tại Công ty XYZ (2020 - 2023)
- Tối ưu hóa truy vấn PostgreSQL giảm 30% độ trễ...
```

## 3. Kiến Trúc CSDL & Tối Ưu Hóa Vector Space
Để xử lý hàng triệu vectors mà không gây sụp đổ bộ nhớ RAM, hệ thống lưu trữ PostgreSQL (`pgvector`) cần tuân thủ các thiết lập sau:

* **Lượng tử hóa vô hướng (Scalar Quantization):** Cột `embedding` trong bảng `AIDOCUMENTCHUNK` phải được định nghĩa cứng bằng kiểu dữ liệu **`halfvec`** (float16). Việc này giúp giảm ngay **50% dung lượng RAM** yêu cầu, tăng tốc độ xây dựng chỉ mục mà không làm suy giảm chỉ số Recall.
* **Thuật toán Chỉ mục:** Sử dụng **HNSW** (Hierarchical Navigable Small World) kết hợp phép đo khoảng cách **Cosine Similarity** (`<=>`) để tối ưu hóa tốc độ và độ chính xác.

**Lược đồ ánh xạ `AIDOCUMENTCHUNK`:**
* `jobAppId` (FK): Cầu nối nghiệp vụ.
* `sourceType`: Phân loại (CV, JD, Cover Letter) để lọc nhanh
* `chunkIndex`: Thứ tự khôi phục bối cảnh.
* `content`: Chuỗi văn bản đã tiêm bối cảnh (Section-Pinning).
* `tokenCount`: Ngắt mạch chống tràn ngữ cảnh LLM.
* `metadata` (JSONB): Lưu trữ các nhãn trích xuất, hỗ trợ Hybrid Search.
* `embedding` (halfvec): Vector toán học.

## 4. Chiến Lược Truy Xuất Lai (Hybrid Retrieval Strategy)
Khi truy vấn, hệ thống không chỉ dùng Vector Search mà phải kết hợp đa luồng:
1.  **Dense Vector Search:** So khớp ngữ nghĩa trên các Child Chunks.
2.  **Sparse Search (BM25):** Tìm kiếm từ khóa chính xác để bắt các thuật ngữ kỹ thuật ngách.
3.  **Metadata Hard Filtering:** Lọc cứng dựa trên `metadata` (Vị trí, Kỹ năng bắt buộc) để thu hẹp không gian tìm kiếm ngay lập tức.
4.  **Reciprocal Rank Fusion (RRF):** Thuật toán tổng hợp điểm số để chọn ra Top-K phân mảnh tốt nhất.

## 5. Kế Hoạch Triển Khai Tiếp Theo
1.  Phát triển module `services/markdown_builder.py` để mapping `ParsedCV` sang chuỗi Markdown chuẩn.
2.  Cài đặt `langchain-text-splitters` và cấu hình `MarkdownHeaderTextSplitter` kết hợp `RecursiveCharacterTextSplitter` cho luồng Small-to-Big.
3.  Phát triển hàm trích xuất và tiêm `Global Metadata` vào các chunk.
4.  Thiết lập schema `AIDOCUMENTCHUNK` trên PostgreSQL với kiểu `halfvec`.
5.  Viết file `test_chunking.py` để kiểm chứng cấu trúc đầu ra trước khi tích hợp mô hình nhúng.

### Giải thích thêm về tỷ lệ kích thước chunk và đánh giá khách quan về kiểu dữ liệu lưu trữ vector dựa trên các báo cáo nghiên cứu
## 1. Kích thước Parent và Child Chunk trong kiến trúc Small-to-Big

Kiến trúc Small-to-Big Retrieval được thiết kế để giải quyết tình huống khi xử lý các khối dữ liệu quá dài (Long-tail nodes) trong CV: nhúng toàn bộ thì bị "pha loãng" từ khóa, mà băm nhỏ thì LLM mất bối cảnh tổng thể. 

Quy tắc kích thước được phân bổ như sau:
* **Parent Chunk (Ngưỡng kích hoạt > 512 tokens):** 512 tokens là điểm giới hạn (threshold) được xác định từ các thử nghiệm thực tế. Nếu một khối cấu trúc (ví dụ: kinh nghiệm làm việc 10 năm) vượt quá con số này, nó sẽ được giữ nguyên vẹn lưu trữ riêng làm "Parent Document". Vai trò của nó không phải để tìm kiếm, mà là để cung cấp toàn bộ bối cảnh không bị cắt xén cho LLM khi sinh câu trả lời.
* **Child Chunks (150 - 200 tokens):** Parent Chunk sẽ bị chia đệ quy thành các phân mảnh nhỏ cỡ 150 đến 200 tokens. Khoảng kích thước này đảm bảo mật độ từ khóa (như tên công nghệ, kỹ năng ngách) cực kỳ đậm đặc, giúp vector không bị mờ nhạt và tăng độ chính xác (precision) khi tìm kiếm nội suy.
* **Độ chồng chéo (~20% / 64 tokens):** Khi băm Parent thành Child, thuật toán buộc phải dùng độ chồng chéo khoảng 20% (hay 64 tokens). Đây là lưới an toàn để đảm bảo một khái niệm hoặc một từ khóa dài không bị thuật toán cắt làm đôi ngay tại ranh giới của 2 phân mảnh.

---

## 2. So sánh thực tế giữa `vector` (fullvec) và `halfvec`

Quyết định sử dụng `vector` hay `halfvec` trong `pgvector` là sự đánh đổi trực tiếp giữa độ chính xác số học siêu nhỏ và bài toán về chi phí RAM của máy chủ.

**Kiểu `vector` mặc định (float32 - Dấu phẩy động 32-bit):**
* **Bản chất:** Giữ nguyên vẹn độ phân giải số học cao nhất của vector nhúng do API trả về.
* **Hại (Thực tế triển khai):** Tiêu tốn tài nguyên phần cứng khổng lồ. Một vector 1536 chiều sẽ chiếm khoảng 6.15 KB dung lượng. Khi kết hợp với thuật toán HNSW (thuật toán lưu toàn bộ cấu trúc đồ thị trên RAM), lượng RAM cần thiết thường phình to gấp 2-3 lần dữ liệu thô. Ở quy mô hàng triệu CV, chi phí thuê máy chủ để duy trì RAM in-memory sẽ chạm mức không thể chấp nhận được đối với dự án.

**Kiểu `halfvec` (float16 - Lượng tử hóa vô hướng):**
* **Bản chất:** Ép kiểu giảm độ phân giải số học xuống 16-bit (2 bytes mỗi chiều).
* **Lợi ích kinh tế & Hiệu năng:** Cắt giảm 50% dung lượng lưu trữ (chỉ còn khoảng 3 KB mỗi vector), cho phép hệ thống nhồi nhét 2 vector vào một trang đĩa (page) 8KB tiêu chuẩn của PostgreSQL. Động thái này tiết kiệm 50% chi phí RAM và tăng tốc độ xây dựng chỉ mục (index building) lên 23%.
* **Đánh đổi (Thực tế triển khai):** Trên lý thuyết, việc ép kiểu làm suy giảm độ chính xác tuyệt đối của vector. Tuy nhiên, các nghiên cứu độc lập đã chứng minh rằng trong ứng dụng tìm kiếm ngữ nghĩa RAG, tác động làm suy giảm chỉ số độ phủ thông tin (Recall) từ việc dùng `halfvec` là hoàn toàn không thể nhận biết bằng mắt thường. Lợi ích về tài nguyên áp đảo hoàn toàn sự hy sinh về độ chính xác số thập phân này.

---

Tham khảo (tại prj_docs):
    1. Nghiên cứu về RAG Chunking (2)
    2. Nghiên cứu về RAG Chunking (3)
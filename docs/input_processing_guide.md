# Hướng dẫn Luồng Xử Lý Dữ Liệu Đầu Vào

Tài liệu này mô tả phần "Xử lý dữ liệu đầu vào" của FANG, tức toàn bộ đường đi từ một CV PDF thô cho đến khi dữ liệu đã sẵn sàng trong PostgreSQL dưới dạng:

* `CVPARSED` cho dữ liệu đã parse
* `AIDOCUMENTCHUNK` cho chunk và embedding

Đây là phần giao nhau giữa Parser, Chunking, Embedding và Persistence.

## 1. Mục tiêu của Input Processing

Luồng này giải quyết ba bài toán:

* biến PDF thành dữ liệu có cấu trúc
* biến dữ liệu có cấu trúc thành đơn vị truy xuất tốt
* biến đơn vị truy xuất thành vector có thể tìm kiếm ngữ nghĩa

## 2. Luồng tổng quát

Hiện tại luồng xử lý đầu vào có thể tóm tắt như sau:

1. **Nhận CV**
   * đọc từ file local hoặc URL
2. **Parse CV**
   * PDF được gửi vào parser Gemini
   * đầu ra là `rawText` và JSON `ParsedCV`
3. **Chuyển sang Markdown**
   * JSON được flatten bằng `markdown_builder.py`
   * đồng thời trích xuất `global_context`
4. **Chunking**
   * Markdown được tách thành `ChunkPayload`
   * nếu section quá dài, hệ thống sẽ băm thành nhiều child chunk nhưng vẫn giữ header cha
5. **Embedding**
   * từng chunk được gửi vào OpenAI Embeddings API
6. **Persistence**
   * `CVPARSED` lưu dữ liệu parse
   * `AIDOCUMENTCHUNK` lưu nội dung chunk, metadata và vector

## 3. Các thành phần tham gia

### Parser Layer

* file chính: `app/services/cv_parser.py`
* nhiệm vụ: PDF -> `ParsedCV`

### Markdown / Chunking Layer

* file chính:
  * `app/services/markdown_builder.py`
  * `app/services/chunking.py`
* nhiệm vụ: `ParsedCV` -> `ChunkPayload`

### Embedding Layer

* file chính: `app/services/embedding.py`
* nhiệm vụ: `ChunkPayload.content` -> vector

### Persistence Layer

* file chính: `app/services/persistence.py`
* nhiệm vụ: ghi `CVPARSED` và `AIDOCUMENTCHUNK`

## 4. Dữ liệu được lưu ở đâu

### Bảng `CVPARSED`

Lưu:

* `rawText`
* `parsedJson`
* `parserVer`

### Bảng `AIDOCUMENTCHUNK`

Lưu:

* `content`
* `chunkIndex`
* `tokenCount`
* `metadata`
* `embedding`

Hai bảng này tạo thành nền tảng cho các bước truy xuất và matching về sau.

## 5. Điểm quan trọng của luồng hiện tại

### 5.1. Không phá contract parser

Parser vẫn giữ contract cũ:

* nhận `cv_bytes`
* trả về `rawText` và JSON

Điều này giúp embedding phase được thêm vào mà không làm gãy giai đoạn parse đã có.

### 5.2. Chunking bảo toàn ngữ cảnh cha

Các child chunk dài hiện đã được gắn lại:

* `#` tiêu đề tài liệu
* `##` section cha
* `###` mục con

Điều này rất quan trọng cho chất lượng embedding.

### 5.3. Storage vector đủ linh hoạt

Hệ thống hiện mặc định dùng `halfvec`, nhưng cho phép chuyển sang `vector` qua cấu hình và schema với thay đổi nhỏ.

## 6. Script kiểm chứng end-to-end

File kiểm thử chính:

* `test_e2e_pipeline.py`

Script này giúp kiểm chứng toàn bộ luồng:

* đọc CV
* parse thật
* chunking thật
* embedding thật
* lưu DB thật

Đây là tài liệu hóa sống cho luồng input processing hiện tại.

## 7. Những điều cần kiểm tra khi debug

Nếu input processing fail, nên kiểm tra theo thứ tự:

1. API key parser có hợp lệ không
2. OpenAI embedding có credit không
3. `EMBEDDING_DIM` runtime có khớp schema DB không
4. `EMBEDDING_VECTOR_TYPE` runtime có khớp schema DB không
5. PostgreSQL đã apply schema mới nhất chưa

## 8. Tài liệu liên quan

* `docs/cv_parser_guide.md`
* `docs/chunking_strategy.md`
* `docs/chunking_guide.md`
* `docs/embedding_strategy.md`
* `docs/embedding_guide.md`
* `docs/system_architecture.md`

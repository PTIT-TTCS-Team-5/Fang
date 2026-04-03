# Chiến Lược Chunking & Ingestion (AI Core - Pha 2)

Tài liệu này định hướng quy trình chuyển đổi dữ liệu CV đã bóc tách (JSON) thành các vector nhúng (Embeddings) để lưu trữ vào cơ sở dữ liệu Vector (PostgreSQL `pgvector`), phục vụ cho hệ thống RAG.

## 1. Nguyên Tắc Cốt Lõi
- **Dữ liệu đầu vào:** Object Pydantic `ParsedCV` (được lưu dưới dạng JSONB trong bảng `CVPARSED`).
- **Dữ liệu đầu ra:** Các đoạn văn bản nhỏ (Chunks) có độ dài tối ưu, mang ý nghĩa trọn vẹn, kèm theo Vector Embedding.
- **Loại bỏ nhiễu:** KHÔNG sử dụng Raw Text từ PDF. KHÔNG đưa JSON trực tiếp vào mô hình Embedding để tránh lãng phí token cho các ký tự cấu trúc (`{}`, `[]`, `""`).
- **Không xử lý Job Posting:** Mô tả công việc (`jobposting.desc`) không được chunking tại đây. JD sẽ được nạp trực tiếp vào Context Window của LLM ở pha truy vấn (Retrieval) để đối chiếu 1-N.

## 2. Quy Trình 3 Bước Chunking CV

### Bước 2.1: JSON to Markdown Transformation
Viết một Service/Utility để map các trường từ `ParsedCV` thành một chuỗi Markdown chuẩn mực.

**Cấu trúc Markdown mẫu:**
```markdown
# Thông tin Ứng viên
- Email: user@example.com
- Số điện thoại: 0123456789
- Tóm tắt: Lập trình viên Python 3 năm kinh nghiệm...

## Kỹ năng (Skills)
- Python (Chuyên gia)
- PostgreSQL
- ReactJS

## Kinh nghiệm làm việc (Experience)
### Software Engineer tại Công ty XYZ (2020-01 - 2023-01)
- Tham gia xây dựng hệ thống RAG...
- Tối ưu hóa query database...

## Học vấn (Education)
### Cử nhân CNTT - Đại học Bách Khoa (2016-09 - 2020-06)
- GPA: 3.8/4.0
```

### Bước 2.2: Markdown Text Splitting
Sử dụng `MarkdownHeaderTextSplitter` (ví dụ từ thư viện LangChain) để chia cắt văn bản.
- **Tiêu chí cắt:** Cắt theo các thẻ `#` (H1), `##` (H2), `###` (H3).
- **Ưu điểm:** Đảm bảo một kinh nghiệm làm việc hoặc một list kỹ năng không bị cắt ngang giữa chừng.
- **Fallback:** Nếu một section (như mô tả kinh nghiệm) quá dài (vượt quá chunk_size), sử dụng thêm `RecursiveCharacterTextSplitter` để chia nhỏ phần đó ra.

### Bước 2.3: Gắn Metadata
Mỗi Chunk sinh ra cần được đính kèm một `metadata` (kiểu Dictionary) chứa thông tin ngữ cảnh của đoạn text đó để hỗ trợ Vector Search kết hợp SQL Filtering (Hybrid Search).

**Ví dụ một chunk kinh nghiệm:**
```json
{
  "content": "Tham gia xây dựng hệ thống RAG... Tối ưu hóa query database...",
  "metadata": {
    "Header 1": "Thông tin Ứng viên",
    "Header 2": "Kinh nghiệm làm việc (Experience)",
    "Header 3": "Software Engineer tại Công ty XYZ"
  }
}
```

## 3. Kiến trúc Database Lưu Trữ

Sau khi tạo Chunks và gọi API (OpenAI/Gemini/Gecko) để lấy Embeddings, dữ liệu được ghi vào bảng `AIDOCUMENTCHUNK` thông qua hàm `save_document_chunks`:

- `jobAppId`: Khóa ngoại liên kết với đơn ứng tuyển.
- `sourceType`: Lưu là `'CV'`.
- `content`: Nội dung đoạn text của chunk (Markdown).
- `chunkIndex`: Thứ tự của chunk.
- `tokenCount`: Số lượng token tính toán được của chunk.
- `metadata`: Đẩy dictionary metadata ở Bước 2.3 vào cột `JSONB` này.
- `embedding`: Vector toán học.

## 4. Kế Hoạch Triển Khai Tiếp Theo
1. Viết hàm `convert_cv_to_markdown(parsed_cv: ParsedCV) -> str` trong thư mục `services`.
2. Cài đặt thư viện Langchain (`langchain-text-splitters`) và viết hàm `split_markdown_cv()`.
3. Tạo file `test_chunking.py` để verify output của hàm chuyển đổi và bộ chia cắt.
4. Tích hợp mô hình nhúng (Embedding Model) vào đường ống.
5. Hoàn thiện API `POST /v1/ingestion/jobs` tích hợp từ đầu chí cuối: *Upload -> Parse -> Save JSON -> Markdown -> Chunk -> Embed -> Save Vector.*
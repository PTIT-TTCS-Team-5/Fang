# Hướng dẫn Module Chunking (`chunking.py` & `markdown_builder.py`)

Tài liệu này giải thích chi tiết về cách hoạt động của Chunking Layer, nằm trước quy trình parseCV và sau nhúng Vector (Embedding)

`chunking_strategy.md` mang tính định hướng lý thuyết, tài liệu này tập trung vào cách mã nguồn thực thi các chiến lược đó.

## 1. Luồng hoạt động (Workflow)

Quá trình phân mảnh nhận đầu vào là một đối tượng dữ liệu đã được cấu trúc hóa (`ParsedCV`) và trả về một danh sách các phân mảnh văn bản tối ưu (`ChunkPayload`).

1. **Tiếp nhận `ParsedCV`:** Hệ thống lấy đối tượng JSON từ module `cv_parser`.
2. **Xây dựng Markdown & Siêu dữ liệu (Module `markdown_builder.py`):**
   * **Trích xuất Bối cảnh Toàn cục (Global Context):** Hàm `extract_global_metadata` phân tích CV để tạo ra một chuỗi định danh duy nhất (chứa Tên, Tổng số năm KN, Vị trí mục tiêu, Kỹ năng lõi).
   * **Làm phẳng dữ liệu (Flattening):** Hàm `convert_json_to_markdown` chuyển đổi cấu trúc phân cấp của JSON thành chuẩn Markdown, sử dụng các thẻ Heading (`#`, `##`, `###`) để phân định ranh giới ngữ nghĩa (Học vấn, Kinh nghiệm, Kỹ năng). Quy trình này đi kèm các logic làm sạch văn bản (loại bỏ khoảng trắng thừa, chuẩn hóa bullet points).
3. **Phân mảnh văn bản (Module `chunking.py`):**
   * **Chia cắt theo Cấu trúc (Primary Split):** Sử dụng `MarkdownHeaderTextSplitter` để chia văn bản thành các Node độc lập dựa trên thẻ Heading.
   * **Xử lý Ngoại lệ (Small-to-Big Fallback):** Hàm `process_document_to_chunks` duyệt qua các Node. Nếu một Node vượt quá giới hạn an toàn (`PARENT_CHUNK_TOKEN_LIMIT` = 512 tokens), nó kích hoạt `RecursiveCharacterTextSplitter` để băm Node đó thành các Child Chunks nhỏ hơn (~180 tokens, overlap 36 tokens).
4. **Tiêm Bối cảnh (Context Injection):** Chuỗi "Global Context" (từ Bước 2) được nối vào phần đầu của mọi phân mảnh con.
5. **Đóng gói Payload:** Trả về danh sách các đối tượng kiểu `ChunkPayload` chứa nội dung văn bản cuối cùng, chỉ số chunk (Index) và số token xấp xỉ.

## 2. Xử lý Đếm Token Độc lập Hệ sinh thái (Tokenization) 

Mã nguồn áp dụng giải pháp **Xấp xỉ Heuristic (Heuristic Approximation)**:
* Hàm `approx_token_count` trong `chunking.py` được thiết kế để đếm token dựa trên tỷ lệ ký tự.
* Hằng số `CHARS_PER_TOKEN = 3.5` được tinh chỉnh cho dữ liệu CV song ngữ Anh/Việt. Điều này giúp hệ thống tách rời hoàn toàn khỏi sự phụ thuộc vào tokenizer của một nhà cung cấp LLM cụ thể.

## 3. Cấu trúc Đầu ra (`ChunkPayload`)

Đầu ra của luồng này được chuẩn hóa thông qua `TypedDict` `ChunkPayload`, thiết kế map 1-1 với các cột trong CSDL `AIDOCUMENTCHUNK`:

```python
class ChunkPayload(TypedDict):
    content: str      # Nội dung đã ghép Context, sẵn sàng gửi đi Embedding
    tokenCount: int   # Số token xấp xỉ (hỗ trợ tính năng ngắt mạch khi truy xuất)
    chunkIndex: int   # Thứ tự gốc của đoạn text trong tài liệu
```

## 4. Cơ chế Xử lý Ngoại lệ Dữ liệu (Edge Cases)

* **Thiếu trường dữ liệu:** Nếu một ứng viên không có phần Summary hoặc không có chức danh rõ ràng, `markdown_builder` sử dụng các hàm fallback (như lấy kinh nghiệm mới nhất làm `Target Role`) hoặc trả về chuỗi `"Unknown"` để đảm bảo đoạn Global Context không bị gãy format.
* **Format CV "dị biệt":** Các hàm làm sạch như `_split_description_lines` sử dụng Regex (`BULLET_PREFIX_PATTERN`) để gọt bỏ mọi loại ký tự gạch đầu dòng hỗn tạp (từ dấu `*`, `-` cho đến các bullet unicode của Word) nhằm đưa text về dạng sạch nhất.

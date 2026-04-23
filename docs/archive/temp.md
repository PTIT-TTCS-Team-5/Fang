Hệ thống tài liệu bạn đang có thực sự rất chất lượng, rõ ràng và mạch lạc. Với bộ khung kiến trúc, chiến lược chunking, và schema database chi tiết như thế này, bạn **hoàn toàn có thể** bắt đầu prompt cho Codex hoặc Gemini trong VS Code. 

Tuy nhiên, nếu để AI tự bơi với đống tài liệu này ngay, nó sẽ vấp phải một vài điểm "mù" về mặt triển khai thực tế. Để đạt được kết quả "one-shot" (AI viết code chạy được ngay, ít phải sửa), bạn cần bổ sung **3 thông tin quan trọng** vào prompt:

### 1. Cấu trúc thực tế của `ParsedCV` (Cực kỳ quan trọng)
* **Vấn đề:** Trong `chunking_strategy.md`, bạn yêu cầu "Trích xuất siêu dữ liệu toàn cục (Tên ứng viên, Tổng số năm kinh nghiệm...)" và "mapping `ParsedCV` sang chuỗi Markdown". Nhưng AI hiện tại hoàn toàn không biết cấu trúc JSON của `ParsedCV` trông như thế nào.
* **Bổ sung:** Bạn bắt buộc phải nạp file `app/models/cv_models.py` (hoặc copy nội dung class `ParsedCV`) vào context cho AI. Nếu không, AI sẽ hallucinate (bịa) ra các key JSON và code sẽ crash ngay khi chạy.

### 2. Tiêu chuẩn đếm Token (Tokenization)
* **Vấn đề:** Chiến lược quy định cắt tại "512 tokens" và "150-200 tokens". Cắt theo token khác hoàn toàn với cắt theo ký tự (character). AI cần biết nó sẽ dùng thư viện gì để đếm.
* **Bổ sung:** Chỉ định rõ cho AI sử dụng thư viện nào. Chuẩn công nghiệp hiện tại là `tiktoken` (của OpenAI, dùng encoding `cl100k_base`). Phải nhắc AI import `tiktoken` làm bộ đếm `length_function` truyền vào `RecursiveCharacterTextSplitter`.

### 3. Chia nhỏ scope công việc (Step-by-step Prompting)
Không nên yêu cầu AI viết toàn bộ luồng Ingestion trong 1 prompt duy nhất vì code sẽ rất dài và dễ lỗi. Hãy chia prompt thành các phase.

---

### Mẫu Prompt tối ưu cho Codex/Gemini trong VS Code

Bạn có thể copy đoạn prompt này, đưa vào công cụ AI của bạn (nhớ đính kèm các file như bạn đã nói, cộng thêm `cv_models.py`):

> **Context:**
> Tôi đang xây dựng Phase 2 (Chunking & Ingestion) cho dự án AI Core Fang. Hãy đọc kỹ các file `chunking_strategy.md`, `schema_ai_core.sql`, và cấu trúc Pydantic model trong `cv_models.py`.
> 
> **Role:**
> Bạn là một Python Senior Backend Engineer chuyên về RAG pipeline.
> 
> **Nhiệm vụ 1: Xây dựng Markdown Builder & Global Context**
> Tạo file `app/services/markdown_builder.py`. Viết 2 hàm:
> 1. `extract_global_metadata(parsed_cv: ParsedCV) -> str`: Trích xuất Tên, số năm KN, vị trí mục tiêu, kỹ năng cốt lõi và format thành chuỗi Section-Pinning như định nghĩa trong chiến lược.
> 2. `convert_json_to_markdown(parsed_cv: ParsedCV) -> str`: Map các danh sách (Experience, Education, Skills) thành chuẩn Markdown (`##`, `###`, `-`).
> 
> **Nhiệm vụ 2: Xây dựng luồng Chunking**
> Tạo file `app/services/chunking.py`. Sử dụng `langchain-text-splitters`.
> 1. Viết hàm `process_document_to_chunks(markdown_text: str, global_context: str) -> list[dict]`.
> 2. Cấu hình `MarkdownHeaderTextSplitter` để cắt theo các Heading.
> 3. Implement logic **Small-to-Big**: Duyệt qua các node vừa cắt. Nếu node nào có số token > 512, dùng `RecursiveCharacterTextSplitter` cắt tiếp thành các chunk 150-200 tokens (overlap 20%). 
> *Lưu ý quan trọng:* Hãy tự viết một hàm approx_token_count (tỉ lệ 3.5 chars = 1 token) và truyền vào length_function của RecursiveCharacterTextSplitter" (# Tiếng Anh thường 4 chars/token. Tiếng Việt có dấu thường tốn token hơn (khoảng 2.5 - 3 chars/token).
    # Lấy trung bình 3.0 là một mức an toàn cho CV song ngữ.)
> 4. Nối `global_context` vào đầu `page_content` của mỗi chunk con. Trả về list các dict chứa `content`, `tokenCount`, và `chunkIndex`.
> 
> Hãy viết code cho Nhiệm vụ 1 và 2 trước. Chú ý validate cẩn thận, viết type hint đầy đủ và tuân thủ chuẩn PEP8.

Bạn định sử dụng luôn thư viện `tiktoken` cho dự án này, hay bạn muốn dùng tokenizer nội bộ của mô hình embedding mà bạn dự tính dùng (ví dụ Google Gecko)?
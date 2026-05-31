# Hướng Dẫn Quản Trị Cơ Sở Dữ Liệu (v2)

Tài liệu này mô tả các bảng dữ liệu trong PostgreSQL (pgvector) cho hệ thống FANG v2.

## 1. Các bảng quan trọng

### Bảng `AICHATCONVERSATION`
Lưu trữ thông tin định danh của một phiên hội thoại chat.
- `conversationId`: UUID (Khóa chính).
- `jobAppId`: ID của đơn ứng tuyển liên quan.
- `hrId`: ID của nhân sự đang tham gia chat.
- `lastMessageAt`: Thời điểm tin nhắn cuối cùng được gửi (dùng để sắp xếp danh sách chat).

### Bảng `AICHATMESSAGE`
Lưu trữ chi tiết từng tin nhắn trong hội thoại.
- `messageId`: Serial.
- `role`: `user`, `assistant` hoặc `system`.
- `content`: Nội dung tin nhắn.
- `summarized`: Boolean (Đánh dấu message đã được gộp vào bản tóm tắt context chưa).
- `model`: Tên model thực tế đã trả lời (ví dụ: `google:gemini-3.1-flash-lite-preview`).
- `fallbackPath`: Trace luồng fallback nếu có.

### Bảng `AIDOCUMENTCHUNK`
Lưu trữ các đoạn cắt từ CV và vector embedding.
- `embedding`: halfvec(1536) - Vector không gian 1536 chiều dùng cho truy tìm ngữ nghĩa. Mặc định dùng mô hình Gemini `gemini-embedding-001`.

## 2. Lưu ý về Role "system" trong Chat
Trong FANG v2, role `system` được sử dụng với mục đích đặc biệt:
1. **Context Summarization**: Khi hội thoại quá dài (vượt ngưỡng Token Budget), hệ thống sẽ dùng LLM tóm tắt phần cũ và lưu lại thành một message `system`. 
2. **Context Persistence**: Giúp khôi phục ngữ cảnh nhanh chóng mà không cần gửi lại toàn bộ lịch sử tin nhắn thô lên LLM.

## 3. Chính sách dữ liệu local

Local DB hiện được xem là fixture ổn định cho test tích hợp. Không reset DB
trong quy trình test thông thường vì thao tác này sẽ xóa dữ liệu ứng viên,
conversation, ranking và JobPosting Agent đang dùng để kiểm thử.

## 4. Bảo mật & Safeguard
- Mọi truy vấn vector sử dụng cosine distance (`<=>`) để tìm kiếm mức độ tương đồng.

---
*Cập nhật ngày 13/04/2026.*

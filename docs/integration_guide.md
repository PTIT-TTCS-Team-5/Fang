# Hướng Dẫn Tích Hợp API FANG v2

Tài liệu này hướng dẫn phía Frontend (miCareer-mini) cách gọi và tương tác với các Endpoint của FANG v2.

## 1. Thông Tin Chung
- **Base URL**: `http://localhost:8000/v2`
- **CORS**: Đã được cấu hình để cho phép các request từ miCareer-mini (mặc định cho phép tất cả trong môi trường Dev).
- **Format**: JSON.

## 2. Luồng Chat (HR Chatbot)

### Bước 1: Gửi câu hỏi đầu tiên
Frontend không cần tạo Conversation trước. Chỉ cần gửi `conversationId: null`.
- **Endpoint**: `POST /v2/chat/query`
- **Request Body**:
```json
{
  "jobAppId": 101,
  "hrId": 1,
  "prompt": "Ứng viên này có kinh nghiệm Python không?",
  "modelMode": "auto-lite",
  "conversationId": null
}
```
- **Response**: Lưu lại `conversationId` từ response để dùng cho các lượt chat sau.

### Bước 2: Chat tiếp theo
Gửi kèm `conversationId` để duy trì ngữ cảnh.
```json
{
  "jobAppId": 101,
  "hrId": 1,
  "prompt": "Vậy còn kỹ năng SQL thì sao?",
  "modelMode": "auto-lite",
  "conversationId": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Bước 3: Xử lý Cảnh báo Context (Context Warning)
Nếu response trả về `contextWarning != null`, Frontend **phải** hiển thị Dialog cho HR với 2 lựa chọn:

1.  **Tóm tắt & Tiếp tục**:
    - Gọi: `POST /v2/chat/conversations/{id}/summarize`
    - Mục tiêu: AI tóm tắt phần cũ, giải phóng token để chat tiếp trong cùng một cửa sổ.
2.  **Sang hội thoại mới**:
    - Gọi: `POST /v2/chat/conversations/{id}/branch-new`
    - Mục tiêu: Tạo một Conversation hoàn toàn mới, AI tự động mang summary từ bản cũ sang làm context nền.

## 3. Lịch Sử Hội Thoại
- **Lấy danh sách các cuộc trò chuyện**: `GET /v2/chat/conversations?hrId=1&jobAppId=101`
- **Lấy tin nhắn của một cuộc trò chuyện**: `GET /v2/chat/conversations/{id}/messages`

## 4. Ingestion (Tải CV)
- **Trigger**: `POST /v2/ingestion/jobs`
- **Request**: `{ "jobAppId": 101, "cvSnapUrl": "..." }`
- **Polling trạng thái**: `GET /v2/ingestion/jobs/{id}`

## 5. Quy Tắc Xử Lý Lỗi
- **400 Bad Request**: Thường do `jobAppId` chưa được ingestion thành công. Cần kiểm tra status ingestion là `SUCCESS` trước khi cho phép chat.
- **502 Bad Gateway**: Lỗi từ phía Provider LLM (Google/OpenAI). Frontend nên hiển thị thông báo "AI đang bận, vui lòng thử lại sau".
- **504 Gateway Timeout**: Quá trình sinh câu trả lời quá lâu.

---
*Tài liệu này dành cho đội ngũ phát triển Frontend miCareer-mini.*

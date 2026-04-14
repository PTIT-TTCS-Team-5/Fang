# Chiến Lược Tích Hợp FANG v2 ↔ Client (Integration Layer)

Tài liệu này định nghĩa kiến trúc giao tiếp giữa FANG AI Core v2 và các client web. Mục tiêu: biến FANG thành dịch vụ API độc lập, dễ tích hợp với bất kỳ web framework nào (Streamlit, Java Servlet, Spring Boot, v.v.).

> [!NOTE]
> FANG v2 nâng cấp toàn diện: 5-tier model, RAG query API, chat management, context đa nguồn, context window management. Tất cả endpoint mới dùng prefix `/v2/`. Endpoint `/v1/` giữ lại tạm thời.

## 1. Nguyên Tắc Cốt Lõi

* **FANG là API thuần JSON**: Client gửi JSON, nhận JSON. Không cần biết FANG dùng model nào, embed thế nào, hay DB ở đâu.
* **Stateless từ phía client**: Client không lưu chat history, không quản lý session AI. FANG quản lý toàn bộ qua `conversationId`.
* **CORS-ready**: FANG được thiết kế để nhận request từ browser (JS) hoặc server-side (Python, Java). CORS middleware hỗ trợ cả hai.
* **Giảm thiểu trách nhiệm client**: Client chỉ cần: (1) giao diện đăng nhập, (2) render danh sách/detail, (3) gửi prompt + hiển thị response, (4) upload CV + polling status.

## 2. Phân Chia Trách Nhiệm

### FANG chịu trách nhiệm
| Chức năng | API |
|---|---|
| Nhận prompt HR, trả response AI | `POST /v2/chat/query` |
| Quản lý conversation lifecycle | `GET /v2/chat/conversations`, `GET .../messages` |
| Tóm tắt & tiếp tục hội thoại | `POST /v2/chat/conversations/{id}/summarize` |
| Tạo hội thoại mới từ summary | `POST /v2/chat/conversations/{id}/branch-new` |
| Embed prompt + vector search | Nội bộ |
| Context đa nguồn (CV + JD + ATS) | Nội bộ |
| 5-tier model invocation + fallback | Nội bộ |
| Persist chat, audit log | Nội bộ (AICHATMESSAGE, AIQUERYLOG) |
| Ingestion pipeline (parse→chunk→embed) | `POST /v2/ingestion/jobs` |
| Kiểm tra trạng thái ingestion | `GET /v2/ingestion/jobs/{id}` |
| Context window management + cảnh báo | Nội bộ + field `contextWarning` trong response |

### Client (miCareer-mini, Java Servlet, v.v.) chịu trách nhiệm
| Chức năng | Cách thực hiện |
|---|---|
| Xác thực người dùng (HR/Candidate) | Truy vấn DB trực tiếp (hoặc qua auth service riêng) |
| Hiển thị danh sách Job, Candidate | Truy vấn DB trực tiếp |
| Render chat UI | Gọi FANG API, hiển thị response |
| Upload CV | Upload lên Cloudinary → gọi FANG ingestion API |
| Polling trạng thái CV processing | Gọi FANG `GET /v1/ingestion/jobs/{id}` |
| Kiểm tra eligibility cho chat | Kiểm tra ingestion status = SUCCESS trước khi cho phép chat |

## 3. API Contract Đầy Đủ

### 3.1 Chat API

#### `POST /v2/chat/query`
Nhận prompt từ HR, FANG tự xử lý toàn bộ pipeline RAG với context đa nguồn.

**Request:**
```json
{
    "jobAppId": 123,
    "hrId": 5,
    "prompt": "Ứng viên này có kinh nghiệm Docker không?",
    "conversationId": null,
    "modelMode": "auto-lite"
}
```

| Field | Type | Required | Mô tả |
|---|---|---|---|
| `jobAppId` | int | ✅ | ID hồ sơ ứng viên |
| `hrId` | int | ✅ | ID nhân sự đang chat |
| `prompt` | string | ✅ | Câu hỏi của HR |
| `conversationId` | uuid / null | ❌ | null = tạo mới, uuid = tiếp tục |
| `modelMode` | string | ✅ | 1 trong 7 mode (xem `rag_query_strategy.md`) |

**Response (200) — Bình thường:**
```json
{
    "conversationId": "a1b2c3d4-...",
    "messageId": 42,
    "response": "Dựa trên CV, ứng viên có kinh nghiệm Docker...",
    "model": "google:gemini-3.1-flash-lite-preview",
    "modelMode": "auto-lite",
    "fallbackPath": "tier1:google:gemini-flash(succeeded)",
    "latencyMs": 1200,
    "topK": 3,
    "contextWarning": null
}
```

**Response (200) — Khi ngữ cảnh sắp đầy:**
```json
{
    "conversationId": "a1b2c3d4-...",
    "messageId": 42,
    "response": "...",
    "model": "google:gemini-3.1-flash-lite-preview",
    "latencyMs": 1200,
    "topK": 3,
    "contextWarning": {
        "type": "budget_near_limit",
        "usedPercent": 85,
        "options": ["summarize_and_continue", "new_conversation_with_summary"]
    }
}
```

**Error (4xx/5xx):**
```json
{
    "detail": "Ingestion chưa hoàn thành cho jobAppId=123. Trạng thái hiện tại: PROCESSING"
}
```

#### `GET /v2/chat/conversations?hrId={hrId}&jobAppId={jobAppId}`
Lấy danh sách conversation của HR cho một ứng viên.

**Response (200):**
```json
[
    {
        "conversationId": "a1b2c3d4-...",
        "jobAppId": 123,
        "hrId": 5,
        "createdAt": "2026-04-13T10:00:00",
        "lastMessageAt": "2026-04-13T10:05:00",
        "messageCount": 6
    }
]
```

#### `GET /v2/chat/conversations/{conversationId}/messages`
Lấy toàn bộ messages của một conversation (loại trừ `role='system'`).

**Response (200):**
```json
[
    {
        "messageId": 41,
        "role": "user",
        "content": "Ứng viên này có kinh nghiệm Docker không?",
        "model": null,
        "createdAt": "2026-04-13T10:00:00"
    },
    {
        "messageId": 42,
        "role": "assistant",
        "content": "Dựa trên CV...",
        "model": "google:gemini-3.1-flash-lite-preview",
        "createdAt": "2026-04-13T10:00:02"
    }
]
```

#### `POST /v2/chat/conversations/{conversationId}/summarize`
HR chọn "Tóm tắt & tiếp tục" — FANG tóm tắt phần cũ, persist dưới `role='system'`, unlock input.

**Response (200):**
```json
{ "status": "done", "summarizedMessageCount": 12 }
```

#### `POST /v2/chat/conversations/{conversationId}/branch-new`
HR chọn "Sang hội thoại mới" — FANG tạo conversation mới với summary làm context nền.

**Response (200):**
```json
{ "newConversationId": "uuid-moi", "summaryMessageId": 1 }
```

### 3.2 Ingestion API

#### `POST /v2/ingestion/jobs`
Yêu cầu parse → chunk → embed CV (5-tier parser trong v2).

**Request:**
```json
{
    "jobAppId": 123,
    "cvSnapUrl": "https://res.cloudinary.com/..."
}
```

**Response (202):**
```json
{
    "indexJobId": 1,
    "status": "QUEUED"
}
```

#### `GET /v2/ingestion/jobs/{indexJobId}`
Kiểm tra trạng thái ingestion.

**Response (200):**
```json
{
    "status": "QUEUED|PROCESSING|SUCCESS|FAILED",
    "errorMsg": null
}
```

### 3.3 System

#### `GET /v2/healthz`
**Response (200):** `{ "ok": true, "version": "2.0" }`

### 3.4 Backward Compatibility

`/v1/` endpoints được giữ lại tạm thời (deprecated) để không breaking client cũ trong quá trình chuyển đổi. Sẽ được remove sau khi toàn bộ client migrate sang `/v2/`.

## 4. CORS Configuration

FANG cần hỗ trợ CORS vì client có thể gọi từ browser (JavaScript SPA, Java Servlet forward, v.v.).

```python
# app/core/config.py
cors_allowed_origins: list[str] = ["*"]  # Dev: cho phép tất cả
                                          # Production: giới hạn domain cụ thể
```

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 5. Luồng Tích Hợp Cho Client Mới

Khi một web framework mới muốn tích hợp FANG (ví dụ: miCareer Java Servlet gốc):

### Bước 1: Cấu hình
```
FANG_API_URL=http://fang-server:8000
```

### Bước 2: Gọi Ingestion khi candidate apply
```
POST {FANG_API_URL}/v2/ingestion/jobs
Body: { "jobAppId": <id>, "cvSnapUrl": <cloudinary_url> }
```

### Bước 3: Polling trạng thái
```
GET {FANG_API_URL}/v2/ingestion/jobs/{indexJobId}
→ Lặp cho đến khi status = "SUCCESS" hoặc "FAILED"
```

### Bước 4: Chat
```
POST {FANG_API_URL}/v2/chat/query
Body: { "jobAppId": <id>, "hrId": <id>, "prompt": "...", "modelMode": "auto-lite" }
```

### Bước 5: Load history
```
GET {FANG_API_URL}/v2/chat/conversations?hrId=<id>&jobAppId=<id>
GET {FANG_API_URL}/v2/chat/conversations/{conversationId}/messages
```

### Bước 6: Xử lý contextWarning
```
Nếu response.contextWarning != null:
  → Hiển thị dialog cho user chọn:
      Option 1: POST /v2/chat/conversations/{id}/summarize
      Option 2: POST /v2/chat/conversations/{id}/branch-new
```

## 6. Xác Thực và Bảo Mật (Phase sau)

Hiện tại FANG chưa có authentication layer. Trong dev/test, API mở hoàn toàn. Khi deploy production:

- **Phase 1 (hiện tại)**: API key đơn giản qua header `X-API-Key`
- **Phase 2 (production)**: JWT token, client phải authenticate trước khi gọi FANG

> Thiết kế API contract hiện tại **không phụ thuộc** vào cơ chế auth cụ thể. Chỉ cần thêm middleware kiểm tra header.

## 7. Tài Liệu Liên Quan

- `rag_query_strategy.md` — Chiến lược xử lý RAG query bên trong FANG
- `../system_architecture.md` — Kiến trúc ingestion hiện tại
- `README.md` — Quick start

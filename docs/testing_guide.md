# Hướng Dẫn Kiểm Thử (Testing Guide)

Tài liệu này cung cấp hướng dẫn cách chạy các bài kiểm thử (Unit Test & Smoke Test/E2E Test) trên hệ thống FANG AI Core v2.

Các bài test này đặc biệt quan trọng sau khi hệ thống chuyển sang kiến trúc RAG Query tập trung và 5-Tier Fallback.

## 1. Cấu Trúc Thư Mục Test

```
project/
├── smoke_tests/          # Tích hợp thực tế (gọi API thật, database thật)
│   ├── test_parser.py
│   ├── test_e2e_pipeline.py
│   └── test_chat_api.py        # [NEW cho v2]
├── tests/
│   └── unit/             # Unit tests cô lập (mock APIs, mock DB)
│       ├── unit_test_parser_policy.py
│       ├── unit_test_rag_orchestrator.py  # [NEW cho v2]
│       └── unit_test_chat_manager.py      # [NEW cho v2]
└── test_api.http         # Các request mẫu dùng với REST Client
```

## 2. Unit Tests

Unit tests xác minh logic của từng thành phần mã nguồn mà không cần kết nối tới dịch vụ ngoại vi như Database hay LLM API.

**Cách chạy toàn bộ Unit Tests:**
```bash
python -m unittest discover -s tests/unit -p "unit_test_*.py"
```

**Các Test Suit Quan Trọng:**

1.  **`unit_test_parser_policy.py`**: Xác minh logic của `cv_parser.py`, đặc biệt là ProTierGate, xem hệ thống có quyết định fallback từ Lite lên Pro đúng theo quy định chất lượng hay không.
2.  **`unit_test_rag_orchestrator.py`**: Xác minh cơ chế auto-fallback (auto-lite, auto-pro) của generation. Đảm bảo việc resolve model, retry, và fallback diễn ra chính xác.
3.  **`unit_test_chat_manager.py`**: Xác minh các logic của `chat_persistence.py` và `rag_query.py` như tính toán Token Budget (Context Window) và các hàm quản lý hội thoại.

## 3. Smoke Tests / E2E Tests (Tích Hợp)

Khác với Unit test, Smoke Test sẽ tương tác trực tiếp với Database và gọi LLM API thực. Do đó, bạn **BẮT BUỘC** phải có `.env` đầy đủ và hợp lệ.

### Chuẩn Bị Dữ Liệu
Trước khi chạy bất kỳ test tích hợp nào, bạn nên làm sạch và tạo dữ liệu mồi (seed data) cho database:
```bash
python scripts/reset_and_seed_db.py --reset
```
*Ghi lại `jobAppId` và `hrId` được in ra trong console để sử dụng.*

### 3.1. Test E2E Ingestion Pipeline
Khởi động FANG server:
```bash
uvicorn app.main:app
```
Mở terminal khác, dùng cURL (hoặc file `test_api.http`):
```bash
curl -X POST http://localhost:8000/v2/ingestion/jobs \
     -H "Content-Type: application/json" \
     -d '{"jobAppId": <jobAppId_cua_ban>, "cvSnapUrl": "<link_cloudinary_pdf_cua_ban>"}'
```
Dùng JobID trả về để polling trạng thái liên tục đến khi `SUCCESS`.

### 3.2. Test E2E Chat API (`test_chat_api.py`)
Bài test này sẽ mô phỏng luồng gọi của miCareer-mini:
1. Gửi prompt đến `POST /v2/chat/query`.
2. Kiểm tra `conversationId` trả về.
3. Gửi tiếp câu hỏi 2 trong cùng `conversationId`.
4. Gọi `GET /v2/chat/conversations/{id}/messages` để xem lịch sử được lưu chuẩn không.

**Lệnh chạy:**
```bash
python smoke_tests/test_chat_api.py
```
*(Lưu ý: File test_chat_api.py sẽ được tạo trong pha Verification)*

## 4. Kiểm Thử Giao Diện Tích Hợp (miCareer-mini)

Cách test tốt nhất để đảm bảo End-to-End thực sự là thông qua miCareer-mini UI.

1.  Bật FANG server: `uvicorn app.main:app`
2.  Bật miCareer-mini: `python -m streamlit run app.py`
3.  Thực hiện "Luồng Candidate": Đăng nhập ứng viên -> Upload CV. Quan sát progress bar chạy.
4.  Thực hiện "Luồng HR": Đăng nhập HR -> Mở chi tiết ứng viên vừa nộp -> Chat RAG.
5.  Thử đổi Model Mode ở giao diện HR (ví dụ: ép chạy `auto-pro`) và quan sát kết quả trả về + log của FANG.

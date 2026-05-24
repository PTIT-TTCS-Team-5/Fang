# Hướng Dẫn Kiểm Thử (Testing Guide)

Tài liệu này cung cấp hướng dẫn cách chạy các bài kiểm thử (Unit Test & Smoke Test/E2E Test) trên hệ thống FANG AI Core v2.

Các bài test này đặc biệt quan trọng sau khi hệ thống chuyển sang kiến trúc RAG Query tập trung và 5-Tier Fallback.

---

## 1. Cấu Trúc Thư Mục Test

```
project/
├── smoke_tests/                   # Tích hợp thực tế (gọi API thật, database thật)
│   ├── test_chat_api.py           # Test E2E luồng chat của miCareer-mini
│   ├── test_chunking.py           # Test load CV từ DB, chunking & persist
│   ├── test_e2e_pipeline.py       # Chạy full luồng CV ingestion (Parse -> Chunk -> Embed -> DB)
│   ├── test_parser.py             # Test offline pipeline 5-Tier Fallback Parser trên sample.pdf
│   └── test_parser_db.py          # Test offline Parser kết hợp ghi kết quả vào DB
├── tests/
│   └── unit/                      # Unit tests cô lập (mock APIs, mock DB)
│       ├── unit_test_chunking.py  # Test logic sinh markdown & cấu trúc chunk
│       ├── unit_test_embedding.py # Test tích hợp Gemini embedding SDK (Native 1536-dim)
│       ├── unit_test_ingestion_flow.py # Test luồng xử lý và điều phối Ingestion Task
│       ├── unit_test_parser_policy.py  # Test cơ chế điều khiển 5-Tier Fallback & ProTierGate
│       └── unit_test_persistence.py    # Test logic serialize vector & lưu trữ pgvector (halfvec)
└── test_api.http                  # Các request mẫu dùng với REST Client
```

---

## 2. Unit Tests

Unit tests xác minh logic của từng thành phần mã nguồn mà không cần kết nối tới dịch vụ ngoại vi như Database hay LLM API thật. Các dependency chính được mock hoặc cô lập để test không yêu cầu DB/API thật.

### Cách Chạy Toàn Bộ Unit Tests

Sử dụng môi trường ảo (`venv`) để chạy unittest discover:

**Trên Windows (PowerShell/CMD):**
```powershell
venv\Scripts\python -m unittest discover -s tests/unit -p "unit_test_*.py"
```

**Trên Linux / macOS:**
```bash
source venv/bin/activate
python -m unittest discover -s tests/unit -p "unit_test_*.py"
```

### Chi Tiết Các Test Suite Hiện Có

1.  **`unit_test_chunking.py`**:
    Xác minh logic chunking chia nhỏ văn bản markdown của ứng viên, tiêm thông tin ngữ cảnh toàn cục (global context) vào đầu mỗi chunk và đảm bảo các chunk sinh ra tuân thủ giới hạn token.
2.  **`unit_test_embedding.py`**:
    Xác minh tích hợp trực tiếp với Google Gemini SDK. Đảm bảo việc sinh embedding sử dụng model cấu hình (`gemini-embedding-001` với native dimension là `1536`), xử lý phân lô (batching) chính xác, bảo toàn thứ tự chunk và kiểm tra lỗi.
3.  **`unit_test_ingestion_flow.py`**:
    Xác minh luồng điều phối xử lý của ingestion task từ lúc tải file PDF, parse thành JSON, chunking, sinh embedding và gọi persistence layer để lưu trữ.
4.  **`unit_test_parser_policy.py`**:
    Xác minh logic của `cv_parser.py`, đặc biệt là `ProTierGate` và cơ chế Fallback 5-Tier (chuyển đổi linh hoạt giữa các model parser từ Lite sang Pro) hoạt động đúng theo quy định chất lượng đầu ra.
5.  **`unit_test_persistence.py`**:
    Xác minh các hàm hỗ trợ lưu trữ dữ liệu chunk xuống database (`AIDOCUMENTCHUNK`), định dạng pgvector (`halfvec` hoặc `vector`) và cơ chế xóa/ghi đè bản ghi cũ.

### Các Test Suite Còn Thiếu (Known Gaps / Planned Tests)

> [!WARNING]
> Các test suite dưới đây hiện chưa được triển khai trong dự án và được lên kế hoạch bổ sung ở các pha tiếp theo để tăng cường độ phủ test:
> - **`unit_test_rag_orchestrator.py`**: Xác minh cơ chế auto-fallback (auto-lite, auto-pro) của generation. Đảm bảo việc resolve model, retry, và fallback diễn ra chính xác.
> - **`unit_test_chat_manager.py`**: Xác minh các logic của `chat_persistence.py` và `rag_query.py` như tính toán Token Budget (Context Window) và các hàm quản lý hội thoại.

---

## 3. Smoke Tests / E2E Tests (Tích Hợp)

Khác với Unit test, Smoke Test sẽ tương tác trực tiếp với Database và gọi LLM API thực. Do đó, bạn **BẮT BUỘC** phải có file `.env` đầy đủ và hợp lệ (chứa `DATABASE_URL` và `GOOGLE_API_KEY` hoạt động).

### Chuẩn Bị Dữ Liệu

> [!CAUTION]
> **NÊN RESET DATABASE SAU KHI CẬP NHẬT SCHEMA**
> Cần đọc kỹ file `database/schema_ai_core.sql` để hiểu cấu trúc, và chạy lệnh reset db để áp dụng schema mới nhất (lưu ý: lệnh này sẽ xóa toàn bộ dữ liệu hiện có):
>
> ```bash
> python scripts/reset_and_seed_db.py --reset
> ```
> *Ghi lại `jobAppId` và `hrId` được in ra trong console để sử dụng cho các bài test tiếp theo.*

### 3.1. Test E2E Ingestion Pipeline (`test_e2e_pipeline.py`)

Bài test này thực hiện đầy đủ quy trình ingestion ngoại tuyến: tải file CV -> phân tích cú pháp (5-Tier) -> sinh markdown -> chia chunk -> sinh embedding (sử dụng Gemini 1536-dim) -> lưu xuống Database.

**Lệnh chạy:**
```bash
python smoke_tests/test_e2e_pipeline.py --job-app-id <jobAppId_cua_ban> --pdf-path sample.pdf
```
*(Nếu muốn bỏ qua ghi DB chỉ test luồng API, thêm cờ `--skip-db`)*

### 3.2. Test E2E Chat API (`test_chat_api.py`)

Bài test này mô phỏng luồng gọi API chat thực tế của miCareer-mini:
1. Lấy danh sách hội thoại cũ để kiểm tra API kết nối.
2. Gửi câu hỏi đầu tiên đến `POST /v2/chat/query` (tạo hội thoại mới).
3. Gửi tiếp câu hỏi 2 trong cùng `conversationId` vừa nhận (kiểm tra tính liên tục).
4. Gọi `GET /v2/chat/conversations/{id}/messages` để xác minh lịch sử tin nhắn được lưu trữ đúng chuẩn.

**Lệnh chạy:**
```bash
python smoke_tests/test_chat_api.py
```
*(Đảm bảo server FANG đã khởi động bằng lệnh `uvicorn app.main:app` trước khi chạy)*

### 3.3. Các Smoke Test Khác

- **`test_parser.py`**:
  Chạy độc lập bộ parser 5-Tier Fallback trên file PDF mẫu `sample.pdf` để kiểm tra độ tin cậy và cấu trúc JSON đầu ra mà không ghi DB.
  ```bash
  python smoke_tests/test_parser.py
  ```
- **`test_parser_db.py`**:
  Chạy bộ parser trên `sample.pdf` và lưu trực tiếp bản ghi parsed JSON vào bảng `CVPARSED` trong Database.
  ```bash
  python smoke_tests/test_parser_db.py
  ```
- **`test_chunking.py`**:
  Đọc dữ liệu `CVPARSED` sẵn có từ DB, thực hiện thuật toán chunking và lưu các chunk vào bảng `AIDOCUMENTCHUNK` (không gọi embedding API).
  ```bash
  python smoke_tests/test_chunking.py
  ```

---

## 4. Kiểm Thử Giao Diện Tích Hợp (miCareer-mini)

Cách test tốt nhất để đảm bảo End-to-End thực sự hoạt động trơn tru là thông qua giao diện miCareer-mini UI.

1.  Bật FANG server: `uvicorn app.main:app`
2.  Bật miCareer-mini: `python -m streamlit run app.py`
3.  Thực hiện "Luồng Candidate": Đăng nhập ứng viên -> Upload CV. Quan sát progress bar chạy.
4.  Thực hiện "Luồng HR": Đăng nhập HR -> Mở chi tiết ứng viên vừa nộp -> Chat RAG.
5.  Thử đổi Model Mode ở giao diện HR (ví dụ: ép chạy `auto-pro`) và quan sát kết quả trả về + log của FANG.

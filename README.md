# FANG - AI Core v2.0

AI layer trung tâm cho hệ sinh thái miCareer. Xây dựng trên nền tảng **FastAPI**, FANG chịu trách nhiệm toàn bộ logic xử lý AI khép kín, từ việc hấp thụ tài liệu (Ingestion) cho đến truy vấn phân tích (RAG Query) với kiến trúc dự phòng 5-Tier Fallback mạnh mẽ.

## Kiến Trúc Tổng Quan (v2)

FANG v2 hoạt động như một REST API Server độc lập, bao gồm 2 Pipeline chính:

1.  **Ingestion Pipeline (`/v2/ingestion`):** Nhận CV (URL Cloudinary) -> Phân tích dữ liệu bằng LLM 5-Tier (Parse) -> Chia nhỏ dữ liệu theo cấu trúc ngữ nghĩa (Chunk) -> Nhúng thành vector (Embed) -> Lưu trữ vào PostgreSQL (pgvector).
2.  **RAG Chat Pipeline (`/v2/chat`):** Nhận Prompt từ người dùng -> Tự động nhúng Prompt -> Tìm kiếm Vector ngữ cảnh đa nguồn (CV, Job, ATS) -> Ghép nối System Prompt & Quản lý Context Window (Tóm tắt hội thoại) -> Truy vấn LLM 5-Tier -> Lưu trữ tin nhắn.

## API Contract (v2)

### Chat API
- `POST /v2/chat/query` — Gửi câu hỏi, nhận phản hồi AI (hỗ trợ 7 chế độ model/fallback).
- `GET /v2/chat/conversations` — Lấy danh sách hội thoại của HR.
- `GET /v2/chat/conversations/{id}/messages` — Lấy lịch sử tin nhắn.
- `POST /v2/chat/conversations/{id}/summarize` — Tóm tắt lịch sử cũ để giảm tải token.
- `POST /v2/chat/conversations/{id}/branch-new` — Tạo hội thoại mới với tóm tắt ngữ cảnh cũ.

### Ingestion API
- `POST /v2/ingestion/jobs` — Kích hoạt xử lý CV.
- `GET /v2/ingestion/jobs/{indexJobId}` — Kiểm tra trạng thái xử lý (`PENDING`, `PROCESSING`, `SUCCESS`, `FAILED`).

## 5-Tier LLM Architecture

Cả Parser và Generator đều sử dụng chung một cơ chế **5-Tier Fallback** với **ProTierGate** nghiêm ngặt để tối ưu chi phí và chất lượng:

**🟢 Lite tier (Ưu tiên tiết kiệm, fallback tuần tự):**
1.  Gemini Flash (`gemini-3.1-flash-lite-preview`)
2.  GPT-5.4 mini (`gpt-5.4-mini`)
3.  Claude 4.5 Haiku (`claude-4.5-haiku`)

**🟠 Pro tier (Chỉ kích hoạt khi Lite gặp sự cố hạ tầng hoặc chất lượng output quá kém):**
4.  Gemini 3.1 Pro (`gemini-3.1-pro-preview`)
5.  GPT-5.4 (`gpt-5.4`)

*Lưu ý: Hệ thống có cơ chế tự động resolve tên model (`MODEL_CANDIDATES`) để tránh bị gián đoạn khi nhà cung cấp nâng cấp hoặc đổi tên API.*

## Cài đặt & Cấu hình

1. **Khởi tạo môi trường:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Cấu hình `.env`:**
   Copy `.env.example` thành `.env` và điền:
   - `DATABASE_URL`: PostgreSQL chứa DB micareer_lite_db (cần có extension `vector`).
   - Các API Key: `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `CLAUDE_API_KEY`.
   - `CORS_ALLOWED_ORIGINS`: Để `*` cho môi trường Dev.

3. **Khởi chạy Server:**
   ```bash
   uvicorn app.main:app --reload
   ```
   *Mặc định chạy ở cổng 8000.*

## Tài Liệu Hệ Thống

*Các tài liệu được chia thành `strategy` (Lý thuyết, kiến trúc) và `guide` (Thực hành, cài đặt).*

1.  [docs/system_architecture.md](./docs/system_architecture.md)
2.  [docs/strategy/rag_query_strategy.md](./docs/strategy/rag_query_strategy.md) — Tổng quan kiến trúc RAG v2
3.  [docs/strategy/integration_strategy.md](./docs/strategy/integration_strategy.md) — Hợp đồng API v2 chi tiết
4.  [docs/guide/rag_query_guide.md](./docs/guide/rag_query_guide.md) — Cẩm nang vận hành RAG v2
5.  [docs/guide/integration_guide.md](./docs/guide/integration_guide.md) — Hướng dẫn tích hợp Frontend
6.  [docs/guide/cv_parser_guide.md](./docs/guide/cv_parser_guide.md) — Chi tiết về 5-Tier Parser
7.  [docs/guide/database_guide.md](./docs/guide/database_guide.md) — Cấu trúc CSDL pgvector

---

## Legacy (v1)

> ⚠️ Các tính năng dưới đây vẫn được hỗ trợ để tương thích ngược (`/v1/*`), nhưng không khuyến khích sử dụng cho các phát triển mới.

**Smoke tests (chỉ Parser):**
- Chạy Parser độc lập: `python test_parser.py`
- Test Chunking (in ra console): `python test_chunking.py`
- Test Parser + DB: `python test_parser_db.py`

**Chạy tích hợp Ingestion API v1:**
1. Reset DB: `python scripts/reset_and_seed_db.py --reset` (Lưu ý ID được in ra)
2. Mở `test_api.http` trong VS Code (cần REST Client extension) để bắn request test.

# FANG - AI Core v2.0

AI layer trung tâm cho hệ sinh thái miCareer. Xây dựng trên nền tảng **FastAPI**, FANG chịu trách nhiệm toàn bộ logic xử lý AI khép kín, từ việc hấp thụ tài liệu (Ingestion) cho đến truy vấn phân tích (RAG Query) với kiến trúc dự phòng đa tầng mạnh mẽ.

## Kiến Trúc Tổng Quan (v2)

FANG v2 hoạt động như một REST API Server độc lập, bao gồm 2 Pipeline chính:

1.  **Ingestion Pipeline (`/v2/ingestion`):** Nhận CV (URL Cloudinary) → Phân tích dữ liệu bằng LLM 5-Tier Parser (Parse) → Chia nhỏ dữ liệu theo cấu trúc ngữ nghĩa (Chunk) → Nhúng thành vector (Embed) → Lưu trữ vào PostgreSQL (pgvector). NMAIex enrichment (skill mapping, province mapping, expyears) chạy sidecar sau ingestion chính — fail enrichment không chặn `SUCCESS` của ingestion.
2.  **RAG Chat Pipeline (`/v2/chat`):** Nhận Prompt từ người dùng → Tự động nhúng Prompt → Tìm kiếm Vector ngữ cảnh đa nguồn (CV, Job, ATS) → Ghép nối System Prompt & Quản lý Context Window (Tóm tắt hội thoại) → Truy vấn LLM (7 modelMode) → Lưu trữ tin nhắn.

## API Contract (v2)

### Chat API
- `POST /v2/chat/query` — Gửi câu hỏi, nhận phản hồi AI (hỗ trợ 7 chế độ model/fallback).
- `GET /v2/chat/conversations` — Lấy danh sách hội thoại của HR.
- `GET /v2/chat/conversations/{id}/messages` — Lấy lịch sử tin nhắn.
- `POST /v2/chat/conversations/{id}/summarize` — Tóm tắt lịch sử cũ để giảm tải token.
- `POST /v2/chat/conversations/{id}/branch-new` — Tạo hội thoại mới với tóm tắt ngữ cảnh cũ.

### Ingestion API
- `POST /v2/ingestion/jobs` — Kích hoạt xử lý CV.
- `GET /v2/ingestion/jobs/{indexJobId}` — Kiểm tra trạng thái xử lý (`PENDING`, `PROCESSING`, `SUCCESS`, `FAILED`). Lưu ý: `SUCCESS` chỉ đại diện pipeline ingestion chính (parse → chunk → embed → save). NMAIex enrichment có trạng thái riêng.

### NMAIex Ranking API
- `GET /v2/nmaiex/ranking/candidates/{job_id}` — **J→C**: Danh sách ứng viên phù hợp nhất cho một job (có `score_breakdown`).
- `GET /v2/nmaiex/ranking/jobs/{candidate_id}` — **C→J**: Danh sách job gợi ý cho ứng viên (salary adjustment + language scoring).

  Query params: `?limit=20&province_id=HANOI&work_mode=REMOTE`

### NMAIex Master Data API
- `GET /v2/nmaiex/master/provinces` — 34 tỉnh/thành (nhóm theo vùng Bắc/Trung/Nam sau sáp nhập 2025).
- `GET /v2/nmaiex/master/levels` — Các cấp bậc công việc (Intern, Fresher, Junior → Director).
- `GET /v2/nmaiex/master/categories` — Danh mục ngành IT (17 mục).
- `GET /v2/nmaiex/master/skills` — Catalog kỹ năng hệ thống (dùng cho LLM mapper).

## Kiến trúc LLM đa tầng

### CV Parser — 5-Tier Fallback + ProTierGate

Parser sử dụng cơ chế **5-Tier Fallback** với **ProTierGate** nghiêm ngặt để tối ưu chi phí và chất lượng:

**🟢 Lite tier (fallback tuần tự):**
1.  Gemini Flash (`gemini-flash`)
2.  GPT-5.4 mini (`gpt-5.4-mini`)
3.  Claude 4.5 Haiku (`claude-4.5-haiku`)

**🟠 Pro tier (chỉ kích hoạt qua ProTierGate khi Lite gặp sự cố hạ tầng hoặc chất lượng output quá kém):**
4.  Gemini Pro (`gemini-pro`)
5.  GPT-5.5 (`gpt-5.5`)

### RAG Generation — 7 ModelMode

Generation sử dụng **7 chế độ modelMode** riêng biệt, **không dùng chung ProTierGate** với Parser:

- **auto-lite**: Gemini Flash → GPT-5.4 mini → Claude 4.5 Haiku (fallback tuần tự)
- **auto-pro**: Gemini Pro → GPT-5.5 (fallback tuần tự)
- **5 specific modes**: `gemini-flash`, `gpt-mini`, `claude-haiku`, `gemini-pro`, `gpt-full` (không fallback)

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

3. **Khởi tạo Database (nên làm mỗi khi test):**
   ```bash
   python scripts/reset_and_seed_db.py --reset
   ```

4. **Khởi chạy Server:**
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

> **NMAIex Module:** NMAIex (Nhập môn AI module) là module chính thức của FANG — hệ thống
> xếp hạng ứng viên hai chiều (J→C, C→J) dựa trên RRF + Late Fusion, tích hợp trực tiếp trong FANG core.
>
> **Chiến lược:** [`docs/strategy/nmaiex_ranking_strategy.md`](./docs/strategy/nmaiex_ranking_strategy.md)
>
> **Hướng dẫn vận hành:** [`docs/guide/nmaiex_ranking_guide.md`](./docs/guide/nmaiex_ranking_guide.md)
>
> **Cấu hình môi trường:** copy `.env.nmaiex.example` → `.env.nmaiex` và điền giá trị. Router được mount tại `/v2/nmaiex`.

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

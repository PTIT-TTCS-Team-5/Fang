# FANG - AI Core v2

AI layer cho miCareer, bao gồm ingestion CV (parse → chunk → embed) và RAG query (embed prompt → vector search → 5-tier LLM generation). Xây dựng trên FastAPI.

## API Contract (v2)

### Chat
- `POST /v2/chat/query` — Nhận prompt từ HR, trả response AI + conversation context
- `GET /v2/chat/conversations?hrId=&jobAppId=` — Danh sách hội thoại
- `GET /v2/chat/conversations/{id}/messages` — Lịch sử message
- `POST /v2/chat/conversations/{id}/summarize` — Tóm tắt & tiếp tục
- `POST /v2/chat/conversations/{id}/branch-new` — Sang hội thoại mới

### Ingestion
- `POST /v2/ingestion/jobs` — Request: `{ "jobAppId": 123, "cvSnapUrl": "https://..." }` — Response `202`: `{ "indexJobId": 1, "status": "QUEUED" }`
- `GET /v2/ingestion/jobs/{indexJobId}` — Response `200`: `{ "status": "QUEUED|PROCESSING|SUCCESS|FAILED", "errorMsg": null }`

### System
- `GET /v2/healthz` — Response `200`: `{ "ok": true, "version": "2.0" }`

> `/v1/` endpoints giữ lại tạm thời (deprecated). Xem API contract đầy đủ: [docs/strategy/integration_strategy.md](./docs/strategy/integration_strategy.md)

## Tài liệu nên đọc trước
1. [docs/system_architecture.md](./docs/system_architecture.md)
2. [docs/strategy/rag_query_strategy.md](./docs/strategy/rag_query_strategy.md) — Tổng quan kiến trúc RAG v2
3. [docs/guide/rag_query_guide.md](./docs/guide/rag_query_guide.md) — **Cẩm nang vận hành RAG v2**
4. [docs/strategy/integration_strategy.md](./docs/strategy/integration_strategy.md) — Hợp đồng API v2
5. [docs/guide/integration_guide.md](./docs/guide/integration_guide.md) — **Hướng dẫn tích hợp phía Frontend**
6. [docs/guide/cv_parser_guide.md](./docs/guide/cv_parser_guide.md)
7. [docs/guide/database_guide.md](./docs/guide/database_guide.md)
8. [docs/cau_truc_thu_muc.txt](./docs/cau_truc_thu_muc.txt)

## Cấu trúc thư mục docs
- [docs/strategy](./docs/strategy): tài liệu định hướng, quyết định kiến trúc, trade-off.
- [docs/guide](./docs/guide): tài liệu triển khai chi tiết, cấu hình, vận hành, troubleshooting.
- [docs/research](./docs/research): tài liệu nghiên cứu và benchmark làm căn cứ cho các quyết định kỹ thuật.

## Parser Architecture (v2 — 5-Tier)
CV parser dùng 5 tier với ProTierGate nghiêm ngặt giữa Lite và Pro:

**🟢 Lite tier (fallback tuần tự):**
- Tier 1: Gemini Flash (`gemini-3.1-flash-lite-preview`)
- Tier 2: GPT-5.4 mini (`gpt-5.4-mini`)
- Tier 3: Claude 4.5 Haiku (`claude-4.5-haiku`)

**🟠 Pro tier (chỉ leo khi Lite output chất lượng thấp):**
- Tier 4: Gemini 3.1 Pro (`gemini-3.1-pro-preview`)
- Tier 5: GPT-5.4 (`gpt-5.4`)

Mọi tier dùng chung orchestration policy:
- Retry bằng `tenacity`, có thể bật/tắt bằng config toàn cục.
- Chỉ retry transient error: timeout, rate limit, 5xx, connection reset.
- Fallback tier tiếp khi exception hoặc output quality thấp.
- Quality gate deterministic, không gọi thêm LLM.
- `parserVer` được gán theo định dạng `provider:model`.
- Model name resolve tự động qua `MODEL_CANDIDATES` dict (chống tên model thay đổi).

## Cài đặt
1. Tạo virtual environment: `python -m venv venv`
2. Kích hoạt venv:
   Windows: `venv\Scripts\activate`
   Linux/Mac: `source venv/bin/activate`
3. Cài dependencies: `python -m pip install -r requirements.txt`

## Cấu hình
Copy `.env.example` thành `.env`, sau đó điền các biến cần thiết:

**Cơ sở dữ liệu & Provider:**
- `DATABASE_URL`
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY`
- `CLAUDE_API_KEY`

**Parser (giữ từ v1):**
- `PARSER_RETRY_ENABLED`
- `PARSER_RETRY_ATTEMPTS`
- `PARSER_RETRY_BASE_SECONDS`
- `PARSER_RETRY_MAX_SECONDS`
- `PARSER_QUALITY_MIN_RAWTEXT_LENGTH`
- `PARSER_QUALITY_MIN_SECTION_SIGNALS`

**RAG Query (mới trong v2):**
- `FANG_API_URL` — URL của chính FANG (nếu cần self-reference)
- `CORS_ALLOWED_ORIGINS` — Domain được phép gọi API (mặc định `*` cho dev)
- `RAG_TOP_K_CHUNKS` — Số chunk trả về từ vector search (mặc định: 3)
- `CONTEXT_BUDGET_WARNING_THRESHOLD` — Ngưỡng cảnh báo context (mặc định: 0.80)
- `CONTEXT_SUMMARIZATION_MODEL` — Model dùng để tóm tắt (mặc định: `gemini-flash`)

**Logging:**
- `LOG_LEVEL`

Lưu ý:
- Không commit `.env`.
- Log không in secret value, chỉ log metadata và tên env var khi cảnh báo thiếu config.

## Chạy server
```bash
uvicorn app.main:app --reload
```

## Smoke tests
### Parser only
```bash
python test_parser.py
```

### Chunking smoke test (in ket qua tren console)
```bash
python test_chunking.py
```

Script sẽ in:
- `parserVer`
- `fallbackPath`
- raw text cắt ngắn
- JSON output nếu parse thành công

Nếu retry tắt (`PARSER_RETRY_ENABLED=false`), parser sẽ fail-fast trên mỗi tier và fallback ngay sang tier tiếp theo.

### Parser + DB
```bash
python test_parser_db.py
```

Script sẽ:
- tạo mock relational data tối thiểu
- parse `sample.pdf`
- lưu vào `CVPARSED`
- in `parserVer` và `fallbackPath`

### API End-to-End (Parse -> Chunk -> Embed)
1. Reset CSDL:
```bash
python scripts/reset_and_seed_db.py --reset
Chú ý log trả về để lấy jobAppId.
```
2. Khởi động server (nên mở trong terminal mới):
```bash
uvicorn app.main:app
```
3. Gửi Request: mở file `test_api.http` trong VS Code/PyCharm và bấm `Send Request` trên các endpoint được định nghĩa sẵn, hoặc dùng CURL. Mọi tác vụ như parse, chunk, embed và lưu Vector DB PostgreSQL sẽ được thực thi (Cần cài extension REST client trong VS Code)

## Unit test policy
```bash
python -m unittest discover -s tests/unit -p "unit_test_*.py"
```

Test cover:
- Tier 1 transient error rồi recover
- Tier 1 success nhưng quality thấp nên fallback tier 2
- Tier 1 và 2 fail, tier 3 success
- Retry disabled thì không sleep backoff

# Fang - AI Core

AI layer cho luồng ingestion CV của miCareer, xây dựng trên FastAPI và các service parser/chunking/embedding.

## API contract
- `POST /v1/ingestion/jobs`
  Request: `{ "jobAppId": 123, "cvSnapUrl": "https://..." }`
  Response `202`: `{ "indexJobId": 1, "status": "QUEUED" }`
- `GET /v1/ingestion/jobs/{indexJobId}`
  Response `200`: `{ "status": "QUEUED|PROCESSING|SUCCESS|FAILED", "errorMsg": null }`
- `GET /healthz`
  Response `200`: `{ "ok": true }`

## Tài liệu nên đọc trước
1. [docs/system_architecture.md](./docs/system_architecture.md)
2. [docs/cv_parser_guide.md](./docs/cv_parser_guide.md)
3. [docs/chunking_strategy.md](./docs/chunking_strategy.md)
4. [docs/cau_truc_thu_muc.txt](./docs/cau_truc_thu_muc.txt)
5. [docs/database_guide.md](./docs/database_guide.md)

## Parser architecture
CV parser hiện tại dùng 3 tier:
- Tier 1: Gemini Flash
- Tier 2: GPT-5.4 mini
- Tier 3: Claude 4.5 Haiku

Mỗi tier dùng chung orchestration policy:
- Retry bằng `tenacity`, có thể bật/tắt bằng config toàn cục.
- Chỉ retry transient error: timeout, rate limit, 5xx, connection reset / transport error.
- Fallback tier tiếp theo khi provider exception hoặc output quality thấp.
- Quality gate là deterministic, không gọi thêm LLM.
- `parse_to_raw_and_json` vẫn giữ contract cũ: trả về `(raw_text, parsed_json)`.
- `parserVer` được gán theo định dạng `provider:model`.

## Cài đặt
1. Tạo virtual environment: `python -m venv venv`
2. Kích hoạt venv:
   Windows: `venv\Scripts\activate`
   Linux/Mac: `source venv/bin/activate`
3. Cài dependencies: `python -m pip install -r requirements.txt`

## Cấu hình
Copy `.env.example` thành `.env`, sau đó điền các biến cần thiết:
- `DATABASE_URL`
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY`
- `CLAUDE_API_KEY`
- `PARSER_RETRY_ENABLED`
- `PARSER_RETRY_ATTEMPTS`
- `PARSER_RETRY_BASE_SECONDS`
- `PARSER_RETRY_MAX_SECONDS`
- `PARSER_QUALITY_MIN_RAWTEXT_LENGTH`
- `PARSER_QUALITY_MIN_SECTION_SIGNALS`
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

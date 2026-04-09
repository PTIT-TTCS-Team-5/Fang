# Fang - AI Core

AI layer cho luong ingestion CV cua miCareer, xay dung tren FastAPI va cac service parser/chunking/embedding.

## API contract
- `POST /v1/ingestion/jobs`
  Request: `{ "jobAppId": 123, "cvSnapUrl": "https://..." }`
  Response `202`: `{ "indexJobId": 1, "status": "QUEUED" }`
- `GET /v1/ingestion/jobs/{indexJobId}`
  Response `200`: `{ "status": "QUEUED|PROCESSING|SUCCESS|FAILED", "errorMsg": null }`
- `GET /healthz`
  Response `200`: `{ "ok": true }`

## Tai lieu nen doc truoc
1. [docs/system_architecture.md](./docs/system_architecture.md)
2. [docs/cv_parser_guide.md](./docs/cv_parser_guide.md)
3. [docs/chunking_strategy.md](./docs/chunking_strategy.md)
4. [docs/cau_truc_thu_muc.txt](./docs/cau_truc_thu_muc.txt)

## Parser architecture
CV parser hien tai dung 3 tier:
- Tier 1: Gemini Flash
- Tier 2: GPT-5.4 mini
- Tier 3: Claude 4.5 Haiku

Moi tier dung chung orchestration policy:
- Retry bang `tenacity`, co the bat/tat bang config toan cuc.
- Chi retry transient error: timeout, rate limit, 5xx, connection reset / transport error.
- Fallback tier tiep theo khi provider exception hoac output quality thap.
- Quality gate la deterministic, khong goi them LLM.
- `parse_to_raw_and_json` van giu contract cu: tra ve `(raw_text, parsed_json)`.
- `parserVer` duoc gan theo dinh dang `provider:model`.

## Cai dat
1. Tao virtual environment: `python -m venv venv`
2. Kich hoat venv:
   Windows: `venv\Scripts\activate`
   Linux/Mac: `source venv/bin/activate`
3. Cai dependencies: `python -m pip install -r requirements.txt`

## Cau hinh
Copy `.env.example` thanh `.env`, sau do dien cac bien can thiet:
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

Luu y:
- Khong commit `.env`.
- Log khong in secret value, chi log metadata va ten env var khi canh bao thieu config.

## Chay server
```bash
uvicorn app.main:app --reload
```

## Smoke tests
### Parser only
```bash
python test_parser.py
```

Script se in:
- `parserVer`
- `fallbackPath`
- raw text cat ngan
- JSON output neu parse thanh cong

Neu retry tat (`PARSER_RETRY_ENABLED=false`), parser se fail-fast tren moi tier va fallback ngay sang tier tiep theo.

### Parser + DB
```bash
python test_parser_db.py
```

Script se:
- tao mock relational data toi thieu
- parse `sample.pdf`
- luu vao `CVPARSED`
- in `parserVer` va `fallbackPath`

## Unit test policy
```bash
python -m unittest test_parser_policy.py
```

Test cover:
- Tier 1 transient error roi recover
- Tier 1 success nhung quality thap nen fallback tier 2
- Tier 1 va 2 fail, tier 3 success
- Retry disabled thi khong sleep backoff

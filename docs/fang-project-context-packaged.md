# FANG Project Context Package

**Project**: Fang (AI Core) - miCareer CV ingestion pipeline  
**Prepared for**: Handoff to next chat / next agent  
**Current branch**: `feat/embedding-phase`  
**Date**: 2026-04-09

## 1. Tóm tắt ngắn
- Dự án xây dựng AI Core cho miCareer, xử lý CV từ PDF thành dữ liệu có cấu trúc, sau đó chunking, embedding và lưu vào PostgreSQL/pgvector.
- Phase parser đã hoàn thành và được tách thành nhánh riêng `feat/parser-multi-provider-3tier`.
- Phase chunking đã có thiết kế và code hiện tại nằm trên nhánh `ai-core-chunking`.
- Nhánh hiện tại `feat/embedding-phase` được tạo từ `develop` để bắt đầu phase embedding.

## 2. Kiến trúc hiện tại

### Luồng ingestion tổng quát
1. `POST /v1/ingestion/jobs`
2. Tải CV PDF từ `cvSnapUrl`
3. Parse CV qua `parse_to_raw_and_json`
4. Chunking raw text / ParsedCV
5. Embedding chunks
6. Lưu chunk + vector vào database
7. Cập nhật trạng thái ingestion job

### Parser phase hiện tại
- Tier 1: Gemini Flash
- Tier 2: GPT-5.4 mini
- Tier 3: Claude 4.5 Haiku
- Có retry bằng `tenacity`, có thể bật/tắt bằng `PARSER_RETRY_ENABLED`
- Có quality gate deterministic để fallback khi output thấp chất lượng
- `parserVer` được gán theo dạng `provider:model`
- Có telemetry trace qua `get_last_parse_trace()`

## 3. Các file chính của parser phase
- `app/services/cv_parser.py`: orchestrator 3 tầng, retry, quality gate, trace
- `app/services/cv_parser_adapters.py`: adapter chung cho Gemini/OpenAI/Anthropic
- `app/core/config.py`: env settings cho API keys, retry policy, quality thresholds
- `app/api/routes_ingestion.py`: background ingestion flow
- `app/services/persistence.py`: lưu parsed CV và document chunks
- `test_parser.py`: smoke test parser
- `test_parser_db.py`: smoke test parser + DB
- `test_parser_policy.py`: unit test orchestration bằng mock provider

## 4. Config / env hiện có
- `GOOGLE_API_KEY`
- `OPENAI_API_KEY`
- `CLAUDE_API_KEY`
- `PARSER_RETRY_ENABLED`
- `PARSER_RETRY_ATTEMPTS`
- `PARSER_RETRY_BASE_SECONDS`
- `PARSER_RETRY_MAX_SECONDS`
- `PARSER_QUALITY_MIN_RAWTEXT_LENGTH`
- `PARSER_QUALITY_MIN_SECTION_SIGNALS`
- `EMBEDDING_PROVIDER`
- `EMBEDDING_DIM`
- `DATABASE_URL`

## 5. Chunking strategy đã được định hướng
Tài liệu chính: `docs/chunking_strategy.md`

Các nguyên tắc đã chốt:
- Zero-LLM chunking
- Markdown-aware flattening từ ParsedCV
- Small-to-Big retrieval
- Parent node > 512 tokens sẽ split thành child chunks
- Child chunks khoảng 150-200 tokens, overlap khoảng 20%
- Section pinning / deterministic context injection
- Lưu vector vào PostgreSQL `pgvector`, ưu tiên `halfvec` và HNSW

## 6. Những gì đã làm xong
### Parser
- Refactor parser sang kiến trúc multi-provider 3 tầng
- Thêm retry policy có thể bật/tắt
- Thêm quality gate deterministic
- Sửa call signature persistence để lưu `parsed_json`
- Cập nhật docs parser và system architecture

### Docs
- `docs/system_architecture.md`: đã có diagram bao gồm retry, low quality, all-tier failed
- `docs/cv_parser_guide.md`: mô tả workflow parser chi tiết
- `docs/cau_truc_thu_muc.txt`: mô tả cấu trúc thư mục có dấu tiếng Việt
- `README.md`: mô tả parser 3 tầng và retry toggle

## 7. Repository / branch state
- `main` / `develop` vẫn là các nhánh gốc
- `ai-core-chunking`: chứa phase chunking
- `feat/parser-multi-provider-3tier`: chứa parser refactor
- `feat/embedding-phase`: nhánh sạch được tạo từ `develop` để làm embedding

## 8. Lưu ý quan trọng khi sang phase embedding
- Parser output đã ổn định, nên embedding phase có thể nhận `ParsedCV` làm input chính
- Nên giữ contract cũ của parser để tránh ảnh hưởng ingestion route và test hiện tại
- Phase embedding nên tập trung vào:
  - `markdown_builder.py`
  - `chunking.py`
  - `embedding.py`
  - persistence cho `AIDOCUMENTCHUNK`
  - smoke test chunking / embedding

## 9. Blockers / hạn chế hiện tại
- GitHub CLI trên máy này chưa đăng nhập nên chưa tạo PR tự động được
- Hai file PDF nghiên cứu trong `docs/` vẫn đang là file chưa theo dõi; nếu muốn repo sạch có thể bỏ hoặc chuyển sang markdown
- Một số model names trong ví dụ là placeholder theo thiết kế, nhưng logic provider đã tách riêng và có thể thay model bằng config

## 10. Gợi ý cho agent/chat tiếp theo
Khi bắt đầu phase embedding, hãy đọc trước:
- `README.md`
- `docs/system_architecture.md`
- `docs/cv_parser_guide.md`
- `docs/chunking_strategy.md`
- `docs/cau_truc_thu_muc.txt`
- `app/services/markdown_builder.py`
- `app/services/chunking.py`
- `app/services/embedding.py`
- `app/services/persistence.py`

Sau đó tập trung vào đúng nhiệm vụ của **Chat A (Gemini Pro - phân tích & thiết kế kiến trúc)**:
1. Đánh giá kiến trúc hiện tại và xác định khoảng trống trước khi vào phase embedding.
2. Thiết kế kiến trúc embedding end-to-end (ingestion -> flatten -> chunk -> embed -> persist -> retrieve).
3. Chốt chiến lược chunking chi tiết (ngưỡng, overlap, metadata injection, chuẩn hóa token).
4. Thiết kế schema dữ liệu và index cho `AIDOCUMENTCHUNK` (bao gồm metadata, `halfvec`, HNSW).
5. Đề xuất kế hoạch kiểm thử và tiêu chí nghiệm thu (smoke/integration/quality checks).
6. Xuất đặc tả bàn giao cho Chat B (model thực thi) theo format: phạm vi file, thứ tự triển khai, rủi ro, rollback plan.

**Lưu ý:** Chat A không thực thi code; chỉ tạo bản thiết kế/đặc tả để chuyển sang Chat B (Claude Opus hoặc OpenAI Codex) triển khai.

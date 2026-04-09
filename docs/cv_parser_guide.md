# Hướng dẫn module CV Parser

Tài liệu này mô tả chi tiết module parser CV sau refactor multi-provider 3-tier.

## 1. Mục tiêu thiết kế
- Giữ contract cũ: `parse_to_raw_and_json(cv_bytes) -> (raw_text, parsed_json)`.
- Tách adapter/provider interface chung để dễ test và để thêm provider mới.
- Retry có thể bật/tắt bằng config.
- Fallback khi exception hoặc output quality thấp.
- Không log secret value.

## 2. Thành phần chính

### `app/services/cv_parser.py`
Chứa orchestration policy:
- danh sách tiers
- retry policy bằng `tenacity`
- quality gate deterministic
- trace `fallbackPath`
- helper `get_last_parse_trace()`

### `app/services/cv_parser_adapters.py`
Chứa adapter chung và 3 provider cụ thể:
- `GeminiProviderAdapter`
- `OpenAIProviderAdapter`
- `AnthropicProviderAdapter`

Adapter có nhiệm vụ:
- kiểm tra env var cần thiết
- gọi SDK tương ứng
- chuẩn hóa exception thành `TransientProviderError` hoặc `NonRetryableProviderError`
- trả về `ParsedCV` và model đã resolve

## 3. Workflow chi tiết

1. `parse_to_raw_and_json` tạo `CVParserOrchestrator`.
2. Orchestrator lặp qua các tier theo thứ tự:
   - Tier 1: `google / gemini-flash`
   - Tier 2: `openai / gpt-5.4-mini`
   - Tier 3: `anthropic / claude-4.5-haiku`
3. Mỗi tier được chạy qua `AsyncRetrying`.
4. Nếu provider trả kết quả hợp lệ, quality gate được check ngay lập tức.
5. Nếu quality gate pass:
   - gán `parserVer = provider:model`
   - return `rawText` và `model_dump()`
6. Nếu quality gate fail:
   - log `low_confidence_output`
   - chuyển tier kế tiếp
7. Nếu tier fail với transient error:
   - retry theo policy
   - hết retry thì fallback sang tier kế tiếp
8. Nếu tất cả tiers đều fail:
   - raise `CVParsingError`

## 4. Retry policy

Config:
- `PARSER_RETRY_ENABLED`
- `PARSER_RETRY_ATTEMPTS`
- `PARSER_RETRY_BASE_SECONDS`
- `PARSER_RETRY_MAX_SECONDS`

Mặc định:
- enabled = `true`
- attempts = `3`
- base = `2`
- max = `8`

Error được coi là transient:
- timeout
- rate limit
- HTTP 408/409/429
- HTTP 5xx
- connection reset / transport error

Khi `PARSER_RETRY_ENABLED=false`:
- mỗi tier chỉ gọi 1 lần
- không sleep backoff
- fallback ngay sang tier tiếp theo nếu gặp lỗi

## 5. Quality gate

Quality gate không gọi thêm LLM. Toàn bộ là deterministic code path.

### Rule 1: `rawText`
- không rỗng
- độ dài >= `PARSER_QUALITY_MIN_RAWTEXT_LENGTH`

### Rule 2: `candidateInfo`
Cần có ít nhất một signal định danh:
- `fullName`
- `emails`
- `phones`
- `location`

### Rule 3: section signals
Số section chính không rỗng phải đạt ngưỡng `PARSER_QUALITY_MIN_SECTION_SIGNALS`.

Section hiện tại được tính:
- `experience`
- `education`
- `skills`
- `certificates`
- `languages`
- `summary`

## 6. Logging và trace

Mỗi invocation log:
- `tierIndex`
- `provider`
- `model`
- `durationMs`
- `retryCount`
- `fallbackReason`

Giá trị `fallbackReason`:
- `transient_error`
- `non_retryable_error`
- `low_confidence_output`

`get_last_parse_trace()` trả về:
- `parser_ver`
- `fallback_path`
- `selected_tier_index`
- danh sách attempts

Script `test_parser.py` và `test_parser_db.py` in `parserVer` / `fallbackPath` từ trace này.

## 7. Lưu ý provider

### Gemini
- Vẫn dùng Files API + schema response của Gemini.
- Có cơ chế resolve alias model để tìm model flash đang available.

### OpenAI
- Dùng `responses.create`.
- Gửi PDF dạng `input_file`.
- Parse JSON và validate lại bằng `ParsedCV`.

### Anthropic
- Dùng `messages.create`.
- Gửi PDF dạng `document` block.
- Ép response JSON bằng prompt + schema text, sau đó validate lại bằng `ParsedCV`.

## 8. Unit tests

`test_parser_policy.py` cover:
- transient error rồi recover trong cùng tier
- low-quality output fallback sang tier tiếp theo
- tier 1 và 2 fail, tier 3 success
- retry disabled thì không có backoff sleep

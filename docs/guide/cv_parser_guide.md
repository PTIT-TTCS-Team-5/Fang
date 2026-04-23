# Hướng dẫn module CV Parser (v2)

Tài liệu này mô tả chi tiết module parser CV trong FANG v2 với kiến trúc **5-Tier Fallback** và cơ chế **ProTierGate**.

## 1. Mục tiêu thiết kế
- **Độ tin cậy cao**: Sử dụng 5 model từ 3 provider lớn (Google, OpenAI, Anthropic).
- **Tối ưu chi phí**: Cơ chế ProTierGate chỉ cho phép leo lên các model Pro đắt đỏ khi các model Lite không đạt yêu cầu chất lượng.
- **Tự động hóa**: Resolve model name tự động và retry bằng tenacity.

## 2. Các tầng Parser (5-Tier)

| Tầng | Nhóm | Model định danh | Provider |
| :--- | :--- | :--- | :--- |
| **Tier 1** | Lite | `gemini-flash` | Google |
| **Tier 2** | Lite | `gpt-5.4-mini` | OpenAI |
| **Tier 3** | Lite | `claude-4.5-haiku` | Anthropic |
| **Tier 4** | Pro | `gemini-pro` | Google |
| **Tier 5** | Pro | `gpt-5.4` | OpenAI |

## 3. Cơ chế ProTierGate
Đây là điểm mới quan trọng trong v2. Hệ thống không chỉ fallback khi gặp lỗi hệ thống (Transient Error), mà còn fallback dựa trên **chất lượng đầu ra**.

- **Lite-to-Lite Fallback**: Xảy ra khi Tier 1 hoặc 2 lỗi (timeout, rate limit) hoặc trả về JSON không hợp lệ.
- **Lite-to-Pro Escalation (ProTierGate)**: Nếu cả 3 Tier Lite đều không vượt qua được **Quality Gate**, hệ thống mới kích hoạt Tier 4 (Pro). 
- *Lưu ý*: Nếu Lite tiers fail do lỗi hạ tầng (ví dụ: DNS, Network toàn cục), hệ thống sẽ KHÔNG leo lên Pro để tránh lãng phí.

## 4. Quality Gate (Deterministic)
Quality gate không gọi thêm LLM để đánh giá mà dùng các quy tắc cứng:
- **`rawText` length**: Phải đạt ngưỡng tối thiểu (`PARSER_QUALITY_MIN_RAWTEXT_LENGTH`).
- **Identity Signals**: Phải tìm thấy ít nhất 1 thông tin (Họ tên, Email, SĐT).
- **Section Signals**: Phải nhận diện được số lượng section chính (Kinh nghiệm, Học vấn...) đạt ngưỡng quy định.

## 5. Workflow thực thi
1. Gọi Tier 1 (Gemini Flash).
2. Nếu fail/chất lượng thấp → Sang Tier 2.
3. Nếu fail/chất lượng thấp → Sang Tier 3.
4. Nếu cả 3 Lite fail/chất lượng thấp → **ProTierGate** quyết định có leo lên Tier 4 hay không.
5. Nếu Tier 4 fail → Tier 5 (Last resort).
6. Hoàn tất và trả về `parserVer` (ví dụ: `google:gemini-3.1-pro-preview`) và `fallbackPath`.

## 6. Cấu hình Quan trọng
- `PARSER_RETRY_ENABLED`: Bật/tắt retry cho từng tier.
- `PARSER_QUALITY_MIN_SECTION_SIGNALS`: Số lượng block thông tin tối thiểu để coi là parse thành công.

---
*Cập nhật ngày 13/04/2026 cho FANG v2.*

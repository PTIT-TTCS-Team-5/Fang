# Hướng dẫn Luồng Xử Lý Dữ Liệu Đầu Vào (v2)

Tài liệu này mô tả hạ tầng xử lý dữ liệu của FANG v2, từ lúc nhận CV PDF thô cho đến khi dữ liệu được cấu trúc hóa và nhúng vector (embedding) sẵn sàng cho RAG.

## 1. Mục tiêu
- **Chuyển đổi đa tầng**: Biến PDF thô thành JSON có cấu trúc qua 5-tier parser.
- **Tối ưu truy xuất**: Phân mảnh văn bản (Chunking) giữ vững ngữ cảnh cha.
- **Tiêu chuẩn hóa Vector**: Nhúng vector 1024 chiều dùng cho tìm kiếm ngữ nghĩa.

## 2. Luồng tổng quát v2

1. **Nhận CV (Trigger)**
   - API `POST /v2/ingestion/jobs` nhận `jobAppId` và `cvSnapUrl`.
2. **Parse CV (5-Tier Fallback)**
   - Hệ thống lặp qua các tier (Gemini Flash → GPT-5.4 mini → Claude 4.5 Haiku → Gemini Pro → GPT-5.4).
   - Sử dụng **ProTierGate** để quyết định leo lên tầng Pro.
3. **Chuyển sang Markdown & Global Context**
   - Chuyển JSON về Markdown để giữ cấu trúc heading.
   - Trích xuất thông tin chung (Tên, Năm kinh nghiệm, Kỹ năng) làm `global_context`.
4. **Chunking (Hybrid Strategy)**
   - Tách theo heading. Nếu đoạn quá dài (~512 tokens), băm nhỏ thành child chunks.
   - Mỗi chunk được tiêm `global_context` ở đầu.
5. **Embedding (v2 Standard)**
   - Sử dụng OpenAI `text-embedding-3-small` với `dimensions=1024`.
6. **Persistence**
   - Lưu kết quả parse vào `CVPARSED`.
   - Lưu chunks và vectors vào `AIDOCUMENTCHUNK`.

## 3. Các điểm cải tiến trong v2
- **API Prefix**: Toàn bộ luồng hiện tại chạy dưới đầu mục `/v2/`.
- **ProTierGate**: Tiết kiệm chi phí bằng cách ưu tiên các model Lite, chỉ dùng model Pro cho các CV phức tạp hoặc khi chất lượng parser Lite thấp.
- **Cấu hình tập trung**: Mọi thông số về token limit, batch size, và threshold chất lượng được quản lý trong `app/core/config.py`.

## 4. Script Kiểm chứng (E2E)
Bạn có thể chạy toàn bộ luồng xử lý để kiểm tra tính đúng đắn:
```bash
python smoke_tests/test_e2e_pipeline.py
```
*Lưu ý: Script này sẽ thực hiện gọi API thật và yêu cầu cài đặt đầy đủ API Keys.*

---
*Cập nhật ngày 13/04/2026 cho FANG v2.*

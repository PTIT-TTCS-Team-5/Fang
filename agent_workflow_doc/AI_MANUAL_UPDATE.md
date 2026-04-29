# Quy trình Cập nhật Định kỳ (Periodic Maintenance & Update Workflow)

Bạn là một AI Agent có khả năng truy cập web để thực hiện việc kiểm kê và cập nhật các thông số kỹ thuật định kỳ cho hệ thống FANG. Mục tiêu là đảm bảo dự án luôn sử dụng các công nghệ AI (LLM, Embedding) tối ưu, tiết kiệm chi phí và tránh rủi ro từ các mô hình bị khai tử (deprecated).

---

## NGUYÊN TẮC CỐT LÕI
1. **Không "tự nhớ":** Bạn tuyệt đối không được dựa vào kiến thức có sẵn (knowledge cutoff). BẮT BUỘC phải sử dụng công cụ tìm kiếm web để lấy dữ liệu mới nhất tại thời điểm thực hiện.
2. **Nguồn tin uy tín:** Ưu tiên thông tin từ trang chủ của nhà cung cấp (Google AI, OpenAI, Meta, Hugging Face) hoặc các bảng so sánh uy tín.
3. **Cập nhật tinh gọn:** Chỉ sửa đổi những thông số cần thiết. Giữ nguyên cấu trúc, văn phong và thiết kế của các tài liệu hiện tại.
4. **Đồng bộ hóa:** Nếu thay đổi model, phải cập nhật cả tài liệu chiến lược (Strategy) và mã nguồn (Adapter/Config) để đảm bảo tính nhất quán (Name Resolution). phải cập nhật đồng bộ "General Name" tại tài liệu Strategy (bảng Tier), từ điển Candidates, và toàn bộ các nơi gọi model đó (`cv_parser.py`, `rag_model_adapters.py`) để tránh lệch key.
5. **Đơn giản và dễ hiểu:** Luôn ưu tiên những giải pháp đơn giản, dễ hiểu và dễ bảo trì. Tránh các giải pháp phức tạp, khó hiểu hoặc khó bảo trì. Nếu gặp vướng mắc thì mạnh dạn hỏi user, hoặc tự tìm hiểu qua web để cập nhật kiến thức và đưa ra giải pháp tối ưu
---

## CÁC BƯỚC THỰC HIỆN TUẦN TỰ

### Bước 1: Kiểm toán Nội bộ (Local Audit)
Hãy đọc các file sau để lập danh sách các model và thông số hiện tại:
- **Chiến lược:** `Fang/docs/strategy/embedding_strategy.md`, `Fang/docs/strategy/rag_query_strategy.md`.
- **Mã nguồn:** `Fang/app/core/config.py`, `Fang/app/services/embedding.py`, `Fang/app/services/rag_model_adapters.py`.
- **Ghi chú:** Xác định các model name, kích thước context, và các hằng số định danh.

### Bước 2: Thu thập Thông tin Web (Intelligence Gathering)
Sử dụng công cụ `search_web` để tìm kiếm thông tin mới nhất cho từng model đã tìm thấy:
- **Thông số kỹ thuật:** Kích thước Context Window (Token limit).
- **Chi phí:** Giá trên mỗi 1 triệu tokens (Input/Output).
- **Trạng thái:** Ngày hỗ trợ cuối cùng (nếu có), các thông báo thay thế model cũ bằng model mới.
- **Tính năng mới:** Có tính năng nào mới (như hỗ trợ tiếng Việt tốt hơn, tốc độ nhanh hơn) mà dự án nên cân nhắc không?

### Bước 3: Phân tích Tác động (Impact Analysis)
Dựa trên thông tin mới, hãy đánh giá:
- Có cần thay đổi giá trị `CONTEXT_WINDOW` trong code không?
- Có cần cập nhật danh sách "Name Resolution" (Ánh xạ tên model từ logic sang API thực tế) không?
- Nếu một model bị deprecated, hãy đề xuất 01 model thay thế tốt nhất dựa trên giá thành và hiệu năng.

### Bước 4: Thực thi Cập nhật (Precise Execution)
Thực hiện các chỉnh sửa theo thứ tự:
1. **Tài liệu:** Cập nhật bảng so sánh model trong `Fang/docs/strategy/rag_query_strategy.md`.
2. **Cấu hình:** Cập nhật các hằng số trong `Fang/app/core/config.py`.
3. **Mã nguồn (Backend):** Cập nhật từ điển Candidates trong `cv_parser_adapters.py` VÀ đổi tên model tại `cv_parser.py` (Default Tiers), `rag_model_adapters.py` (Registry/Chains).
4. **Giao diện (Frontend):** Cập nhật `MODEL_MODES` trong `miCareer-mini/app.py` để hiển thị đúng tên phiên bản cho người dùng.

---

## KẾT QUẢ ĐẦU RA (Output Requirement)
Sau khi hoàn thành, bạn phải báo cáo cho tôi:
1. Danh sách những thay đổi đã thực hiện (trước và sau khi cập nhật).
2. Lý do của sự thay đổi (kèm link nguồn từ web).
3. Xác nhận tính hoạt động của hệ thống (ví dụ: code vẫn đúng cú pháp, không làm gãy các liên kết cũ).

---

> **Lưu ý cho AI:** Nếu thấy một thay đổi có nguy cơ gây lỗi lớn hoặc tốn kém chi phí đột biến, hãy dừng lại ở Bước 3 và xin ý kiến của User trước khi thực hiện Bước 4.

---

## Cập nhật lần cuối: 27/04/2026 - 10:30 PM (Giờ Việt Nam)
Cần cập nhật lại giá trị thời gian sau mỗi lần thực hiện xong quy trình update.

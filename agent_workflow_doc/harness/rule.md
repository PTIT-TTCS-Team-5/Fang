# 🛠️ Quy Tắc Hoạt Động & Kiểm Thử Cốt Lõi (Fang Project Guardrails)

## 1. Ràng Buộc Môi Trường (CRITICAL)
- **Môi trường Python:** LUÔN LUÔN ưu tiên sử dụng môi trường ảo (`venv`). TUYỆT ĐỐI KHÔNG dùng Python global để cài package hoặc chạy script dự án.
- **Xử lý File:** Khi gọi terminal/PowerShell để đọc/ghi file, bắt buộc thêm tham số `-Encoding UTF8` để tránh lỗi mojibake. 
- **Ngữ nghĩa Tiếng Việt:** Khi dùng thư viện (parser) để đọc hoặc bóc tách dữ liệu từ các file `.md`, `.pdf` tiếng Việt, phải đảm bảo cấu hình đọc chuẩn UTF-8. 

## 2. Tiêu Chuẩn Kiểm Thử Bắt Buộc (Definition of Done)
Trước khi báo cáo hoàn thành công việc, bạn (Agent) phải tự đánh giá phạm vi thay đổi code và bắt buộc thực thi kiểm thử theo các cấp độ sau:
- **Cấp độ 1 (Thay đổi logic nhỏ, cú pháp hàm):** Bắt buộc tự chạy `pycompile` và `pytest` trên file vừa sửa. Cấm việc tuyên bố code chạy đúng mà không có log terminal thực tế.
- **Cấp độ 2 (Thay đổi Database, API, Logic Backend lõi):** Phải đạt (Cấp độ 1) + Bắt buộc gọi test end-to-end bằng file `test_api.http` hoặc Postman MCP để kiểm chứng payload trả về thực tế.
- **Cấp độ 3 (Thay đổi Giao diện UI/UX, Frontend flow):** Phải đạt (Cấp độ 2) + Bắt buộc dùng `chrome-devtools-mcp` (hoặc MCP trình duyệt tương đương) để khởi chạy app cục bộ, render UI và xác nhận không có lỗi hiển thị (thông qua đọc DOM hoặc console log trình duyệt).

## 3. Tự Học Từ Lỗi Sai (Self-Updating Failure Mechanism)
Trong quá trình làm việc, nếu bạn phát hiện ra một luồng xử lý thất bại nhiều lần do cấu hình ẩn, một anti-pattern cốt lõi, hoặc một giả định sai về kiến trúc dự án:
- Bạn được cấp quyền (và bị bắt buộc) tự động cập nhật file rule này để răn đe các phiên làm việc sau.
- **Chỉ định:** Viết đúng 1 dòng cực ngắn tóm tắt nguyên nhân lỗi và cách phòng tránh. Bỏ qua các lỗi lặt vặt (như gõ sai typo) mà chỉ tập trung vào lỗi đặc thù hệ thống.
- **Hành động:** Append (Ghi thêm) dòng đó vào phần "Hồ Sơ Lỗi (Failures Log)" ở cuối file này theo cú pháp: `[Ngày/Tháng] - [Thành phần]: Lỗi phát hiện -> Cách xử lý chốt.`

---
## 📝 Hồ Sơ Lỗi (Failures Log) - AI BẮT BUỘC ĐỌC TRƯỚC KHI CODE:
- [Ví dụ ban đầu] - [Database]: Chỉ query PostgreSQL local qua thông số trong `.env`, không được hardcode thông tin kết nối.
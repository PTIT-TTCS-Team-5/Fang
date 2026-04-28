# Định hướng Chuẩn hóa Cơ sở dữ liệu (Database Standardization)

Tài liệu này ghi nhận quyết định chiến lược về việc nâng cấp cấu trúc cơ sở dữ liệu để phục vụ phân hệ xếp hạng NMAIex. Việc chuẩn hóa này được coi là điều kiện tiên quyết (Prerequisite) trong kế hoạch triển khai AI.

---

## 1. Các bảng cần chuẩn hóa tối thiểu
Để đảm bảo tính chính xác cho các bộ lọc cứng (Hard Filters) và thuật toán xếp hạng, hệ thống cần bổ sung tối thiểu 4 bảng chuẩn sau:

1. **Bảng Region (Vùng miền):** Quản lý các khu vực địa lý lớn (Bắc, Trung, Nam...).
2. **Bảng Province (Tỉnh/Thành phố):** Lưu trữ mã và tên tỉnh thành chuẩn hóa để loại bỏ việc nhập liệu tự do.
3. **Bảng Skill (Kỹ năng):** Danh mục kỹ năng chuẩn (Ontology) để tính toán độ chồng lặp kỹ năng chính xác.
4. **Bảng JobLevel (Cấp bậc):** Định nghĩa các mức độ thâm niên (Intern, Junior, Senior, Lead...) phục vụ tính toán hàm phạt thâm niên (Seniority Penalty).

---

## 2. Định hướng triển khai
- **Thời điểm:** Đây là phần việc đầu tiên trong lộ trình xây dựng NMAIex.
- **Phạm vi ảnh hưởng:** Cần cập nhật đồng bộ cả Backend (FANG) và Frontend (miCareer-mini).
- **Mục tiêu:** Chuyển đổi từ dữ liệu dạng chuỗi (String-based) sang dữ liệu dạng định danh (ID-based) để tối ưu hóa truy vấn SQL và độ chính xác của AI.

---

## 3. Tích hợp AI
- Sử dụng mô hình AI Lite (Gemini Flash-Lite) hoặc cập nhật trực tiếp các giá trị chuẩn vào file seed_data để tự động ánh xạ (Mapping) các dữ liệu cũ (chuỗi tự do) về các ID chuẩn trong bảng mới trong quá trình Migration dữ liệu (hiện chỉ có dữ liệu mẫu trong thư mục database, có root_data và seed_data)

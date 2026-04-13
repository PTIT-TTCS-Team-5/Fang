# Hướng Dẫn Quản Trị Cơ Sở Dữ Liệu (Reset & Seed DB)

Tài liệu này cung cấp hướng dẫn cách khởi tạo, làm sạch và cấp phát dữ liệu mẫu cho hệ thống cơ sở dữ liệu `miCareer_lite_db` thông qua tập lệnh. Chú ý các cảnh báo nguy hiểm khi thao tác.

## 1. Công cụ Khởi Tạo (`reset_and_seed_db.py`)
Script nằm tại thư mục `scripts/reset_and_seed_db.py`, sử dụng thư viện `psycopg2` và `asyncpg`. Giải pháp này đảm nhiệm 2 vai trò cốt lõi:
1. **Khởi tạo Cấu trúc (Schema Definition)**: Tự động tuần tự đọc và thực thi chuỗi lệnh CREATE từ các file SQL trong thư mục `database/` (`schema_web_core.sql`, sau đó là `schema_ai_core.sql`).
2. **Nạp Dữ liệu Mẫu (Mock Seeding)**: Bơm dữ liệu từ `root_data.sql` (Master Data hệ thống như Quyền Hạn, Email template, Danh mục Skill) và `seed_data.sql` (Data giả lập mô phỏng hệ sinh thái HR, Company, Candidate, Job Postings).

## 2. Cách Thực Thi Lệnh
Vui lòng mở Terminal tại thư mục gốc của FANG và đảm bảo đã kích hoạt môi trường ảo (virtual environment).

### Khởi chạy Tiêu Quản (Chỉ thêm Cấu trúc)
Nếu Database trống hoặc chưa có dữ liệu, cách này đơn thuần chạy qua các file tuần tự:
```bash
python scripts/reset_and_seed_db.py
```
*(Nếu đã có bảng, script có thể báo lỗi Conflict Exception do cố gắng tạo lại quan hệ đã tốn tại)*

### Chế độ Dọn Dẹp Sâu (Hard Reset)
Khuyên dùng cho khâu Development/Testing. Quá trình mô phỏng Ingestion tạo ra nhiều Chunk Rác, hãy sử dụng cờ `--reset` để đưa hệ thống về trạng thái nhà máy:
```bash
python scripts/reset_and_seed_db.py --reset
```
**🚨 CẢNH BÁO:** Thẻ `--reset` sẽ thực thi lệnh `DROP SCHEMA public CASCADE;`. Hệ thống sẽ bốc hơi sạch sẽ 100% dữ liệu không thể khôi phục. Cấm tuyệt đối chạy dòng lệnh này trên môi trường Production!

## 3. Cơ Chế Bảo Vệ Kép (Safe-guard)
Để phòng tránh rủi ro Dev trỏ nhầm `.env` vào CSDL Production, script được trang bị lớp bảo mật (Hard-coded lock).
Hệ thống sẽ ping truy vấn mệnh đề: `SELECT current_database()` và **chỉ cấp phép Reset nếu tên database chính xác là `micareer_lite_db`**. 

Nếu chuỗi cấu hình `DATABASE_URL` trong file `.env` trỏ tới bất kì Tên Database nào khác, script sẽ lập tức văng ngoại lệ chặn đứng giao dịch (Rise Exception): `"BẢO VỆ CSDL: Không được phép drop schema trên DB..."`.

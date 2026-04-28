# Ghi chú Chiến lược Triển khai NMAIex: Chuẩn hóa & Triết lý Lọc

Tài liệu này ghi lại các quyết định quan trọng về hạ tầng và tư duy cốt lõi khi xây dựng phân hệ NMAIex để Agent AI tham khảo khi lập kế hoạch.

---

## 1. Chuẩn hóa Cơ sở dữ liệu (Database Foundations)
Để AI có thể hoạt động chính xác, hệ thống cần thực hiện chuẩn hóa dữ liệu từ dạng chuỗi tự do sang định danh (ID-based) cho ít nhất 4 bảng mục tiêu:

1. **Region & Province:** Đưa toàn bộ địa lý về mã chuẩn để thực hiện "Lọc cứng" (Hard Filter) chính xác 100%.
2. **Skill Ontology:** Xây dựng danh mục kỹ năng chuẩn để tính toán độ chồng lặp (Overlap) mà không bị nhiễu bởi cách viết khác nhau.
3. **JobLevel:** Định nghĩa rõ các cấp độ thâm niên để tính hàm phạt (Penalty) định lượng.

* Ngoài ra có thể phân tích và đánh giá kỹ lưỡng hơn đề xuất thêm các cải tiến khác
---

## 2. Triết lý "Ưu tiên Độ phủ" (Recall over Precision)
Trong các lớp lọc đầu tiên (Retrieval Stage) khi cơ chế còn cứng nhắc, hệ thống tuân thủ triết lý: **Thà chọn thừa còn hơn bỏ sót.**

### Nguyên tắc thực thi:
- **Tránh âm tính giả (False Negatives):** Không được phép loại bỏ một ứng viên tiềm năng chỉ vì họ lệch một từ khóa hoặc có kỹ năng viết CV chưa tốt.
- **Vai trò của Semantic & LLM Lite:** 
    - Sử dụng tìm kiếm Vector và LLM Lite để "mở rộng biên độ" tìm kiếm, hiểu được ý định ngầm định thay vì chỉ khớp từ khóa thô.
    - Mục tiêu là tạo ra một tập hợp ứng viên đủ rộng và đa dạng ở vòng ngoài.
    - Có thể cân nhắc sử dụng LLM-lite để chuẩn hóa một từ khóa thuộc danh mục nào đó về chuẩn của hệ thống (ví dụ các ứng viên viết cùng một kỹ năng nhưng diễn giải khác nhau sẽ được phiên ra thành 1 chuẩn, có thể là ID)
- **Lọc sâu ở vòng trong:** Việc tinh lọc khắt khe sẽ được đẩy cho các lớp sau (Reranking/Cross-Encoder) xử lý. Tại đây, các cơ chế phức tạp hơn sẽ có thể đánh giá sâu hơn mà không sợ bỏ lỡ nhân tài ở bước lọc thô.

---

## 3. Cơ chế Tính toán sẵn (Pre-calculation)
Hệ thống sẽ hướng tới việc lưu trữ các giá trị tính toán được (Scoring) vào Database để tối ưu hiệu năng:
- **Định kỳ/Sự kiện:** Cập nhật lại điểm số khi có thay đổi từ phía ứng viên (sửa thông tin cá nhân v.v) hoặc phía HR (thay đổi trạng thái tuyển dụng v.v).
- **Trải nghiệm HR:** Đảm bảo khi HR truy cập danh sách, kết quả được hiển thị nhanh chóng từ dữ liệu đã tính sẵn thay vì chờ đợi AI xử lý thời gian thực cho hàng ngàn hồ sơ.

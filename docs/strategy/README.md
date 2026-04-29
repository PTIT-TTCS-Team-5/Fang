# Tài Liệu Strategy

Thư mục này chứa tài liệu định hướng kiến trúc và các quyết định kỹ thuật ở mức hệ thống.

Phạm vi chính:
- Nguyên tắc thiết kế và ràng buộc kỹ thuật.
- Phân tích trade-off giữa các phương án.
- Chính sách fallback, quality gate, token budget, và tiêu chí vận hành.
- Liên kết tới tài liệu nghiên cứu làm căn cứ kỹ thuật.

Nguyên tắc biên soạn:
- Nêu rõ bối cảnh, quyết định, lý do chọn và tác động.
- Ưu tiên tính nhất quán giữa kiến trúc, cấu hình và triển khai thực tế.
- Mỗi quyết định quan trọng cần có tham chiếu nghiên cứu hoặc benchmark liên quan.

Tài liệu trong thư mục này trả lời câu hỏi: "Tại sao chọn cách này?"

# NOTE by Hưng: ở lần làm việc tới về NMAIex, cần để ý về tác động lên FANG core hiện tại

1. Model routing có bắt buộc can thiệp FANG không
Không bắt buộc ở giai đoạn đầu. Có 3 mức:
1. Không can thiệp FANG core
* Làm policy ở lớp NMAI extension hoặc runner riêng.
* Ví dụ: theo từng run profile, chọn modelMode nào được phép gọi, giới hạn retry, giới hạn số vòng sửa dữ liệu.
* Ưu điểm: an toàn, bật tắt nhanh, không ảnh hưởng API contract đang chạy.
2. Can thiệp nhẹ, tương thích ngược
* Thêm cờ cấu hình để giới hạn trần tier theo workload.
* Ví dụ: synthetic generation chỉ cho phép nhóm Lite trừ khi vượt ngưỡng lỗi.
* Ưu điểm: kiểm soát chi phí tốt hơn nhưng vẫn ít rủi ro.
3. Can thiệp sâu vào orchestrator
* Sửa logic fallback/pro tier gate theo policy mới.
* Ưu điểm: tối ưu mạnh nhất.
* Nhược điểm: rủi ro regression cao, không nên làm ngay khi bạn còn tối ưu ngân sách.
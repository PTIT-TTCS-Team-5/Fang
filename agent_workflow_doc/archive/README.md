# FANG Next Phase - Historical Workflow Archives

Thư mục này chứa các tài liệu workflow, kế hoạch thực thi (implementation plans) và checklist nhiệm vụ (task trackers) đã được hoàn thành trong các giai đoạn trước của dự án FANG.

> [!NOTE]
> Tất cả các nhiệm vụ tại đây đều đã được hoàn thành và gán nhãn thực tế thành công. Chúng được lưu trữ tại đây nhằm mục đích tham khảo lịch sử (historical reference) và tránh gây nhầm lẫn cho các mô hình AI hoặc thành viên nhóm phát triển sau này về các công việc còn mở.

## Danh sách tài liệu lưu trữ (Archived Files)

### 1. Nhiệm vụ & Checklist (Task Trackers)
- **[task_data_set.md](task_data_set.md)**: Checklist quy trình xây dựng và gán nhãn bộ dữ liệu mẫu (synthetic data) gồm 500 ứng viên & 20 công việc.
- **[task_nmaiex_tuning.md](task_nmaiex_tuning.md)**: Giai đoạn 1 của tối ưu hóa Hyperparameters cho công cụ xếp hạng (Optuna tuning).
- **[task_nmaiex_tuning_6h.md](task_nmaiex_tuning_6h.md)**: Giai đoạn 2 của tối ưu hóa với ngân sách 6 tiếng+, phân bổ ứng viên ngẫu nhiên thông minh và mở khóa Chat RAG.

### 2. Kế hoạch thực thi (Implementation Plans)
- **[implementation_plan_data_set.md](implementation_plan_data_set.md)**: Kế hoạch sinh dữ liệu giả lập chất lượng cao bằng Gemini API & 9Router proxy.
- **[implementation_plan_nmaiex_tuning.md](implementation_plan_nmaiex_tuning.md)**: Kế hoạch tối ưu hóa các tham số tính điểm của thuật toán so khớp Job ↔ Candidate.
- **[implementation_plan_nmaiex_tuning_6h.md](implementation_plan_nmaiex_tuning_6h.md)**: Kế hoạch chạy full-scale tuning 6 tiếng+ và kịch bản phân bổ ứng viên.

### 3. Prompt giao việc tier 2 đã hoàn tất

Các prompt trong [tier2_completed_tasks/](tier2_completed_tasks/) đã được dùng để giao việc, đã có kết quả và đã được tier 1 review/cleanup. Chúng chỉ còn giá trị lịch sử, không phải task đang mở.

---
*Cập nhật gần nhất vào ngày: 2026-05-23.*

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

### 4. NMAIex Implementation Historical (archived via P0-C)

Các tài liệu NMAIex gốc — đã hoàn thành hoặc đã lỗi thời. Chứa một số thông tin conflict với quyết định mới (ví dụ: clip score, OpenAI embedding, NMAIex extension). Giữ nguyên content để tham khảo lịch sử, **không phải truth source hiện tại**.

- **[[NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md]([NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md)**: Low-level design cho NMAIex (hoàn thành). Một số thiết kế đã thay đổi: embedding → Gemini, clip → disabled.
- **[[NMAIex]_DOC_UPDATE_INSTRUCTIONS.md]([NMAIex]_DOC_UPDATE_INSTRUCTIONS.md)**: Hướng dẫn cập nhật docs sau Phase 4 NMAIex (lỗi thời — NMAIex giờ là module chính thức).
- **[[NMAIex]_TASK_CHECKLIST_BACKEND.md]([NMAIex]_TASK_CHECKLIST_BACKEND.md)**: Checklist backend NMAIex (hoàn thành, mọi items đã [x]).
- **[[NMAIex]_TASK_CHECKLIST_FRONTEND.md]([NMAIex]_TASK_CHECKLIST_FRONTEND.md)**: Checklist frontend NMAIex (chưa hoàn thành tất cả, nhưng đã đủ cho MVP — archive theo quyết định P0-A triage).

---
*Cập nhật gần nhất vào ngày: 2026-05-23.*

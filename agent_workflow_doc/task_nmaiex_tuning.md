# Tasks: Finetuning Ranking Engine NMAIex

- [x] **1. Chuẩn bị Thư mục & Cài đặt Thư viện**
  - [x] Khởi tạo thư mục `nmaiex_tuning/` và cấu hình Gitignore
  - [x] Cài đặt thư viện `optuna` vào virtual environment

- [x] **2. Database Backfill (Zero API Cost)**
  - [x] Tạo file `nmaiex_tuning/backfill_candidate_skills.py`
  - [x] Thực hiện logic Exact String Matching cho 500 CVs
  - [x] Thực hiện logic nhúng Vector cho các kỹ năng unmatched (Tầng 2)
  - [x] Chạy kiểm chứng để đảm bảo DB được nạp 100%

- [x] **3. Xây dựng Ground-Truth (LLM Batching & Pydantic)**
  - [x] Tạo file `nmaiex_tuning/build_ground_truth.py`
  - [x] Cấu hình gọi qua `9Router` với Pydantic schema (10 CVs/request)
  - [x] Chạy gán nhãn cho 2,000 cặp và lưu cache `nmaiex_tuning/output/ground_truth_matrix.json` (Hoàn thành 2,000/2,000 cặp)

- [x] **4. Cấu hình & Tắt Score Clipping**
  - [x] Sửa cấu hình `NMAIEX_ENABLE_SCORE_CLIP` trong `app/core/nmaiex_config.py` và `.env.nmaiex`
  - [x] Sửa logic clip điểm trong `app/services/nmaiex_ranking_service.py`
  - [x] Cập nhật Frontend miCareer-mini để hiển thị điểm thô ở Dev mode

- [/] **5. Tối Ưu Hóa Bằng Optuna (50,000 Trials)**
  - [x] Tạo file `nmaiex_tuning/tune_nmaiex_hyperparams.py`
  - [/] Cài đặt Study J→C (MRR) và C→J (nDCG@10) (Hoàn thành Phase 1 J→C)
  - [/] Chạy tối ưu hóa trên CPU và xuất bộ tham số tối ưu ra `.env.nmaiex` (Đã lưu optimal parameters Phase 1)

- [ ] **6. Nghiệm Thu & Đánh Giá**
  - [ ] Khởi động lại hệ thống và gọi API ranking thực tế để nghiệm thu
  - [ ] Hoàn thành tài liệu Walkthrough

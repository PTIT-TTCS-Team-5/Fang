# Tasks: Tối Ưu Ranking NMAIex 6 Tiếng + Phân Bổ Ứng Viên

- [x] **1. Phân Bổ Ứng Viên Thông Minh & Mở Khóa Chat RAG**
  - [x] Viết `scripts/redistribute_applications.py`:
    - [x] Tính điểm so khớp 500 candidates với 20 Job Postings (catalog skills + title keywords + seniority)
    - [x] **Giữ nguyên tất cả 500 applications ở Job 1** (trường hợp đặc biệt, đánh dấu ★)
    - [x] Cho mỗi candidate, INSERT **3 JOBAPPLICATION mới** cho top-3 jobs phù hợp nhất (loại trừ Job 1)
    - [x] Nhân bản đầy đủ `CVPARSED` (rawText, parsedJson, parserVer) → **1,500 records**
    - [x] Nhân bản tất cả `AIDOCUMENTCHUNK` (content, chunkIndex, tokenCount, metadata, **embedding halfvec(1536)**) → **7,401 records**
    - [x] INSERT `AIINDEXJOB` với `stat='SUCCESS'` → **2,000 records** (500 gốc + 1,500 mới)
  - [x] Chạy script thành công (13 giây, tổng 2,000 applications phân bổ trên 18 jobs)
  - [x] Xác nhận Chat RAG mở khóa trên giao diện

- [x] **2. Nâng Cấp Script Tuning (Resume + 6h Budget)**
  - [x] Thêm CLI arguments `--resume` và `--trials-per-phase`
  - [x] Logic `--resume`: KHÔNG xóa SQLite DB, đếm trials hiện có, chạy tiếp phần còn thiếu
  - [x] Phase 1 (J→C MRR): resume từ 25,000 trials → chạy thêm 75,000 = tổng 100,000
  - [x] Phase 2 (C→J nDCG@10): chạy 75,000 trials (resume nếu bị ngắt giữa chừng)
  - [x] Tự động backup DB + .env trước khi chạy
  - [x] Nâng cấp Sampler: `TPESampler(n_startup_trials=1000, multivariate=True, group=True)`
  - [ ] Kiểm tra resume hoạt động đúng

- [ ] **3. Backup An Toàn + Khởi Chạy Tuning Qua Đêm**
  - [ ] Khởi chạy: `venv\Scripts\python nmaiex_tuning/tune_nmaiex_hyperparams.py --resume --trials-per-phase 75000`
  - [ ] Theo dõi vài trăm trials đầu để xác nhận tốc độ
  - [ ] Để máy chạy xuyên đêm (~5 tiếng)

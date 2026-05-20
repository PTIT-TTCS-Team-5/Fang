# Kế Hoạch Triển Khai: Tối Ưu Ranking NMAIex 6 Tiếng Qua Đêm + Phân Bổ Ứng Viên

## Tổng Quan

Nâng cấp pipeline tối ưu hóa ranking NMAIex để chạy khít **6 tiếng liên tục** qua đêm, đồng thời phân bổ thông minh 500 ứng viên vào 20 công việc (giữ nguyên Job 1 làm trường hợp đặc biệt) và mở khóa Chat RAG.

---

## Điểm Cần Duyệt

> [!IMPORTANT]
> **Thay đổi chiến lược so với phiên bản trước:**
> 1. **Phase 1 KHÔNG bỏ qua** — tiếp tục (resume) từ 25,000 trials hiện có, chạy thêm 75,000 trials mới.
> 2. **Hai phase chia đều** — mỗi phase nhận đúng **75,000 trials mới**, tổng 150,000 trials mới.
> 3. **Job 1 giữ nguyên** — tất cả 500 ứng viên vẫn có đơn ứng tuyển vào Job 1. Ngoài ra, mỗi ứng viên được ghép thêm **top-3 công việc phù hợp nhất** qua INSERT mới.
> 4. **Sao chép đầy đủ CV** — mỗi đơn ứng tuyển mới sẽ nhân bản `CVPARSED` + tất cả `AIDOCUMENTCHUNK` (bao gồm vector embeddings) từ đơn gốc ở Job 1.

---

## Phân Tích Toán Học: Budget 6 Tiếng

### Dữ kiện thực nghiệm từ Phase 1

| Thông số | Giá trị |
|---|---|
| Số trials hoàn thành | 25,000 |
| Thời gian chạy | 2,877.76 giây |
| Throughput tổng hợp | **8.687 trials/giây** |
| GT Matrix | 2,000 cặp (20 jobs × ~100 candidates/job) |
| Unique candidates trong GT | 497 |
| Pairs per candidate | ~4 |

### Phân tích độ phức tạp từng Phase

Mỗi trial gọi hàm tính metric trên **2,000 cặp dữ liệu đã precompute**. Chi tiết:

**Phase 1 — `compute_mrr()` (J→C):**
1. Vòng lặp tính điểm: 2,000 iterations, mỗi iteration ~6 phép toán số học
2. Gom nhóm theo Job: 20 nhóm, mỗi nhóm ~100 phần tử
3. Sắp xếp: 20 × sort(100) ≈ 20 × 100·log₂(100) ≈ **13,288 comparisons**
4. Tìm relevant đầu tiên: 20 × scan(≤100) ≈ **2,000 iterations**
5. **Tổng cộng: ~17,288 operations/trial**

**Phase 2 — `compute_ndcg_at_k()` (C→J):**
1. Vòng lặp tính điểm: 2,000 iterations, mỗi iteration ~8 phép toán (thêm lang penalty, salary, title)
2. Gom nhóm theo Candidate: 497 nhóm, mỗi nhóm ~4 phần tử
3. Sắp xếp: 497 × sort(4) ≈ 497 × 4·log₂(4) ≈ **3,976 comparisons**
4. Tính DCG top-10: 497 × min(4,10) × (pow + log₂) ≈ **3,976 float ops**
5. Tính IDCG: 497 × sort(4) + 497 × 4 × (pow + log₂) ≈ **7,952 operations**
6. **Tổng cộng: ~17,904 operations/trial**

### Kết luận về tốc độ

| Chỉ số | Phase 1 (MRR) | Phase 2 (nDCG@10) |
|---|---|---|
| Operations/trial | ~17,288 | ~17,904 |
| Chênh lệch | baseline | **+3.6%** |
| Throughput ước tính | 8.687 trials/s | **8.375 trials/s** |

> [!NOTE]
> Kết quả phân tích cho thấy Phase 2 chỉ chậm hơn Phase 1 khoảng **3.6%** (không phải 10% hay 25% như ước lượng ban đầu). Lý do: mặc dù số nhóm candidates lớn hơn (497 vs 20), nhưng kích thước mỗi nhóm lại rất nhỏ (4 jobs/candidate vs 100 candidates/job). Sorting 497 nhóm × 4 phần tử nhanh hơn đáng kể so với sorting 20 nhóm × 100 phần tử.

### Tính toán phân bổ thời gian

Thêm **2% overhead** cho SQLite B-Tree scaling khi DB tăng từ 23.7 MB lên ~150 MB:

$$\text{Phase 2 throughput} = 8.687 \times (1 - 0.036 - 0.02) = 8.687 \times 0.944 = \mathbf{8.201 \text{ trials/s}}$$

**Chia đều 75,000 trials mới cho mỗi phase:**

| Phase | Trials mới | Throughput | Thời gian | Cộng dồn |
|---|---|---|---|---|
| Precomputation | — | — | ~2 phút | 2 phút |
| Phase 1 (continue MRR) | 75,000 | 8.687 t/s | **143.8 phút** (2h 24m) | 2h 26m |
| Phase 2 (nDCG@10) | 75,000 | 8.201 t/s | **152.4 phút** (2h 32m) | 4h 58m |
| **Tổng** | **150,000** | | | **~5 tiếng** |

**Safety buffer: ~60 phút** (dư 1 tiếng cho các yếu tố bất ngờ).

### Kết quả sau khi chạy xong

| Phase | Trials tổng cộng | Metric |
|---|---|---|
| Phase 1 (J→C) | 25,000 + 75,000 = **100,000** | MRR |
| Phase 2 (C→J) | **75,000** | nDCG@10 |

---

## Thay Đổi Cụ Thể

### 1. Nâng cấp Script Tuning với Resume + CLI

#### [MODIFY] [tune_nmaiex_hyperparams.py](file:///c:/Users/os/Desktop/cur_prj/Fang/nmaiex_tuning/tune_nmaiex_hyperparams.py)

**1.1 Thêm CLI Arguments:**
```python
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--resume", action="store_true", help="Tiếp tục từ SQLite DB hiện tại")
parser.add_argument("--trials-per-phase", type=int, default=75000, help="Số trials MỚI cho mỗi phase")
args = parser.parse_args()
```

**1.2 Tự động Backup trước khi chạy:**
```python
backup_dir = DB_DIR / "backup"
backup_dir.mkdir(exist_ok=True)
if db_file.exists():
    shutil.copy2(db_file, backup_dir / f"nmaiex_tuning_{timestamp}.db")
if ENV_NMAIEX_PATH.exists():
    shutil.copy2(ENV_NMAIEX_PATH, backup_dir / f".env.nmaiex_{timestamp}")
```

**1.3 Logic Resume — Không xóa DB nếu `--resume`:**
```python
if not args.resume and db_file.exists():
    db_file.unlink()  # Chỉ xóa khi KHÔNG resume
```

**1.4 Phase 1 — Tiếp tục (Resume) từ trials hiện có:**
```python
study_jc = optuna.create_study(study_name="jc_study", ..., load_if_exists=True)
existing_jc = len(study_jc.trials)
remaining_jc = max(0, args.trials_per_phase - existing_jc) if args.resume else args.trials_per_phase
# Nếu remaining_jc == 0 → Phase 1 đã xong, đọc alpha từ best_params
# Nếu remaining_jc > 0 → chia cho workers và tiếp tục optimize
```

**1.5 Phase 2 — Logic tương tự:**
```python
study_cj = optuna.create_study(study_name="cj_study", ..., load_if_exists=True)
existing_cj = len(study_cj.trials)
remaining_cj = max(0, args.trials_per_phase - existing_cj) if args.resume else args.trials_per_phase
```

**1.6 Nâng cấp Sampler:**
```python
optuna.samplers.TPESampler(
    n_startup_trials=1000,
    multivariate=True,
    group=True,
    seed=42
)
```

---

### 2. Phân Bổ Ứng Viên Thông Minh + Mở Khóa Chat RAG

#### [MODIFY] [redistribute_applications.py](file:///c:/Users/os/Desktop/cur_prj/Fang/scripts/redistribute_applications.py)

**Thay đổi cốt lõi so với phiên bản hiện tại:**

| Tiêu chí | Phiên bản cũ | Phiên bản mới |
|---|---|---|
| Job 1 | UPDATE jobPostId → mất Job 1 | **Giữ nguyên** Job 1 làm trường hợp đặc biệt |
| Số job ghép | Top-1 | **Top-3** |
| Cơ chế | UPDATE trực tiếp | **INSERT mới** + nhân bản CVPARSED + chunks |
| AIINDEXJOB | Upsert | **INSERT only** (bảng hiện đang rỗng) |

**Quy trình cho mỗi candidate:**
1. Giữ nguyên JOBAPPLICATION hiện tại (Job 1)
2. Tính điểm so khớp với tất cả 20 jobs
3. Chọn **top-3 jobs phù hợp nhất** (loại trừ Job 1 nếu đã có)
4. Cho mỗi job trong top-3:
   - INSERT JOBAPPLICATION mới (candidateId, jobPostId, cvSnapUrl copy từ gốc)
   - INSERT CVPARSED mới (copy rawText, parsedJson, parserVer từ gốc)
   - INSERT tất cả AIDOCUMENTCHUNK (copy content, chunkIndex, tokenCount, metadata, **embedding** từ gốc)
5. INSERT AIINDEXJOB `stat='SUCCESS'` cho **tất cả** applications (cả Job 1 gốc lẫn 3 cái mới)

**Dự tính khối lượng dữ liệu:**
- Đơn ứng tuyển mới: 500 × 3 = **1,500 records**
- CVPARSED mới: **1,500 records**
- Chunks mới (ước ~5 chunks/CV): **~7,500 records** (mỗi record chứa halfvec(1536))
- AIINDEXJOB: 500 (Job 1 gốc) + 1,500 (mới) = **2,000 records**

---

## Kế Hoạch Xác Nhận

### Tự động
1. **Phân bổ ứng viên:**
   ```powershell
   $env:PYTHONPATH="."; venv\Scripts\python scripts/redistribute_applications.py
   ```
   Kiểm tra: bảng thống kê phân bổ hiển thị đa dạng trên 20 jobs. Job 1 vẫn có đầy đủ 500 applications gốc.

2. **Tuning qua đêm:**
   ```powershell
   venv\Scripts\python nmaiex_tuning/tune_nmaiex_hyperparams.py --resume --trials-per-phase 75000
   ```
   Kiểm tra: Phase 1 nhận diện 25,000 trials cũ và chạy thêm 75,000. Phase 2 chạy 75,000 từ đầu.

3. **Test Resume:** Ngắt script giữa chừng (Ctrl+C), chạy lại lệnh trên → script đếm trials đã hoàn thành và chạy tiếp phần còn thiếu.

### Thủ công
- Kiểm tra giao diện miCareer-mini: candidates xuất hiện ở nhiều job khác nhau.
- Chat RAG hoạt động cho candidates (không còn hiển thị `%`).

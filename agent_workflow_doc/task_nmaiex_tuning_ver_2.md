# Task: Thực Thi Pipeline Mở Rộng Dữ Liệu & Tuning NMAIex v2

> **Dành cho Agent thực thi** — Đọc kỹ toàn bộ file này trước khi bắt đầu bất kỳ bước nào.
> **Tài liệu tham chiếu chính**: [implementation_plan_nmaiex_tuning_ver_2.md](file:///c:/Users/os/Desktop/cur_prj/Fang/agent_workflow_doc/implementation_plan_nmaiex_tuning_ver_2.md)

---

## 📋 Bối Cảnh & Trạng Thái Hiện Tại

### Đã hoàn thành (DONE — KHÔNG cần làm lại)
- [x] Sửa [nmaiex_config.py](file:///c:/Users/os/Desktop/cur_prj/Fang/app/core/nmaiex_config.py): Tách `skill_alpha_jc` / `skill_alpha_cj`, thêm `cj_weight_salary`.
- [x] Sửa [nmaiex_ranking_service.py](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/nmaiex_ranking_service.py): Loại bỏ `base_weight = 0.20` hardcoded, áp dụng dynamic weight fusion.
- [x] Sửa [personas.py](file:///c:/Users/os/Desktop/cur_prj/Fang/synthetic_data/personas.py): 12 personas đầy đủ + Extended Seeded Hybrid Manifest (`generate_manifest(1000)` hoạt động, Zone 1 bất biến đã xác nhận).
- [x] Sửa [prompts.py](file:///c:/Users/os/Desktop/cur_prj/Fang/synthetic_data/prompts.py): JSON output mode, Pydantic validation, 6.67% out-of-catalog skills.
- [x] Sửa [run_pipeline.py](file:///c:/Users/os/Desktop/cur_prj/Fang/synthetic_data/run_pipeline.py): Thêm `--start-index` CLI arg cho `write-cvs`.
- [x] Sửa [build_ground_truth.py](file:///c:/Users/os/Desktop/cur_prj/Fang/nmaiex_tuning/build_ground_truth.py): 150 candidates/job → 3000 pairs.
- [x] Sửa [tune_nmaiex_hyperparams.py](file:///c:/Users/os/Desktop/cur_prj/Fang/nmaiex_tuning/tune_nmaiex_hyperparams.py): Search space mở rộng (alpha_jc, alpha_cj, cj_w_salary).

### Trạng thái Database hiện tại
- PostgreSQL đang chạy cục bộ, chứa: **500 candidates**, **20 jobs**, **~7k embedded vectors**, **2000 cặp Ground Truth**.
- File cache CVs: `synthetic_data/output/cvs/batch_001.json` → `batch_100.json` — **GIỮ NGUYÊN TUYỆT ĐỐI**.
- Optuna Phase 2 cũ đã kết thúc. Sẵn sàng thực thi pipeline mới.

---

## ⚠️ QUY TẮC BẮT BUỘC CHO AGENT

> [!CAUTION]
> **TUYỆT ĐỐI KHÔNG** gộp 4 lệnh dưới đây vào một script rồi chạy tự động. Mỗi lệnh phải được:
> 1. **Thực thi riêng lẻ** theo đúng thứ tự từng bước.
> 2. **Chờ xác nhận từ người dùng** sau mỗi bước trước khi tiếp tục.
> 3. **Kiểm tra output / log** sau mỗi bước và báo cáo kết quả trước khi chuyển sang bước tiếp.

> [!IMPORTANT]
> **Không được xóa hoặc ghi đè** các file sau:
> - `synthetic_data/output/cvs/batch_001.json` → `batch_100.json` (500 CVs cũ)
> - `nmaiex_tuning/output/ground_truth_matrix.json` (backup trước khi xóa)
> - `nmaiex_tuning/output/nmaiex_tuning.db` (Optuna study cũ — backup trước khi xóa)

---

## 🗂️ Checklist Thực Thi (Từng Bước)

### [ ] BƯỚC 0 — Kiểm tra trạng thái hệ thống (Pre-flight Check)

Trước khi bắt đầu, thực thi và báo cáo kết quả của lệnh sau:

```powershell
# Kiểm tra số candidates hiện có trong DB
venv\Scripts\python -c "
import asyncio
from app.core.database import db, acquire_conn

async def check():
    await db.connect()
    async with acquire_conn() as conn:
        count = await conn.fetchval('SELECT COUNT(*) FROM CANDIDATE')
        jobs  = await conn.fetchval('SELECT COUNT(*) FROM JOBPOSTING')
        apps  = await conn.fetchval('SELECT COUNT(*) FROM JOBAPPLICATION')
        print(f'Candidates: {count}, Jobs: {jobs}, Applications: {apps}')
    await db.disconnect()

asyncio.run(check())
"
```

**Kết quả mong đợi**: `Candidates: 500, Jobs: 20, Applications: ~1500`

Nếu số liệu khác xa → **dừng lại và hỏi người dùng** trước khi tiếp tục.

---

### [ ] BƯỚC 1 — Sinh 500 CVs mới (LLM Generation)

> [!NOTE]
> Bước này gọi LLM qua 9Router để sinh 500 CVs mới (index 500-999). 500 CVs cũ (batch_001-100) sẽ được **cache hit 100%** — không tốn API token. Ước tính thời gian: ~15-30 phút tùy rate limit.

**Lệnh thực thi:**
```powershell
venv\Scripts\python -m synthetic_data.run_pipeline generate-cvs --total 1000
```

**Giám sát trong khi chạy:**
- Log sẽ hiển thị từng batch được xử lý. Batch `batch_001` → `batch_100` sẽ log `Cache hit` (không gọi LLM).
- Batch `batch_101` → `batch_200` sẽ gọi LLM và log `Generated batch_XXX`.
- Nếu gặp lỗi `429 Rate Limit`: script tự retry — **không cần can thiệp**.
- Nếu gặp lỗi `Pydantic ValidationError` liên tục (>3 lần/batch): dừng lại và báo cáo.

**Xác minh sau khi hoàn thành:**
```powershell
# Kiểm tra số file batch mới được tạo
Get-ChildItem synthetic_data\output\cvs\batch_1*.json | Measure-Object | Select-Object Count
Get-ChildItem synthetic_data\output\cvs\batch_2*.json | Measure-Object | Select-Object Count
```
**Kết quả mong đợi**: Tổng 100 file mới (batch_101 → batch_200). File batch_001-100 timestamp **không thay đổi**.

> **[DỪNG]** — Báo cáo kết quả cho người dùng và chờ xác nhận trước khi tiếp tục BƯỚC 2.

---

### [ ] BƯỚC 2 — Ghi 500 CVs mới vào Database

> [!WARNING]
> Chỉ thực thi bước này sau khi BƯỚC 1 hoàn thành thành công và đủ 100 file batch mới. Cờ `--start-index 500` đảm bảo chỉ ghi index 500-999, **bảo toàn hoàn toàn 500 candidates cũ**.

**Lệnh thực thi:**
```powershell
venv\Scripts\python -m synthetic_data.run_pipeline write-cvs --total 1000 --start-index 500
```

**Giám sát trong khi chạy:**
- Log sẽ hiển thị `skipped=500` (500 CVs cũ bị bỏ qua) và `written=500` khi hoàn thành.
- Mỗi CV được ghi kèm embedding (tốn ~0.5-1 giây/CV do embed chunks). Ước tính: ~10-15 phút.
- Nếu gặp `duplicate key` error: dừng ngay và báo cáo — đây là dấu hiệu `start-index` không hoạt động đúng.

**Xác minh sau khi hoàn thành:**
```powershell
venv\Scripts\python -c "
import asyncio
from app.core.database import db, acquire_conn

async def check():
    await db.connect()
    async with acquire_conn() as conn:
        count = await conn.fetchval('SELECT COUNT(*) FROM CANDIDATE')
        print(f'Total candidates in DB: {count}')
        # Kiem tra khong co duplicate
        dup = await conn.fetchval('SELECT COUNT(*) FROM (SELECT fullname, COUNT(*) as c FROM CANDIDATE GROUP BY fullname HAVING COUNT(*) > 1) t')
        print(f'Duplicate names: {dup}')
    await db.disconnect()

asyncio.run(check())
"
```
**Kết quả mong đợi**: `Total candidates in DB: 1000`, `Duplicate names: 0`

> **[DỪNG]** — Báo cáo kết quả cho người dùng và chờ xác nhận trước khi tiếp tục BƯỚC 3.

---

### [ ] BƯỚC 3 — Phân bổ ứng tuyển Idempotent

> [!NOTE]
> Script `redistribute_applications.py` cần được kiểm tra xem đã có logic idempotent (kiểm tra tồn tại application trước khi insert) chưa. Nếu chưa có → **phải thêm trước khi chạy** (xem phần "Việc cần làm của Agent" bên dưới).

**Kiểm tra trước khi chạy — Agent đọc file này:**

```powershell
# Doc doan logic chinh de xac nhan co kiem tra ton tai khong
Select-String -Path scripts\redistribute_applications.py -Pattern "SELECT 1 FROM JOBAPPLICATION" -SimpleMatch
```

Nếu không tìm thấy pattern → **Agent cần sửa `redistribute_applications.py`** để thêm idempotent check (xem Implementation Plan Section 2, "Idempotent Applications Distribution").

**Lệnh thực thi (sau khi xác nhận idempotent OK):**
```powershell
venv\Scripts\python scripts\redistribute_applications.py
```

**Giám sát trong khi chạy:**
- Script phân bổ mỗi candidate vào top-3 jobs phù hợp và tạo embeddings cho AIINDEXJOB.
- Ước tính: ~20-40 phút cho 500 candidates mới.
- Các candidates cũ (index 0-499) sẽ bị **skip** nhờ idempotent check.

**Xác minh sau khi hoàn thành:**
```powershell
venv\Scripts\python -c "
import asyncio
from app.core.database import db, acquire_conn

async def check():
    await db.connect()
    async with acquire_conn() as conn:
        apps  = await conn.fetchval('SELECT COUNT(*) FROM JOBAPPLICATION')
        rag_ok = await conn.fetchval(\"SELECT COUNT(*) FROM AIINDEXJOB WHERE status = 'SUCCESS'\")
        print(f'Total applications: {apps}')
        print(f'RAG SUCCESS count: {rag_ok}')
    await db.disconnect()

asyncio.run(check())
"
```
**Kết quả mong đợi**: `Total applications: ~3000` (1000 candidates × 3 jobs), `RAG SUCCESS: ~3000`

> **[DỪNG]** — Báo cáo kết quả cho người dùng và chờ xác nhận trước khi tiếp tục BƯỚC 4.

---

### [ ] BƯỚC 4A — Backup & Rebuild Ground Truth (3000 cặp)

> [!CAUTION]
> Bước này xóa Ground Truth matrix cũ (2000 cặp). Phải backup trước.

**Bước 4A.1 — Backup Ground Truth cũ:**
```powershell
Copy-Item nmaiex_tuning\output\ground_truth_matrix.json `
          nmaiex_tuning\output\ground_truth_matrix_backup_2000pairs.json -ErrorAction Stop
Write-Host "Backup OK: ground_truth_matrix_backup_2000pairs.json"
```

**Bước 4A.2 — Xóa cache cũ:**
```powershell
Remove-Item nmaiex_tuning\output\ground_truth_matrix.json -ErrorAction SilentlyContinue
Write-Host "Old ground truth removed."
```

**Bước 4A.3 — Sinh 3000 cặp GT mới:**
```powershell
venv\Scripts\python nmaiex_tuning\build_ground_truth.py
```

**Giám sát:**
- Script sample 150 candidates/job từ toàn bộ pool 1000 ứng viên → 20 jobs × 150 = 3000 cặp.
- Dùng LLM-as-Judge (Gemini Flash Lite) để đánh giá từng cặp (score 0-4).
- Ước tính: ~45-90 phút (có cơ chế resume nếu bị interrupt).
- Nếu gặp `429`: script tự retry sau 10-15 giây.

**Xác minh:**
```powershell
venv\Scripts\python -c "
import json
data = json.loads(open('nmaiex_tuning/output/ground_truth_matrix.json', encoding='utf-8').read())
print(f'Ground Truth pairs: {len(data)}')
scores = [v[\"score\"] for v in data.values()]
from collections import Counter
print('Score distribution:', dict(sorted(Counter(scores).items())))
"
```
**Kết quả mong đợi**: `Ground Truth pairs: 3000`, score distribution hợp lý (không quá tập trung vào 1 score).

> **[DỪNG]** — Báo cáo kết quả cho người dùng và chờ xác nhận trước khi tiếp tục BƯỚC 4B.

---

### [ ] BƯỚC 4B — Khởi động Optuna Tuning v2

> [!CAUTION]
> Bước này xóa Optuna study cũ. Phase 1 cũ (~99k trials) sẽ bị xóa. Người dùng đã xác nhận reset.

**Bước 4B.1 — Backup Optuna study cũ:**
```powershell
Copy-Item nmaiex_tuning\output\nmaiex_tuning.db `
          nmaiex_tuning\output\nmaiex_tuning_backup_phase2_old.db -ErrorAction SilentlyContinue
Write-Host "Backup OK."
```

**Bước 4B.2 — Xóa study cũ:**
```powershell
Remove-Item nmaiex_tuning\output\nmaiex_tuning.db -ErrorAction SilentlyContinue
Write-Host "Old Optuna study removed."
```

**Bước 4B.3 — Khởi động Tuning v2:**
```powershell
venv\Scripts\python nmaiex_tuning\tune_nmaiex_hyperparams.py --trials-per-phase 100000
```

**Giám sát:**
- Phase 1 (J→C): ~3-4 giờ cho 100k trials.
- Phase 2 (C→J): ~3-4 giờ cho 100k trials.
- Tiến trình có thể chạy qua đêm — **không cần agent theo dõi liên tục**.
- Người dùng sẽ paste kết quả Phase 1 + Phase 2 vào chat khi hoàn thành.

> **[DỪNG]** — Báo cáo "Tuning đã được khởi động" cho người dùng. **Không cần chờ kết quả tuning.**

---

## 🔧 Việc Cần Làm Của Agent Trước BƯỚC 3

### Kiểm tra & Vá lỗi `redistribute_applications.py`

File [redistribute_applications.py](file:///c:/Users/os/Desktop/cur_prj/Fang/scripts/redistribute_applications.py) cần có idempotent check. Agent phải:

1. **Đọc** file để tìm vòng lặp chính (nơi insert JOBAPPLICATION).
2. **Kiểm tra** xem có `SELECT 1 FROM JOBAPPLICATION WHERE candidateId = ... AND jobPostId = ...` trước `INSERT` không.
3. **Nếu chưa có** → Thêm vào. Logic mẫu:
   ```python
   # Trước mỗi INSERT JOBAPPLICATION:
   existing = await conn.fetchval(
       "SELECT 1 FROM JOBAPPLICATION WHERE candidateId = $1 AND jobPostId = $2",
       candidate_id, job_post_id
   )
   if existing:
       logger.info(f"Skip: candidate {candidate_id} already applied to job {job_post_id}")
       continue
   # Nếu không có → thực hiện INSERT như bình thường
   ```
4. **Báo cáo** cho người dùng: đã thêm hay đã có sẵn.

---

## 📊 Kết Quả Mong Đợi Sau Khi Hoàn Thành

| Metric | Trước | Sau |
|---|---|---|
| Số Candidates trong DB | 500 | **1000** |
| File batch cache | batch_001-100 | batch_001-200 |
| Số Job Applications | ~1500 | **~3000** |
| Ground Truth pairs | 2000 | **3000** |
| Personas covered | 8 (cũ) | **12 (cũ + 4 niche)** |
| Optuna Search Space | Phase 1 done | **v2 fresh start** |

---

## 🚫 Danh Sách CẤM

- ❌ **KHÔNG** chạy `python scripts/reset_and_seed_db.py` — sẽ xóa toàn bộ 500 candidates cũ.
- ❌ **KHÔNG** chạy `write-cvs` **mà không có** `--start-index 500`.
- ❌ **KHÔNG** xóa `synthetic_data/output/cvs/batch_001.json` → `batch_100.json`.
- ❌ **KHÔNG** gộp nhiều lệnh vào 1 script và chạy tự động mà không có checkpoint.
- ❌ **KHÔNG** chạy BƯỚC 4B trước khi BƯỚC 4A hoàn thành và có đủ 3000 Ground Truth pairs.

---

## 📝 Template Báo Cáo Sau Mỗi Bước

Sau mỗi bước, Agent báo cáo theo format:

```
## Báo Cáo BƯỚC [X]
- Trạng thái: THÀNH CÔNG / LỖI / CẦN XEM XÉT
- Kết quả đo được: [paste số liệu từ lệnh xác minh]
- Log bất thường (nếu có): [paste đoạn log quan trọng]
- Đề xuất: [tiếp tục BƯỚC tiếp / dừng lại vì ...]
```

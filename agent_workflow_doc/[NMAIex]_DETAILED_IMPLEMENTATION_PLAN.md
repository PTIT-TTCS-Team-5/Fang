# [NMAIex] Kế Hoạch Triển Khai Chi Tiết Hệ Thống Xếp Hạng Hai Chiều

> **Ngữ cảnh:** FANG AI Core (FastAPI, PostgreSQL + pgvector, asyncpg) là backend AI xử lý toàn bộ. miCareer-mini là frontend thin-client chỉ gọi API. Hai CSDL song song: `schema_web_core.sql` (dữ liệu tuyển dụng) và `schema_ai_core.sql` (bảng AI: chunk, vector, conversation). DB connection dùng `asyncpg` pool, truy cập qua `acquire_conn()` từ `app/core/database.py`.

Tài liệu này là **bản thiết kế kỹ thuật chi tiết (Low-level Design)** để hiện thực hóa NMAIex trên nền tảng FANG hiện hữu. Cần đối chiếu với [`NMAIex_th_3`] và [`NMAIex_3`] trước khi code.

---

> **[Cập nhật 2026-04-29]** Bổ sung Mục 7 (Strategy C Tiered Skill Matching), Mục 8 (Pydantic Mapper Upgrade), Mục 9 (HR JobPosting Edit — Cascade Impact). Xem chi tiết cuối tài liệu.


## 1. Kiến Trúc Cơ Sở Dữ Liệu (PostgreSQL FANG)

### 1.1. Hiện Trạng Cần Biết Trước Khi Sửa

Rà soát `schema_web_core.sql` và `root_data.sql` hiện tại phát hiện:

| Vấn đề | Tình trạng hiện tại (FANG PostgreSQL) |
|---|---|
| `prov` trong `user`, `COMPANY` | **String tự do** (VARCHAR 100), không FK |
| `workLoc` trong `JOBPOSTING` | **String tự do** (VARCHAR 255) |
| Bảng `REGION`, `PROVINCE` | **Chưa có** — cần tạo mới |
| Bảng `JOBLEVEL`, `JOBCATEGORY` | **Chưa có** — cần tạo mới |
| `cvUrl` trong `CANDIDATE` | **Đã có** (không cần thêm) |
| `cvSnapUrl` trong `JOBAPPLICATION` | **Đã có** (không cần thêm) |
| `SKILL`, `CANDIDATESKILL`, `JOBREQUIREMENT` | **Đã có** trong FANG |

### 1.2. Các Bảng Master Data Mới Cần Tạo

Thêm vào `schema_web_core.sql` (phải đặt **trước** bảng `user` và `COMPANY`):

```sql
-- [NMAIex] Bảng địa lý chuẩn
CREATE TABLE REGION (
  regId   VARCHAR(20)  PRIMARY KEY,
  regName VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE PROVINCE (
  provId      VARCHAR(20)  PRIMARY KEY,   -- Mã viết tắt: HANOI, TPHCM, DANANG, HAIPHONG...
  provName    VARCHAR(100) NOT NULL UNIQUE,
  regId       VARCHAR(20)  NOT NULL,
  mergedFrom  TEXT,                        -- Ghi chú sáp nhập (VD: 'Hải Phòng + Hải Dương')
  FOREIGN KEY (regId) REFERENCES REGION(regId)
);

-- [NMAIex] Bảng cấp bậc và danh mục
CREATE TABLE JOBLEVEL (
  levelId   SERIAL PRIMARY KEY,
  levelName VARCHAR(50) NOT NULL UNIQUE,  -- Intern/Fresher/Junior/Middle/Senior/Lead
  minYears  INT NOT NULL DEFAULT 0,        -- Số năm KN tối thiểu để tính Seniority Penalty
  maxYears  INT,                           -- NULL = không giới hạn trên
  description TEXT
);

CREATE TABLE JOBCATEGORY (
  catId   SERIAL PRIMARY KEY,
  catName VARCHAR(100) NOT NULL UNIQUE,
  description TEXT
);
```

> **Sáp nhập tỉnh thành Việt Nam 2025:** Schema dùng **34 tỉnh/thành sau sáp nhập** theo file `[NMAIex]_PROVINCE_MERGER_GUIDE.md`. Cột `mergedFrom` lưu ghi chú sáp nhập để truy vết. Seed data tham chiếu đúng INSERT trong PROVINCE_MERGER_GUIDE.

### 1.3. Quyết Định N-N: JobLevel và JobCategory

Một `JOBPOSTING` có thể tuyển nhiều cấp độ (VD: "Junior hoặc Middle"). Dùng bảng nối N-N vì: (1) phản ánh thực tế, (2) phục vụ tính `Seniority Gap Penalty` chính xác hơn (penalty thấp nếu ứng viên nằm trong *bất kỳ* level nào được chấp nhận).

```sql
-- [NMAIex] Bảng nối N-N
CREATE TABLE JOB_LEVEL_MAP (
  jobPostId INT NOT NULL,
  levelId   INT NOT NULL,
  PRIMARY KEY (jobPostId, levelId),
  FOREIGN KEY (jobPostId) REFERENCES JOBPOSTING(jobPostId) ON DELETE CASCADE,
  FOREIGN KEY (levelId)   REFERENCES JOBLEVEL(levelId)
);

CREATE TABLE JOB_CATEGORY_MAP (
  jobPostId INT NOT NULL,
  catId     INT NOT NULL,
  PRIMARY KEY (jobPostId, catId),
  FOREIGN KEY (jobPostId) REFERENCES JOBPOSTING(jobPostId) ON DELETE CASCADE,
  FOREIGN KEY (catId)     REFERENCES JOBCATEGORY(catId)
);
```

### 1.4. Cập Nhật Bảng Hiện Có

```sql
-- [NMAIex] Thêm provId FK vào user, COMPANY, JOBPOSTING
-- workLoc giữ nguyên để HIỂN THỊ, provId dùng để FILTER cứng
ALTER TABLE "user"     ADD COLUMN provId VARCHAR(20) REFERENCES PROVINCE(provId);
ALTER TABLE COMPANY    ADD COLUMN provId VARCHAR(20) REFERENCES PROVINCE(provId);
ALTER TABLE JOBPOSTING ADD COLUMN provId VARCHAR(20) REFERENCES PROVINCE(provId);
-- Sau khi migrate xong: DROP COLUMN prov từ user và COMPANY
```

> **Chiến lược migration:** Dữ liệu hiện tại là dữ liệu test, có thể reset. Sẽ DROP + CREATE lại schema thay vì ALTER. File `reset_and_seed_db.py` chạy lại toàn bộ.

---

## 2. Tư Vấn Chiến Lược Billing & Cấu Hình

### 2.1. Phân Tích Ảnh Hưởng Của Việc Tách Bill Cho Mapper

Tác vụ Mapping (chuyển String → ID) bản chất là một bước thuộc Parser (Ingestion Pipeline). Việc chuẩn hóa dữ liệu này giúp cho toàn bộ hệ thống TTCS (tìm kiếm, chatbot RAG) hoạt động chính xác hơn, chứ không chỉ phục vụ riêng NMAIex.


- Thay vì tách key trong code làm gãy kiến trúc, chúng ta sẽ để **2 bộ API Keys** (của TTCS và của NMAIex) ngay trong file `.env` gốc của dự án.
- Khi làm việc ở context của NMAIex, chỉ cần comment bộ key của TTCS và uncomment bộ key của NMAIex. TTCS/FANG sẽ tự động dùng key NMAIex mà không hề nhận ra sự khác biệt.
- **Mapper (Parser):** Hoàn toàn tái sử dụng `invoke_generation("auto-lite")` cực kỳ robust. Không cần code thêm một dòng LLM wrapper nào.
- File `.env.nmaiex` giờ đây sẽ cực kỳ sạch sẽ: **chỉ chứa các tham số công thức thuật toán** (Weights, Limit, K, Storage). Không chứa LLM Keys. Mọi thứ liên quan đến LLM Keys quy về một mối là `.env`.

### 2.2. File `.env.nmaiex`

```env
# ============================================================
# [NMAIex] Environment — NMAIex Ranking System
# KHÔNG COMMIT FILE NÀY lên Git (đã có trong .gitignore)
# ============================================================

# --- API Keys LLM ---
# LƯU Ý: KHÔNG đặt API Keys ở đây. LLM Keys được quản lý linh hoạt tại `.env` gốc
# bằng cách comment/uncomment 2 bộ keys (TTCS vs NMAIex) khi cần test/bill riêng.

# --- Cloud Storage (Cloudinary dùng CHUNG cho TTCS và NMAIex) ---
# Account Cloudinary là tài khoản chung. Mỗi project upload vào folder riêng.
# Thư mục đã tạo sẵn trên Cloudinary Home: Home/ttcs và Home/nmaiex
# CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET, CLOUDINARY_UPLOAD_FOLDER → đặt tại .env gốc
# Thay đổi giá trị CLOUDINARY_UPLOAD_FOLDER khi switch project (ttcs ↔ nmaiex)
# Không cần khai báo riêng ở .env.nmaiex vì NMAIex là phần của AI layer hỗ trợ

# --- Static Weights Giai Đoạn 1 (không Calibration) ---
# LƯU Ý: Tổng w_rrf + w_skill < 1 là CÓ CHỦ Ý.
#
# TẠI SAO CẦN CLIP final_score VỀ [0, 1]?
# ─────────────────────────────────────────────────────────────────────
# Công thức: final_score = w_rrf * rrf_score + w_skill * skill_overlap - penalty
#
# Vấn đề phía dưới (âm): penalty = penalty_coef * gap có thể rất lớn khi ứng
# viên lệch nhiều cấp bậc so với yêu cầu. Kết quả có thể < 0, vô nghĩa về
# mặt điểm xếp hạng (không thể hiển thị % âm cho HR).
#
# Vấn đề phía trên (> 1): Dù tổng weights < 1 nhưng rrf_score và skill_overlap
# đều ∈ [0,1] nên tổng có thể chạm 1.0. Tuy nhiên nếu về sau thêm bonus
# (ví dụ bonus location match, bonus ATS feedback tốt) thì có thể vượt 1.
# Clip phòng vệ tương lai mà không cần sửa code.
#
# Clip [0, 1] = chuẩn hóa điểm về khoảng trực quan, nhất quán với
# cách hiển thị % trên UI (match_score: 0.87 → "87%"), đồng thời
# giữ ngữ nghĩa: 0 = không phù hợp, 1 = khớp hoàn toàn.
# ─────────────────────────────────────────────────────────────────────
#
# Luồng J->C: Nhà tuyển dụng tìm ứng viên (ưu tiên Precision/MRR)
NMAIEX_JC_WEIGHT_RRF=0.30
NMAIEX_JC_WEIGHT_SKILL=0.40
NMAIEX_JC_WEIGHT_EDU=0.00
NMAIEX_JC_PENALTY_SENIORITY_COEF=0.25

# Luồng C->J: Ứng viên tìm công việc (ưu tiên Recall/nDCG@10)
NMAIEX_CJ_WEIGHT_RRF=0.35
NMAIEX_CJ_WEIGHT_TITLE=0.15
NMAIEX_CJ_PENALTY_SALARY_COEF=0.20

# --- RRF Config ---
NMAIEX_RRF_K=60
NMAIEX_RANKING_DEFAULT_LIMIT=20  # Số kết quả trả về mặc định
NMAIEX_RANKING_MAX_LIMIT=100     # Giới hạn tối đa
```

**Thêm vào `.gitignore`:** `.env.nmaiex`

### 2.3. Module `app/core/nmaiex_config.py`

```python
# [NMAIex] Config loader — tái dùng pydantic_settings như FANG
from pydantic_settings import BaseSettings, SettingsConfigDict

class NMAIexSettings(BaseSettings):
    # Cloud Storage — Cloudinary dùng chung, chỉ tách folder
    # CLOUDINARY_CLOUD_NAME / API_KEY / API_SECRET đọc từ .env gốc qua FangSettings
    # Note: cloudinary_upload_folder được quản lý chung tại .env gốc
    # Weights J->C
    nmaiex_jc_weight_rrf: float = 0.30
    nmaiex_jc_weight_skill: float = 0.40
    nmaiex_jc_penalty_seniority_coef: float = 0.25
    # Weights C->J
    nmaiex_cj_weight_rrf: float = 0.35
    nmaiex_cj_weight_title: float = 0.15
    nmaiex_cj_penalty_salary_coef: float = 0.20
    # RRF
    nmaiex_rrf_k: int = 60
    nmaiex_ranking_default_limit: int = 20
    nmaiex_ranking_max_limit: int = 100

    model_config = SettingsConfigDict(
        env_file=".env.nmaiex", env_file_encoding="utf-8", extra="ignore"
    )

nmaiex_settings = NMAIexSettings()
```

---

## 3. Kiến Trúc Backend (Lõi NMAIex trên FANG)

### 3.1. Cấu Trúc File Mới

```
Fang/
├── app/
│   ├── api/
│   │   ├── routes_chat.py          # TTCS — không đụng vào
│   │   ├── routes_ingestion.py     # TTCS — không đụng vào
│   │   └── nmaiex_routes_ranking.py  # [NMAIex] MỚI
│   ├── core/
│   │   ├── config.py               # TTCS — không đụng vào
│   │   ├── nmaiex_config.py        # [NMAIex] MỚI
│   │   └── database.py             # Dùng chung (acquire_conn)
│   ├── services/
│   │   ├── rag_orchestrator.py     # TTCS — không đụng vào
│   │   ├── nmaiex_ranking_service.py   # [NMAIex] MỚI: RRF + Late Fusion
│   │   └── nmaiex_mapper_service.py    # [NMAIex] MỚI: String->ID via LLM
│   ├── models/
│   │   └── nmaiex_schemas.py       # [NMAIex] MỚI: Pydantic models
│   └── main.py                     # Chỉ THÊM include_router, không sửa cũ
```

### 3.2. NMAIex Mapper — Cách Gọi LLM

Dựa trên quyết định tại Mục 2.1, `nmaiex_mapper_service.py` sẽ **tái dùng `invoke_generation("auto-lite")`** của TTCS.

```python
# [NMAIex] nmaiex_mapper_service.py
from app.core.database import acquire_conn
from app.services.rag_orchestrator import invoke_generation

async def map_string_to_province_id(text: str) -> str | None:
    """Map địa chỉ tự do → provId chuẩn bằng LLM."""
    async with acquire_conn() as conn:  # asyncpg pattern đúng của FANG
        rows = await conn.fetch("SELECT provId, provName FROM PROVINCE ORDER BY provId")
    province_list = "\n".join(f"- {r['provid']}: {r['provname']}" for r in rows)
    
    # [NMAIex] System prompt cho Province Mapper — PHẢI chặt chẽ để tránh hallucination
    # Nguyên tắc: (1) Chỉ được chọn trong danh sách cung cấp, (2) Trả về ĐÚNG provId,
    # (3) Không được suy diễn hay tự ý tạo mã mới, (4) Nếu không khớp → UNKNOWN.
    # Lưu ý: province_list phản ánh 34 tỉnh SAU SÁP NHẬP — LLM cần map cả tên cũ
    # (ví dụ: 'Hải Dương' → HAIPHONG vì đã sáp nhập vào 'Thành phố Hải Phòng').
    messages = [
        {"role": "system", "content": (
            "Bạn là công cụ mapping địa chỉ Việt Nam. Nhiệm vụ DUY NHẤT của bạn là "
            "xác định mã provId phù hợp nhất từ DANH SÁCH SAU ĐÂY và chỉ trả về MÃ ĐÓ.\n"
            "DANH SÁCH TỈNH HỢP LỆ (sau sáp nhập 2025):\n"
            f"{province_list}\n\n"
            "QUY TẮC BẮT BUỘC:\n"
            "1. CHỈ trả về một mã provId duy nhất từ danh sách trên. Không được thêm text khác.\n"
            "2. Nếu địa chỉ thuộc tỉnh cũ đã sáp nhập, map sang tỉnh mới tương ứng "
            "(VD: 'Hải Dương' → HAIPHONG; 'Bình Dương' → TPHCM).\n"
            "3. Nếu không xác định được hoặc không khớp bất kỳ tỉnh nào → trả về: UNKNOWN\n"
            "4. TUYỆT ĐỐI KHÔNG tự tạo mã mới, KHÔNG giải thích, KHÔNG thêm dấu câu."
        )},
        {"role": "user", "content": f"Địa chỉ cần map: {text}"}
    ]
    
    trace = await invoke_generation(messages, "auto-lite")
    result = trace.response.strip().upper()
    return result if result != "UNKNOWN" else None

async def map_strings_to_skill_ids(skills: list[str]) -> list[int]:
    """Map danh sách kỹ năng text → skillId. Dùng LLM vì cách viết đa dạng."""
    async with acquire_conn() as conn:
        rows = await conn.fetch("SELECT skillId, skillName FROM SKILL ORDER BY skillName")
    skill_list = "\n".join(f"- {r['skillid']}: {r['skillname']}" for r in rows)
    
    # [NMAIex] System prompt cho Skill Mapper — chặt chẽ, chỉ trả về JSON hợp lệ
    messages = [
        {"role": "system", "content": (
            "Bạn là công cụ mapping kỹ năng. Nhiệm vụ DUY NHẤT của bạn là map các kỹ năng "
            "người dùng cung cấp sang các skillId từ DANH SÁCH SAU ĐÂY.\n"
            "DANH SÁCH KỸ NĂNG HỆ THỐNG:\n"
            f"{skill_list}\n\n"
            "QUY TẮC BẮT BUỘC:\n"
            "1. Trả về MỘT JSON array duy nhất, chứa các skillId (số nguyên). VD: [1, 5, 12]\n"
            "2. CHỈ dùng skillId từ danh sách trên. KHÔNG được tự tạo ID mới.\n"
            "3. Nếu một kỹ năng không khớp bất kỳ mục nào → bỏ qua (không thêm vào array).\n"
            "4. Nếu không có kỹ năng nào khớp → trả về: []\n"
            "5. TUYỆT ĐỐI KHÔNG giải thích, KHÔNG thêm text ngoài JSON array."
        )},
        {"role": "user", "content": f"Kỹ năng cần map: {', '.join(skills)}"}
    ]
    trace = await invoke_generation(messages, "auto-lite")
    # Parse JSON từ trace.response ...
```

> **Lưu ý asyncpg:** FANG dùng `asyncpg` qua `acquire_conn()`. Kết quả `conn.fetch()` trả về list `Record` — truy cập bằng `r['fieldname']` (chữ thường), **không** dùng `r.fieldName` hay `r.field_name`.

### 3.3. API Endpoints (Chi Tiết)

#### Luồng J->C: Tìm Ứng Viên Cho Công Việc
```
GET /v2/nmaiex/ranking/candidates/{job_id}
    ?limit=20           # Số kết quả (default=20, max=100 từ config)
    &province_id=HANOI  # Hard filter thêm nếu muốn
    &work_mode=ONSITE   # Hard filter (ONSITE | HYBRID | REMOTE)

Response:
{
  "job_id": 1,
  "total_candidates": 150,  # Tổng pool trước filter
  "returned": 20,
  "results": [
    {
      "candidate_id": 42,
      "candidate_name": "Nguyễn Văn An",
      "match_score": 0.87,
      "score_breakdown": {       # Luôn trả về để debug (UI ẩn nếu không phải dev mode)
        "rrf_score": 0.62,
        "skill_overlap": 0.80,
        "seniority_penalty": -0.05,
        "hard_filter_passed": true
      }
    }
  ]
}
```

#### Luồng C->J: Tìm Công Việc Cho Ứng Viên
```
GET /v2/nmaiex/ranking/jobs/{candidate_id}
    ?limit=20
    &province_id=HANOI  # Hard filter địa lý
    &work_mode=REMOTE   # Hard filter làm việc từ xa

Response: tương tự, trả về danh sách jobs với match_score.
```

#### API Phụ Trợ (Master Data — phục vụ Frontend Dropdown)
```
GET /v2/nmaiex/master/provinces   → REGION + PROVINCE (có nhóm theo region)
GET /v2/nmaiex/master/levels      → JOBLEVEL
GET /v2/nmaiex/master/categories  → JOBCATEGORY
GET /v2/nmaiex/master/skills      → SKILL
```

### 3.4. Logic Ranking Engine (Tóm Tắt)

```
[REQUEST: job_id, limit, filters]
     |
     v
[STAGE 1 - RETRIEVAL]
  SQL Hard Filter: provId + workMode (loại bỏ ngay từ DB trước khi vector search)
  Vector HNSW: top-K chunk gần nhất (K=limit*5, ví dụ 100)
  Text Match: ts_rank từ PostgreSQL full-text search
     |
     v
[RRF FUSION]
  rrf_score = 1/(k + rank_vector) + 1/(k + rank_text)
     |
     v
[LATE FUSION + PENALTY]
  base = w_rrf * rrf_score + w_skill * skill_overlap
  penalty = penalty_coef * max(0, required_level - candidate_level)
  final_score = clip(base - penalty, 0.0, 1.0)
     |
     v
[SORT & RETURN top-N với score_breakdown]
```

---

## 4. Tác Động Lên Hệ Thống TTCS (Impact Assessment)

| Khu vực | File TTCS liên quan | Cơ chế bị gãy | Phương án fix |
|---|---|---|---|
| **Ingestion Parser** | `cv_parser.py`, `cv_parser_adapters.py` | Parser trả về `skills` và `location` dạng string. Sau khi có bảng chuẩn, cần map sang ID. | Gọi `nmaiex_mapper_service.py` (tái dùng **`invoke_generation(..., "auto-lite")`**). Lưu `skillId[]` và `provId` vào DB thay vì string. |
| **RAG Query** | `rag_query.py`, `rag_orchestrator.py` | Có thể query `workLoc` hoặc `prov` dạng string. | Sửa query JOIN với `PROVINCE` để lấy `provName` khi cần display. `workLoc` vẫn giữ để hiển thị. |
| **Chat Context** | `markdown_builder.py` | Build context từ metadata CV/JD — có thể chứa field `prov`. | Kiểm tra, đổi sang đọc `provId` rồi JOIN lấy `provName`. |
| **Reset DB Script** | `scripts/reset_and_seed_db.py` | Script sẽ lỗi FK nếu tạo `user`/`COMPANY` trước `PROVINCE`. | Cập nhật thứ tự: `REGION` → `PROVINCE` → `user`/`COMPANY`/`JOBPOSTING`. |
| **Seed Data** | `database/seed_data.sql` | INSERT dùng `prov = 'Hà Nội'` (string tự do). | Sửa thành `provId = 'HANOI'`, thêm INSERT cho `JOB_LEVEL_MAP`, `JOB_CATEGORY_MAP`. *Tham khảo dữ liệu từ `miCareer/database/seed_data.sql`*. |

**Yêu cầu System Prompt cho AI Mapping:**
- Query DB lấy toàn bộ master data (`provId`, `skillId`...) **lúc runtime** rồi inject vào system prompt.
- Dùng `asyncpg` pattern đúng: `async with acquire_conn() as conn: rows = await conn.fetch(...)` — truy cập field bằng `row['fieldname']` (chữ thường).
- Gọi LLM một lần cho cả batch (VD: cả list skills) thay vì gọi từng cái một để tiết kiệm chi phí.

> **Nguyên tắc tối thiểu can thiệp:** Chỉ fix những gì thực sự lỗi. Các API `/v2/chat` và `/v2/ingest` phải tiếp tục hoạt động sau khi sửa DB.

---

## 5. Quản Lý CV và Hồ Sơ Ứng Viên

Luồng CV đã thiết kế sẵn trong FANG (`cvUrl`, `cvSnapUrl` đều đã có):
- **`CANDIDATE.cvUrl`** ← CV gốc, ứng viên quản lý bất cứ lúc nào.
- **`JOBAPPLICATION.cvSnapUrl`** ← Snapshot bất biến lúc apply. FANG Ingestion nhận URL này để parse + embed.

**Luồng Apply Job (Frontend cần implement):**
1. Ứng viên nhấn Apply → Modal hỏi "Dùng CV hiện tại" hay "Upload CV mới".
2. Cả hai đường đều upload file lên **Cloudinary** (theo `NMAIEX_CLOUDINARY_*` config).
3. URL Cloudinary được lưu vào `JOBAPPLICATION.cvSnapUrl`.
4. Frontend gọi FANG Ingestion API với URL snapshot đó.

---

## 6. Lộ Trình Thực Thi (Phased Roadmap)

| Phase | Mục tiêu | Chặn bởi |
|---|---|---|
| **Phase 1: DB & Config** | Cập nhật schema (34 tỉnh sau sáp nhập), seed data, tạo `.env.nmaiex` (Cloudinary shared + folder nmaiex), fix TTCS break points | Không |
| **Phase 2: Ranking Core** | Viết `nmaiex_ranking_service.py`, `nmaiex_mapper_service.py` (system prompt chặt, tái dùng auto-lite) | Phase 1 |
| **Phase 3: API & Router** | Tạo endpoints, Pydantic models, include vào `main.py` | Phase 2 |
| **Phase 4: Frontend** | Dropdown chuẩn (34 tỉnh mới), màn hình ranking, Dev Mode Score, quản lý CV Cloudinary (folder nmaiex) | Phase 3 |
| **Phase 5: Tài Liệu Hóa** | Claude viết `nmaiex_ranking_strategy.md` (docs/strategy). AI khác viết guide + cập nhật toàn bộ tài liệu hiện có theo file `[NMAIex]_DOC_UPDATE_INSTRUCTIONS.md` | Phase 3 |
| **Phase 6 (tương lai)** | Sinh dữ liệu Synthetic (180:1), Benchmark nDCG@10 vs MRR | Phase 5 |

### Phân công tài liệu hóa

| Loại tài liệu | Ai làm | Thời điểm | File đích |
|---|---|---|---|
| Strategy NMAIex | Claude (AI dev) | Sau Phase 3 | `docs/strategy/nmaiex_ranking_strategy.md` |
| Guide NMAIex | AI khác | Sau Phase 4 | `docs/guide/nmaiex_ranking_guide.md` |
| Cập nhật README & tài liệu hiện có | AI khác | Sau Phase 4 | Theo `[NMAIex]_DOC_UPDATE_INSTRUCTIONS.md` |

> **Quy trình:** Claude dev xong sẽ cập nhật liên tục file `agent_workflow_doc/[NMAIex]_DOC_UPDATE_INSTRUCTIONS.md` với các thay đổi cần tài liệu hóa. AI tài liệu sẽ đọc file đó và thực hiện toàn bộ sau khi dev xong.

---

## 7. Strategy C: Tiered Skill Matching

> **Quyết định [2026-04-29]:** Thay thế cơ chế "Closed-World bỏ qua skill ngoài catalog" bằng chiến lược 2 tầng.

### 7.1. Vấn Đề Gốc

Catalog skill là `CLOSED-WORLD`: LLM mapper trả `[]` cho skill không có trong DB → mất thông tin âm thầm, ảnh hưởng nghiêm trọng đến ranking (skill_overlap là thành phần weight cao nhất trong công thức).

Re-mapping batch khi catalog update (Strategy B) có rủi ro hạ tầng + chi phí LLM hàng loạt → bác bỏ.

### 7.2. Kiến Trúc 2 Tầng

**Tầng 1 — Closed-World (LLM Mapper, có schema enforcement):**
- LLM nhận catalog từ DB (runtime), trả `SkillMappingResult(matched_ids, unmatched_texts)` (Pydantic-validated).
- `matched_ids` → lưu `CANDIDATESKILL` như cũ → dùng cho exact scoring.
- `unmatched_texts` → chuyển xuống Tầng 2.

**Tầng 2 — Open-World (Embedding Fallback):**
- `unmatched_texts` được embed bằng `text-embedding-3-small` → lưu vector vào `CANDIDATE_SKILL_RAW`.
- Chi phí ~5x rẻ hơn LLM. Phù hợp cho các string ngắn.
- Dùng cho fuzzy scoring trong ranking.

### 7.3. Bảng DB Mới

Thêm vào `schema_web_core.sql` sau `CANDIDATESKILL`:

> **Embedding Dims cho Skill Matching:** TTCS dùng `halfvec(1024)` cho document chunks (kích thước lớn vì cần semantic depth cho toàn bộ context). Skills là text ngắn (1-5 từ) — **256 dims là đủ và rẻ hơn 4x**. `text-embedding-3-small` hỗ trợ giảm chiều Matryoshka (truyền `dimensions=256` lúc gọi API — không cần post-process). Lưu ý: `vector(N)` trong PostgreSQL là **fixed at CREATE TABLE** — nếu đổi dims phải DROP + recreate bảng. `reset_and_seed_db.py` cần đọc `NMAIEX_SKILL_EMBEDDING_DIMS` và sinh SQL động.

**Thêm vào `.env.nmaiex`:**
```env
NMAIEX_SKILL_EMBEDDING_DIMS=256  # 256 là đủ cho skill text ngắn, rẻ hơn 1024/1536
```

**Thêm vào `nmaiex_config.py`:**
```python
nmaiex_skill_embedding_dims: int = 256
```

```sql
-- [NMAIex] Strategy C: Unmatched skills với vector cho fuzzy matching
CREATE TABLE CANDIDATE_SKILL_RAW (
    rawId      SERIAL PRIMARY KEY,
    candId     INT NOT NULL REFERENCES CANDIDATE(candId) ON DELETE CASCADE,
    rawText    VARCHAR(200) NOT NULL,
    embedding  vector(256),   -- dims = NMAIEX_SKILL_EMBEDDING_DIMS (default 256)
    createdAt  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_cand_skill_raw_cand ON CANDIDATE_SKILL_RAW(candId);

-- [NMAIex] Unmatched skills phía Job (khi HR nhập text-free skill)
CREATE TABLE JOB_SKILL_RAW (
    rawId      SERIAL PRIMARY KEY,
    jobPostId  INT NOT NULL REFERENCES JOBPOSTING(jobPostId) ON DELETE CASCADE,
    rawText    VARCHAR(200) NOT NULL,
    embedding  vector(256),   -- cùng dims với CANDIDATE_SKILL_RAW để cosine có nghĩa
    createdAt  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_job_skill_raw_job ON JOB_SKILL_RAW(jobPostId);
```

> **JOB_SKILL_RAW — ĐÃ CÓ LÝ DO TẠO NGAY:** User quyết định bổ sung text-free skill input cho HR (xem Mục 9.3). HR có thể nhập skill không có trong catalog → LLM mapper chạy → unmatched → lưu `JOB_SKILL_RAW`. Fuzzy overlap bây giờ có dữ liệu từ **cả 2 phía** — có ý nghĩa hơn.


### 7.4. Công Thức Ranking Mới

```
skill_score = α * exact_overlap + (1-α) * fuzzy_overlap

exact_overlap = |matched_job_ids ∩ matched_cand_ids| / max(|job_ids|, 1)
fuzzy_overlap = avg_max_cosine(job_raw_embeddings, cand_raw_embeddings)
                0.0 nếu một trong hai bên không có raw skills

α = 0.8  → tham số NMAIEX_SKILL_ALPHA trong .env.nmaiex (dễ tune)

final_score = clip(w_rrf*rrf + w_skill*skill_score - penalty, 0.0, 1.0)
```

`score_breakdown` trả thêm: `exact_overlap`, `fuzzy_overlap`, `skill_alpha`.

---

## 8. Pydantic Mapper Upgrade

> **Quyết định [2026-04-29]:** Nâng mapper lên Pydantic-validated output, học theo pattern của `cv_parser_adapters.py`.

### 8.1. Tại Sao Cần Nâng Cấp

Mapper hiện tại (`nmaiex_mapper_service.py`) parse thủ công: strip markdown → `json.loads` → check `list[int]`. Không có schema enforcement, silent fail trả `[]`.

### 8.2. Models Mới

Thêm vào `app/models/nmaiex_schemas.py`:

```python
class SkillMappingResult(BaseModel):
    """Output Pydantic-validated của LLM skill mapper."""
    matched_ids: list[int]       # skillId có trong catalog
    unmatched_texts: list[str]   # Raw text không map được → đưa sang Tầng 2

class ProvinceMappingResult(BaseModel):
    """Output Pydantic-validated của LLM province mapper."""
    prov_id: str | None          # None nếu UNKNOWN
```

### 8.3. API Mapper Mới

Hàm `map_strings_to_skill_ids` → đổi thành `map_skills` trả `SkillMappingResult`.
Prompt mới: LLM trả `{"matched_ids": [...], "unmatched_texts": [...]}` thay vì chỉ array.

Graceful degradation:
- LLM trả output hợp lệ → validate Pydantic → return
- Validation fail → log warning → trả `SkillMappingResult(matched_ids=[], unmatched_texts=all_input_skills)`

Hàm mới `embed_and_store_raw_skills(entity_type, entity_id, unmatched_texts, conn)`:
- `entity_type`: `"candidate"` hoặc `"job"` — quyết định INSERT vào bảng tương ứng.
- Gọi `embed_chunks(unmatched_texts)` (tái dùng `app/services/embedding.py`) với `dimensions=nmaiex_settings.nmaiex_skill_embedding_dims`.
- INSERT batch vào `CANDIDATE_SKILL_RAW` hoặc `JOB_SKILL_RAW`.


---

## 9. HR JobPosting Edit — Cascade Impact & Chiến Lược

> **Vấn đề [2026-04-29]:** Khi frontend có trang quản lý Job cho HR, việc HR sửa JobPosting ảnh hưởng cascade lên nhiều thành phần. Cần chiến lược rõ ràng.

### 9.1. Bản Đồ Cascade

| Field HR sửa | Bảng bị ảnh hưởng | Hành động backend cần trigger |
|---|---|---|
| `title`, `description` | `AIDOCUMENTCHUNK` (vector chunks) | **Re-ingest**: DELETE chunks cũ → call FANG Ingestion API với nội dung mới → re-embed |
| Skills (custom text + dropdown) | `JOBREQUIREMENT`, `JOB_SKILL_RAW` | Dropdown skills → DELETE+INSERT `JOBREQUIREMENT`. Text-free skills → LLM mapper → matched vào `JOBREQUIREMENT`, unmatched → embed + INSERT `JOB_SKILL_RAW`. |
| `provId` / `workLoc` | `JOBPOSTING` | UPDATE trực tiếp |
| Level (JOB_LEVEL_MAP) | `JOB_LEVEL_MAP` | DELETE cũ → INSERT mới |
| Category (JOB_CATEGORY_MAP) | `JOB_CATEGORY_MAP` | DELETE cũ → INSERT mới |
| `minSalary`, `maxSalary` | `JOBPOSTING` | UPDATE trực tiếp |

> **Tại sao `title`/`description` ảnh hưởng AIDOCUMENTCHUNK?** FANG Ingestion Pipeline đã chunk + embed nội dung job description vào `AIDOCUMENTCHUNK` (kèm HNSW index). Ranking engine dùng HNSW vector search trên bảng này để tính `rrf_score`. Nếu HR sửa description (VD: "Python Backend" → "Java Spring Boot") nhưng chunks không được re-embed, vector search vẫn trả kết quả theo **nội dung cũ** → ranking sai. Re-ingest là bắt buộc cho Semantic Edit.


### 9.2. Chiến Lược Xử Lý

**Rule: Phân loại edit thành 2 loại:**

1. **Semantic Edit** (thay đổi nội dung mô tả): `title`, `description` → **bắt buộc re-ingest** vì vector chunks lỗi thời → ranking bằng vector sẽ sai.
2. **Structured Edit** (thay đổi metadata): skills, province, level, category, salary → **UPDATE/DELETE-INSERT trực tiếp**, không cần re-ingest.

**API Backend cần cung cấp:**

```
PATCH /v2/nmaiex/jobs/{job_id}/structured
    Body: { provId, levelIds[], catIds[], skillIds[], minSalary, maxSalary, workMode }
    → UPDATE trực tiếp, không re-embed
    → Trả: { job_id, updated_fields: [...] }

PATCH /v2/nmaiex/jobs/{job_id}/content
    Body: { title, description }
    → UPDATE JOBPOSTING + trigger async re-ingest pipeline
    → Trả: { job_id, reingestion_status: "queued" }
```

**Trạng thái re-ingest:**
- Khi re-ingest đang chạy, job vẫn hiển thị bình thường nhưng ranking score có thể tạm thời kém chính xác.
- Không cần thông báo realtime ở giai đoạn MVP. Log server-side là đủ.

### 9.3. Frontend — Trang Quản Lý Job (HR)

Đây là tính năng **mới hoàn toàn** chưa có trong frontend hiện tại. Cần bổ sung:

- Trang `HR / Job Management` (list + CRUD job postings)
- Form tạo/sửa Job: dùng các component chuẩn hóa (`LocationSelector`, `SkillSelector`, `LevelSelector`, `CategorySelector`)
- **Skill Input — Hybrid Input:**
  - **Dropdown** cho skills có sẵn trong catalog (giữ nguyên SkillSelector).
  - **Text field** bổ sung cho skill không có trong catalog: HR gõ vào, backend chạy LLM mapper → nếu match → vào `JOBREQUIREMENT`; nếu không → embed → vào `JOB_SKILL_RAW`.
  - UX: Tag input kiểu chip — khi HR nhập text và nhấn Enter, skill được thêm dưới dạng chip màu khác (phân biệt catalog skill vs. custom skill).
- Nút **"Save Content"** (trigger re-ingest) tách biệt với **"Save Settings"** (structured update) để tránh re-embed không cần thiết.

> **Hệ quả cập nhật:** Vì HR có text-free skill input, `JOB_SKILL_RAW` **cần được tạo ngay** (không còn DEFER). Fuzzy overlap trong ranking sẽ có dữ liệu từ cả 2 phía — ý nghĩa hơn nhiều.

---

## 10. Chuẩn Hóa Hạ Tầng Toàn Hệ Thống (Infrastructure Standardization)

> **Quyết định [2026-04-30]:** Thay vì cố gắng chắp vá NMAIex một cách độc lập ("minimal intervention"), chúng ta chuẩn hóa một số thành phần lõi của TTCS để trở thành các dịch vụ dùng chung (Generic Services) mạnh mẽ hơn.

### 10.1. Refactor `embedding.py`
- Biến hàm `embed_chunks` thành một dịch vụ chung có thể cấu hình số chiều.
- Signature mới: `async def embed_chunks(chunks: List[str], dimensions: Optional[int] = None) -> List[List[float]]`.
- Việc này giúp NMAIex tái sử dụng cơ chế batching, error handling, và logging của TTCS cho các skill chunks ngắn với `dimensions=256`. 
- **Backward compatibility:** Nếu `dimensions=None` thì fallback về `settings.embedding_dim`.

### 10.2. Schema Động (Infrastructure as Code)
- Để đảm bảo Single Source of Truth, mọi cấu hình số chiều (dims) phải được kiểm soát từ `.env` và `.env.nmaiex`.
- Đổi các số literal như `vector(1024)` hay `vector(256)` trong file `schema_ai_core.sql` và `schema_web_core.sql` thành các placeholder: `__TTCS_EMBEDDING_DIM__` và `__NMAIEX_SKILL_EMBEDDING_DIM__`.
- Nâng cấp `scripts/reset_and_seed_db.py` để tự động thực hiện string replace các placeholder này bằng giá trị từ `settings` và `nmaiex_settings` trước khi thực thi lệnh SQL. Điều này loại bỏ hoàn toàn rủi ro lệch pha cấu hình DB và code.


---
## 11. C→J Flow Optimization (2026-05-01)

> **Bối cảnh:** Sau khi review code thực tế `nmaiex_ranking_service.py`, phát hiện 5 vấn đề trong luồng C→J. Tài liệu phân tích gốc: `[NMAIex]_CJ_FLOW_OPTIMIZATION_REPORT.md`.

### 11.1. Tại Sao C→J Không Dùng Vector Search (Intentional Design)

> **Quyết định có chủ ý — cần document để tránh nhầm lẫn khi đọc code.**

**J→C** lấy embedding của JobPosting (đã index trong `AIDOCUMENTCHUNK` từ FANG TTCS pipeline) → vector search tìm CV chunks gần nhất. Vector index đã tồn tại sẵn.

**C→J** chiều ngược lại gặp 2 vấn đề kỹ thuật ở giai đoạn MVP:
1. `AIDOCUMENTCHUNK` index theo chiều "CV nào gần Job này", không tối ưu cho "Job nào gần CV này".
2. CV có nhiều chunks (5-15 chunks/CV), không có "representative vector" rõ ràng.

**MVP scope:** Với Job pool nhỏ (~100-200 trong MVP), FTS (`ts_rank`) đủ hiệu quả.

> **Future improvement** (ghi vào `docs/strategy/nmaiex_ranking_strategy.md`): Khi scale >1000 jobs, thêm index `JOB_EMBEDDING` (embed `title + description` mỗi Job), cho phép C→J: embed candidate profile → ANN search → RRF với text score.

### 11.2. Fix Weight Bug — w_skill Dùng Nhầm J→C Config

**Bug (dòng 394 `nmaiex_ranking_service.py`):** C→J dùng `nmaiex_jc_weight_skill` (0.40) thay vì config riêng. `nmaiex_cj_weight_title` (0.15) được định nghĩa nhưng không bao giờ enable.

**Fix — Thêm vào `.env.nmaiex`:**
```env
NMAIEX_CJ_WEIGHT_SKILL=0.30
```

**Thêm vào `nmaiex_config.py`:**
```python
nmaiex_cj_weight_skill: float = 0.30
```

**Sửa `nmaiex_ranking_service.py` dòng 392-394:**
```python
w_rrf   = nmaiex_settings.nmaiex_cj_weight_rrf    # 0.35
w_skill = nmaiex_settings.nmaiex_cj_weight_skill  # 0.30 (đúng CJ config)
w_title = nmaiex_settings.nmaiex_cj_weight_title  # 0.15 (enable)
```

**Lý do w_skill CJ (0.30) < JC (0.40):** J→C có 2 tín hiệu (vector + text), RRF mạnh hơn → skill có thể đóng vai trò lớn hơn. C→J chỉ có text search → cần nhường weight cho title (0.15).

**Về tổng weight không = 1.0:** Tổng CJ = 0.35 + 0.15 + 0.30 = 0.80. Room 0.20 còn lại cho salary_adjustment (cộng/trừ). `clip(0,1)` đảm bảo output hợp lệ.

### 11.3. Title Matching & CV Profile Enrichment

**Vấn đề:** C→J chỉ dùng `rawText` làm candidate profile cho FTS. Không khai thác `experience[].title` (chức danh gần đây) — nguồn relevance cao nhất.

**Giải pháp — Enrich candidate_text:**
```python
# Thêm vào SELECT query
cv.parsedData -> 'experience' as experiences,
cv.parsedData -> 'certificates' as certificates_list,
cv.parsedData -> 'education' as education_list

# Build enriched profile
experiences = (cv_row["parseddata"] or {}).get("experience", [])
recent_titles = [e["title"] for e in experiences[:3] if e and e.get("title")]
certs = (cv_row["parseddata"] or {}).get("certificates", [])
edu_list = (cv_row["parseddata"] or {}).get("education", [])
edu_degrees = [e.get("degree") for e in edu_list if e and e.get("degree")]

profile_parts = []
if recent_titles:        profile_parts.append(" ".join(recent_titles))
if candidate_row["bio"]: profile_parts.append(candidate_row["bio"])
if certs:                profile_parts.append(" ".join(certs))
if edu_degrees:          profile_parts.append(" ".join(edu_degrees))
candidate_text = " ".join(filter(None, profile_parts)) or candidate_row["rawtext"] or "Experienced candidate"
```

**Title score (w_title = 0.15):** Tính ts_rank riêng giữa `recent_titles` và `job.title`.

> **Future note (strategy doc):** Embed `recent_titles` → cosine với job title embedding → chính xác hơn với alias ("BE Dev" ≈ "Backend Engineer").

### 11.4. Salary Adjustment

**Vấn đề:** `salary_penalty = 0.0` hard-code. `nmaiex_cj_penalty_salary_coef` không được dùng. DB không có `expectedSalary` của ứng viên.

**Giải pháp 2 tầng:**

**Tầng 1 — Parse expectedSalary từ CV (nguồn chính):**

Thêm vào `app/models/cv_models.py` (`ParsedCV`):
```python
expectedSalaryMin: int | None = Field(None, description="Expected min salary (VND). None if not stated.")
expectedSalaryMax: int | None = Field(None, description="Expected max salary (VND). None if not stated.")
```
Cập nhật LLM prompt trong `cv_parser_adapters.py` để extract 2 field này. LLM trả `null` nếu không có.

**Tầng 2 — Fallback estimate khi CV không có expected salary:**
```python
estimate = salary_base[location] + expyears * salary_increment[tier]
```

**Xử lý "lương thỏa thuận":** `minSalary IS NULL AND maxSalary IS NULL` → `salary_adjustment = 0.0` (neutral).

**Logic asymmetric:**
```python
mid_job = (minSalary + maxSalary) / 2
expected = parsedCV.expectedSalaryMin/Max hoặc estimate()

mid < expected*0.8*0.8  → penalty mạnh (quá thấp)
mid < expected*0.8      → penalty nhẹ
mid < expected*1.2      → neutral 0.0
mid >= expected*1.2     → bonus (tối đa salary_bonus_cap)
```

**Config mới trong `.env.nmaiex`:**
```env
NMAIEX_SALARY_BASE_HANOI=15000000
NMAIEX_SALARY_BASE_TPHCM=14000000
NMAIEX_SALARY_BASE_DANANG=12000000
NMAIEX_SALARY_BASE_DEFAULT=13000000
NMAIEX_SALARY_INCREMENT_JUNIOR=1500000
NMAIEX_SALARY_INCREMENT_MIDDLE=2000000
NMAIEX_SALARY_INCREMENT_SENIOR=2500000
NMAIEX_SALARY_INCREMENT_LEAD=3000000
NMAIEX_SALARY_TOLERANCE_LOWER=0.8
NMAIEX_SALARY_TOLERANCE_UPPER=1.2
NMAIEX_SALARY_BONUS_CAP=0.2
```
* NOTE FROM USER: Nếu có thể phân tách số tiền VND cho dễ đọc thì tốt, ví dụ 15_000_000
**Công thức C→J cuối (sau tất cả fixes + Language System):**
```python
final_score = clip(
    w_rrf   * rrf_score_norm
    + w_title * title_score
    + w_skill * skill_score
    + salary_adjustment    # âm = penalty, dương = bonus
    - lang_penalty         # Mục 12
    + lang_bonus           # Mục 12
, 0.0, 1.0)
```

---

## 12. Language Requirement System (2026-05-01)

> **Quyết định:** Implement ngay cùng với C→J optimizations (không defer sau Phase 3).
> **Lý do thực tế thị trường VN:** Phân biệt REQUIRED/PREFERRED ngôn ngữ rất phổ biến trong IT jobs outsourcing (FPT/Fujitsu/Samsung). Job yêu cầu tiếng Nhật thường trả lương cao hơn 15-30%.

### 12.1. Schema Mới

Thêm vào `schema_web_core.sql` (sau bảng `JOBCATEGORY`):

```sql
-- [NMAIex] Bảng ngôn ngữ chuẩn
CREATE TABLE LANGUAGE (
    langId   SERIAL PRIMARY KEY,
    langCode VARCHAR(10)  NOT NULL UNIQUE,
    langName VARCHAR(50)  NOT NULL
);

-- [NMAIex] Yêu cầu ngôn ngữ của Job (N-N, REQUIRED vs PREFERRED)
CREATE TABLE JOB_LANG_REQUIREMENT (
    jobPostId  INT         NOT NULL REFERENCES JOBPOSTING(jobPostId) ON DELETE CASCADE,
    langId     INT         NOT NULL REFERENCES LANGUAGE(langId),
    reqType    VARCHAR(10) NOT NULL CHECK (reqType IN ('REQUIRED', 'PREFERRED')),
    minLevel   VARCHAR(20) CHECK (minLevel IN ('BASIC','INTERMEDIATE','ADVANCED','FLUENT','NATIVE')),
    PRIMARY KEY (jobPostId, langId)
);
```

**Seed data (`root_data.sql`):**
```sql
INSERT INTO LANGUAGE (langCode, langName) VALUES
('en','English'),('ja','Japanese'),('ko','Korean'),
('zh','Chinese'),('vi','Vietnamese'),('fr','French'),('de','German');
```
* NOTE FROM USER: Đây cũng là một cái đáng lưu tâm để cập nhật thường xuyên -> Cân nhắc thêm task vào agent_workflow_doc\AI_MANUAL_UPDATE.md

### 12.2. CV Parser Update — `ParsedCV.languages`
* NOTE FROM USER: Web tuyển dụng phục vụ 99% là người Việt Nam, vậy tiếng Việt sẽ không cần phải xét đâu chứ nhỉ?, nghĩa là mặc định tiếng Việt không cần chỉ định trong JobPosting hay CV. Còn ngoại lệ ư? Tư vấn mình nếu cần thiết và việc thiếu tiếng Việt không phải là hiếm.
**Breaking change:** `list[str]` → `list[LanguageEntry]`

Thêm class mới vào `app/models/cv_models.py`:
```python
class LanguageEntry(CVBaseModel):
    """Represents a language skill from a CV."""
    language: str = Field(..., description="Language name (e.g. 'English', 'Japanese').")
    proficiency: str | None = Field(
        None,
        description="Proficiency as stated in CV (e.g. 'N3', 'Fluent', 'B2'). Raw string."
    )
```

Sửa `ParsedCV`:
```python
languages: list[LanguageEntry] = Field(
    default_factory=list,
    description="List of languages with proficiency levels."
)
```

Cập nhật LLM prompt trong `cv_parser_adapters.py` để extract `[{"language": "Japanese", "proficiency": "N3"}, ...]`.

### 12.3. Proficiency Normalization

Tái dùng LLM mapper pattern:
```python
Raw proficiency → invoke_generation("auto-lite") → chuẩn hóa về:
BASIC | INTERMEDIATE | ADVANCED | FLUENT | NATIVE

Thứ tự: BASIC(1) < INTERMEDIATE(2) < ADVANCED(3) < FLUENT(4) < NATIVE(5)

Ví dụ mapping:
  "N3" → INTERMEDIATE
  "N2" → ADVANCED
  "N1" → FLUENT
  "Business level" → ADVANCED
  "Native speaker" / "Tiếng mẹ đẻ" → NATIVE
  "Sơ cấp" / "Basic" → BASIC
```

### 12.4. Language Scoring Logic

Hàm `compute_language_score(job_post_id, candidate_languages, conn)` trả `(lang_penalty, lang_bonus, breakdown)`:

```python
Với mỗi yêu cầu ngôn ngữ của Job:
  REQUIRED + candidate không có ngôn ngữ → penalty += NMAIEX_LANG_REQUIRED_PENALTY (0.25)
  REQUIRED + candidate có nhưng level không đủ → penalty += NMAIEX_LANG_LEVEL_PENALTY (0.10)
  PREFERRED + candidate có đủ level → bonus += NMAIEX_LANG_PREFERRED_BONUS (0.08)

Tổng bonus bị cap bởi NMAIEX_LANG_BONUS_CAP (0.15)
```

### 12.5. Config Mới

**`.env.nmaiex`:**
```env
NMAIEX_LANG_REQUIRED_PENALTY=0.25
NMAIEX_LANG_LEVEL_PENALTY=0.10
NMAIEX_LANG_PREFERRED_BONUS=0.08
NMAIEX_LANG_BONUS_CAP=0.15
```

**`nmaiex_config.py`:**
```python
nmaiex_lang_required_penalty: float = 0.25
nmaiex_lang_level_penalty: float = 0.10
nmaiex_lang_preferred_bonus: float = 0.08
nmaiex_lang_bonus_cap: float = 0.15
```

### 12.6. Frontend Cascade

`LangSelector` component cần được thêm vào Phase 1.5 (HR Job Management form), tương tự `LevelSelector`. Cập nhật `TASK_CHECKLIST_FRONTEND.md` khi đến lượt.

### 12.7. Quyết Định Về Chứng Chỉ & Education

> **Chứng chỉ:** Text enrichment only — gom vào `candidate_text` → ts_rank tự xử lý. Cert keywords (`AWS`, `CKA`) rất specific → FTS match tự nhiên. Không cần bảng riêng.
>
> **Education (Bachelor/Master/PhD):** Text enrichment only. Ít phổ biến hơn language requirement trong IT VN. Future: thêm `educationLevel` enum vào `CANDIDATE` nếu cần HR filter.

# [NMAIex] Kế Hoạch Triển Khai Chi Tiết Hệ Thống Xếp Hạng Hai Chiều

> **Ngữ cảnh:** FANG AI Core (FastAPI, PostgreSQL + pgvector, asyncpg) là backend AI xử lý toàn bộ. miCareer-mini là frontend thin-client chỉ gọi API. Hai CSDL song song: `schema_web_core.sql` (dữ liệu tuyển dụng) và `schema_ai_core.sql` (bảng AI: chunk, vector, conversation). DB connection dùng `asyncpg` pool, truy cập qua `acquire_conn()` từ `app/core/database.py`.

Tài liệu này là **bản thiết kế kỹ thuật chi tiết (Low-level Design)** để hiện thực hóa NMAIex trên nền tảng FANG hiện hữu. Cần đối chiếu với [`NMAIex_th_3`] và [`NMAIex_3`] trước khi code.

---

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
# CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET → đặt tại .env gốc
# Biến dưới đây chỉ định folder đích khi upload từ NMAIex:
NMAIEX_CLOUDINARY_UPLOAD_FOLDER="nmaiex"
# Tương ứng, TTCS dùng folder: ttcs (đặt biến TTCS_CLOUDINARY_UPLOAD_FOLDER="ttcs" tại .env gốc)

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
    nmaiex_cloudinary_upload_folder: str = "nmaiex"  # Home/nmaiex trên Cloudinary
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

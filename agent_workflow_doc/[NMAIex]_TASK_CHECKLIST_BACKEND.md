# [NMAIex] Checklist Backend (FANG AI Core)

Tài liệu checklist thực thi. AI Agent tick `[x]` khi hoàn thành, `[/]` khi đang làm.
Tham chiếu: `[NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md`

---

## Phase 1: Database & Cấu Hình

### 1a. Schema Mới
- [ ] Thêm bảng `REGION` và `PROVINCE` vào `database/schema_web_core.sql` (**đặt trước** bảng `user` và `COMPANY` để tránh lỗi FK).
- [ ] Thêm bảng `JOBLEVEL` (có cột `minYears`, `maxYears`) vào `schema_web_core.sql`.
- [ ] Thêm bảng `JOBCATEGORY` vào `schema_web_core.sql`.
- [ ] Thêm bảng nối `JOB_LEVEL_MAP` (jobPostId, levelId) vào `schema_web_core.sql`.
- [ ] Thêm bảng nối `JOB_CATEGORY_MAP` (jobPostId, catId) vào `schema_web_core.sql`.
- [ ] Thêm cột `provId VARCHAR(20) FK → PROVINCE` vào bảng `user`, `COMPANY`, `JOBPOSTING`.
  - *Giữ lại `workLoc` cho mục đích display text (VD: "Tầng 15, Keangnam, Hà Nội").*
  - *Xóa cột `prov` (string tự do) khỏi `user` và `COMPANY`.*

### 1b. Seed Data
> Tham khảo dữ liệu từ `cur_prj\miCareer\database\seed_data.sql` (MySQL) để convert sang PostgreSQL.

- [ ] Cập nhật `database/root_data.sql`: INSERT 3 Region (`NORTH`, `CENTRAL`, `SOUTH`) và 34 Province chuẩn theo mô hình hành chính mới. Mã tỉnh dùng tên viết liền không dấu (`HANOI`, `HCM`, `BACNINH`...).
- [ ] Cập nhật `root_data.sql`: INSERT `JOBLEVEL` 8 cấp (Intern, Fresher, Junior, Middle, Senior, Lead, Manager, Director) với `minYears`/`maxYears` hợp lý.
- [ ] Cập nhật `root_data.sql`: INSERT `JOBCATEGORY` 17 danh mục IT (Backend, Frontend, AI/ML...).
- [ ] Cập nhật `database/seed_data.sql`:
  - Sửa `prov = '...'` → `provId = 'HANOI'` cho tất cả user/company.
  - Giữ `workLoc` text display, thêm `provId = 'HANOI'` cho JOBPOSTING.
  - Thêm INSERT vào `JOB_LEVEL_MAP` và `JOB_CATEGORY_MAP` cho từng JobPosting.
  - Giữ lại ứng viên đặc biệt **Nguyễn Hải Hưng** và `cvUrl` gốc FANG.

### 1c. Cấu Hình NMAIex
- [ ] Tạo file `.env.nmaiex` tại root FANG (theo template trong Implementation Plan).
- [ ] Thêm `.env.nmaiex` vào `.gitignore`.
- [ ] Tạo `app/core/nmaiex_config.py` dùng `pydantic_settings`, đọc `.env.nmaiex` (Chỉ chứa Cloudinary + Weights + Limits, **KHÔNG** chứa API Keys LLM).
- [ ] Tạo `app/core/.env.nmaiex.example` (template) để commit lên Git.

### 1d. Fix TTCS Break Points
- [ ] Kiểm tra `app/services/cv_parser.py` và `cv_parser_adapters.py`: Xác nhận nơi ghi `prov`/`location` vào DB — cập nhật để ghi `provId` thay vì string.
- [ ] Kiểm tra `app/services/rag_query.py` và `markdown_builder.py`: Sửa query/build-string đang đọc `prov` string → JOIN với `PROVINCE` để lấy `provName`.
- [ ] Chạy lại `scripts/reset_and_seed_db.py` — xác nhận DB reset thành công không lỗi FK.
- [ ] Chạy smoke test: `POST /v2/ingest`, `POST /v2/chat` — xác nhận TTCS không bị gãy.

---

## Phase 2: Core Ranking Engine

- [ ] Tạo `app/services/nmaiex_mapper_service.py`:
  - **Tái dùng toàn bộ `invoke_generation(messages, "auto-lite")`** của TTCS.
  - Hàm `map_string_to_province_id(text: str) -> str | None`:
    - `async with acquire_conn() as conn: rows = await conn.fetch("SELECT provId, provName FROM PROVINCE")` (asyncpg pattern — truy cập field bằng `row['provid']` chữ thường).
    - Build system prompt inject danh sách tỉnh → gọi `await invoke_generation(messages, "auto-lite")` → parse `trace.response`.
  - Hàm `map_strings_to_skill_ids(skills: list[str]) -> list[int]`:
    - Gọi LLM **một lần cho cả batch** (không gọi từng kỹ năng riêng lẻ).
    - System prompt inject danh sách `skillId: skillName` từ DB.
    - Parse JSON array trả về từ LLM.

- [ ] Tạo `app/services/nmaiex_ranking_service.py`:
  - **Hard Filter SQL**: Lọc `provId` và `workMode` ngay trong SQL trước khi vector search.
  - **Vector HNSW**: Truy vấn `AIDOCUMENTCHUNK` top-K (K = limit × 5) bằng cosine distance.
  - **Text Match**: Dùng `ts_rank` (PostgreSQL full-text) từ `JOBPOSTING.description` vs `CVPARSED.rawText`.
  - **RRF Score**: `1/(k + rank_vector) + 1/(k + rank_text)` với `k` từ `nmaiex_settings.nmaiex_rrf_k`.
  - **Skill Overlap**: `|Job Skills ∩ Candidate Skills| / |Job Skills|` từ `JOBREQUIREMENT` và `CANDIDATESKILL`.
  - **Seniority Penalty** (J→C): gap giữa `JOBLEVEL.minYears` của job và `CANDIDATE.expyears` × `penalty_seniority_coef`.
  - **Salary Gap Penalty** (C→J): gap giữa `JOBPOSTING.minSalary` và salary expectation ứng viên.
  - **Late Fusion**: `final_score = clip(w_rrf*rrf + w_skill*skill_overlap - penalty, 0.0, 1.0)`.
  - **score_breakdown**: dict chi tiết từng thành phần để debug (luôn trả về, UI tự ẩn/hiện).

---

## Phase 3: API & Router

- [ ] Tạo `app/models/nmaiex_schemas.py`: Pydantic models (`ScoreBreakdown`, `CandidateRankResult`, `JobRankResult`, `RankingResponse`, `MasterDataItem`).
- [ ] Tạo `app/api/nmaiex_routes_ranking.py`:
  - `GET /v2/nmaiex/ranking/candidates/{job_id}?limit=20&province_id=...&work_mode=...`
  - `GET /v2/nmaiex/ranking/jobs/{candidate_id}?limit=20&province_id=...&work_mode=...`
  - `GET /v2/nmaiex/master/provinces` (có nhóm theo region)
  - `GET /v2/nmaiex/master/levels`
  - `GET /v2/nmaiex/master/categories`
  - `GET /v2/nmaiex/master/skills`
- [ ] Cập nhật `app/main.py`: Thêm `include_router(nmaiex_router, prefix="/v2")` — **KHÔNG** sửa các router TTCS hiện có.
- [ ] Kiểm tra: `GET /v2/nmaiex/ranking/candidates/1?limit=10` trả về JSON hợp lệ với `score_breakdown`.

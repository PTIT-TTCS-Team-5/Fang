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

- [x] Cập nhật `database/root_data.sql`: INSERT 3 Region (`NORTH`, `CENTRAL`, `SOUTH`) và **34 Province theo mô hình sau sáp nhập 2025** — dùng INSERT từ `[NMAIex]_PROVINCE_MERGER_GUIDE.md`. Mã tỉnh dùng mã đầy đủ (`HANOI`, `TPHCM`, `DANANG`, `HAIPHONG`,...), có cột `mergedFrom`. (Tham khảo agent_workflow_doc\[NMAIex]_PROVINCE_MERGER_GUIDE.md)
- [x] Cập nhật `root_data.sql`: INSERT `JOBLEVEL` 8 cấp (Intern, Fresher, Junior, Middle, Senior, Lead, Manager, Director) với `minYears`/`maxYears` hợp lý.
- [x] Cập nhật `root_data.sql`: INSERT `JOBCATEGORY` 17 danh mục IT (Backend, Frontend, AI/ML...).
- [x] Cập nhật `database/seed_data.sql`:
  - Sửa `prov = '...'` → `provId = 'HANOI'` (mã mới) cho tất cả user/company.
  - Giữ `workLoc` text display, thêm `provId` mới cho JOBPOSTING.
  - Thêm INSERT vào `JOB_LEVEL_MAP` và `JOB_CATEGORY_MAP` cho từng JobPosting.
  - Giữ lại ứng viên đặc biệt **Nguyễn Hải Hưng** và `cvUrl` gốc FANG.

### 1c. Cấu Hình NMAIex
- [x] Tạo file `.env.nmaiex` tại root FANG (theo template trong Implementation Plan).
  - **Cloudinary dùng chung:** Credentials (`CLOUD_NAME`, `API_KEY`, `API_SECRET`) đặt ở `.env` gốc. Chỉ thêm `NMAIEX_CLOUDINARY_UPLOAD_FOLDER="nmaiex"` vào `.env.nmaiex`.
  - **TTCS:** Thêm `TTCS_CLOUDINARY_UPLOAD_FOLDER="ttcs"` vào `.env` gốc.
- [x] Thêm `.env.nmaiex` vào `.gitignore`.
- [x] Tạo `app/core/nmaiex_config.py` dùng `pydantic_settings`, đọc `.env.nmaiex` (Chỉ chứa `upload_folder` + Weights + Limits, **KHÔNG** chứa API Keys LLM hay Cloudinary credentials).
- [x] Tạo `app/core/.env.nmaiex.example` (template) để commit lên Git.

### 1d. Fix TTCS Break Points
- [x] Kiểm tra `app/services/cv_parser.py` và `cv_parser_adapters.py`: Xác nhận nơi ghi `prov`/`location` vào DB — cập nhật để ghi `provId` thay vì string.
- [x] Kiểm tra `app/services/rag_query.py` và `markdown_builder.py`: Sửa query/build-string đang đọc `prov` string → JOIN với `PROVINCE` để lấy `provName`.
- [x] Chạy lại `scripts/reset_and_seed_db.py` — xác nhận DB reset thành công không lỗi FK.
- [x] Chạy smoke test: `POST /v2/ingest`, `POST /v2/chat` — xác nhận TTCS không bị gãy.

---

## Phase 2: Core Ranking Engine

- [ ] Tạo `app/services/nmaiex_mapper_service.py`:
  - **Tái dùng toàn bộ `invoke_generation(messages, "auto-lite")`** của TTCS.
  - Về vấn đề Billing: Quản lý linh hoạt bằng cách khai báo 2 bộ API Key (TTCS và NMAIex) ngay trong file `.env` gốc, và chủ động comment/uncomment để switch luồng billing khi cần. Không làm phức tạp hóa code.
  - Hàm `map_string_to_province_id(text: str) -> str | None`:
    - Fetch 34 tỉnh (sau sáp nhập 2025) từ DB, inject vào system prompt.
    - **System prompt PHẢI chặt chẽ** (xem template trong Implementation Plan §3.2): chỉ trả về provId hợp lệ, map tỉnh cũ → tỉnh mới (sáp nhập), UNKNOWN nếu không xác định được. Không giải thích, không tự tạo mã mới.
    - Parse `trace.response.strip().upper()` — trả `None` nếu là `UNKNOWN`.
  - Hàm `map_strings_to_skill_ids(skills: list[str]) -> list[int]`:
    - Gọi LLM **một lần cho cả batch** (không gọi từng kỹ năng riêng lẻ).
    - **System prompt PHẢI chặt chẽ**: chỉ trả về JSON array chứa skillId hợp lệ, không tự tạo ID mới, không thêm text ngoài array.
    - Parse JSON array trả về từ LLM — xử lý lỗi parse gracefully (trả `[]` nếu fail).

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

---

## Phase 4 (Sau khi dev xong): Chiến lược tài liệu hóa

> **Lưu ý:** Phần này KHÔNG phải task code. Claude thực hiện task (1), AI khác thực hiện task (2) và (3) sau khi dev xong.

- [ ] **(Claude — Sau Phase 3)** Viết `docs/strategy/nmaiex_ranking_strategy.md`:
  - Lý do chọn RRF + Late Fusion (thay vì Cross-Encoder thuần).
  - Triết lý Recall over Precision ở Retrieval Stage.
  - Quyết định clip [0,1] và tại sao weights tổng < 1.
  - Chính sách system prompt chặt chẽ cho mapper (chống hallucination).
  - Lý do dùng 34 tỉnh sau sáp nhập
  - Liên kết research: `[NMAIex_th_3]`, `[NMAIex_3]`.

- [ ] **(Claude — Liên tục trong quá trình dev)** Cập nhật `agent_workflow_doc/[NMAIex]_DOC_UPDATE_INSTRUCTIONS.md` với hướng dẫn cho AI tài liệu.

- [ ] **(AI tài liệu — Sau Phase 4 frontend xong)** Thực hiện theo `[NMAIex]_DOC_UPDATE_INSTRUCTIONS.md`:
  - Viết `docs/guide/nmaiex_ranking_guide.md`.
  - Cập nhật `docs/strategy/README.md`, `docs/guide/README.md`.
  - Cập nhật `Fang/README.md` để nhắc đến NMAIex extension.


# [NMAIex] Checklist Backend (FANG AI Core)

Tài liệu checklist thực thi. AI Agent tick `[x]` khi hoàn thành, `[/]` khi đang làm.
Tham chiếu: `[NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md`

---

## Phase 1: Database & Cấu Hình

### 1a. Schema Mới
- [x] Thêm bảng `REGION` và `PROVINCE` vào `database/schema_web_core.sql` (**đặt trước** bảng `user` và `COMPANY` để tránh lỗi FK).
- [x] Thêm bảng `JOBLEVEL` (có cột `minYears`, `maxYears`) vào `schema_web_core.sql`.
- [x] Thêm bảng `JOBCATEGORY` vào `schema_web_core.sql`.
- [x] Thêm bảng nối `JOB_LEVEL_MAP` (jobPostId, levelId) vào `schema_web_core.sql`.
- [x] Thêm bảng nối `JOB_CATEGORY_MAP` (jobPostId, catId) vào `schema_web_core.sql`.
- [x] Thêm cột `provId VARCHAR(20) FK → PROVINCE` vào bảng `user`, `COMPANY`, `JOBPOSTING`.
  - *Giữ lại `workLoc` cho mục đích display text (VD: "Tầng 15, Keangnam, Hà Nội").*
  - *Xóa cột `prov` (string tự do) khỏi `user` và `COMPANY`.*
- [ ] **[Mới — Strategy C]** Thêm bảng `CANDIDATE_SKILL_RAW` vào `schema_web_core.sql` sau `CANDIDATESKILL`:
  ```sql
  CREATE TABLE CANDIDATE_SKILL_RAW (
      rawId      SERIAL PRIMARY KEY,
      candId     INT NOT NULL REFERENCES CANDIDATE(candId) ON DELETE CASCADE,
      rawText    VARCHAR(200) NOT NULL,
      embedding  vector(256),   -- dims = NMAIEX_SKILL_EMBEDDING_DIMS (default 256)
      createdAt  TIMESTAMPTZ DEFAULT NOW()
  );
  CREATE INDEX idx_cand_skill_raw_cand ON CANDIDATE_SKILL_RAW(candId);
  ```
- [ ] **[Mới — Strategy C]** Thêm bảng `JOB_SKILL_RAW` vào `schema_web_core.sql` sau `CANDIDATE_SKILL_RAW`:
  ```sql
  CREATE TABLE JOB_SKILL_RAW (
      rawId      SERIAL PRIMARY KEY,
      jobPostId  INT NOT NULL REFERENCES JOBPOSTING(jobPostId) ON DELETE CASCADE,
      rawText    VARCHAR(200) NOT NULL,
      embedding  vector(256),   -- cùng dims với CANDIDATE_SKILL_RAW (cần khớp để cosine có nghĩa)
      createdAt  TIMESTAMPTZ DEFAULT NOW()
  );
  CREATE INDEX idx_job_skill_raw_job ON JOB_SKILL_RAW(jobPostId);
  ```
  *HR có text-free skill input → `JOB_SKILL_RAW` được tạo ngay, không DEFER.*
- [ ] **[Mới — Embedding Config]** Thêm `NMAIEX_SKILL_EMBEDDING_DIMS=256` vào `.env.nmaiex` và `nmaiex_config.py`:
  - `nmaiex_skill_embedding_dims: int = 256` trong `NMAIexSettings`.
  - `reset_and_seed_db.py` đọc giá trị này và sinh SQL `vector(N)` động khi CREATE TABLE.
  - `embed_and_store_raw_skills` truyền `dimensions=nmaiex_settings.nmaiex_skill_embedding_dims`.

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

- [x] Tạo `app/services/nmaiex_mapper_service.py`:
  - **Tái dùng toàn bộ `invoke_generation(messages, "auto-lite")`** của TTCS.
  - Hàm `map_string_to_province_id(text: str) -> str | None` — wrap output vào `ProvinceMappingResult` (Pydantic).
  - **[Đã thành `map_skills` — xem bên dưới]** ~~Hàm `map_strings_to_skill_ids`~~.

- [ ] **[Mới — Upgrade Mapper]** Nâng cấp `nmaiex_mapper_service.py` lên Pydantic-validated output:
  - Thêm `SkillMappingResult(matched_ids, unmatched_texts)` vào `app/models/nmaiex_schemas.py`.
  - Thêm `ProvinceMappingResult(prov_id)` vào `app/models/nmaiex_schemas.py`.
  - **Đổi** `map_strings_to_skill_ids` → `map_skills(skills, cand_id, conn) -> SkillMappingResult`.
    - Prompt mới: LLM trả `{"matched_ids": [...], "unmatched_texts": [...]}` (phân loại matched và unmatched).
    - Validate bằng `SkillMappingResult.model_validate_json(response)` — graceful degradation nếu fail.
  - **Thêm** hàm `embed_and_store_raw_skills(entity_type, entity_id, unmatched_texts, conn)`:
    - `entity_type = "candidate"` → INSERT vào `CANDIDATE_SKILL_RAW`.
    - `entity_type = "job"` → INSERT vào `JOB_SKILL_RAW` (dùng cho HR text-free skill input).
    - Gọi `embed_chunks(unmatched_texts)` với `dimensions=nmaiex_settings.nmaiex_skill_embedding_dims`.


- [x] Tạo `app/services/nmaiex_ranking_service.py`:
  - **Hard Filter SQL**: Lọc `provId` và `workMode` ngay trong SQL trước khi vector search.
  - **Vector HNSW**: Truy vấn `AIDOCUMENTCHUNK` top-K (K = limit × 5) bằng cosine distance.
  - **Text Match**: Dùng `ts_rank` (PostgreSQL full-text) từ `JOBPOSTING.description` vs `CVPARSED.rawText`.
  - **RRF Score**: `1/(k + rank_vector) + 1/(k + rank_text)` với `k` từ `nmaiex_settings.nmaiex_rrf_k`.
  - **Skill Overlap (Exact)**: `|Job Skills ∩ Candidate Skills| / |Job Skills|` từ `JOBREQUIREMENT` và `CANDIDATESKILL`.
  - **Seniority Penalty** (J→C): gap giữa `JOBLEVEL.minYears` của job và `CANDIDATE.expyears` × `penalty_seniority_coef`.
  - **Salary Gap Penalty** (C→J): gap giữa `JOBPOSTING.minSalary` và salary expectation ứng viên.
  - **Late Fusion**: `final_score = clip(w_rrf*rrf + w_skill*skill_score - penalty, 0.0, 1.0)`.
  - **score_breakdown**: dict chi tiết từng thành phần để debug (luôn trả về, UI tự ẩn/hiện).

- [ ] **[Mới — Strategy C Ranking]** Nâng cấp `nmaiex_ranking_service.py` với Tiered Skill Scoring:
  - Hàm `compute_skill_score(job_skill_ids, cand_skill_ids, job_post_id, cand_id, conn, alpha=0.8)`:
    - **Exact overlap**: `|job_ids ∩ cand_ids| / max(|job_ids|, 1)`
    - **Fuzzy overlap**: Lấy `embedding` từ `CANDIDATE_SKILL_RAW` (cand) và `JOB_SKILL_RAW` (job, hiện tại luôn rỗng vì HR dùng dropdown). Tính `avg_max_cosine`. Nếu một bên rỗng → fuzzy=0.0.
    - **skill_score = 0.8 * exact + 0.2 * fuzzy**
  - Thêm `exact_overlap`, `fuzzy_overlap`, `skill_alpha` vào `score_breakdown`.
  - Thêm `NMAIEX_SKILL_ALPHA=0.8` vào `.env.nmaiex` và `nmaiex_config.py`.

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


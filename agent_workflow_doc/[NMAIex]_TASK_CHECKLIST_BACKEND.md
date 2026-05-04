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
- [x] **[Mới — Strategy C]** Thêm bảng `CANDIDATE_SKILL_RAW` vào `schema_web_core.sql` sau `CANDIDATESKILL` (dung placeholder `vector(__NMAIEX_SKILL_EMBEDDING_DIM__)`)
- [x] **[Mới — Strategy C]** Thêm bảng `JOB_SKILL_RAW` vào `schema_web_core.sql` sau `CANDIDATE_SKILL_RAW` (cùng dims placeholder)
  *HR có text-free skill input → `JOB_SKILL_RAW` được tạo ngay, không DEFER.*
- [x] **[Mới — Embedding Config]** Thêm `NMAIEX_SKILL_EMBEDDING_DIMS=256` và `NMAIEX_SKILL_ALPHA=0.8` vào `.env.nmaiex` và `nmaiex_config.py`:
  - `nmaiex_skill_embedding_dims: int = 256` trong `NMAIexSettings`.
  - `nmaiex_skill_alpha: float = 0.8` trong `NMAIexSettings`.
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

### 1b. Chuẩn Hóa Hạ Tầng (Infrastructure Standardization)
- [x] Refactor `app/services/embedding.py`: Thêm tham số `dimensions: Optional[int] = None` vào `embed_chunks` và fallback về `settings.embedding_dim`.
- [x] Cập nhật `database/schema_ai_core.sql`: Đổi `halfvec(1024)` thành `halfvec(__TTCS_EMBEDDING_DIM__)`.
- [x] Cập nhật `database/schema_web_core.sql`: Đổi `vector(256)` thành `vector(__NMAIEX_SKILL_EMBEDDING_DIM__)` cho bảng `CANDIDATE_SKILL_RAW` và `JOB_SKILL_RAW`.
- [x] Cập nhật `scripts/reset_and_seed_db.py`: Bổ sung hàm `inject_embedding_dims()` thực hiện string replace các placeholder (`__TTCS_EMBEDDING_DIM__`, `__NMAIEX_SKILL_EMBEDDING_DIM__`) bằng giá trị thực tế từ `.env`.

### 1c. Cấu Hình NMAIex
- [x] Tạo file `.env.nmaiex` tại root FANG (theo template trong Implementation Plan).
  - **Cloudinary dùng chung:** Credentials (`CLOUD_NAME`, `API_KEY`, `API_SECRET`) và `CLOUDINARY_UPLOAD_FOLDER` đặt ở `.env` gốc. Không cần khai báo lại ở `.env.nmaiex` (NMAIex là phần của AI layer hỗ trợ TTCS).
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

- [x] **[Mới — Upgrade Mapper]** Nâng cấp `nmaiex_mapper_service.py` lên Pydantic-validated output:
  - [x] Thêm `SkillMappingResult(matched_ids, unmatched_texts)` vào `app/models/nmaiex_schemas.py`.
  - [x] Thêm `ProvinceMappingResult(prov_id)` vào `app/models/nmaiex_schemas.py`.
  - [x] **Đổi** `map_strings_to_skill_ids` → `map_skills(skills) -> SkillMappingResult`.
    - Prompt mới: LLM trả `{"matched_ids": [...], "unmatched_texts": [...]}` (phân loại matched và unmatched).
    - Validate bằng `SkillMappingResult.model_validate_json(response)` — graceful degradation nếu fail.
  - [x] **Thêm** hàm `embed_and_store_raw_skills(entity_type, entity_id, unmatched_texts, conn)`:
    - `entity_type = "candidate"` → INSERT vào `CANDIDATE_SKILL_RAW`.
    - `entity_type = "job"` → INSERT vào `JOB_SKILL_RAW` (dùng cho HR text-free skill input).
    - Gọi `embed_chunks(unmatched_texts)` với `dimensions=nmaiex_settings.nmaiex_skill_embedding_dims`.

- [x] Tạo `app/services/nmaiex_ranking_service.py`:
  - **Hard Filter SQL**: Lọc `provId` và `workMode` ngay trong SQL trước khi vector search.
  - **Vector HNSW**: Truy vấn `AIDOCUMENTCHUNK` top-K (K = limit × 5) bằng cosine distance.
  - **Text Match**: Dùng `ts_rank` (PostgreSQL full-text) từ `JOBPOSTING.description` vs `CVPARSED.rawText`.
  - **RRF Score**: `1/(k + rank_vector) + 1/(k + rank_text)` với `k` từ `nmaiex_settings.nmaiex_rrf_k`.
  - [x] **[Mới — Strategy C Ranking]** Nâng cấp `nmaiex_ranking_service.py` với Tiered Skill Scoring:
    - [x] Hàm `compute_skill_score(job_skill_ids, cand_skill_ids, job_post_id, cand_id, conn, alpha)`:
      - **Exact overlap**: `|job_ids ∩ cand_ids| / max(|job_ids|, 1)`
      - **Fuzzy overlap**: Tính `avg_max_cosine` qua PostgreSQL CROSS JOIN giữa `CANDIDATE_SKILL_RAW` và `JOB_SKILL_RAW`. Nếu một bên rỗng → fuzzy=0.0.
      - **skill_score = alpha * exact + (1-alpha) * fuzzy**
    - [x] Thêm `exact_overlap`, `fuzzy_overlap`, `skill_score`, `skill_alpha` vào `score_breakdown`.
    - [x] Thêm `NMAIEX_SKILL_ALPHA=0.8` vào `.env.nmaiex` và `nmaiex_config.py`.
  - **Seniority Penalty** (J→C): Asymmetric Buffer-based penalty. Xem chi tiết tại `[NMAIex]_SENIORITY_PENALTY_PROPOSAL.md`. Đã implement.
  - **Salary Gap Penalty** (C→J): placeholder, chưa implement đầy đủ (xẻ Issue #3 trong Phase 2.5).
  - **Late Fusion**: `final_score = clip(w_rrf*rrf + w_skill*skill_score - penalty, 0.0, 1.0)`.
  - **score_breakdown**: dict chi tiết từng thành phần để debug (luôn trả về, UI tự ẩn/hiện).

---

## Phase 2.5: C→J Flow Optimization & Language System (2026-05-01)

> Tham chiếu: `[NMAIex]_CJ_FLOW_OPTIMIZATION_REPORT.md`, `[NMAIex]_SENIORITY_PENALTY_PROPOSAL.md`, Mục 11-12 trong `DETAILED_IMPLEMENTATION_PLAN.md`.

### 2.5a. Fix Weight Bug (Issue #1 & #2)
- [x] Thêm `NMAIEX_CJ_WEIGHT_SKILL=0.30` vào `.env.nmaiex`.
- [x] Thêm `nmaiex_cj_weight_skill: float = 0.30` vào `app/core/nmaiex_config.py`.
- [x] Sửa `nmaiex_ranking_service.py` hàm `rank_jobs_for_candidate()` dòng 392-394: đổi `nmaiex_jc_weight_skill` → `nmaiex_cj_weight_skill` và enable `w_title`.

### 2.5b. Seniority Penalty — Asymmetric Buffer (Issue #0)
- [x] Implement `compute_seniority_penalty(cand_expyears, job_min_threshold, career_stage)` theo spec `[NMAIex]_SENIORITY_PENALTY_PROPOSAL.md`.
  - Thiếu kinh nghiệm: `penalty = 0.25 * gap`
  - Thừa kinh nghiệm (overqualified, vượt buffer): `penalty = 0.5 * excess * 0.5` (nhẹ hơn)
  - Rename biến `job_max_raw` → `job_level_threshold_max` cho rõ nghĩa.
- [x] Thêm `seniority_penalty`, `career_stage`, `exp_gap` vào `score_breakdown`.
- [x] Thêm config buffer tiers vào `.env.nmaiex` + `nmaiex_config.py`:

### 2.5c. Title Matching & CV Profile Enrichment (Issue #4 & #5-cert)
- [x] Cập nhật SELECT query trong `rank_jobs_for_candidate()`: thêm `cv.parsedData -> 'experience'`, `cv.parsedData -> 'certificates'`, `cv.parsedData -> 'education'`.
- [x] Build `candidate_text` enriched từ: recent_titles (3 gần nhất) + bio + certs + education degrees.
- [x] Tính `title_score` riêng (ts_rank của `recent_titles` vs `job.title`) và nhân với `w_title`.

### 2.5d. Salary Adjustment — Full Implementation (Issue #3)
- [x] Thêm `expectedSalaryMin: int | None` và `expectedSalaryMax: int | None` vào `ParsedCV` trong `app/models/cv_models.py`.
- [x] Cập nhật LLM prompt trong `app/services/cv_parser_adapters.py`: thêm hướng dẫn extract `expectedSalaryMin`/`expectedSalaryMax`. LLM trả `null` nếu không có.
- [x] Implement `estimate_expected_salary(expyears, location)` fallback dùng config tiers.
- [x] Implement `compute_salary_adjustment(job_min, job_max, expected_min, expected_max)`:
  - `NULL job salary` → return `0.0` (neutral)
  - Asymmetric: penalty nếu job thấp hơn expected, bonus nếu cao hơn (capped)
- [x] Thêm các `NMAIEX_SALARY_*` vào `.env.nmaiex` + `nmaiex_config.py` (xem Mục 11.4 trong Implementation Plan).
- [x] Tích hợp `salary_adjustment` vào `final_score` trong `rank_jobs_for_candidate()`.

### 2.5e. Language Requirement System (Issue #5-lang) — Schema
- [x] Thêm bảng `LANGUAGE` vào `database/schema_web_core.sql` (sau `JOBCATEGORY`).
- [x] Thêm bảng `JOB_LANG_REQUIREMENT` vào `database/schema_web_core.sql`.
- [x] Thêm INSERT seed data 7 ngôn ngữ vào `database/root_data.sql`.
- [x] Chạy lại `scripts/reset_and_seed_db.py` — xác nhận không lỗi FK.

### 2.5f. Language Requirement System — CV Parser Update
- [x] Thêm class `LanguageEntry(CVBaseModel)` vào `app/models/cv_models.py`.
- [x] Đổi `ParsedCV.languages: list[str]` → `list[LanguageEntry]` (**breaking change, migration cần test**).
- [x] Cập nhật LLM prompt trong `cv_parser_adapters.py`: extract `[{"language": "...", "proficiency": "..."}]`.
- [x] Test: parse lại 1 CV mẫu có ngôn ngữ → xác nhận output đúng format.

### 2.5g. Language Requirement System — Mapper & Scoring
- [x] Implement `normalize_proficiency(raw_str) -> str` trong `nmaiex_mapper_service.py`:
  - Dùng LLM mapper `invoke_generation("auto-lite")` chuẩn hóa về `BASIC|INTERMEDIATE|ADVANCED|FLUENT|NATIVE`.
- [x] Implement `compute_language_score(job_post_id, candidate_languages, conn) -> (penalty, bonus, breakdown)`.
- [x] Thêm các `NMAIEX_LANG_*` vào `.env.nmaiex` + `nmaiex_config.py`.
- [x] Tích hợp `lang_penalty`, `lang_bonus` vào `final_score` trong `rank_jobs_for_candidate()`.
- [x] Thêm `lang_breakdown` vào `score_breakdown`.

### 2.5h. Strategy Doc Note
- [x] Tạo/cập nhật `docs/strategy/nmaiex_ranking_strategy.md`: Ghi chú lý do C→J không dùng vector search (MVP scope), future plan cho JOB_EMBEDDING index.

---

## Phase 3: API & Router

- [x] Tạo `app/models/nmaiex_schemas.py`: Pydantic models (`ScoreBreakdown`, `CandidateRankResult`, `JobRankResult`, `RankingResponse`, `MasterDataItem`).
- [x] Tạo `app/api/nmaiex_routes_ranking.py`:
  - `GET /v2/nmaiex/ranking/candidates/{job_id}?limit=20&province_id=...&work_mode=...`
  - `GET /v2/nmaiex/ranking/jobs/{candidate_id}?limit=20&province_id=...&work_mode=...`
  - `GET /v2/nmaiex/master/provinces` (có nhóm theo region)
  - `GET /v2/nmaiex/master/levels`
  - `GET /v2/nmaiex/master/categories`
  - `GET /v2/nmaiex/master/skills`
- [x] Cập nhật `app/main.py`: Thêm `include_router(nmaiex_router, prefix="/v2")` — **KHÔNG** sửa các router TTCS hiện có.
- [x] Kiểm tra: `GET /v2/nmaiex/ranking/candidates/1?limit=10` trả về JSON hợp lệ với `score_breakdown`.

---

## Phase 4 (Sau khi dev xong): Chiến lược tài liệu hóa

> **Lưu ý:** Phần này KHÔNG phải task code. Claude thực hiện task (1), AI khác thực hiện task (2) và (3) sau khi dev xong.

- [x] **(Claude — Sau Phase 3)** Viết `docs/strategy/nmaiex_ranking_strategy.md`:
  - Lý do chọn RRF + Late Fusion (thay vì Cross-Encoder thuần).
  - Triết lý Recall over Precision ở Retrieval Stage.
  - Quyết định clip [0,1] và tại sao weights tổng < 1.
  - Chính sách system prompt chặt chẽ cho mapper (chống hallucination).
  - Lý do dùng 34 tỉnh sau sáp nhập
  - Liên kết research: `[NMAIex_th_3]`, `[NMAIex_3]`.

- [x] **(Claude — Liên tục trong quá trình dev)** Cập nhật `agent_workflow_doc/[NMAIex]_DOC_UPDATE_INSTRUCTIONS.md` với hướng dẫn cho AI tài liệu.

- [x] **(AI tài liệu — Sau Phase 4 frontend xong)** Thực hiện theo `[NMAIex]_DOC_UPDATE_INSTRUCTIONS.md`:
  - Viết `docs/guide/nmaiex_ranking_guide.md`.
  - Cập nhật `docs/strategy/README.md`, `docs/guide/README.md`.
  - Cập nhật `Fang/README.md` để nhắc đến NMAIex extension.


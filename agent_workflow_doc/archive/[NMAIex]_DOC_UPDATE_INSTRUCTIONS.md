# [NMAIex] Hướng Dẫn Cập Nhật Tài Liệu (Cho AI Tài Liệu Hóa)

> **Đây là living document.** Claude (AI dev) cập nhật file này liên tục trong quá trình triển khai NMAIex.
> AI tài liệu hóa đọc file này và thực hiện toàn bộ sau khi dev xong (sau Phase 4 Frontend).

---

## Nguyên Tắc Đọc File Này

1. Đọc `docs/strategy/README.md` và `docs/guide/README.md` để hiểu nguyên tắc biên soạn.
2. Đọc các file hiện có trong `docs/strategy/` và `docs/guide/` để nắm tone, format.
3. Thực hiện **tuần tự** các mục bên dưới theo thứ tự được đánh số.
4. KHÔNG thay đổi nội dung các file TTCS hiện có — chỉ **thêm** section NMAIex hoặc cập nhật index.

---

## Phần A: Tài Liệu MỚI Cần Tạo

### A1. `docs/strategy/nmaiex_ranking_strategy.md`

**Người tạo:** Claude (AI dev) — tạo sau khi hoàn thành Phase 3 (API & Router).

**Nội dung cần có:**
- Bối cảnh: NMAIex là extension của FANG, phục vụ đề tài "Xây dựng hệ thống AI gợi ý việc làm và xếp hạng ứng viên".
- Tại sao chọn kiến trúc hai chiều (J→C và C→J)?
- Tại sao chọn RRF + Late Fusion thay vì Cross-Encoder thuần? (trade-off latency vs accuracy)
- Triết lý "Recall over Precision" ở Retrieval Stage — tại sao thà chọn thừa?
- Quyết định clip `final_score` về `[0, 1]` — lý do đầy đủ (xem `.env.nmaiex`).
- Tại sao `w_rrf + w_skill < 1` (buffer cho penalty, phòng vệ bonus tương lai)?
- Chính sách system prompt chặt chẽ cho LLM mapper — tại sao cần và rủi ro hallucination.
- Lý do dùng 34 tỉnh sau sáp nhập 2025
- Cloudinary dùng chung: lý do và cơ chế tách folder (Home/ttcs vs Home/nmaiex).
- Tham chiếu research: `docs/research/[NMAIex_th_3]`, `docs/research/[NMAIex_3]`.

**Format:** Theo chuẩn strategy (xem `rag_query_strategy.md`): heading rõ, có mermaid diagram nếu cần, giải thích trade-off.

---

### A2. `docs/guide/nmaiex_ranking_guide.md`

**Người tạo:** AI tài liệu — tạo sau khi Phase 4 Frontend hoàn thành.

**Nội dung cần có (theo chuẩn guide — trả lời "Làm thế nào?"):**

#### 1. Thiết lập môi trường NMAIex
- Tạo `.env.nmaiex` (copy từ `.env.nmaiex.example`) với ranking weights và limits.
- Cloudinary credentials (`CLOUD_NAME`, `API_KEY`, `API_SECRET`, `CLOUDINARY_UPLOAD_FOLDER`) đã có trong `.env` gốc — không cần thêm.
- Cấu trúc folder Cloudinary: `Home/ttcs` (TTCS), `Home/nmaiex` (NMAIex). Thay đổi `CLOUDINARY_UPLOAD_FOLDER` ở `.env` khi cần switch project.

#### 2. Reset DB với schema NMAIex
- Chạy `scripts/reset_and_seed_db.py`.
- Xác nhận thứ tự: `REGION → PROVINCE → user/COMPANY/JOBPOSTING`.
- Kiểm tra 34 tỉnh (sau sáp nhập) đã có trong bảng PROVINCE.

#### 3. Test API Ranking
- `GET /v2/nmaiex/ranking/candidates/{job_id}` — tham số, response format.
- `GET /v2/nmaiex/ranking/jobs/{candidate_id}` — tham số, response format.
- `GET /v2/nmaiex/master/provinces` — dropdown data cho frontend.
- Bật Dev Mode: set `VITE_DEV_MODE=true` để xem `score_breakdown` trên UI.

#### 4. Mapper LLM — Cách vận hành
- Province mapper: input là text tự do → output là provId (34 tỉnh mới).
- Xử lý tỉnh cũ đã sáp nhập: ví dụ 'Hải Dương' → `HAIPHONG`, 'Bình Dương' → `TPHCM`.
- Skill mapper: input là list string → output là JSON array skillId.
- Lưu ý: Gọi batch (cả list) để tiết kiệm chi phí.

#### 5. Kiểm thử nhanh (Smoke Test)
- `POST /v2/ingest` → `POST /v2/chat` — xác nhận TTCS không bị gãy.
- `GET /v2/nmaiex/ranking/candidates/1?limit=10` — xác nhận NMAIex hoạt động.

**Format:** Theo chuẩn guide (xem `rag_query_guide.md`): ngắn gọn, thực thi ngay, có code snippet.

---

## Phần B: Cập Nhật Tài Liệu Hiện Có

### B1. `docs/strategy/README.md`
**Thêm vào cuối phần "Phạm vi chính":**
```
- [NMAIex] Chiến lược xếp hạng hai chiều (J→C, C→J): RRF, Late Fusion, Penalty design.
- [NMAIex] Chính sách LLM mapper: System prompt design, chống hallucination.
```

### B2. `docs/guide/README.md`
**Thêm vào cuối phần "Phạm vi chính":**
```
- [NMAIex] Hướng dẫn vận hành hệ thống xếp hạng ứng viên và gợi ý việc làm.
```

### B3. `Fang/README.md`
**Tìm section mô tả hệ thống, thêm ghi chú:**
```
> **NMAIex Extension:** FANG tích hợp thêm phân hệ NMAIex (Nhập môn AI extension) — hệ thống
> xếp hạng ứng viên hai chiều (J→C, C→J) dựa trên RRF + Late Fusion. Xem:
> - Chiến lược: `docs/strategy/nmaiex_ranking_strategy.md`
> - Hướng dẫn: `docs/guide/nmaiex_ranking_guide.md`
```

---

## Phần C: Log Thay đổi (Claude cập nhật khi dev)

> Claude điền vào đây sau mỗi thay đổi code quan trọng để AI tài liệu biết cần phản ánh vào đâu.

| Ngày | Thay đổi | File ảnh hưởng | Cần tài liệu hóa ở |
|---|---|---|---|
| 2026-04-29 | Tạo `nmaiex_mapper_service.py` v1 + `nmaiex_ranking_service.py` v1 (RRF + Late Fusion cơ bản). Tạo `nmaiex_config.py`, `.env.nmaiex`, schema cơ bản | `nmaiex_mapper_service.py`, `nmaiex_ranking_service.py`, `nmaiex_config.py`, `.env.nmaiex`, `schema_web_core.sql`, `root_data.sql` | A1 (ranking strategy), guide mục 4 (mapper), mục 3 (test API) |
| 2026-04-30 | **Phase 1b**: Refactor `embedding.py` thêm `dimensions` param (Matryoshka). Schema placeholder `__TTCS_EMBEDDING_DIM__` và `__NMAIEX_SKILL_EMBEDDING_DIM__`. Reset script inject dims. Thêm `CANDIDATE_SKILL_RAW` + `JOB_SKILL_RAW` vào schema. | `embedding.py`, `schema_ai_core.sql`, `schema_web_core.sql`, `reset_and_seed_db.py`, `.env.nmaiex`, `nmaiex_config.py` | A2 (guide mục 1: reset DB), B3 (README nhắc đến NMAIex) |
| 2026-04-30 | **Phase 2 Upgrade**: Tạo `nmaiex_schemas.py` (Pydantic models). Nâng cấp mapper lên Pydantic-validated `map_skills` + Tier-2 `embed_and_store_raw_skills`. Nâng cấp ranking với `compute_skill_score` (exact + fuzzy cosine). `score_breakdown` bổ sung `exact_overlap`, `fuzzy_overlap`, `skill_score`, `skill_alpha`. | `nmaiex_mapper_service.py`, `nmaiex_ranking_service.py`, `app/models/nmaiex_schemas.py` | A1 (chiến lược Strategy C, Tiered Skill), A2 (guide mục 4: mapper 2 tầng), A2 (guide mục 3: score_breakdown) |

| 2026-05-01 | **Phase 2.5 Optimization**: Sửa lỗi logic w_skill của luồng C→J. Implement Asymmetric Seniority Penalty theo career path buffer. Thêm extract Title/Cert/Edu/Language/Salary từ CV (đổi ParsedCV.languages sang model mới). Code hàm penalty salary và language. Tích hợp full C→J (Title match + RRF + Score adjustment). Tạo nmaiex_ranking_strategy.md. | pp/services/nmaiex_ranking_service.py, pp/services/cv_parser_adapters.py, pp/models/cv_models.py, database/schema_web_core.sql, docs/strategy/nmaiex_ranking_strategy.md | A1 (giải thích Ranking Score, Penalty Salary & Language, Asymmetric Buffer), A2 (guide mục score_breakdown) |

---

*File này được tạo ngày 2026-04-29. Claude cập nhật Phần C liên tục. AI tài liệu đọc và thực hiện Phần A + B sau khi toàn bộ dev hoàn tất.*

# Hướng Dẫn Vận Hành NMAIex Ranking Engine

Tài liệu này hướng dẫn chi tiết về cách thức hoạt động, cấu hình và các điểm cần lưu ý khi làm việc với hệ thống xếp hạng hai chiều NMAIex

Tham chiếu chiến lược: `../strategy/nmaiex_ranking_strategy.md`

---

## 1. Cấu Trúc Module

```
app/
├── api/
│   └── nmaiex_routes_ranking.py   # API endpoints, thin wrapper
├── services/
│   ├── nmaiex_ranking_service.py  # Core logic: RRF, Late Fusion, Penalty
│   └── nmaiex_mapper_service.py   # LLM mapper: Province, Skill, Language
├── models/
│   └── nmaiex_schemas.py          # Pydantic models: RankingResponse, ScoreBreakdown
└── core/
    └── nmaiex_config.py           # NMAIexSettings — đọc từ .env.nmaiex
```

Router được mount tại `app/main.py`:
```python
app.include_router(nmaiex_router, prefix="/v2/nmaiex")
```

Các TTCS router (`/v2/chat`, `/v2/ingest`) **không bị sửa**.

---

## 2. Pipeline Thực Thi — Luồng J→C

Khi một request đến `GET /v2/nmaiex/ranking/candidates/{job_id}`:

1. **Fetch Job**: Lấy `title`, `description`, `minSalary`, `maxSalary` từ `JOBPOSTING`.
2. **Fetch Job Skills (Tầng 1)**: Lấy `skillId[]` từ `JOBREQUIREMENT` — đây là exact matching set.
3. **Fetch Job Level**: Lấy `minYears` từ `JOB_LEVEL_MAP → JOBLEVEL`, tính `job_min` và `job_max` (đã cộng buffer theo career tier).
4. **Embed Job Text**: Gọi `embed_chunks([title + description])` → vector HNSW query.
5. **Hard Filter SQL**: Lọc `user.stat = 'ACTIVE'` + optional `provId`, `workMode`.
6. **Vector HNSW Search**: Truy vấn `AIDOCUMENTCHUNK` — tìm CV chunks gần nhất theo cosine distance. Group by `jobAppId`, lấy `MIN(distance)`.
7. **Full-text ts_rank**: Song song với vector search, tính `ts_rank(cv.rawText, job_text)`.
8. **RRF Fusion**: Kết hợp `vector_rank` và `text_rank` → `rrf_score_norm`.
9. **Tiered Skill Scoring**: Tính `skill_score` từ exact overlap + fuzzy cosine (xem Mục 4).
10. **Seniority Penalty**: Tính penalty asymmetric dựa vào `c.expyears` so với `[job_min, job_max]`.
11. **Late Fusion**: `final_score = w_rrf × rrf + w_skill × skill − seniority_penalty` (raw score, không clip mặc định)
12. **Sort & Return**: Sắp xếp giảm dần `final_score`, cắt theo `limit`, đính kèm `score_breakdown`.

---

## 3. Pipeline Thực Thi — Luồng C→J

Khi một request đến `GET /v2/nmaiex/ranking/jobs/{candidate_id}`:

1. **Fetch Candidate**: Lấy `expyears`, `bio`, `provId` + `parsedData` (JSON) từ CV gần nhất qua `LatestApp` CTE.
2. **Enrich Candidate Profile**: Parse `parsedData` → lấy `experience[].title` (3 gần nhất), `certificates`, `education[].degree`. Build `candidate_text` tổng hợp — đây là đầu vào cho FTS. Lý do: `rawText` quá dài và loãng, `recent_titles` là tín hiệu relevance tập trung nhất.
3. **Salary Expectation**: Nếu CV có `expectedSalaryMin/Max` → dùng để tính ra trọng số (cơ chế giống khoảng seniority penalty). Nếu không → `estimate_expected_salary(expyears, location)` từ config salary tiers -> tính tương tự.
4. **Fetch Candidate Skills (Tầng 1)**: Lấy `skillId[]` từ `CANDIDATESKILL`.
5. **Hard Filter SQL**: Lọc job còn hạn (`expAt > CURRENT_TIMESTAMP`) + optional `provId`, `workMode`.
6. **Full-text ts_rank (2 truy vấn)**: Tính `text_rank` (candidate_text vs job description) và `title_rank` (recent_titles vs job title) riêng biệt.
7. **RRF Fusion**: C→J không có vector search — chỉ dùng `text_rank` làm đầu vào RRF, `title_rank` tính riêng.

   > **Lưu ý**: C→J không có vector search là **quyết định có chủ ý**. Index `AIDOCUMENTCHUNK` được xây theo chiều "CV gần Job nào", không tối ưu ngược. Với pool job nhỏ ở MVP, FTS là đủ. Future: thêm `JOB_EMBEDDING` table khi scale >1000 jobs.

8. **Tiered Skill Scoring**: Tương tự J→C nhưng chiều ngược.
9. **Salary Adjustment**: `compute_salary_adjustment(job.minSalary, job.maxSalary, expected_salary)` — âm nếu job trả thấp hơn kỳ vọng, dương nếu cao hơn (cap 0.2).
10. **Language Scoring**: `compute_language_score(job_post_id, cand_languages, conn)` — query `JOB_LANG_REQUIREMENT` (Đã có DB/Scoring), so sánh với proficiency của ứng viên (Lưu ý: hiện tại code thực tế đang so khớp trực tiếp trong dictionary, chưa gọi LLM normalize_proficiency).
11. **Late Fusion**: `final_score = w_rrf×rrf + w_title×title + w_skill×skill + salary_adj − lang_penalty + lang_bonus` (raw score, không clip mặc định)
12. **Sort & Return**: Tương tự J→C.

---

## 4. Tiered Skill Scoring — Hàm `compute_skill_score`

Hàm `compute_skill_score(job_skill_ids, cand_skill_ids, job_post_id, cand_id, conn, alpha)` trong `nmaiex_ranking_service.py`:

**Tầng 1 — Exact Overlap (Closed-World)**:
```
exact_overlap = |job_ids ∩ cand_ids| / max(|job_ids|, 1)
```
Dùng Python set intersection — chi phí O(n).

**Tầng 2 — Fuzzy Overlap (Open-World)**:
- Query `JOB_SKILL_RAW` và `CANDIDATE_SKILL_RAW` — chứa vector embedding (256-dim) của skills không có trong catalog.
- Tính `avg_max_cosine` bằng SQL CROSS JOIN trực tiếp trên PostgreSQL — không round-trip Python.
- Trả `0.0` nếu một trong hai bên rỗng (không có raw skills).

```sql
SELECT AVG(max_sim) FROM (
    SELECT MAX(1 - (j.embedding <=> c.embedding)) as max_sim
    FROM JOB_SKILL_RAW j
    CROSS JOIN CANDIDATE_SKILL_RAW c
    WHERE j.jobPostId = $1 AND c.candId = $2
      AND j.embedding IS NOT NULL AND c.embedding IS NOT NULL
    GROUP BY j.rawId
) sub
```

**Tổng hợp**:
```
skill_score = α × exact_overlap + (1 − α) × fuzzy_overlap
```
`α = nmaiex_settings.nmaiex_skill_alpha` (default 0.8).

---

## 5. LLM Mapper — Mapper Service

`nmaiex_mapper_service.py` tái dùng `invoke_generation(messages, "auto-lite")` của TTCS — không có LLM wrapper riêng cho NMAIex.

### Province Mapper — `map_string_to_province_id(text)`
- Fetch toàn bộ `PROVINCE` từ DB lúc runtime → inject vào system prompt.
- LLM trả duy nhất một `provId` hoặc `UNKNOWN`.
- Validate bằng `ProvinceMappingResult` — fail → trả `None` (graceful, không crash).

### Skill Mapper — `map_skills(skills: list[str])`
- Fetch toàn bộ `SKILL` từ DB → inject vào system prompt.
- LLM trả JSON `{"matched_ids": [...], "unmatched_texts": [...]}`.
- Validate bằng `SkillMappingResult.model_validate_json()`.
- **Graceful degradation**: Nếu LLM trả output không hợp lệ → toàn bộ skills chuyển sang `unmatched_texts`, tính tiếp Tầng 2. Không bao giờ crash pipeline.

### Language Proficiency Normalizer — `normalize_proficiency(raw)`
> [!WARNING]
> **Active Discrepancy / Gap:** Hàm `normalize_proficiency()` đã được triển khai dưới dạng helper utility sử dụng LLM auto-lite trong `app/services/nmaiex_mapper_service.py`. Tuy nhiên, trong runtime pipeline hiện tại của Ranking Service (`app/services/nmaiex_ranking_service.py`), hàm này **CHƯA ĐƯỢC GỌI**.
>
> Code thực tế thực hiện so khớp trực tiếp bằng dictionary tra cứu:
> ```python
> prof = cl.get("proficiency", "BASIC")
> cand_lang_map[code] = PROFICIENCY_LEVELS.get(prof, 1)
> ```
> Do đó, các chuỗi trình độ thô từ CV không khớp chính xác các key chuẩn (`BASIC`, `INTERMEDIATE`, etc.) như `"N3"`, `"IELTS 7.5"` sẽ tự động bị fallback về mức `1` (`"BASIC"`). Đây là một gap đã được ghi nhận để xử lý trong Tier-1 tiếp theo (Phase 2.5 / P0-C).

Dưới đây là thiết kế/quy tắc chuẩn hóa dự kiến khi tích hợp đầy đủ `normalize_proficiency(raw)`:
- Fast path: Nếu đã là chuẩn (`BASIC|INTERMEDIATE|ADVANCED|FLUENT|NATIVE`) → return ngay, không gọi LLM.
- LLM map các dạng như `"N3"`, `"IELTS 7.5"`, `"Business level"` → chuẩn hóa. Mapping tham khảo:

  | Input mẫu | Output chuẩn |
  |---|---|
  | N5, A1, Sơ cấp, Beginner | `BASIC` |
  | N3, N4, B1, B2, Conversational, Trung cấp | `INTERMEDIATE` |
  | N2, C1, IELTS 6.5–7.5, Business level, Khá | `ADVANCED` |
  | N1, C2, IELTS 8+, Fluent, Thành thạo | `FLUENT` |
  | Native speaker, Tiếng mẹ đẻ, Mother tongue | `NATIVE` |

- Fallback về `BASIC` nếu LLM fail hoặc không xác định được.
- **Lưu ý**: System prompt LLM được thiết kế chặt để tránh hallucination — có ví dụ cụ thể cho từng dải điểm, rõ ràng về boundary.
---

## 6. Cấu Hình — `nmaiex_config.py` & `.env.nmaiex`

`NMAIexSettings` đọc từ `.env.nmaiex` (không commit). Template tại `.env.nmaiex.example`.

Các nhóm cấu hình chính:

| Nhóm | Ví dụ biến | Mô tả |
|---|---|---|
| **Weights J→C** | `NMAIEX_JC_WEIGHT_RRF=0.30`, `NMAIEX_JC_WEIGHT_SKILL=0.40` | Tổng < 1 là có chủ ý — room cho seniority penalty |
| **Weights C→J** | `NMAIEX_CJ_WEIGHT_RRF=0.35`, `NMAIEX_CJ_WEIGHT_TITLE=0.15`, `NMAIEX_CJ_WEIGHT_SKILL=0.30` | Room 0.20 cho salary + language |
| **RRF** | `NMAIEX_RRF_K=60` | Hằng số làm mịn trong công thức RRF |
| **Skill** | `NMAIEX_SKILL_ALPHA=0.8`, `NMAIEX_SKILL_EMBEDDING_DIMS=256` | α=0.8 ưu tiên exact; 256 dims đủ cho text ngắn |
| **Seniority Buffer** | `NMAIEX_BUFFER_JUNIOR=3`, `NMAIEX_BUFFER_SENIOR=5` | Buffer năm cho từng career tier |
| **Salary** | `NMAIEX_SALARY_BASE_HANOI=15_000_000`, `NMAIEX_SALARY_TOLERANCE_LOWER=0.8` | Baseline và neutral zone |
| **Language** | `NMAIEX_LANG_REQUIRED_PENALTY=0.25`, `NMAIEX_LANG_PREFERRED_BONUS=0.08` | Penalty/bonus ngôn ngữ |
| **Score Clip** | `NMAIEX_ENABLE_SCORE_CLIP=false` | Mặc định không clip để giữ khả năng xếp hạng các trường hợp quá thấp/quá cao; chỉ bật cho UI legacy cần score trong `[0, 1]` |

> Thay đổi weights không cần redeploy code — chỉ cần update `.env.nmaiex` và restart server.

---

## 7. Response Format & `score_breakdown`

Response từ cả hai endpoint tuân theo `RankingResponse` (`nmaiex_schemas.py`):

```json
// J→C: rank_candidates_for_job
{
  "job_id": 1,
  "total_candidates": 45,
  "returned": 20,
  "results": [
    {
      "candidate_id": 42,
      "candidate_name": "Nguyễn Văn An",
      "match_score": 0.7821,
      "score_breakdown": {
        "rrf_score": 0.6100,
        "exact_overlap": 0.8000,
        "fuzzy_overlap": 0.3500,
        "skill_score": 0.7100,
        "skill_alpha": 0.8,
        "seniority_penalty": 0.0000,
        "hard_filter_passed": true
      }
    }
  ]
}

// C→J: rank_jobs_for_candidate
{
  "candidate_id": 42,
  "total_jobs": 120,
  "returned": 20,
  "results": [
    {
      "job_id": 7,
      "job_title": "Senior Java Engineer",
      "match_score": 0.8134,
      "score_breakdown": {
        "text_score": 0.5200,
        "title_score": 0.4800,
        "exact_overlap": 0.7500,
        "fuzzy_overlap": 0.2200,
        "skill_score": 0.6860,
        "skill_alpha": 0.8,
        "salary_adjustment": 0.0400,
        "lang_penalty": 0.0000,
        "lang_bonus": 0.0800,
        "lang_breakdown": {
          "requirements": [
            {
              "lang": "ja",
              "req_type": "PREFERRED",
              "min_level": "INTERMEDIATE",
              "cand_level_num": 3,
              "met": true,
              "score_diff": 0.08
            }
          ]
        },
        "hard_filter_passed": true
      }
    }
  ]
}
```
* NOTE FROM USER: sau có thời gian thì bổ sung hướng dẫn về cơ chế xếp hạng và dùng LLM để từ hướng dẫn chi tiết đó -> Giải thích thêm
`score_breakdown` **luôn được trả về** trong response, kể cả trên production. Frontend tự quyết định ẩn/hiện theo `VITE_DEV_MODE`. Việc giữ breakdown phía backend giúp debug và audit không cần thay đổi API và tận dụng để làm LLM giải thích trong tương lai

Với C→J, breakdown còn có thêm: `text_score`, `title_score`, `salary_adjustment`, `lang_penalty`, `lang_bonus`, `lang_breakdown`.

---

## 8. Master Data Endpoints

Năm endpoint phụ trợ phục vụ frontend dropdown — query thẳng từ DB, không qua ranking logic:

| Endpoint | Nguồn | Đặc biệt |
|---|---|---|
| `GET /v2/nmaiex/master/provinces` | `PROVINCE JOIN REGION` | Trả về nhóm theo `region` (Bắc/Trung/Nam) |
| `GET /v2/nmaiex/master/levels` | `JOBLEVEL` | Bao gồm `levelId`, `levelName`, `description` |
| `GET /v2/nmaiex/master/categories` | `JOBCATEGORY` | Danh mục IT (17 mục) |
| `GET /v2/nmaiex/master/skills` | `SKILL` | Catalog skill chuẩn cho LLM mapper |
| `GET /v2/nmaiex/master/languages` | `LANGUAGE` | **Chưa triển khai (Planned / Do not call)** — bảng DB đã có, route chưa được tạo |

### Management API

| Method | Path | Mô tả |
|---|---|---|
| `GET` | `/v2/nmaiex/management/jobs` | Danh sách jobs với filters |
| `GET` | `/v2/nmaiex/management/jobs/{job_id}` | Chi tiết job |
| `PUT` | `/v2/nmaiex/management/jobs/{job_id}` | Cập nhật job |
| `PATCH` | `/v2/nmaiex/management/jobs/{job_id}/content` | **Canonical** — Cập nhật content + re-ingest job embeddings |
| `GET` | `/v2/nmaiex/management/candidates` | Danh sách candidates với filters |
| `GET` | `/v2/nmaiex/management/candidates/{candidate_id}` | Chi tiết candidate |
| `PUT` | `/v2/nmaiex/management/candidates/{candidate_id}` | Cập nhật candidate |

> [!IMPORTANT]
> Route canonical cho job content update + re-ingestion là `/v2/nmaiex/management/jobs/{job_id}/content`.

---

## 9. Điểm Cần Chú Ý Khi Phát Triển

**asyncpg pattern**: Toàn bộ DB query dùng `acquire_conn()` từ `app/core/database.py`. Kết quả `conn.fetch()` trả `Record` — truy cập field bằng `row['fieldname']` (lowercase), **không** dùng `row.fieldName`.

**Tách connection context**: J→C và C→J mở nhiều `async with acquire_conn()` riêng biệt (không nest). Lý do: embed_chunks là async I/O nằm ngoài DB context — không thể giữ connection mở trong suốt quá trình embed.

**Fuzzy overlap fallback**: Nếu một bên không có `*_SKILL_RAW` records (embeddings), `fuzzy_overlap = 0.0`. Đây là hành vi mong muốn — không ảnh hưởng `exact_overlap`.

**Language scoring**: Chỉ áp dụng trong luồng C→J. J→C hiện không có language scoring (chỉ có seniority penalty). Tiếng Việt không có trong `JOB_LANG_REQUIREMENT` vì là ngôn ngữ mặc định.
*Lưu ý quan trọng về Code Reality:* Hiện có sự không nhất quán giữa thiết kế tài liệu và thực tế code liên quan đến Language Proficiency. Hàm `normalize_proficiency()` dù đã được implement trong `nmaiex_mapper_service.py` nhưng chưa được gọi tại `compute_language_score()`. Code thực tế thực hiện tra cứu trực tiếp trong dictionary `PROFICIENCY_LEVELS`, dẫn tới các trình độ thô (ví dụ `"N3"`) bị fallback về `"BASIC"` (level 1). Gap này cần được resolve ở phase tiếp theo.

**Hard filter**: `province_id` và `work_mode` là optional — nếu không truyền, hệ thống không lọc theo hai tiêu chí này. Filter áp dụng ngay tại tầng SQL trước vector search.

---

## 10. Tài Liệu Liên Quan

- `../strategy/nmaiex_ranking_strategy.md` — Toàn bộ quyết định kiến trúc và trade-off.
- `../../agent_workflow_doc/archive/[NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md` — Low-level design gốc, chỉ dùng làm historical reference.

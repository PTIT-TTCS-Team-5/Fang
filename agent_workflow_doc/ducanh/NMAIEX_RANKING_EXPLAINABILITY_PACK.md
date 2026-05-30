# NMAIEX\_RANKING\_EXPLAINABILITY\_PACK

**Workstream:** Explainability — phục vụ JobPosting Agent Option B
**Ngày tạo:** 2026-05-27
**Trạng thái:** Draft — cần review và confirm Open Questions

---

## Mục lục

1. [Executive Summary](#1-executive-summary)
2. [Current Ranking Flow J→C](#2-current-ranking-flow-jc)
3. [Score Breakdown Glossary](#3-score-breakdown-glossary)
4. [Explanation Template Set](#4-explanation-template-set)
5. [Mapping Rules từ Score Breakdown sang Explanation](#5-mapping-rules)
6. [Missing-Data và Confidence Policy](#6-missing-data-và-confidence-policy)
7. [Risks và Anti-Overclaiming Rules](#7-risks-và-anti-overclaiming-rules)
8. [Recommendation cho JobPosting Agent Option B](#8-recommendation-cho-jobposting-agent-option-b)
9. [Implementation Handoff Notes](#9-implementation-handoff-notes)
10. [Open Questions](#10-open-questions)
11. [Appendix: File References](#appendix-file-references)

---

## 1. Executive Summary

### 1.1 Mục tiêu

Tài liệu này giải thích rõ ràng cơ chế xếp hạng ứng viên của NMAIex (luồng J→C), tạo glossary chuẩn cho từng thành phần score, đề xuất templates và mapping rules để JobPosting Agent có thể giải thích kết quả ranking cho HR một cách an toàn, không overclaim.

### 1.2 Kết quả chính từ phân tích code

- **Source of truth:** `app/services/nmaiex_ranking_service.py` — hàm `rank_candidates_for_job()`
- **Công thức J→C final score:**

```
match_score = clip(w_rrf × rrf_score_norm + w_skill × skill_score - seniority_penalty)
```

Với `w_rrf = 0.4219`, `w_skill = 0.5329`. Phần còn lại là seniority penalty (deduction).

- **RRF** fusion 2 nguồn: vector search (HNSW trên `AIDOCUMENTCHUNK`) + full-text search (PostgreSQL `ts_rank` trên rawText/bio)
- **Skill scoring** 2 tầng: exact overlap (catalog ID) + fuzzy overlap (cosine embedding của raw skill text), blended bằng `skill_alpha = 0.7362`
- **Seniority penalty** bất đối xứng: thiếu kinh nghiệm bị phạt nặng hơn thừa kinh nghiệm
- **Score clip** mặc định tắt (`NMAIEX_ENABLE_SCORE_CLIP=false`), nghĩa là `match_score` có thể âm hoặc > 1 trong các trường hợp biên
- **Findings:** Response hiện tại không trả `jobAppId`, không có `confidence` hay `explanation_warnings` — cần bổ sung để JobPosting Agent hoạt động tốt

### 1.3 Phạm vi tài liệu này

| Làm | Không làm |
|-----|-----------|
| Giải thích cơ chế ranking | Sửa công thức hoặc tuning weight |
| Glossary từng field score | Implement agent/MCP/LangGraph |
| Templates và mapping rules | Sửa DB schema |
| Risk và anti-overclaiming | Viết code production |
| Handoff notes cho dev | |

---

## 2. Current Ranking Flow J→C

### 2.1 Tổng quan luồng

```
HR gọi API: rank_candidates_for_job(job_id, limit, province_id, work_mode)
      │
      ▼
[1]  Load job metadata từ JOBPOSTING
      │  title, description, minSalary, maxSalary
      ▼
[2]  Load job catalog skills từ JOBREQUIREMENT
      │  → set job_skills (skillId integers)
      ▼
[3]  Load seniority range từ JOB_LEVEL_MAP + JOBLEVEL
      │  → job_min, job_max (với buffer theo career tier)
      ▼
[4]  Embed job text (title + description) → job_vector (HNSW embedding)
      │
      ▼
[5]  Query candidates (hard filter: user.stat = 'ACTIVE', tùy chọn province_id)
      │  JOIN JOBAPPLICATION (lấy latest_app_id per candidate)
      │  JOIN CVPARSED (rawText)
      │  LEFT JOIN AIDOCUMENTCHUNK (vector_distance via pgvector <=>)
      │  ts_rank(rawText, job_text) → text_rank
      ▼
[6]  Batch load candidate catalog skills từ CANDIDATESKILL
      │
      ▼
[7]  Tính RRF score cho từng ứng viên
      │  vec_rank + txt_rank → rrf_score → rrf_score_norm
      ▼
[8]  Tính Skill Score (2 tầng)
      │  exact_overlap (catalog ID intersection)
      │  fuzzy_overlap (avg_max cosine: JOB_SKILL_RAW <=> CANDIDATE_SKILL_RAW)
      │  skill_score = alpha × exact + (1-alpha) × fuzzy
      ▼
[9]  Tính Seniority Penalty
      │  So sánh c.expyears vs [job_min, job_max + buffer]
      ▼
[10] Tổng hợp match_score + sort + limit
      │
      ▼
[Output] List CandidateRankResult
         { candidate_id, candidate_name, match_score, score_breakdown }
```

### 2.2 Input của ranking

| Parameter | Kiểu | Ý nghĩa |
|-----------|------|---------|
| `job_id` | `int` | ID của job posting cần tìm ứng viên |
| `limit` | `int` | Số ứng viên tối đa trả về (default: 20, max: 100) |
| `province_id` | `str?` | Lọc ứng viên theo tỉnh thành (tùy chọn) |
| `work_mode` | `str?` | Lọc theo hình thức làm việc (tùy chọn) |

### 2.3 Data sources được dùng trong query

| Bảng | Vai trò |
|------|---------|
| `JOBPOSTING` | title, description, minSalary, maxSalary của job |
| `JOBREQUIREMENT` | Catalog skillId mà job yêu cầu (exact matching) |
| `JOB_LEVEL_MAP` | Mapping job → levelId để xác định seniority range |
| `JOBLEVEL` | minYears per level → dùng để tính job\_min/job\_max |
| `JOBAPPLICATION` | Lấy `latest_app_id` của từng ứng viên cho job này |
| `AIDOCUMENTCHUNK` | Chunk CV embedding → vector search (HNSW, pgvector) |
| `CVPARSED` | rawText CV (fallback sang bio nếu NULL) |
| `CANDIDATE` | expyears của ứng viên (dùng cho seniority penalty) |
| `CANDIDATESKILL` | Catalog skillId của ứng viên (exact matching) |
| `JOB_SKILL_RAW` | Raw skill embedding của job (fuzzy matching tầng 2) |
| `CANDIDATE_SKILL_RAW` | Raw skill embedding của ứng viên (fuzzy matching tầng 2) |

### 2.4 Công thức tính score chi tiết

#### RRF Score (Reciprocal Rank Fusion)

```
rrf_k = 60

# Rank theo vector distance (nhỏ = gần = tốt)
r_vec[cid] = rank của candidate theo vector_distance ASC

# Rank theo text rank (lớn = tốt)
r_txt[cid] = rank của candidate theo ts_rank DESC

# RRF raw
rrf_score = 1/(rrf_k + r_vec) + 1/(rrf_k + r_txt)

# Normalize tương đối
rrf_score_norm = rrf_score × rrf_k / 2.0
```

> **Lưu ý:** `rrf_score_norm` là normalize **tương đối**, không phải tuyệt đối về \[0,1\].
> Với `rrf_k=60`, giá trị cao nhất lý thuyết là `(1/61 + 1/61) × 60/2 ≈ 0.984`.
> Trong thực tế, ứng viên top thường có norm ≈ 0.3–0.7 tùy pool.

---

#### Skill Score (2 tầng)

```
# Tầng 1: Exact Overlap (catalog ID)
exact_overlap = |job_skill_ids ∩ cand_skill_ids| / max(|job_skill_ids|, 1)

# Tầng 2: Fuzzy Overlap (avg_max cosine từ raw embeddings)
fuzzy_overlap = AVG over each job raw skill of:
    MAX cosine_similarity(job_raw_emb, cand_raw_emb)  ∈ [0.0, 1.0]
# = 0.0 nếu một trong hai bên không có raw embeddings

# Blend
skill_alpha = 0.7362
skill_score = 0.7362 × exact_overlap + 0.2638 × fuzzy_overlap
```

---

#### Seniority Penalty (Bất đối xứng)

```
# Buffer theo career tier của job
job_max_raw ≤ 1yr  → buffer = 2  (Very Junior / Fresher)
job_max_raw ≤ 3yr  → buffer = 3  (Junior)
job_max_raw ≤ 5yr  → buffer = 4  (Middle)
job_max_raw ≤ 8yr  → buffer = 5  (Senior)
job_max_raw > 8yr  → buffer = 7  (Lead / Manager)

job_max = job_max_raw + buffer

# Penalty logic
penalty_coef          = 0.4255
overqualified_ratio   = 0.1134

if c_exp < job_min:        # Thiếu seniority
    seniority_penalty = 0.4255 × (job_min - c_exp)
elif c_exp > job_max:      # Thừa seniority — phạt nhẹ hơn ~8.8x
    seniority_penalty = 0.4255 × 0.1134 × (c_exp - job_max)
else:                      # Trong range (kể cả buffer)
    seniority_penalty = 0.0
```

---

#### Final Score

```
w_rrf   = 0.4219  (J→C)
w_skill = 0.5329  (J→C)

match_score = clip(0.4219 × rrf_score_norm + 0.5329 × skill_score - seniority_penalty)

# clip() chỉ active khi NMAIEX_ENABLE_SCORE_CLIP = true (default: false)
# → match_score có thể âm hoặc > 1 khi clip tắt
```

### 2.5 Response shape hiện tại

```json
{
  "job_id": 123,
  "total_candidates": 45,
  "returned": 20,
  "results": [
    {
      "candidate_id": 789,
      "candidate_name": "Nguyễn Văn A",
      "match_score": 0.6234,
      "score_breakdown": {
        "rrf_score": 0.4521,
        "exact_overlap": 0.7500,
        "fuzzy_overlap": 0.6100,
        "skill_score": 0.7220,
        "skill_alpha": 0.7362,
        "seniority_penalty": 0.0000,
        "hard_filter_passed": true
      }
    }
  ]
}
```

**Thiếu trong response hiện tại:**

- `jobAppId` — JobPosting Agent không thể drill-down vào CV cụ thể
- `confidence` / `explanation_warnings` — không có tín hiệu data quality
- Missing-data flags — không biết ứng viên có CVPARSED hay không

---

## 3. Score Breakdown Glossary

### 3.1 `match_score`

| Thuộc tính | Nội dung |
|------------|---------|
| **Ý nghĩa** | Điểm tổng hợp cuối cùng phản ánh mức độ phù hợp của ứng viên với job. Tính từ RRF score, skill score và seniority penalty. |
| **Nguồn dữ liệu** | Tổng hợp từ tất cả các thành phần bên dưới. |
| **HR nên hiểu** | Điểm xếp hạng tương đối trong pool ứng viên cho job này, không phải điểm tuyệt đối. |
| **Không nên suy diễn** | Score cao ≠ ứng viên giỏi. Score thấp ≠ ứng viên kém. Score phụ thuộc nhiều vào chất lượng CV và data trên hệ thống. |
| **Rủi ro / Missing-data** | `NMAIEX_ENABLE_SCORE_CLIP=false` → score có thể âm hoặc > 1. Nếu CV thiếu text hoặc skill data, score bị kéo xuống không phản ánh năng lực thực. |

---

### 3.2 `rrf_score`

| Thuộc tính | Nội dung |
|------------|---------|
| **Ý nghĩa** | Điểm Reciprocal Rank Fusion — tổng hợp từ (1) độ gần vector embedding giữa CV và job description, (2) độ khớp text qua full-text search. |
| **Nguồn dữ liệu** | `AIDOCUMENTCHUNK` (vector embedding CV chunks) và `CVPARSED.rawText` / `CANDIDATE.bio` (full-text). |
| **HR nên hiểu** | CV ứng viên có nội dung "gần" với job description về mặt ngữ nghĩa và từ khóa. |
| **Không nên suy diễn** | RRF cao ≠ có đủ skill cụ thể. Ứng viên có thể dùng từ ngữ gần giống job nhưng không đáp ứng yêu cầu kỹ thuật. |
| **Rủi ro / Missing-data** | Nếu không có CVPARSED: `vector_distance = NULL`, `text_rank = 0` → RRF rank thấp nhất dù ứng viên có thể rất phù hợp. |

---

### 3.3 `exact_overlap`

| Thuộc tính | Nội dung |
|------------|---------|
| **Ý nghĩa** | Tỷ lệ skill job (catalog ID) mà ứng viên có trong hồ sơ. Công thức: `\|job_skills ∩ cand_skills\| / \|job_skills\|`. |
| **Nguồn dữ liệu** | `JOBREQUIREMENT` (skill catalog job) và `CANDIDATESKILL` (skill catalog ứng viên). |
| **HR nên hiểu** | Skill match chính xác theo catalog. Giá trị 0.75 = ứng viên có 75% skill job yêu cầu (theo danh mục chuẩn). |
| **Không nên suy diễn** | Exact overlap = 0 ≠ ứng viên không có skill. Có thể ứng viên có skill nhưng chưa được đưa vào catalog. |
| **Rủi ro / Missing-data** | Nếu HR hoặc ứng viên chưa điền catalog skill → exact\_overlap = 0, không phản ánh thực tế. |

---

### 3.4 `fuzzy_overlap`

| Thuộc tính | Nội dung |
|------------|---------|
| **Ý nghĩa** | Mức độ tương đồng ngữ nghĩa giữa skill text job và skill text ứng viên, tính bằng cosine similarity embedding theo avg\_max. |
| **Nguồn dữ liệu** | `JOB_SKILL_RAW` (embedding skill text job) và `CANDIDATE_SKILL_RAW` (embedding skill text ứng viên). |
| **HR nên hiểu** | Skill match "mờ" — ứng viên có kỹ năng tương đương về mặt ngữ nghĩa dù tên skill khác nhau. Ví dụ: "ReactJS" và "React.js". |
| **Không nên suy diễn** | Fuzzy cao ≠ skill thực sự tương đương. Embedding có thể match sai nếu tên gần nhau về ngôn ngữ. |
| **Rủi ro / Missing-data** | **Rủi ro cao nhất.** Nếu `JOB_SKILL_RAW` hoặc `CANDIDATE_SKILL_RAW` rỗng → `fuzzy_overlap = 0.0` tự động (không phải "không match" mà là "không có data"). Caveat này BẮT BUỘC đi kèm khi giải thích. |

---

### 3.5 `skill_score`

| Thuộc tính | Nội dung |
|------------|---------|
| **Ý nghĩa** | Điểm skill tổng hợp: `skill_score = 0.7362 × exact_overlap + 0.2638 × fuzzy_overlap`. Weighted về phía exact matching (73.62%) để ưu tiên độ chính xác. |
| **Nguồn dữ liệu** | Tổng hợp từ `exact_overlap` và `fuzzy_overlap`. |
| **HR nên hiểu** | Trọng số 73.62% cho exact và 26.38% cho fuzzy — hệ thống ưu tiên skill đã được xác nhận trong catalog. |
| **Không nên suy diễn** | skill\_score cao ≠ ứng viên sẽ làm được việc ngay. Đây là matching dựa trên data hệ thống, không phải đánh giá năng lực thực. |
| **Rủi ro / Missing-data** | Phụ thuộc chất lượng data cả 2 phía. Cần xem riêng exact\_overlap và fuzzy\_overlap để hiểu điểm đến từ đâu. |

---

### 3.6 `skill_alpha`

| Thuộc tính | Nội dung |
|------------|---------|
| **Ý nghĩa** | Hệ số blend giữa exact và fuzzy. Giá trị: `0.7362` (73.62% exact, 26.38% fuzzy). Config-level constant, không thay đổi per candidate. |
| **Nguồn dữ liệu** | `NMAIEX_SKILL_ALPHA` từ `.env.nmaiex`. |
| **HR nên hiểu** | Tham số hệ thống, không phải đặc điểm của ứng viên. Không cần diễn giải cho HR. |
| **Không nên suy diễn** | Field này chỉ để debug/audit, không mang ý nghĩa business với HR. |
| **Rủi ro / Missing-data** | Không áp dụng — đây là constant. |

---

### 3.7 `seniority_penalty`

| Thuộc tính | Nội dung |
|------------|---------|
| **Ý nghĩa** | Điểm bị trừ do ứng viên không nằm trong khoảng kinh nghiệm phù hợp. Trừ **0.4255/năm thiếu**; trừ **0.0482/năm thừa** (= 0.4255 × 0.1134, nhẹ hơn ~8.8x). |
| **Nguồn dữ liệu** | `CANDIDATE.expyears` vs `JOBLEVEL.minYears` (qua `JOB_LEVEL_MAP`). |
| **HR nên hiểu** | Penalty cao (> 0.4255) có 2 trường hợp: (a) thiếu kinh nghiệm so với yêu cầu, (b) quá nhiều kinh nghiệm (overqualified). Cần xem `expyears` và job level range để phân biệt. |
| **Không nên suy diễn** | Penalty cao ≠ ứng viên không phù hợp tuyệt đối. Job có buffer 2–7 năm tùy tier, penalty chỉ xảy ra khi thực sự lệch nhiều. |
| **Rủi ro / Missing-data** | `expyears = NULL` → code dùng `c_exp = 0` (Fresher). Ứng viên chưa điền kinh nghiệm sẽ nhận penalty sai. Đây là bug tiềm ẩn cần flag. |

---

### 3.8 `hard_filter_passed`

| Thuộc tính | Nội dung |
|------------|---------|
| **Ý nghĩa** | Luôn `true` — hard filter (`user.stat = 'ACTIVE'`) đã áp dụng ở SQL query trước khi scoring. |
| **Nguồn dữ liệu** | `user.stat` trong DB. |
| **HR nên hiểu** | Tất cả ứng viên trong list đều đang active và đã apply vào job này. |
| **Không nên suy diễn** | Không có thêm ý nghĩa ngoài confirmation qua hard filter. |
| **Rủi ro / Missing-data** | Không áp dụng. |

---

### 3.9 Các field C→J (tham khảo)

| Field | Ý nghĩa |
|-------|---------|
| `text_score` | RRF từ full-text search (profile ứng viên vs job description). Tương tự rrf\_score nhưng chỉ text, không có vector. |
| `title_score` | RRF từ text search job title. Ưu tiên ứng viên có lịch sử làm đúng loại job. Weight: `NMAIEX_CJ_WEIGHT_TITLE = 0.3999`. |
| `salary_adjustment` | Điểm thưởng/phạt lương (cap ±`NMAIEX_SALARY_BONUS_CAP = 0.20`). Âm nếu lương job thấp hơn kỳ vọng, dương nếu cao hơn. |
| `lang_penalty` | Trừ `−0.4744/ngôn ngữ` REQUIRED thiếu; trừ `−0.0980` nếu không đủ level. |
| `lang_bonus` | Cộng `+0.0255/ngôn ngữ` PREFERRED đủ level; cap `0.1018`. |
| `lang_breakdown` | Chi tiết từng yêu cầu ngôn ngữ: loại (REQUIRED/PREFERRED), level yêu cầu, level ứng viên, đáp ứng hay không. |

---

## 4. Explanation Template Set

> **Nguyên tắc xuyên suốt:**
> - Tất cả templates phải dùng ngôn ngữ xác suất, không tuyệt đối.
> - Không biến score thành quyết định tuyển dụng.
> - Luôn nhắc HR kiểm tra CV gốc và phỏng vấn.

---

### T1 — Giải thích vì sao ứng viên đứng top

```
"{tên_ứng_viên}" xếp hạng cao trong danh sách ứng viên cho vị trí này
dựa trên dữ liệu có trên hệ thống.

Điểm nổi bật:
- Hồ sơ có nội dung liên quan chặt chẽ đến mô tả công việc
  (điểm tương đồng văn bản và ngữ nghĩa ở mức {mức_rrf}).
- Kỹ năng trong hồ sơ khớp với {số_skill}/{tổng_skill} kỹ năng
  yêu cầu của job ({mức_exact_overlap}%).
- Năm kinh nghiệm nằm trong khoảng phù hợp với yêu cầu.

Lưu ý: Đây là đánh giá dựa trên dữ liệu hồ sơ, không thay thế
cho việc review CV gốc và phỏng vấn trực tiếp.
```

---

### T2 — Giải thích điểm mạnh chính của ứng viên

```
Dựa trên hồ sơ trên hệ thống, điểm mạnh của "{tên_ứng_viên}"
với vị trí này bao gồm:

[Nếu exact_overlap cao:]
→ Kỹ năng catalog khớp tốt ({exact_overlap_pct}% skill yêu cầu có trong hồ sơ).

[Nếu rrf_score cao:]
→ Nội dung hồ sơ/CV gần với mô tả công việc theo phân tích ngữ nghĩa.

[Nếu seniority_penalty = 0:]
→ Kinh nghiệm phù hợp với khoảng yêu cầu của vị trí.

Hệ thống không thể xác nhận các điểm mạnh này nếu không có
review CV gốc.
```

---

### T3 — Giải thích điểm yếu / rủi ro

```
Hệ thống phát hiện một số điểm cần HR lưu ý khi xem xét "{tên_ứng_viên}":

[Nếu seniority_penalty > 0 do thiếu kinh nghiệm:]
→ Số năm kinh nghiệm ({c_exp} năm) thấp hơn yêu cầu tối thiểu.
   Đây là tín hiệu rủi ro, không phải loại trực tiếp — HR nên xem xét thêm.

[Nếu seniority_penalty > 0 do overqualified:]
→ Số năm kinh nghiệm ({c_exp} năm) cao hơn khoảng phù hợp của vị trí.
   Ứng viên có thể overqualified — cần trao đổi về kỳ vọng.

[Nếu exact_overlap thấp:]
→ Ít kỹ năng catalog khớp trực tiếp. Ứng viên có thể có kỹ năng liên quan
   nhưng chưa được ghi nhận trong hệ thống.

[Nếu missing data:]
→ Hồ sơ thiếu một số thông tin (xem cảnh báo bên dưới). Score có thể
   không đại diện đầy đủ cho năng lực thực.
```

---

### T4 — Giải thích skill match

```
Về kỹ năng với vị trí này:

- Kỹ năng khớp chính xác (catalog): {exact_overlap_pct}%
  ({overlap_count}/{job_skill_count} kỹ năng yêu cầu).
- Kỹ năng tương đương / semantic: {fuzzy_label}
  (dựa trên phân tích ngữ nghĩa tên kỹ năng).

[Nếu fuzzy cao hơn exact:]
→ Phần lớn điểm skill đến từ matching ngữ nghĩa, không phải khớp chính xác catalog.
   HR nên xác minh ứng viên thực sự có các kỹ năng yêu cầu qua CV và phỏng vấn.

[Nếu cả 2 đều thấp:]
→ Ít bằng chứng về skill match trong hệ thống.
   Ứng viên có thể phù hợp nhưng chưa cập nhật hồ sơ đầy đủ.
```

**Label cho `fuzzy_overlap`:**

| Giá trị | Label |
|---------|-------|
| `< 0.3` | "thấp" |
| `0.3 – 0.6` | "trung bình" |
| `> 0.6` | "cao" |

---

### T5 — Giải thích seniority fit / risk

```
[Không có penalty:]
Năm kinh nghiệm của ứng viên ({c_exp} năm) nằm trong khoảng phù hợp
với yêu cầu vị trí ({job_min}–{job_max} năm, đã tính buffer).

[Thiếu kinh nghiệm:]
Năm kinh nghiệm ({c_exp} năm) thấp hơn mức tối thiểu yêu cầu ({job_min} năm).
Đây là rủi ro về seniority — hệ thống đã trừ {seniority_penalty:.2f} điểm.
HR nên đánh giá thêm qua CV và phỏng vấn trước khi quyết định.

[Overqualified:]
Năm kinh nghiệm ({c_exp} năm) cao hơn khoảng dự kiến (tối đa {job_max} năm với buffer).
Ứng viên có thể overqualified — hệ thống đã trừ nhẹ {seniority_penalty:.2f} điểm.
Nên trao đổi về kỳ vọng lương, career path và sự gắn bó lâu dài.
```

---

### T6 — Giải thích khi thiếu dữ liệu / score không đáng tin

```
⚠️ Lưu ý về độ tin cậy của kết quả ranking cho "{tên_ứng_viên}":

{danh_sách_cảnh_báo}

Ví dụ:
- Ứng viên chưa có CV được xử lý. Điểm tương đồng nội dung không đáng tin.
- Không có dữ liệu kỹ năng raw embedding. Điểm fuzzy skill = 0
  và không phản ánh thực tế.
- Năm kinh nghiệm chưa được điền — hệ thống mặc định 0 năm,
  có thể làm seniority penalty sai.

Đề xuất: HR nên thu thập thêm thông tin trực tiếp từ ứng viên
trước khi kết luận.
```

---

### T7 — Giải thích khi hai ứng viên có score gần nhau

```
"{tên_A}" (điểm: {score_A:.4f}) và "{tên_B}" (điểm: {score_B:.4f})
có điểm tương đương nhau. Chênh lệch {diff:.4f} điểm nằm trong
biên độ không đáng kể về mặt thống kê.

Để phân biệt 2 ứng viên này, HR nên xem xét thêm:
- Kỹ năng cụ thể nào khớp với job (xem exact_overlap từng người).
- Seniority fit thực tế (xem seniority_penalty và số năm kinh nghiệm).
- Chất lượng và nội dung CV gốc.
- Thông tin không có trên hệ thống: tính cách, soft skill, fit văn hóa.

Hệ thống không thể phân định winner giữa 2 ứng viên này chỉ dựa trên score.
```

> **Ngưỡng "gần nhau":** chênh lệch `match_score < 0.05` — cần confirm (xem OQ-8).

---

## 5. Mapping Rules

> Các rules dưới đây đủ cụ thể để implement thành deterministic helper function.

### 5.1 Rules chọn template

```
RULE-01: Chọn template tổng quan
  IF match_score >= 0.5 AND seniority_penalty == 0  → T1 + T2
  IF seniority_penalty > 0.4255                      → T3 + T5
  IF has_missing_data_warnings                        → luôn thêm T6
  IF |score_A - score_B| < 0.05                      → T7
```

### 5.2 Rules cho skill explanation

```
RULE-02: Skill match chính xác tốt
  IF exact_overlap >= 0.7
  → "Ứng viên có kỹ năng phù hợp tốt"
  → Nêu tỷ lệ cụ thể: "{X}/{Y} kỹ năng yêu cầu"

RULE-03: Skill match chủ yếu qua fuzzy
  IF exact_overlap < 0.3 AND fuzzy_overlap >= 0.5
  → "Matching dựa nhiều vào kỹ năng tương đương/semantic"
  → BẮT BUỘC thêm: "HR cần xác minh trực tiếp qua CV và phỏng vấn"
  → Không được nói "ứng viên có skill X" nếu chỉ từ fuzzy

RULE-04: Cả 2 đều thấp
  IF exact_overlap < 0.3 AND fuzzy_overlap < 0.3
  → "Ít bằng chứng về skill match trong hệ thống"
  → Không kết luận "ứng viên không có skill"

RULE-05: Fuzzy = 0.0 (missing raw embeddings)
  IF fuzzy_overlap == 0.0
  → Kiểm tra xem có raw embedding không
  → Nếu không có: "Không có dữ liệu để tính fuzzy skill"
  → Không nói "fuzzy score thấp" (misleading)
```

### 5.3 Rules cho seniority explanation

```
RULE-06: Trong range — không penalty
  IF seniority_penalty == 0
  → "Kinh nghiệm phù hợp với yêu cầu vị trí"

RULE-07: Thiếu seniority (c_exp < job_min)
  IF seniority_penalty > 0 AND c_exp < job_min
  → Dùng T5 nhánh "Thiếu kinh nghiệm"
  → Nêu rõ c_exp, job_min, mức penalty
  → Không kết luận "ứng viên không đủ điều kiện"

RULE-08: Overqualified (c_exp > job_max)
  IF seniority_penalty > 0 AND c_exp > job_max
  → Dùng T5 nhánh "Overqualified"
  → Phân biệt rõ: overqualified ≠ thiếu kinh nghiệm
  → Penalty nhẹ hơn ~8.8x so với thiếu (ratio = 0.1134)

RULE-09: expyears = NULL / 0 (missing data)
  IF c_exp == 0 AND không rõ là thực hay missing
  → Warning: "Năm kinh nghiệm chưa xác nhận, hệ thống dùng mặc định 0"
  → Không tin vào seniority_penalty trong trường hợp này
```

### 5.4 Rules cho confidence và data quality

```
RULE-10: Không có CV text
  IF rawText IS NULL AND bio IS NULL
  → Warning: "RRF score không đáng tin — thiếu CV text"
  → Hạ confidence toàn bộ explanation

RULE-11: Không có catalog skills
  IF job_skill_count == 0 OR cand_skill_ids == empty
  → Warning: "Skill score không phản ánh thực tế — thiếu skill data"

RULE-12: Không có raw skill embeddings
  IF JOB_SKILL_RAW rỗng OR CANDIDATE_SKILL_RAW rỗng
  → Warning: "fuzzy_overlap = 0.0 vì thiếu raw embeddings, không phải do không match"

RULE-13: Score âm hoặc > 1 (edge case khi clip tắt)
  IF match_score < 0
  → Warning: "Score âm — ứng viên có nhiều penalty"
  → Không hiển thị score âm trực tiếp cho HR
  IF match_score > 1
  → Edge case hiếm gặp, log và đánh dấu bất thường
```

---

## 6. Missing-Data và Confidence Policy

### 6.1 Các mức confidence

| Mức | Điều kiện | Hiển thị với HR |
|-----|-----------|----------------|
| **HIGH** | Có CVPARSED text + catalog skills cả 2 phía + raw embeddings + expyears != NULL | Giải thích đầy đủ, ít caveat |
| **MEDIUM** | Có CV text nhưng thiếu skill data, hoặc ngược lại | Giải thích kèm caveat |
| **LOW** | Thiếu nhiều loại data (không CV, không skills, expyears = NULL) | Cảnh báo rõ, đề xuất HR thu thập thêm |
| **UNKNOWN** | Không có bất kỳ data nào ngoài user record | Không giải thích score — chỉ nói thiếu data |

### 6.2 Checklist missing-data (implement trong service layer)

```python
def build_missing_data_warnings(candidate_data: dict) -> list[str]:
    warnings = []
    if not candidate_data.get("rawText") and not candidate_data.get("bio"):
        warnings.append("cv_text_missing")       # → "Chưa có CV text được xử lý"
    if not candidate_data.get("job_app_id"):
        warnings.append("no_application")        # → "Ứng viên chưa có đơn ứng tuyển"
    if candidate_data.get("expyears") is None:
        warnings.append("expyears_missing")      # → "Năm KN chưa điền, mặc định 0"
    if candidate_data.get("cand_skill_count", 0) == 0:
        warnings.append("no_catalog_skills")
    if candidate_data.get("cand_raw_skill_count", 0) == 0:
        warnings.append("no_raw_skill_embeddings")
    return warnings
```

### 6.3 Missing-data display rules

- Luôn hiển thị warnings nếu có bất kỳ item nào trong checklist
- Không ẩn warnings dù score trông "đẹp"
- Template **T6** phải được dùng khi `len(warnings) >= 1`
- Nếu `len(warnings) >= 3` → không giải thích score, chỉ nói _"Hồ sơ chưa đủ thông tin để đánh giá"_

---

## 7. Risks và Anti-Overclaiming Rules

### 7.1 Các rủi ro chính

**R1 — Score không phải quyết định tuyển dụng**
- `match_score` là tín hiệu hỗ trợ sàng lọc, không thay thế judgment của HR.
- Không được nói "ứng viên này phù hợp nhất" hay "nên tuyển người này".

**R2 — Score breakdown là tín hiệu, không phải bằng chứng**
- `exact_overlap = 0.8` ≠ "ứng viên chắc chắn có 80% skill yêu cầu".
- Data trong catalog có thể không đầy đủ hoặc lỗi thời.

**R3 — Fuzzy skill có thể match sai hoặc quá rộng**
- Cosine similarity có thể cho điểm cao với skill không liên quan nếu tên gần nhau về ngôn ngữ.
- **Anti-overclaiming:** Nếu explanation dựa nhiều vào fuzzy\_overlap → BẮT BUỘC thêm caveat xác minh.

**R4 — Text/vector rank bị ảnh hưởng bởi CV wording**
- Ứng viên viết CV gần với job description sẽ có RRF cao hơn, không nhất thiết giỏi hơn.
- Ứng viên giỏi nhưng viết CV ngắn gọn có thể bị rank thấp.

**R5 — Seniority penalty phụ thuộc expyears và job level mapping**
- `expyears = NULL` → 0 năm (có thể sai hoàn toàn).
- Job không có `JOB_LEVEL_MAP` → `job_min = 0, job_max = inf` → penalty luôn 0 (misleading).

**R6 — Missing data phải được nói rõ**
- Không giải thích score với độ tự tin cao khi có missing data.
- **Anti-overclaiming:** Nếu có warning → confidence phải hạ và caveat phải hiển thị.

**R7 — Không suy luận đặc điểm nhạy cảm**
- Không suy diễn tuổi, giới tính, dân tộc từ score.
- Score chỉ phản ánh skill và text matching.

**R8 — Agent phân biệt rõ nguồn thông tin**

| Loại | Ý nghĩa | Cách xử lý |
|------|---------|-----------|
| Score-derived | "Theo score, ứng viên có X" | Luôn kèm caveat |
| CV evidence | "Trong CV, ứng viên ghi X" | Cần `jobAppId` để drill-down |
| ATS evidence | Từ hệ thống tracking riêng | Cần tool riêng |
| HR decision | Do HR quyết định | Agent không can thiệp |

### 7.2 Anti-Overclaiming Checklist

Trước khi output explanation, kiểm tra:

- [ ] Có dùng ngôn ngữ xác suất? ("có thể", "theo hồ sơ", "hệ thống ghi nhận")
- [ ] Có tránh kết luận tuyệt đối? ("chắc chắn phù hợp", "nên tuyển")
- [ ] Có hiển thị caveat khi `fuzzy_overlap > exact_overlap`?
- [ ] Có hiển thị warning khi có missing data?
- [ ] Có phân biệt thiếu seniority vs overqualified?
- [ ] Có nhắc HR kiểm tra CV gốc và phỏng vấn?
- [ ] Có tránh suy luận thông tin nhạy cảm?

---

## 8. Recommendation cho JobPosting Agent Option B

### 8.1 Tool `get_job_candidate_ranking` nên trả thêm

| Field cần thêm | Lý do |
|----------------|-------|
| `jobAppId` | Để agent drill-down vào CV cụ thể (hiện không có trong response) |
| `expyears` | Để agent giải thích seniority mà không cần query thêm |
| `job_skill_count` | Số skill job yêu cầu, để tính tỷ lệ % trong giải thích |
| `cand_skill_matched_count` | Số skill khớp exact, để nói "X/Y skill" thay vì chỉ ratio |
| `missing_data_warnings` | List cảnh báo thiếu data |
| `confidence_level` | `"HIGH"` / `"MEDIUM"` / `"LOW"` / `"UNKNOWN"` — build sẵn ở service layer |
| `seniority_direction` | `"insufficient"` / `"overqualified"` / `"ok"` |

### 8.2 Explanation nên build ở đâu?

**Khuyến nghị: Deterministic helper ở service layer.**

Lý do:
- Agent chỉ được diễn đạt lại trong phạm vi đã được cung cấp
- Nếu để agent tự build từ raw score → có thể fabricate rationale
- Deterministic helper đảm bảo consistency và traceability
- Service layer có context đầy đủ (missing data, config values, thresholds)

**Architecture gợi ý:**

```
nmaiex_ranking_service.py
  └── rank_candidates_for_job()
        └── build_score_explanation(score_breakdown, candidate_data, job_data)
              → ExplanationResult {
                  summary: str,                    # 1-2 câu tóm tắt
                  strengths: list[str],            # Điểm mạnh theo mapping rules
                  risks: list[str],                # Điểm yếu / rủi ro
                  missing_data_warnings: list[str],
                  confidence_level: str,
                  seniority_direction: str,
                  caveat: str                      # Bắt buộc nhắc HR kiểm tra lại
                }
```

### 8.3 Warnings mà tool layer nên trả

```python
"explanationWarnings": [
  {
    "code": "cv_text_missing",
    "severity": "HIGH",
    "message": "Ứng viên chưa có CV text được xử lý. RRF score không đáng tin."
  },
  {
    "code": "expyears_missing",
    "severity": "MEDIUM",
    "message": "Năm kinh nghiệm chưa điền — seniority penalty có thể sai."
  },
  {
    "code": "no_raw_skill_embeddings",
    "severity": "LOW",
    "message": "fuzzy_overlap = 0.0 do thiếu raw skill embeddings, không phải do không match."
  }
]
```

### 8.4 Agent được phép và không được phép làm gì

**Được phép:**
- ✓ Trình bày lại `ExplanationResult` bằng ngôn ngữ tự nhiên
- ✓ Thêm context từ job requirements (nếu đã fetch qua tool)
- ✓ So sánh 2 ứng viên dựa trên `ExplanationResult` của cả 2
- ✓ Trả lời câu hỏi cụ thể của HR ("vì sao A đứng trên B")

**Không được phép:**
- ✗ Tự suy luận rationale từ raw score numbers
- ✗ Kết luận "nên tuyển" hay "không nên tuyển"
- ✗ Claim ứng viên có skill nếu chỉ dựa vào fuzzy score cao
- ✗ Bỏ qua warnings trong `ExplanationResult`
- ✗ Tự điều chỉnh confidence lên cao hơn service layer đã set

---

## 9. Implementation Handoff Notes

### 9.1 Module gợi ý

```
app/services/
  nmaiex_ranking_service.py        # Existing — thêm build_score_explanation()
  nmaiex_explanation_service.py    # Mới — mapping rules và template engine
  nmaiex_confidence_service.py     # Mới — missing-data checker và confidence builder

app/models/
  nmaiex_schemas.py                # Thêm ExplanationResult, MissingDataWarning
```

### 9.2 Input / Output gợi ý cho explanation function

```python
# Input
@dataclass
class ExplanationInput:
    score_breakdown: ScoreBreakdown
    candidate_data: dict    # expyears, rawText (bool), skill_counts, jobAppId
    job_data: dict          # job_skill_count, job_min, job_max, job_max_raw
    config: NMAIexSettings  # alpha, thresholds

# Output
@dataclass
class ExplanationResult:
    summary: str
    strengths: list[str]
    risks: list[str]
    missing_data_warnings: list[MissingDataWarning]
    confidence_level: str       # "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN"
    seniority_direction: str    # "insufficient" | "overqualified" | "ok"
    caveat: str                 # Luôn nhắc HR review CV và phỏng vấn
    template_ids_used: list[str]  # ["T1", "T2"] — để debug/audit
```

### 9.3 Test cases tối thiểu

| Test | Input | Expected |
|------|-------|---------|
| TC-01: Ứng viên hoàn hảo | exact=0.9, fuzzy=0.8, seniority=0, no missing | Confidence=HIGH, strengths có skill và seniority |
| TC-02: Thiếu seniority | c\_exp=0, job\_min=3, penalty=1.2765 | T5 "thiếu kinh nghiệm", risks nêu rõ |
| TC-03: Overqualified | c\_exp=10, job\_max=5+buffer, penalty nhẹ | T5 "overqualified", phân biệt với thiếu |
| TC-04: Chỉ fuzzy cao | exact=0.1, fuzzy=0.8 | RULE-03, caveat xác minh bắt buộc |
| TC-05: Missing CV | rawText=None, vectorDist=None | T6 warning, confidence=LOW |
| TC-06: Missing expyears | expyears=None | Warning expyears\_missing, seniority không đáng tin |
| TC-07: Score âm | penalty=1.5, final < 0 | Warning score âm, không hiển thị raw âm cho HR |
| TC-08: 2 ứng viên score gần | diff < 0.05 | T7, không pick winner |

### 9.4 Fields cần JobPosting tool layer trả thêm

```python
# Thêm vào CandidateRankResult
class CandidateRankResultExtended(CandidateRankResult):
    job_app_id: Optional[int] = None          # Để drill-down CV
    expyears: Optional[int] = None            # Để giải thích seniority
    confidence_level: str = "UNKNOWN"         # Build bởi service layer
    seniority_direction: str = "ok"           # "ok" | "insufficient" | "overqualified"
    explanation: Optional[ExplanationResult] = None
    explanation_warnings: list[dict] = []
```

---

## 10. Open Questions

Các câu hỏi cần quyết định trước khi implement explanation builder:

**OQ-1: Giải thích `match_score` tương đối hay tuyệt đối?**
`match_score` không được normalize cứng về \[0, 1\] (clip tắt). Nên:
- (a) Nói "điểm: 0.623" và giải thích tương đối trong pool?
- (b) Convert về % ("phù hợp 62%")?
- (c) Dùng label ("Phù hợp cao/trung bình/thấp") với threshold cụ thể?

**OQ-2: Hiển thị từng thành phần score cho HR hay chỉ dùng nội bộ?**
- (a) Hiển thị full breakdown cho HR?
- (b) Chỉ dùng nội bộ để tạo natural language explanation?
- (c) Hiển thị một phần (ví dụ: chỉ skill % và seniority)?

**OQ-3: `fuzzy_overlap` có cần caveat bắt buộc không?**
Tài liệu đề xuất bắt buộc caveat khi `fuzzy > exact`. Nếu team đồng ý, cần document rõ trong anti-overclaiming rules.

**OQ-4: Seniority penalty — wording "thiếu" vs "overqualified"?**
Logic phân biệt đã có trong code. Nhưng cần confirm: HR muốn thấy distinction này không, hay chỉ cần "có seniority risk"?

**OQ-5: Thiếu `jobAppId` trong response hiện tại**
Response J→C hiện không trả `jobAppId`. Cần confirm: có cập nhật response schema không, hay tool layer sẽ query riêng?

**OQ-6: Tool layer nên trả `confidence` hay `explanationWarnings`?**
Recommend thêm cả 2. Cần confirm với người làm Option B tool layer.

**OQ-7: Explanation builder ở NMAIex service hay JobPosting tool service?**
Tài liệu đề xuất ở NMAIex service layer. Nếu JobPosting tool service có thêm context (ATS data, recruiter notes) thì cần merge ở tool layer.

**OQ-8: Ngưỡng "score gần nhau" cho Template T7?**
Tài liệu đề xuất `diff < 0.05`. Cần xác nhận với distribution score thực tế trong production.

**OQ-9: Score âm có hiển thị cho HR không?**
Khi `NMAIEX_ENABLE_SCORE_CLIP=false`, score có thể âm. Nên xử lý: cắt về 0, hiển thị nguyên, hay chỉ nói "score thấp do nhiều penalty"?

---

## Appendix: File References

| File | Mục đích |
|------|---------|
| `app/services/nmaiex_ranking_service.py` | Source of truth cho toàn bộ ranking logic |
| `app/models/nmaiex_schemas.py` | Pydantic models: ScoreBreakdown, CandidateRankResult, RankingResponse |
| `app/core/nmaiex_config.py` | Tất cả config values: weights, penalties, thresholds |
| `agent_workflow_doc/assign_to_team/FANG_NEXT_PHASE_NMAIEX_RANKING_EXPLAINABILITY_ASSIGNMENT.md` | Assignment gốc |
| `agent_workflow_doc/current_workflow/FANG_NEXT_PHASE_JOBPOSTING_OPTION_B_IMPLEMENTATION_ADVISORY.md` | Advisory cho Option B |

---

*Report được tạo dựa trên code thực tế và `.env.nmaiex.example` tại 2026-05-27.
Nếu config thay đổi sau ngày này, cần cập nhật lại glossary và mapping rules tương ứng.*

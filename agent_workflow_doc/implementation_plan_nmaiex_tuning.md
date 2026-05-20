# Implementation Plan: NMAIex Ranking Engine Hyperparameter Tuning (Optuna)

## Goal

Tạo script `nmaiex_tuning/tune_nmaiex_hyperparams.py` để chạy **50,000 trials** tối ưu hóa Bayesian (Optuna TPE Sampler) trên hệ thống xếp hạng NMAIex. Mục tiêu: tìm bộ trọng số tối ưu cho cả hai chiều **J→C** (HR tìm ứng viên) và **C→J** (Ứng viên tìm việc), sau đó tự động ghi đè `.env.nmaiex`.

## Background Context

- **Ground Truth:** 2,000 cặp (20 Jobs × 100 Candidates mỗi job), nhãn [0–4] do LLM-as-a-Judge gán
- **Score Distribution:** 0=1,145 | 1=465 | 2=221 | 3=95 | 4=74 → sparse nhưng đủ dùng
- **Relevant pairs (≥3):** 169 cặp phân bổ trên 12/20 jobs → đủ cho MRR
- **Score Clipping:** Đã tắt (`NMAIEX_ENABLE_SCORE_CLIP=False`) → raw scores mịn cho gradient

---

## 1. Phân Tích 33 Tham Số — Tune vs. Freeze

Toàn bộ tham số được định nghĩa tại `app/core/nmaiex_config.py`. Dưới đây là phân tích từng nhóm:

### 1.1 Nhóm TUNE (13 tham số — tham gia Optuna search space)

| # | Param | Default | Phase | Range đề xuất | Lý do TUNE |
|---|-------|---------|-------|---------------|------------|
| 1 | `nmaiex_jc_weight_rrf` | 0.30 | J→C | [0.10, 0.60] | Trọng số RRF trong J→C — trực tiếp ảnh hưởng cân bằng giữa retrieval signal (vector+text) và skill match |
| 2 | `nmaiex_jc_weight_skill` | 0.40 | J→C | [0.20, 0.70] | Trọng số Skill trong J→C — quyết định mức độ ưu tiên kỹ năng vs. semantic similarity |
| 3 | `nmaiex_skill_alpha` | 0.80 | Global | [0.40, 1.00] | Cân bằng exact vs fuzzy skill matching — ảnh hưởng cả J→C và C→J. Lock sau Phase 1 |
| 4 | `nmaiex_jc_penalty_seniority_coef` | 0.25 | J→C | [0.05, 0.60] | Hệ số phạt kinh nghiệm thiếu — quá cao sẽ reject candidate hợp lệ, quá thấp sẽ không phân biệt |
| 5 | `nmaiex_seniority_overqualified_penalty_ratio` | 0.50 | J→C | [0.10, 1.00] | Tỷ lệ phạt thừa kinh nghiệm vs thiếu — asymmetry rất nhạy cảm với dataset IT VN |
| 6 | `nmaiex_cj_weight_rrf` | 0.35 | C→J | [0.10, 0.60] | Trọng số text search RRF trong C→J |
| 7 | `nmaiex_cj_weight_title` | 0.15 | C→J | [0.05, 0.40] | Trọng số title match — job title relevance cho ứng viên |
| 8 | `nmaiex_cj_weight_skill` | 0.30 | C→J | [0.10, 0.60] | Trọng số skill match trong C→J — tách riêng vì priority khác J→C |
| 9 | `nmaiex_lang_required_penalty` | 0.25 | C→J | [0.05, 0.50] | Penalty thiếu ngôn ngữ bắt buộc — tuning vì impact trực tiếp lên nDCG |
| 10 | `nmaiex_lang_level_penalty` | 0.10 | C→J | [0.02, 0.30] | Penalty level ngôn ngữ không đủ |
| 11 | `nmaiex_lang_preferred_bonus` | 0.08 | C→J | [0.02, 0.20] | Bonus có ngôn ngữ ưu tiên |
| 12 | `nmaiex_lang_bonus_cap` | 0.15 | C→J | [0.05, 0.30] | Cap tổng bonus ngôn ngữ |

### 1.2 Nhóm FREEZE (21 tham số — KHÔNG tune)

| # | Param | Default | Lý do FREEZE |
|---|-------|---------|-------------|
| 14 | `nmaiex_rrf_k` | 60 | **Chuẩn ngành** — Giá trị k=60 là standard từ RRF paper gốc (Cormack 2009), dùng phổ quát trong ES/Vespa/Weaviate. Tune trên 2,000 sparse pairs chỉ thêm nhiễu, dễ overfit |
| 15 | `nmaiex_skill_embedding_dims` | 256 | **Structural** — Thay đổi dims đòi hỏi re-embed toàn bộ DB. Không thể tune runtime |
| 16 | `nmaiex_ranking_default_limit` | 20 | **UI/UX** — Số kết quả hiển thị mặc định, không ảnh hưởng scoring formula |
| 17 | `nmaiex_ranking_max_limit` | 100 | **UI/UX** — Hard cap, không ảnh hưởng scoring |
| 18 | `nmaiex_buffer_very_junior` | 2 | **Domain Expert** — Buffer years dựa trên kinh nghiệm tuyển dụng IT VN, không nên tối ưu bằng data vì có thể overfit. 5 buffer tiers tạo search space 5^5=3125 combinations mà không đủ signal trong GT (sparse labels) |
| 19 | `nmaiex_buffer_junior` | 3 | **Domain Expert** — Như trên |
| 20 | `nmaiex_buffer_middle` | 4 | **Domain Expert** — Như trên |
| 21 | `nmaiex_buffer_senior` | 5 | **Domain Expert** — Như trên |
| 22 | `nmaiex_buffer_lead_manager` | 7 | **Domain Expert** — Như trên |
| 23 | `nmaiex_salary_base_hanoi` | 15M | **Market Data** — Mức lương base theo thị trường, thay đổi hàng năm, không nên tune bằng ML |
| 24 | `nmaiex_salary_base_tphcm` | 14M | **Market Data** |
| 25 | `nmaiex_salary_base_danang` | 12M | **Market Data** |
| 26 | `nmaiex_salary_base_default` | 13M | **Market Data** |
| 27 | `nmaiex_salary_increment_junior` | 1.5M | **Market Data** — Increment theo tier dựa trên khảo sát lương, không nên data-drive |
| 28 | `nmaiex_salary_increment_middle` | 2.0M | **Market Data** |
| 29 | `nmaiex_salary_increment_senior` | 2.5M | **Market Data** |
| 30 | `nmaiex_salary_increment_lead` | 3.0M | **Market Data** |
| 31 | `nmaiex_salary_tolerance_lower` | 0.80 | **Heuristic ổn định** — Tolerance band ±20% đã được validate trong domain HR. Tune có risk overfit |
| 32 | `nmaiex_salary_tolerance_upper` | 1.20 | **Heuristic ổn định** |
| 33 | `nmaiex_salary_bonus_cap` | 0.20 | **Safety cap** — Bảo vệ khỏi bonus bất hợp lý, không nên relax |
| 34 | `nmaiex_enable_score_clip` | False | **Runtime flag** — Không phải hyperparameter |

> **Tổng kết:** 12/33 tham số được tune → **search space 12 chiều liên tục** (12 float). Với TPE Sampler 25,000 trials/phase, mật độ ~2,100 trials/dim — tối ưu cho Bayesian search.

---

## 2. Kiến Trúc In-Memory Simulation

### 2.1 Nguyên tắc Zero I/O trong Optuna Loop

```
┌─────────────────────────────────────────────────────┐
│  STARTUP (chạy 1 lần)                               │
│                                                      │
│  1. Connect DB → Load metadata 20 Jobs + ~500 Cands  │
│  2. Load ground_truth_matrix.json                    │
│  3. Pre-compute ALL static components cho 2,000 cặp: │
│     • exact_overlap, fuzzy_overlap (cosine on RAM/DB)│
│     • experience_gap (job_min, job_max, cand_exp)    │
│     • salary_adjustment raw components               │
│     • language scores raw components                 │
│     • RRF rank positions (vector_rank, text_rank,    │
│       title_rank) — TĨNH vì ranking KHÔNG thay đổi  │
│       theo weights                                   │
│  4. Pack thành List[PairData] trên RAM               │
├─────────────────────────────────────────────────────┤
│  OPTUNA LOOP (50,000 trials — CPU only)              │
│                                                      │
│  objective(trial) → {                                │
│    w = trial.suggest_float(...)                       │
│    for pair in precomputed_pairs:                     │
│      score = w_rrf * pair.rrf_norm                   │
│             + w_skill * pair.skill_score(alpha)       │
│             - seniority_penalty(coef, ratio, gap)    │
│    compute MRR / nDCG@10 from scores vs ground_truth │
│    return metric                                     │
│  }                                                   │
└─────────────────────────────────────────────────────┘
```

### 2.2 Pre-computation Details

#### a) RRF Components (Tĩnh hoàn toàn)

Từ DB query ban đầu, ta lấy:
- **J→C:** `vector_distance` và `text_rank` của mỗi candidate đối với mỗi job → Sắp xếp 1 lần → lưu `vec_rank_pos[job_id][cand_id]` và `txt_rank_pos[job_id][cand_id]`
- **C→J:** `text_rank` và `title_rank` của mỗi job đối với mỗi candidate → tương tự

> **Lưu ý:** RRF rank positions là tĩnh vì chúng dựa trên vector distance/text rank — **không phụ thuộc** vào weights. Chỉ có giá trị `rrf_k` ảnh hưởng cách tính `1/(k + rank)`, nhưng rank position không đổi.

#### b) Skill Components (Semi-tĩnh)

- `exact_overlap[pair]` = |job_skills ∩ cand_skills| / max(|job_skills|, 1) → **tĩnh hoàn toàn**
- `fuzzy_overlap[pair]` = avg_max_cosine từ DB query → **tĩnh hoàn toàn**
- `skill_score(alpha)` = α × exact + (1-α) × fuzzy → **phụ thuộc alpha** → tính trong loop nhưng chỉ là 1 phép nhân

#### c) Seniority Components (Semi-tĩnh)

- `job_min_years[job]`, `job_max_years_with_buffer[job]` → tĩnh
- `cand_exp_years[cand]` → tĩnh
- `exp_gap_under[pair]` = max(job_min - cand_exp, 0) → tĩnh
- `exp_gap_over[pair]` = max(cand_exp - job_max, 0) → tĩnh
- `seniority_penalty(coef, ratio)` = coef × gap_under + coef × ratio × gap_over → **phụ thuộc coef & ratio** → tính trong loop

#### d) Salary Components (Tĩnh cho C→J)

- `salary_adjustment[pair]` = output từ `compute_salary_adjustment()` → **tĩnh hoàn toàn** (không có tham số tunable trong salary module)

#### e) Language Components (Semi-tĩnh cho C→J)

- Từ DB query 1 lần: cho mỗi cặp (job, candidate), tính:
  - `lang_required_missing_count`: số REQUIRED languages candidate thiếu hoàn toàn
  - `lang_level_insufficient_count`: số REQUIRED languages candidate có nhưng level thấp
  - `lang_preferred_met_count`: số PREFERRED languages candidate đạt level
- Trong Optuna loop:
  - `lang_penalty = req_missing × nmaiex_lang_required_penalty + level_insuf × nmaiex_lang_level_penalty`
  - `lang_bonus = min(pref_met × nmaiex_lang_preferred_bonus, nmaiex_lang_bonus_cap)`

---

## 3. Thiết Kế 2-Phase Study

### Phase 1: J→C Study (HR Tìm Ứng Viên — MRR)

**Search Space (5 params):**

```python
nmaiex_jc_weight_rrf                          = trial.suggest_float("jc_w_rrf", 0.10, 0.60)
nmaiex_jc_weight_skill                        = trial.suggest_float("jc_w_skill", 0.20, 0.70)
nmaiex_skill_alpha                            = trial.suggest_float("skill_alpha", 0.40, 1.00)
nmaiex_jc_penalty_seniority_coef              = trial.suggest_float("jc_sen_coef", 0.05, 0.60)
nmaiex_seniority_overqualified_penalty_ratio  = trial.suggest_float("sen_overq_ratio", 0.10, 1.00)
# rrf_k = 60 (FROZEN — industry standard, Cormack 2009)
```

**Scoring Formula (reconstruct từ ranking_service.py L496-498):**

```python
RRF_K = 60  # frozen
rrf_score_norm = (1/(RRF_K + vec_rank) + 1/(RRF_K + txt_rank)) * RRF_K / 2
skill_score = alpha * exact_overlap + (1 - alpha) * fuzzy_overlap

if cand_exp < job_min:
    seniority_penalty = coef * (job_min - cand_exp)
elif cand_exp > job_max:
    seniority_penalty = coef * overq_ratio * (cand_exp - job_max)
else:
    seniority_penalty = 0.0

final_score = w_rrf * rrf_score_norm + w_skill * skill_score - seniority_penalty
```

**Objective: Maximize MRR**

```python
def compute_mrr(job_scores, ground_truth):
    """MRR based on pairs with ground_truth >= 3 (Good/Perfect)."""
    mrr_sum = 0.0
    n_queries = 0
    
    for job_id in all_jobs:
        sorted_cands = sorted(job_scores[job_id], key=lambda x: x[1], reverse=True)
        relevant_cands = {cid for cid, gt in ground_truth[job_id] if gt >= 3}
        if not relevant_cands:
            continue  # Skip jobs with no relevant candidates
        
        n_queries += 1
        for rank, (cid, _) in enumerate(sorted_cands, 1):
            if cid in relevant_cands:
                mrr_sum += 1.0 / rank
                break
    
    return mrr_sum / n_queries if n_queries > 0 else 0.0
```

**Trials:** 25,000 trials — TPE Sampler with 200 startup random trials

**Output:** Best `nmaiex_skill_alpha` → **LOCK** cho Phase 2

---

### Phase 2: C→J Study (Ứng Viên Tìm Việc — nDCG@10)

> **Ghi chú Data Pivot:** GT matrix được index `j{id}_c{id}` (J→C direction) nhưng relevance score là
> **đối xứng** — "candidate X phù hợp job Y" ≡ "job Y phù hợp candidate X". Phase 2 pivot theo
> candidate để tính nDCG@10. Future work: sinh GT riêng cho C→J nếu cần thêm signal.

**Search Space (7 params — alpha locked):**

```python
# alpha = LOCKED from Phase 1 best trial
# rrf_k = 60 (FROZEN — industry standard)
nmaiex_cj_weight_rrf         = trial.suggest_float("cj_w_rrf", 0.10, 0.60)
nmaiex_cj_weight_title       = trial.suggest_float("cj_w_title", 0.05, 0.40)
nmaiex_cj_weight_skill       = trial.suggest_float("cj_w_skill", 0.10, 0.60)
nmaiex_lang_required_penalty = trial.suggest_float("lang_req_pen", 0.05, 0.50)
nmaiex_lang_level_penalty    = trial.suggest_float("lang_lvl_pen", 0.02, 0.30)
nmaiex_lang_preferred_bonus  = trial.suggest_float("lang_pref_bon", 0.02, 0.20)
nmaiex_lang_bonus_cap        = trial.suggest_float("lang_bon_cap", 0.05, 0.30)
```

**Scoring Formula (reconstruct từ ranking_service.py L736-743):**

```python
RRF_K = 60  # frozen
rrf_score_norm = (1/(RRF_K + txt_rank)) * RRF_K  # C->J chi co text rank
title_score = (1/(RRF_K + title_rank)) * RRF_K
skill_score = alpha_locked * exact_overlap + (1 - alpha_locked) * fuzzy_overlap

# salary_adjustment — tinh, precomputed (base_weight=0.20 CO DINH, Approach A)
# Ly do: salary adjustment co logic asymmetric rieng (tolerance band, cap),
# khong nen couple voi weight tuning. Clip da tat nen diem co the am/vuot 1.
lang_penalty = req_missing * lang_required_penalty + level_insuf * lang_level_penalty
lang_bonus = min(pref_met * lang_preferred_bonus, lang_bonus_cap)

final_score = (w_rrf * rrf_score_norm 
              + w_title * title_score 
              + w_skill * skill_score 
              + salary_adjustment 
              - lang_penalty 
              + lang_bonus)
```

**Objective: Maximize nDCG@10**

```python
def compute_ndcg_at_k(cand_scores, ground_truth, k=10):
    """nDCG@10 using actual GT labels [0,1,2,3,4] as relevance grades."""
    from math import log2
    ndcg_sum = 0.0
    n_queries = 0
    
    for cand_id in all_candidates:
        sorted_jobs = sorted(cand_scores[cand_id], key=lambda x: x[1], reverse=True)[:k]
        
        # DCG
        dcg = sum(
            (2**ground_truth[cand_id][jid] - 1) / log2(rank + 1)
            for rank, (jid, _) in enumerate(sorted_jobs, 1)
            if jid in ground_truth[cand_id]
        )
        
        # Ideal DCG
        ideal_rels = sorted(
            [ground_truth[cand_id][jid] for jid in ground_truth[cand_id]],
            reverse=True
        )[:k]
        idcg = sum(
            (2**rel - 1) / log2(rank + 1)
            for rank, rel in enumerate(ideal_rels, 1)
        )
        
        if idcg > 0:
            ndcg_sum += dcg / idcg
            n_queries += 1
    
    return ndcg_sum / n_queries if n_queries > 0 else 0.0
```

**Trials:** 25,000 trials — TPE Sampler

---

## 4. Proposed Changes

### [NEW] `nmaiex_tuning/tune_nmaiex_hyperparams.py`

Script chính chứa:

1. **`async def precompute_all_pairs()`** — Startup phase:
   - Connect DB 1 lần
   - Load GT matrix
   - Query job metadata (skills, levels, salary, lang requirements)
   - Query candidate metadata (skills, exp, languages)
   - Compute fuzzy overlaps (cosine via DB `<=>` operator)
   - Compute RRF rank positions (vector search + text search)
   - Compute salary adjustments
   - Compute language component counts
   - Pack everything vào `List[JCPairData]` và `List[CJPairData]`

2. **`def jc_objective(trial, pairs, gt)`** — Phase 1 objective (pure Python, ~5ms/trial)

3. **`def cj_objective(trial, pairs, gt, locked_alpha, locked_rrf_k)`** — Phase 2 objective

4. **`def compute_mrr(...)` / `def compute_ndcg_at_k(...)`** — Metric functions

5. **`def update_env_file(best_params)`** — Parse và update `.env.nmaiex`

6. **`async def main()`** — Orchestrator:
   - Precompute
   - Run Phase 1 Study (25,000 trials)
   - Lock alpha & rrf_k
   - Run Phase 2 Study (25,000 trials)
   - Compute before/after metrics
   - Update `.env.nmaiex`

### Data Structures (In-Memory)

```python
@dataclass
class JCPairData:
    """Pre-computed data for a J->C pair."""
    job_id: int
    cand_id: int
    gt_score: int           # Ground truth [0-4]
    vec_rank: int           # Vector search rank position
    txt_rank: int           # Text search rank position  
    exact_overlap: float    # |job intersection cand| / |job|
    fuzzy_overlap: float    # avg_max_cosine
    exp_gap_under: float    # max(job_min - cand_exp, 0)
    exp_gap_over: float     # max(cand_exp - job_max, 0)

@dataclass
class CJPairData:
    """Pre-computed data for a C->J pair."""
    cand_id: int
    job_id: int
    gt_score: int
    txt_rank: int           # Text search rank (candidate text vs job)
    title_rank: int         # Title match rank
    exact_overlap: float
    fuzzy_overlap: float
    salary_adjustment: float  # Pre-computed, static
    lang_req_missing: int     # Count of missing REQUIRED languages
    lang_lvl_insuf: int       # Count of insufficient-level REQUIRED languages
    lang_pref_met: int        # Count of met PREFERRED languages
```

---

## 5. Auto-Update `.env.nmaiex`

Script sẽ:
1. Đọc file `.env.nmaiex`
2. Parse từng dòng, giữ nguyên comments và structure
3. Replace giá trị cho 13 params đã tune bằng regex match
4. Backup file gốc sang `.env.nmaiex.backup_YYYYMMDD_HHMMSS`
5. Ghi file mới

---

## 6. Resolved Decisions (User Approved)

> **Q1 (RESOLVED): C→J Data Pivot — Dùng GT hiện tại, pivot theo candidate.**
> Relevance score là đối xứng: "candidate phù hợp job" ≡ "job phù hợp candidate".
> Future work: sinh GT riêng cho C→J nếu cần thêm signal.

> **Q2 (RESOLVED): Salary base_weight = 0.20 CỐ ĐỊNH (Approach A).**
> Salary adjustment có logic asymmetric riêng (tolerance band, cap). Score clipping đã tắt
> nên điểm có thể âm/vượt 1 tự nhiên. Không couple salary weight với weight tuning.

> **Q3 (RESOLVED): rrf_k = 60 FROZEN — Không tune.**
> Giá trị k=60 là standard từ RRF paper gốc (Cormack 2009), dùng phổ quát.
> Tune trên 2,000 sparse pairs sẽ chỉ thêm nhiễu.

---

## 7. Verification Plan

### Automated Validation

1. **Before/After Comparison:** Sau khi Optuna hoàn tất, script tự động tính:
   - MRR (J→C) với default params vs. tuned params
   - nDCG@10 (C→J) với default params vs. tuned params
   - In kết quả dạng bảng so sánh

2. **Sanity Check:** Verify rằng tuned scores vẫn reasonable:
   - Kiểm tra range của final scores
   - Kiểm tra không có weight nào bị stuck ở boundary
   - Print Optuna optimization history

3. **Performance:** Ước tính runtime:
   - 2,000 cặp × 25,000 trials × 2 phases
   - Với pure Python: ~5-10ms/trial → **~4-8 phút** cho mỗi phase
   - Tổng: **~10-16 phút** trên CPU (i5 tier)

### Manual Verification

- Sau khi ghi `.env.nmaiex`, khởi động lại FANG backend và gọi API ranking thực tế
- So sánh top-10 kết quả trước/sau tune cho 2-3 jobs representative

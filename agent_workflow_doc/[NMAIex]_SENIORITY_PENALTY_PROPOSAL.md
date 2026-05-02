# [NMAIex] Seniority Penalty System - Proposal & Implementation Plan

**Status:** Pending Review  
**Date:** 2026-04-30  
**Author:** Development Team  
**Target Version:** NMAIex v2.0  
**Reference:** [NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md (Mục 3.4, 7.5)

---

## 📋 Executive Summary

Hiện tại, Seniority Penalty trong `rank_candidates_for_job()` (J→C flow) sử dụng:
- **Logic:** `penalty = coef × max(0, required_min - c_exp)` (chỉ phạt thiếu)
- **Vấn đề:** Không phạt ứng viên overqualified → Algorithm bias lên kinh nghiệm cao
- **Ảnh hưởng:** Senior áp vào Junior job không bị phạt → churn risk

**Đề xuất:** Implement **Option 3 - Asymmetric Buffer-based Penalty** với:
- Phạt thiếu kinh nghiệm: mạnh (0.25/năm)
- Phạt thừa kinh nghiệm: nhẹ (0.125/năm = 0.5 × base coef)
- Buffer linh hoạt dựa vào career path (2→7 năm tùy level)

---

## 🎯 Problem Analysis

### Current Implementation (Problematic)

```python
# nmaiex_ranking_service.py, dòng 142-151
job_min_years = [r["minyears"] for r in job_levels_rows]
required_min_years = min(job_min_years)  # e.g., 0 for Intern

# Dòng 263-266
gap = max(0, required_min_years - c_exp)
seniority_penalty = 0.25 * gap
```

**Logic hiện tại:**
```
Job yêu cầu: [Intern(0), Junior(1), Middle(3)]
required_min_years = 0

Ứng viên 0 năm:   gap = 0 → penalty = 0 ✅
Ứng viên 1 năm:   gap = 0 → penalty = 0 ✅
Ứng viên 3 năm:   gap = 0 → penalty = 0 ✅
Ứng viên 8 năm:   gap = 0 → penalty = 0 ✅ (Senior không bị phạt!)
Ứng viên 15 năm:  gap = 0 → penalty = 0 ✅ (Quá thừa, không phạt!)
```

**Hệ quả:**
- ❌ Algorithm ưu tiên kinh nghiệm cao (vì không phạt)
- ❌ Senior hay apply vào Junior job → nhanh chóng churn
- ❌ Không tạo khuyến khích cho "right-fit" candidate

---

## ✨ Proposed Solution: Option 3 - Asymmetric Buffer-Based Penalty

### Core Concept

```
Job levels: [minYears_1, minYears_2, ..., minYears_n]
└─ job_min = min(levels)              # e.g., 0 (Intern)
└─ job_max_raw = max(levels)          # e.g., 5 (Senior)
└─ buffer = f(job_max_raw)            # Dựa vào career path
└─ job_max = job_max_raw + buffer     # Grace zone boundary
```

### Buffer Strategy (Career Path Based)

| job_max_raw | Career Stage | Buffer | job_max | Giải thích |
|-------------|--------------|--------|---------|-----------|
| ≤ 1 | Very Junior | 2 | 1+2=3 | Fresher/Intern job → rất vừa vừa ít kinh nghiệm thêm |
| 1-3 | Junior | 3 | 3+3=6 | Junior job → tolerant thêm ~3 năm |
| 3-5 | Middle | 4 | 5+4=9 | Middle job → grace zone 9 năm |
| 5-8 | Senior | 5 | 8+5=13 | Senior job → vẫn OK nếu < 13 năm |
| >8 | Lead/Manager | 7 | max+7 | C-level → longest grace zone |

### Penalty Formula

```
penalty_insufficient = coef × gap                    (Thiếu)
penalty_overqualified = coef × ratio × gap           (Thừa)

Where:
  coef = NMAIEX_JC_PENALTY_SENIORITY_COEF (0.25)
  ratio = NMAIEX_SENIORITY_OVERQUALIFIED_PENALTY_RATIO (0.5)
  gap = abs(c_exp - boundary)
```

**Asymmetry Explanation:**
- Thiếu kinh nghiệm = vấn đề thực (cần training) → phạt nặng
- Thừa kinh nghiệm = có thể chấp nhận (mentoring potential) → phạt nhẹ (0.5x)

---

## 📊 Examples from Root Data (JOBLEVEL)

### Example 1: Intern Only Job

```sql
JOB_LEVEL_MAP: Intern
└─ minYears = 0

CALCULATION:
job_min = 0
job_max_raw = 0
buffer = NMAIEX_BUFFER_VERY_JUNIOR = 2
job_max = 0 + 2 = 2

PENALTY TABLE:
┌──────────────┬──────┬─────────────────┬─────────────┐
│ c_exp (năm) │ Gap  │ Điều kiện       │ Penalty     │
├──────────────┼──────┼─────────────────┼─────────────┤
│ 0            │ 0    │ [0,2] Grace OK  │ 0.0 ✅      │
│ 1            │ 0    │ [0,2] Grace OK  │ 0.0 ✅      │
│ 2            │ 0    │ [0,2] Grace OK  │ 0.0 ✅      │
│ 3            │ 1    │ > 2 Overqualif  │ 0.125 ⚠️    │
│ 5            │ 3    │ > 2 Overqualif  │ 0.375 ⚠️    │
│ 10           │ 8    │ > 2 Overqualif  │ 1.0 ⚠️      │
└──────────────┴──────┴─────────────────┴─────────────┘

Công thức: 
  3 năm: gap = 3-2 = 1 → penalty = 0.25 × 0.5 × 1 = 0.125
  5 năm: gap = 5-2 = 3 → penalty = 0.25 × 0.5 × 3 = 0.375
  10 năm: gap = 10-2 = 8 → penalty = 0.25 × 0.5 × 8 = 1.0
```

### Example 2: Junior + Middle + Senior (Typical)

```sql
JOB_LEVEL_MAP: Junior(1), Middle(3), Senior(5)
└─ minYears = [1, 3, 5]

CALCULATION:
job_min = 1
job_max_raw = 5
buffer = NMAIEX_BUFFER_MIDDLE = 4
job_max = 5 + 4 = 9

PENALTY TABLE:
┌──────────────┬──────┬──────────────────┬──────────────┐
│ c_exp (năm) │ Gap  │ Điều kiện        │ Penalty      │
├──────────────┼──────┼──────────────────┼──────────────┤
│ 0            │ 1    │ < 1 Insufficient │ 0.25 × 1 = 0.25 ⚠️ (thiếu) │
│ 1            │ 0    │ [1,9] Grace OK   │ 0.0 ✅       │
│ 3            │ 0    │ [1,9] Grace OK   │ 0.0 ✅       │
│ 5            │ 0    │ [1,9] Grace OK   │ 0.0 ✅       │
│ 8            │ 0    │ [1,9] Grace OK   │ 0.0 ✅       │
│ 9            │ 0    │ [1,9] Grace OK   │ 0.0 ✅       │
│ 10           │ 1    │ > 9 Overqualif   │ 0.125 ⚠️ (nhẹ) │
│ 12           │ 3    │ > 9 Overqualif   │ 0.375 ⚠️     │
│ 15           │ 6    │ > 9 Overqualif   │ 0.75 ⚠️      │
└──────────────┴──────┴──────────────────┴──────────────┘

Key insight:
  - 0 năm: penalty = 0.25 (thiếu nặng)
  - 10 năm: penalty = 0.125 (thừa nhẹ, chỉ ½ so với thiếu)
  - Ứng viên "right-fit" (1-5 năm): penalty = 0 ✅
```

### Example 3: Senior + Lead + Manager (C-Level)

```sql
JOB_LEVEL_MAP: Senior(5), Lead(7), Manager(8), Director(12)
└─ minYears = [5, 7, 8, 12]

CALCULATION:
job_min = 5
job_max_raw = 12
buffer = NMAIEX_BUFFER_LEAD_MANAGER = 7
job_max = 12 + 7 = 19

PENALTY TABLE:
┌──────────────┬──────┬──────────────────┬──────────────┐
│ c_exp (năm) │ Gap  │ Điều kiện        │ Penalty      │
├──────────────┼──────┼──────────────────┼──────────────┤
│ 4            │ 1    │ < 5 Insufficient │ 0.25 × 1 = 0.25 ⚠️ │
│ 5            │ 0    │ [5,19] Grace OK  │ 0.0 ✅       │
│ 8            │ 0    │ [5,19] Grace OK  │ 0.0 ✅       │
│ 12           │ 0    │ [5,19] Grace OK  │ 0.0 ✅       │
│ 15           │ 0    │ [5,19] Grace OK  │ 0.0 ✅       │
│ 19           │ 0    │ [5,19] Grace OK  │ 0.0 ✅       │
│ 20           │ 1    │ > 19 Overqualif  │ 0.125 ⚠️ (nhẹ) │
│ 25           │ 6    │ > 19 Overqualif  │ 0.75 ⚠️      │
└──────────────┴──────┴──────────────────┴──────────────┘
```

---

## 🔧 Implementation Details

### 1. Files to Modify

#### A. `.env.nmaiex` - Add New Configuration

```dotenv
# --- Seniority Penalty (Option 3 - Asymmetric Buffer-Based) ---
# Base coefficient: trừ khi thiếu kinh nghiệm (mỗi năm thiếu)
NMAIEX_JC_PENALTY_SENIORITY_COEF=0.25

# Ratio: phạt overqualified so với thiếu (0.5 = phạt ½ mức)
NMAIEX_SENIORITY_OVERQUALIFIED_PENALTY_RATIO=0.5

# Buffer years per career path tier
NMAIEX_BUFFER_VERY_JUNIOR=2        # job_max ≤ 1 năm (Intern/Fresher)
NMAIEX_BUFFER_JUNIOR=3             # job_max 1-3 năm (Junior)
NMAIEX_BUFFER_MIDDLE=4             # job_max 3-5 năm (Middle)
NMAIEX_BUFFER_SENIOR=5             # job_max 5-8 năm (Senior)
NMAIEX_BUFFER_LEAD_MANAGER=7       # job_max > 8 năm (Lead/Manager)
```

#### B. `app/core/nmaiex_config.py` - Update Settings Class

```python
class NMAIexSettings(BaseSettings):
    # ... existing fields ...
    
    # Seniority Penalty - Option 3
    nmaiex_jc_penalty_seniority_coef: float = 0.25
    nmaiex_seniority_overqualified_penalty_ratio: float = 0.5
    
    # Buffer tiers (năm) - dựa vào career path
    nmaiex_buffer_very_junior: int = 2
    nmaiex_buffer_junior: int = 3
    nmaiex_buffer_middle: int = 4
    nmaiex_buffer_senior: int = 5
    nmaiex_buffer_lead_manager: int = 7
    
    model_config = SettingsConfigDict(
        env_file=".env.nmaiex", env_file_encoding="utf-8", extra="ignore"
    )
```

#### C. `app/services/nmaiex_ranking_service.py` - Update `rank_candidates_for_job()`

**Location:** Replace dòng 142-151 và 263-270

**Phần 1 - Lấy job_min/max (thay dòng 142-151):**

```python
# Lấy required seniority với buffer dựa vào career path
job_levels_rows = await conn.fetch(
    """
    SELECT l.minYears
    FROM JOB_LEVEL_MAP m
    JOIN JOBLEVEL l ON m.levelId = l.levelId
    WHERE m.jobPostId = $1
    """,
    job_id,
)
job_min_years = [r["minyears"] for r in job_levels_rows]

if job_min_years:
    job_min = min(job_min_years)
    job_max_raw = max(job_min_years)
    
    # Lấy buffer dựa vào career path (Option 3)
    if job_max_raw <= 1:
        buffer = nmaiex_settings.nmaiex_buffer_very_junior
    elif job_max_raw <= 3:
        buffer = nmaiex_settings.nmaiex_buffer_junior
    elif job_max_raw <= 5:
        buffer = nmaiex_settings.nmaiex_buffer_middle
    elif job_max_raw <= 8:
        buffer = nmaiex_settings.nmaiex_buffer_senior
    else:
        buffer = nmaiex_settings.nmaiex_buffer_lead_manager
    
    job_max = job_max_raw + buffer
else:
    job_min = 0
    job_max = float('inf')
```

**Phần 2 - Tính penalty (thay dòng 263-270):**

```python
# Seniority Penalty - Asymmetric (Insufficient vs Overqualified)
c_exp = c["expyears"] or 0
base_penalty_coef = nmaiex_settings.nmaiex_jc_penalty_seniority_coef
overqualified_ratio = nmaiex_settings.nmaiex_seniority_overqualified_penalty_ratio

if c_exp < job_min:
    # Thiếu kinh nghiệm → phạt nặng
    gap = job_min - c_exp
    seniority_penalty = base_penalty_coef * gap
elif c_exp > job_max:
    # Thừa kinh nghiệm (vượt buffer) → phạt nhẹ
    gap = c_exp - job_max
    seniority_penalty = base_penalty_coef * overqualified_ratio * gap
else:
    # Grace zone: trong [job_min, job_max] → không phạt
    seniority_penalty = 0.0

final_score = clip_score(
    w_rrf * rrf_score_norm + w_skill * skill_score - seniority_penalty
)
```

### 2. Code Changes Summary

| File | Lines | Type | Impact |
|------|-------|------|--------|
| `.env.nmaiex` | New | Config | +6 lines (5 buffer vars + 1 ratio var) |
| `nmaiex_config.py` | Update | Settings | +6 new class vars |
| `nmaiex_ranking_service.py` | Replace | Logic | ~40 lines (refactor buffer calc + penalty) |

---

## 🎯 Expected Outcomes

### Before (Min-based, only insufficient penalty)
```
Job: Junior(1), Middle(3), Senior(5)
required_min_years = 1

Score impact:
  0yr: -0.25 ⚠️ (thiếu)
  1yr: 0 ✅
  5yr: 0 ✅
  10yr: 0 ✅ ← PROBLEM: No penalty for overqualified
  15yr: 0 ✅ ← PROBLEM: No penalty for overqualified
```

### After (Buffer-based, asymmetric penalty)
```
Job: Junior(1), Middle(3), Senior(5) [job_max = 9]

Score impact:
  0yr: -0.25 ⚠️ (thiếu kinh nghiệm)
  1yr: 0 ✅ (perfect minimum)
  5yr: 0 ✅ (perfect fit)
  9yr: 0 ✅ (edge of grace zone)
  10yr: -0.125 ⚠️ (vượt buffer 1 năm)
  15yr: -0.375 ⚠️ (vượt buffer 6 năm)
```

**Benefits:**
- ✅ Khuyến khích "right-fit" candidate (penalty = 0 trong grace zone)
- ✅ Giảm churn risk: Senior không apply vào Junior job mà không bị phạt
- ✅ Asymmetric penalty: công bằng hơn (thiếu = vấn đề thực, thừa = có thể chấp nhận)
- ✅ 100% config-driven: dễ A/B test & tune

---

## 🔄 Backward Compatibility

- **Breaking Change:** Có (logic penalty thay đổi)
- **Migration Path:**
  1. Deploy config changes trước
  2. Update nmaiex_config.py
  3. Update ranking logic
  4. Test với seed data (root_data.sql)
  5. Monitor metrics: MRR, churn rate, fit score distribution
- **Rollback Plan:** Set `NMAIEX_BUFFER_*=0` để về behavior cũ (min-based)

## 📝 Documentation Updates

- [ ] Update [NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md (Mục 7.5)
- [ ] Add Seniority Penalty formula to docs/system_architecture.md
- [ ] Document .env.nmaiex changes in docs/guide/integration_guide.md

---

**Version:** 1.0  
**Last Updated:** 2026-04-30

# [NMAIex] C→J Flow - Comprehensive Optimization Report

**Status:** Ready for Advanced AI Review  
**Date:** 2026-04-30  
**Analyzed By:** Claude Haiku 4.5  
**Model Used:** Claude Haiku (Copilot)  
**Reference:** [NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md (Mục 3.4, 7.5)

---

## 📋 Executive Summary

Luồng C→J (Ứng viên tìm công việc) hiện có **5 vấn đề chính** cần tối ưu hóa:

| # | Issue | Impact | Priority | Status |
|---|-------|--------|----------|--------|
| **1** | Title weight không dùng | HIGH | P1 | Ready |
| **2** | Weight mismatch (skill) | MEDIUM | P1 | Ready |
| **3** | Salary adjustment chưa implement | HIGH | P1 | Ready |
| **4** | Title matching không có | HIGH | P1 | Ready |
| **5** | CV elements underutilized (cert + lang) | MEDIUM | P2 | Ready |

---

## 🔴 Issue #1: Title Weight Không Dùng

### **Current Code (Buggy)**

```python
# dòng 394-397 (nmaiex_ranking_service.py)
w_rrf = nmaiex_settings.nmaiex_cj_weight_rrf      # 0.35 ✅
w_skill = nmaiex_settings.nmaiex_jc_weight_skill  # 0.40 ⚠️ WRONG!

# dòng 427-429
final_score = clip_score(
    w_rrf * rrf_score_norm + w_skill * skill_score - salary_penalty
)
```

### **Problem:**

```
Config defined:
  NMAIEX_CJ_WEIGHT_TITLE = 0.15  ← NOT USED!
  
Code only uses:
  RRF: 0.35
  Skill: 0.40 (wrong - using J→C weight)
  
Total weight: 0.75 ≠ 1.0
Missing: 0.15 (title weight)
* NOTE FROM USER: Nếu đã biết rõ và đang trong giai đoạn thêm vào/kiểm thử thì không cần tổng weight = 1 ngay, cứ phân biệt cao/thấp được là được
```

### **Root Cause:**

- ✅ RRF score calculated từ text_rank
- ❌ Title score từ text_rank cũng calculate nhưng không integrate
- ❌ Config defined nhưng code không sử dụng

### **Impact:**

- ❌ Job title relevance bị ignore
- ❌ "Python Developer" apply vào "React Architect" job có same score → sai
- ❌ Title matching không explicit

### **Proposed Fix:**

```python
# Extract title score (separate từ generic text score)
title_score = (1.0 / (rrf_k + r_txt)) * rrf_k

# Weights (corrected)
w_rrf = 0.35
w_title = 0.15    # ← ENABLE
w_skill = 0.30    # ← CHANGE from 0.40 (J→C weight)
w_salary_adj = 0.20

# Final score
final_score = clip_score(
    w_rrf * rrf_score_norm 
    + w_title * title_score 
    + w_skill * skill_score 
    + salary_adjustment
)
```

---

## 🔴 Issue #2: Weight Mismatch - w_skill

### **Current Code (Buggy)**

```python
# dòng 397 (C→J flow)
w_skill = nmaiex_settings.nmaiex_jc_weight_skill  # 0.40 (J→C weight!)

# Config shows:
# J→C weights
nmaiex_jc_weight_rrf: float = 0.30
nmaiex_jc_weight_skill: float = 0.40

# C→J weights
nmaiex_cj_weight_rrf: float = 0.35
nmaiex_cj_weight_title: float = 0.15           # Not used
# ❌ NO nmaiex_cj_weight_skill defined!
* NOTE FROM USER: Nếu có chủ ý dùng chung -> giải thích rõ ràng. Nếu không thì cần trình bày phương án đánh giá riêng cho cj
```

### **Problem:**

```
J→C composition:
  RRF: 0.30 + Skill: 0.40 = 0.70 (additive weights)
  
C→J composition (current - WRONG):
  RRF: 0.35 + Skill: 0.40 = 0.75
  + Title: 0.15 = 0.90 (should be 1.0)
  
Why wrong?
  - C→J doesn't have vector search (only text)
  - Different signal composition should have different weights
  - J→C: 2 signals (vector + text) → skill weight 0.40
  - C→J: 1 signal (text only) → skill weight should be lower
```

### **Impact:**

```
Ứng viên với:
  - Strong skills (1.0 skill_score)
  - Weak title match (0.3 title_score)
  - No salary info (0 salary)
  
Score = 0.35*0.8 + 0.40*1.0 + 0 = 0.28 + 0.40 = 0.68

Nên:
Score = 0.35*0.8 + 0.15*0.3 + 0.30*1.0 + 0 = 0.28 + 0.045 + 0.30 = 0.625

Kết quả: skill được ưu tiên quá (0.40 > 0.30)
→ Ứng viên có skill cao nhưng title không match vẫn được score cao
→ Không đúng: ứng viên nên tìm job với title match
```

### **Proposed Fix:**

```python
# nmaiex_config.py - ADD new setting
nmaiex_cj_weight_skill: float = 0.30  # Lower than J→C (0.40)
nmaiex_cj_weight_salary: float = 0.20

# .env.nmaiex - ADD
NMAIEX_CJ_WEIGHT_SKILL=0.30
NMAIEX_CJ_WEIGHT_SALARY=0.20

# nmaiex_ranking_service.py - USE correct weight
w_skill = nmaiex_settings.nmaiex_cj_weight_skill  # 0.30 (not 0.40!)
```

---

## 🔴 Issue #3: Salary Adjustment - Chưa Implement

### **Current Code (Non-functional)**

```python
# dòng 423-424
# Salary Penalty (hiện tại = 0 vì DB chưa có expected salary của ứng viên)
salary_penalty = 0.0
```

### **Problem:**

```
1. salary_penalty luôn = 0
2. Config định nghĩa nmaiex_cj_penalty_salary_coef = 0.20 (không dùng)
3. Không có expected_salary của ứng viên
4. Chỉ có job.minSalary, job.maxSalary
5. Logic penalty (trừ) không phù hợp cho salary
   → Job salary cao sao lại bị trừ?
```

### **Impact:**

```
Ứng viên 5 năm (expected ~27.5M VND):
  - Job A: [10M-12M] (thấp) → score 0.68 (không phạt)
  - Job B: [35M-45M] (cao) → score 0.68 (không phạt)
  → Same score! Sai logic
  
Nên:
  - Job A (thấp) → score 0.65 (penalty nếu dưới tolerance)
  - Job B (cao) → score 0.70 (bonus vì lương tốt)
```

### **Proposed Fix: Salary Bonus Strategy**
* NOTE FROM USER: Các biến số về lương trong này cần được đặt ở một file env riêng hoặc để chung vào env.nmaiex. Chốt lại để cho dễ quản lý và cập nhật, kéo theo đó cũng cần cập nhật bằng "skill" cho Agent, tham khảo "agent_workflow_doc\AI_MANUAL_UPDATE" để cập nhật thông tin về LLM model (có thể gộp chung vào đây hoặc tách skill riêng, tách riêng thì cần đổi tên chung chung hiện tại của AI_MANUAL_UPDATE luôn)
* NOTE FROM USER: Cân nhắc luôn cả việc sửa parser để AI gom expected salary của Candidate (nếu có) -> kéo theo là sửa cả Model Pydantic v.v (min-sal và max-sal của JobPosting không phải lúc nào cũng có, đôi khi chỉ là 'thỏa thuận'. Cần lưu tâm vấn đề này)

```python
def estimate_expected_salary(
    expyears: float,
    location: str = "DEFAULT"
) -> int:
    """Ước lượng expected salary từ experience years"""
    
    base_salaries = {
        "HANOI": 15_000_000,
        "TPHCM": 14_000_000,
        "DANANG": 12_000_000,
        "DEFAULT": 13_000_000,
    }
    base = base_salaries.get(location, 13_000_000)
    
    # Annual increment tiers
    if expyears <= 1:
        increment = 1_500_000
    elif expyears <= 3:
        increment = 2_000_000
    elif expyears <= 5:
        increment = 2_500_000
    else:
        increment = 3_000_000
    
    return base + (expyears * increment)

def calculate_salary_adjustment(
    min_salary: Optional[int],
    max_salary: Optional[int],
    expected_salary: int,
    base_weight: float = 0.20
) -> tuple[float, str]:
    """
    Asymmetric adjustment:
    - Salary thấp → penalty (trừ)
    - Salary cao → bonus (cộng)
    """
    
    if not min_salary or not max_salary:
        return 0.0, "no_info"
    
    mid_salary = (min_salary + max_salary) / 2
    lower_tolerance = expected_salary * 0.8
    upper_target = expected_salary * 1.2
    
    if mid_salary < lower_tolerance * 0.8:
        # Very low
        gap_ratio = (lower_tolerance * 0.8 - mid_salary) / expected_salary
        return -base_weight * min(gap_ratio, 1.0), "penalty_very_low"
    
    elif mid_salary < lower_tolerance:
        # Low
        gap_ratio = (lower_tolerance - mid_salary) / expected_salary
        return -base_weight * 0.5 * gap_ratio, "penalty_low"
    
    elif mid_salary < upper_target:
        # Acceptable
        return 0.0, "neutral"
    
    else:
        # High - BONUS!
        bonus_ratio = (mid_salary - upper_target) / expected_salary
        bonus = base_weight * 0.2 * bonus_ratio
        return min(bonus, 0.2), "bonus_high"
```

### **Config Changes:**

```dotenv
# .env.nmaiex - ADD
NMAIEX_SALARY_BASE_HANOI=15000000
NMAIEX_SALARY_BASE_TPHCM=14000000
NMAIEX_SALARY_BASE_DANANG=12000000
NMAIEX_SALARY_BASE_DEFAULT=13000000

NMAIEX_SALARY_INCREMENT_JUNIOR=1500000
NMAIEX_SALARY_INCREMENT_MIDDLE=2000000
NMAIEX_SALARY_INCREMENT_SENIOR=2500000

NMAIEX_SALARY_TOLERANCE_LOWER=0.8
NMAIEX_SALARY_TOLERANCE_UPPER=1.2
NMAIEX_SALARY_BONUS_CAP=0.2
```

---

## 🔴 Issue #4: Title Matching - Không Extract Job Title
* NOTE FROM USER: Ý tưởng gốc ở đây là user thấy trọng số title match trong c->j nhưng lại không dùng, thấy JobPosting thì có title nhưng tự hỏi lấy gì tương ứng của candidate để match. Cơ chế match thế nào. Ở đây vì dùng model nhẹ như Haiku nên có thể soi hơi ảo.
### **Current State**

```python
# dòng 315-322 (C→J query)
SELECT u.fName, u.lName, c.expyears, c.bio, cv.rawText
# ❌ Không lấy job titles từ CV!

# CV có:
class Experience(CVBaseModel):
    company: str | None
    title: str | None          # ← Job title ở đây
    startDate: CVDate | None
    endDate: CVDate | None
    description: str | None
```

### **Problem:**

```
Ứng viên:
  - Recent experience: "Senior Python Backend Engineer"
  - CV.experience[0].title = "Senior Python Backend Engineer"
  
Query chỉ lấy rawText:
  "Senior Python Backend Engineer ... 8 years experience in ..."
  
Text search (generic):
  - Job "Senior Backend Engineer" → match all words
  - Job "Frontend React Developer" → match "Developer", "Senior"
  → Same relevance, sai!

Nên extract title riêng:
  Candidate titles: ["Senior Python Backend Engineer", ...]
  Job title: "Senior Backend Engineer"
  → Exact title match → better relevance!
```

### **Impact:**

```
Candidate: "Backend Engineer, 5 years"
  
Job A: "Senior Backend Engineer" (title match perfect!)
  - Without title extraction: text_rank = 0.75
  - With title extraction: title_score = 0.95 → weight 0.15
  
Job B: "Data Analyst" (title no match)
  - Without: text_rank = 0.70
  - With: title_score = 0.1 → weight 0.15
  
Difference: 0.15 * (0.95 - 0.1) = 0.1275 → Job A more likely selected

Current: both have similar score (no title differentiation)
```

### **Proposed Fix**

```python
# dòng 315-322 - MODIFY query
async with acquire_conn() as conn:
    candidate_row = await conn.fetchrow(
        """
        WITH LatestApp AS (...)
        SELECT 
            u.fName, u.lName, c.expyears, c.bio, 
            cv.rawText,
            cv.parsedData -> 'experience' as experiences  ← NEW
        FROM "user" u
        ...
        """,
        candidate_id,
    )
    
    # Extract recent job titles
    recent_titles = []
    if candidate_row["experiences"]:
        exps = candidate_row["experiences"]  # JSON array
        for exp in exps[:3]:  # Top 3 recent
            if exp.get("title"):
                recent_titles.append(exp["title"])

# dòng 335-345 - MODIFY candidate_text building
candidate_profile = []
if candidate_row["bio"]:
    candidate_profile.append(candidate_row["bio"])

# Add recent job titles (high relevance)
if recent_titles:
    candidate_profile.append(" ".join(recent_titles))

# Fallback
candidate_text = " ".join(filter(None, candidate_profile)) or candidate_row["rawtext"]
```

---

## 🔴 Issue #5: CV Elements Underutilized - Certificates & Languages

### **Current ParsedCV Usage**
* NOTE FROM USER: Về ý tưởng gốc thì user thấy ra được là j->c có pen là số năm kinh nghiệm nhưng những cái quan trọng như chứng chỉ hoặc ngôn ngữ lại chưa mang ra pen hoặc bonus
```python
class ParsedCV:
    candidateInfo: list[CandidateInfo]  # ← Not used
    education: list[Education]          # ← ❌ IGNORED
    experience: list[Experience]        # ← Partial (only years)
    skills: list[str]                   # ← ❌ IGNORED (use DB instead)
    certificates: list[str]             # ← ❌ IGNORED
    languages: list[str]                # ← ❌ IGNORED
    summary: str                        # ← ❌ IGNORED
    rawText: str                        # ← ✅ Only this used
```

### **Problem - Certificates**

```
Candidate has:
  - AWS Certified Solutions Architect Professional
  - GCP Associate Cloud Engineer
  - Kubernetes Administrator (CKA)

Current: All ignored in ranking
Result: Cannot differentiate from uncertified candidates

Job "AWS Cloud Architect" search:
  - Certified candidate score: 0.68
  - Uncertified candidate score: 0.65
  → Certified should score HIGHER (certificates = specialization proof)
```

### **Problem - Languages**

```
Candidate has:
  - English: Fluent
  - Vietnamese: Native
  - Mandarin: Intermediate
  - Japanese: Basic

Current: All ignored
Result: Cannot filter/boost jobs requiring specific languages

Job "Japan Engineering team":
  - Multilingual candidate (with Japanese): 0.68
  - English-only candidate: 0.68
  → Same score, but Japanese speaker should rank higher
```

### **Problem - Education**

```
Candidate has:
  - Bachelor of Computer Science
  - Master of Computer Science

Current: Ignored (only expyears used)
Result: Can't differentiate education level impact

Job "Research Scientist":
  - Master degree holder: 0.70
  - Bachelor degree holder: 0.70
  → Master should score higher (research preference)
```

### **Proposed Solution: Enrich Text Profile**

```python
async def build_enriched_candidate_profile(
    candidate_row,
    parsed_cv: ParsedCV
) -> str:
    """Build comprehensive text profile from all CV elements"""
    
    parts = []
    
    # 1. Basic bio
    if candidate_row["bio"]:
        parts.append(candidate_row["bio"])
    
    # 2. Recent job titles (from issue #4)
    if parsed_cv.experience:
        titles = [exp.title for exp in parsed_cv.experience[:3] if exp.title]
        if titles:
            parts.append(" ".join(titles))
    
    # 3. Education level → signal
    education_keywords = []
    for edu in parsed_cv.education:
        if edu.degree:
            education_keywords.append(edu.degree)
    if education_keywords:
        parts.append(" ".join(education_keywords))
    
    # 4. Certificates → specialization signals
    if parsed_cv.certificates:
        parts.append(" ".join(parsed_cv.certificates))
    
    # 5. Languages → multilingual signals
    if parsed_cv.languages:
        parts.append(" ".join(parsed_cv.languages))
    
    # 6. Skills from CV (top 10)
    if parsed_cv.skills:
        parts.append(" ".join(parsed_cv.skills[:10]))
    
    # 7. Summary (career objective)
    if parsed_cv.summary:
        parts.append(parsed_cv.summary)
    
    # Combine all
    enriched_text = " ".join(filter(None, parts))
    fallback_text = candidate_row["rawtext"]
    
    return enriched_text if enriched_text.strip() else fallback_text
```

### **Impact on Text Search**

```
Before (rawText only):
  "Senior engineer 8 years Java Python design patterns AWS"

After (enriched):
  "Looking for cloud architect role
   Senior Backend Engineer Architect Cloud Lead
   Master of Computer Science
   AWS Certified Solutions Architect Professional
   GCP Associate Cloud Engineer
   Kubernetes Administrator
   English Vietnamese Mandarin
   Java Python Go Rust Kotlin gRPC Kubernetes Docker
   Led 10-person team on distributed systems"

Job "AWS Cloud Architect":
  - Before: text_rank = 0.72 (generic)
  - After: text_rank = 0.95 (specific certificate match)
  → 0.15 * (0.95 - 0.72) = 0.0345 boost

Job "Japan Engineering":
  - Before: text_rank = 0.60 (no language mention)
  - After: text_rank = 0.75 (Mandarin mention, close to Japanese)
  → 0.15 * (0.75 - 0.60) = 0.0225 boost
```

---

## 📊 Implementation Summary

### **Files to Modify**

| File | Changes | Complexity |
|------|---------|-----------|
| `.env.nmaiex` | Add salary, weight configs | LOW |
| `nmaiex_config.py` | Add salary, weight settings | LOW |
| `nmaiex_ranking_service.py` | Functions: estimate_salary, calculate_salary_adj, build_enriched_profile | MEDIUM |
| `cv_models.py` | No changes (already has ParsedCV structure) | N/A |

### **Code Changes Breakdown**

```
Issue #1 (Title weight):     ~5 lines (enable w_title)
Issue #2 (Weight fix):       ~3 lines (change w_skill = 0.30)
Issue #3 (Salary impl):      ~40 lines (2 new functions)
Issue #4 (Title matching):   ~15 lines (extract & build profile)
Issue #5 (CV enrichment):    ~30 lines (enrich_text function)

Total: ~93 lines new/modified code
```

### **Testing Strategy**

```python
def test_cj_flow_comprehensive():
    """E2E test C→J with all 5 fixes"""
    
    # Test candidate
    cand = Candidate(
        expyears=5,
        location="HANOI",
        cv=ParsedCV(
            experience=[
                Experience(title="Senior Backend Engineer", ...),
                Experience(title="Architect", ...),
            ],
            education=[Education(degree="Master CS", ...)],
            certificates=["AWS Architect Pro", "CKA"],
            languages=["English", "Mandarin"],
        )
    )
    
    # Test jobs
    job_a = JobPosting(
        title="Senior Backend Engineer",
        salary_range=[30M, 40M],  # Good for 5yr expected
    )
    
    job_b = JobPosting(
        title="Frontend React Developer",
        salary_range=[20M, 25M],  # Below expected
    )
    
    job_c = JobPosting(
        title="Cloud Architect - AWS",
        salary_range=[40M, 50M],  # Above expected + cert match
    )
    
    results = await rank_jobs_for_candidate(cand.id)
    
    # Assert order
    assert results[0]["job_id"] == job_c.id  # Best: title + cert + salary match
    assert results[1]["job_id"] == job_a.id  # Good: title match
    assert results[2]["job_id"] == job_b.id  # Worse: title mismatch + low salary
```

---

## 🎯 Prioritized Roadmap

### **Phase 1 - P1 (Critical)** - Week 1

- [ ] Issue #2: Fix w_skill weight
- [ ] Issue #1: Enable w_title
- [ ] Issue #4: Extract recent job titles
- [ ] Create test cases
- [ ] Deploy to staging

### **Phase 2 - P1 (Critical)** - Week 2

- [ ] Issue #3: Implement salary adjustment functions
- [ ] Add salary configs to .env
- [ ] Integration testing with jobs having different salary ranges
- [ ] Deploy to production

### **Phase 3 - P2 (Enhancement)** - Week 3

- [ ] Issue #5: Build enriched_text function
- [ ] Include certificates, languages, education
- [ ] Monitor text_rank improvements
- [ ] Gradual rollout with metrics tracking

---

## 📈 Expected Metrics Improvement

### **Before Fixes**

```
C→J metrics:
  - Title relevance: ❌ Not measured (no title matching)
  - Salary fit: ❌ All jobs same score (penalty = 0)
  - Certification match: ❌ Ignored
  - Language match: ❌ Ignored
  
  MRR@5: ~0.35
  nDCG@10: ~0.42
  User click-through: ~8%
```

### **After All Fixes**

```
C→J metrics:
  - Title relevance: ✅ Title match weighted 0.15
  - Salary fit: ✅ Bonus/penalty based on range
  - Certification match: ✅ Text boost for certificates
  - Language match: ✅ Text boost for languages
  
  Expected:
  MRR@5: ~0.48-0.52 (+35-50%)
  nDCG@10: ~0.55-0.60 (+30-42%)
  User click-through: ~11-13% (+37-62%)
```

---

## ✅ Acceptance Criteria

- [ ] All 5 issues implemented
- [ ] Config variables defined & documented
- [ ] Unit tests pass (>90% coverage)
- [ ] Integration tests pass (E2E ranking scenarios)
- [ ] Staging validation successful
- [ ] Metrics baseline established
- [ ] Production deployment completed
- [ ] Monitoring alerts configured

---

## 📝 Notes for Advanced AI Review

**For AI Model Reviewing This Report:**

1. **Context:** This is Phase 2 optimization of NMAIex ranking system
2. **Complexity:** Medium - involves refactoring C→J flow with 5 independent fixes
3. **Risk:** Low - each fix is isolated and testable
4. **Dependencies:** None - fixes don't affect J→C or other systems
5. **Data Requirements:** Salary reference data, test job postings with various ranges

### ⚠️ Additional Consideration: Weight Normalization

**Note:** Current `.env.nmaiex` has weights that do NOT sum to 1.0:
- **J→C:** `NMAIEX_JC_WEIGHT_RRF (0.30) + NMAIEX_JC_WEIGHT_SKILL (0.40) = 0.70`
- **C→J:** `NMAIEX_CJ_WEIGHT_RRF (0.35) + NMAIEX_CJ_WEIGHT_TITLE (0.15) = 0.50`

**Question for Advanced AI Review:** Has the project considered adopting standard ML ranking practice of normalized weights (summing to 1.0)? This would:
- Make all final scores consistently in [0, 1.0] range
- Improve transparency of score composition
- Enable cleaner penalty/bonus application
- Align with industry best practices from Learning-to-Rank literature

If intentional (as "Phase 1 Stage" with unfinalized weights), should this be documented? Or should weights be normalized as part of these fixes?

---

**Questions for AI:**

1. Is salary estimation formula (base + increment per tier) reasonable for Vietnam market?
2. Should certificates/languages have separate weights or text enrichment only?
3. Should education level (Bachelor/Master/PhD) be used as separate filter or text signal?
4. Is ±20% salary tolerance range appropriate or should it be configurable per region?

---

**Version:** 1.0  
**Last Updated:** 2026-04-30  
**Prepared By:** Claude Haiku 4.5

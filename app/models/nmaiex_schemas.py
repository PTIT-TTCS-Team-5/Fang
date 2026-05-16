# [NMAIex] Pydantic models cho NMAIex extension
# Tham chiếu: [NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md — Mục 8 (Pydantic Mapper Upgrade)

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

# ============================================================
# Mapper Models (Mục 8.2)
# ============================================================


class SkillMappingResult(BaseModel):
    """Output Pydantic-validated của LLM skill mapper (Strategy C — 2 tầng).

    - matched_ids: skillId có trong catalog → dùng cho exact scoring.
    - unmatched_texts: text không map được → đưa sang Tầng 2 (embedding fallback).
    """

    matched_ids: list[int] = Field(default_factory=list)
    unmatched_texts: list[str] = Field(default_factory=list)


class ProvinceMappingResult(BaseModel):
    """Output Pydantic-validated của LLM province mapper.

    - prov_id: mã provId chuẩn (34 tỉnh sau sáp nhập 2025), hoặc None nếu UNKNOWN.
    """

    prov_id: Optional[str] = None


# ============================================================
# Ranking Models (Phase 3 — sẽ dùng khi tạo API routes)
# ============================================================


class ScoreBreakdown(BaseModel):
    """Chi tiết từng thành phần điểm — luôn trả về để debug."""

    # Common
    exact_overlap: float
    fuzzy_overlap: float
    skill_score: float
    skill_alpha: float
    hard_filter_passed: bool = True

    # J→C specific
    rrf_score: Optional[float] = None
    seniority_penalty: Optional[float] = None

    # C→J specific
    text_score: Optional[float] = None
    title_score: Optional[float] = None
    salary_adjustment: Optional[float] = None
    lang_penalty: Optional[float] = None
    lang_bonus: Optional[float] = None
    lang_breakdown: Optional[dict] = None


class CandidateRankResult(BaseModel):
    """Một kết quả xếp hạng ứng viên trong luồng J→C."""

    candidate_id: int
    candidate_name: str
    match_score: float
    score_breakdown: ScoreBreakdown


class JobRankResult(BaseModel):
    """Một kết quả gợi ý việc làm trong luồng C→J."""

    job_id: int
    job_title: str
    match_score: float
    score_breakdown: ScoreBreakdown


class RankingResponse(BaseModel):
    """Response wrapper chung cho cả 2 luồng ranking."""

    # J→C fields
    job_id: Optional[int] = None
    total_candidates: Optional[int] = None
    # C→J fields
    candidate_id: Optional[int] = None
    total_jobs: Optional[int] = None
    # Common
    returned: int
    results: list  # list[CandidateRankResult] | list[JobRankResult]


class MasterDataItem(BaseModel):
    """Item dùng cho các Master Data endpoints."""

    id: str | int
    name: str
    description: Optional[str] = None
    # Extra fields tùy loại data
    extra: Optional[dict] = None


# ============================================================
# Management Models (Phase 1.5)
# ============================================================


class JobStructuredUpdateRequest(BaseModel):
    """Request body cho cập nhật cài đặt Job (không cần re-ingest)."""

    provId: Optional[str] = None
    levelIds: list[int] = Field(default_factory=list)
    catIds: list[int] = Field(default_factory=list)
    skillIds: list[int] = Field(
        default_factory=list, description="IDs của skill từ catalog"
    )
    custom_skills: list[str] = Field(
        default_factory=list, description="Text tự do HR nhập thêm"
    )
    minSalary: Optional[int] = None
    maxSalary: Optional[int] = None
    workMode: Optional[str] = None


class JobContentUpdateRequest(BaseModel):
    """Request body cho cập nhật nội dung Job (cần re-ingest)."""

    title: str
    description: str


class CandidateCvUpdateRequest(BaseModel):
    """Request body cho cập nhật CV gốc của Candidate."""

    cvUrl: Optional[str] = None
    bio: Optional[str] = None


# ============================================================
# Job Detail Response (Mục 1.5 — Phase 1.5 luồng HR Job Mgmt)
# ============================================================


class JobDetailResponse(BaseModel):
    """Chi tiết công việc kèm structured NMAIex data."""

    job_id: int
    title: str
    description: str
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    work_loc: Optional[str] = None
    work_mode: Optional[str] = None
    prov_id: Optional[str] = None
    prov_name: Optional[str] = None
    company_id: int
    company_name: str
    created_at: str
    exp_at: str
    # NMAIex structured data
    level_ids: list[int] = Field(default_factory=list)
    level_names: list[str] = Field(default_factory=list)
    category_ids: list[int] = Field(default_factory=list)
    category_names: list[str] = Field(default_factory=list)
    skill_ids: list[int] = Field(default_factory=list)
    skill_names: list[str] = Field(default_factory=list)
    custom_skills: list[str] = Field(
        default_factory=list, description="HR text-free skills"
    )


# ============================================================
# Candidate Detail Response (Mục 1.5 — Update Candidate Profile)
# ============================================================


class CandidateDetailResponse(BaseModel):
    """Chi tiết ứng viên."""

    candidate_id: int
    user_id: int
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    prov_id: Optional[str] = None
    prov_name: Optional[str] = None
    bio: Optional[str] = None
    cv_url: Optional[str] = None
    dob: Optional[str] = None
    exp_years: Optional[int] = None
    # Candidate structured data
    skill_ids: list[int] = Field(default_factory=list)
    skill_names: list[str] = Field(default_factory=list)
    custom_skills: list[str] = Field(default_factory=list)

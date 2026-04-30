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

    rrf_score: float
    exact_overlap: float
    fuzzy_overlap: float
    skill_score: float
    skill_alpha: float
    seniority_penalty: float = 0.0
    salary_penalty: float = 0.0
    hard_filter_passed: bool = True


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

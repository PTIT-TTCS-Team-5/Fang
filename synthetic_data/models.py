"""synthetic_data/models.py — Pydantic models cho Synthetic Data Pipeline."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.cv_models import ParsedCV

# ============================================================
# CV Models
# ============================================================


class SyntheticCV(BaseModel):
    """Wrapper quanh ParsedCV + metadata pipeline."""

    persona_type: str  # "fresher_dreamer", "senior_overqualified"...
    generated_at: datetime
    batch_id: str
    cv_index: int  # Index trong manifest (0-499)
    noise_injected: bool = False
    parsed_cv: ParsedCV  # Reuse chính xác schema hiện tại


class CVBatchResponse(BaseModel):
    """Model để parse batch JSON response từ LLM khi sinh CV.

    LLM được instruct trả {"cvs": [...]}.
    Pipeline parse: CVBatchResponse.model_validate_json(response)
    rồi iterate từng ParsedCV.
    """

    cvs: list[ParsedCV]


# ============================================================
# Job Models
# ============================================================


class SyntheticJob(BaseModel):
    """Job Posting structured, tương thích DB schema."""

    title: str
    description: str  # Full JD text (200-800 từ)
    min_salary: int | None = None
    max_salary: int | None = None
    work_mode: Literal["ONSITE", "HYBRID", "REMOTE"] = "ONSITE"
    prov_id: str  # Từ 34 provinces (HANOI, TPHCM, DANANG...)
    comp_id: int  # compId từ COMPANY table
    level_ids: list[int] = Field(default_factory=list)  # FK → JOBLEVEL
    cat_ids: list[int] = Field(default_factory=list)  # FK → JOBCATEGORY
    skill_names: list[str] = Field(default_factory=list)  # Tên skill catalog (Tầng 1)
    custom_skills: list[str] = Field(default_factory=list)  # Free-text skills (Tầng 2)
    lang_requirements: list[dict] = Field(default_factory=list)
    # Format: [{"lang_code": "en", "req_type": "REQUIRED", "min_level": "INTERMEDIATE"}]


class JobBatchResponse(BaseModel):
    """Model để parse batch JSON response từ LLM khi sinh Job."""

    jobs: list[SyntheticJob]

# [NMAIex] Config loader — tái dùng pydantic_settings như FANG
from pydantic_settings import BaseSettings, SettingsConfigDict


class NMAIexSettings(BaseSettings):
    # Note: CLOUDINARY_UPLOAD_FOLDER được quản lý chung tại .env gốc
    # vì NMAIex là phần của AI layer hỗ trợ TTCS, không cần config riêng
    # Xem app/core/config.py để tham khảo cách FangSettings quản lý Cloudinary

    # ----------------------------------------------------------------
    # Weights J→C (HR tìm ứng viên — ưu tiên Precision/MRR)
    # ----------------------------------------------------------------
    nmaiex_jc_weight_rrf: float = 0.30
    nmaiex_jc_weight_skill: float = 0.40

    # ----------------------------------------------------------------
    # Weights C→J (Ứng viên tìm việc — ưu tiên Recall/nDCG@10)
    # ----------------------------------------------------------------
    nmaiex_cj_weight_rrf: float = 0.35
    nmaiex_cj_weight_title: float = 0.15  # title match (recent job titles vs job.title)
    nmaiex_cj_weight_skill: float = 0.30  # [Phase 2.5a] riêng CJ, thấp hơn JC (0.40)
    # Room 0.20 còn lại = salary_adjustment (âm=penalty, dương=bonus); clip(0,1) bảo vệ

    # ----------------------------------------------------------------
    # RRF
    # ----------------------------------------------------------------
    nmaiex_rrf_k: int = 60
    nmaiex_ranking_default_limit: int = 20
    nmaiex_ranking_max_limit: int = 100

    # ----------------------------------------------------------------
    # Strategy C: Tiered Skill Matching
    # ----------------------------------------------------------------
    nmaiex_skill_embedding_dims: int = (
        256  # 256 đủ cho text ngắn, rẻ hơn 4x so với 1024
    )
    nmaiex_skill_alpha: float = 0.8  # exact_overlap weight; (1-alpha) = fuzzy

    # ----------------------------------------------------------------
    # Seniority Penalty — Asymmetric Buffer-based (Phase 2.5b)
    # Tham chiếu: [NMAIex]_SENIORITY_PENALTY_PROPOSAL.md
    # ----------------------------------------------------------------
    nmaiex_jc_penalty_seniority_coef: float = 0.25  # base coef (thiếu kinh nghiệm)
    nmaiex_seniority_overqualified_penalty_ratio: float = 0.5  # ratio thừa = 0.5x thiếu
    # Buffer years per career path tier (job_max = job_max_raw + buffer)
    nmaiex_buffer_very_junior: int = 2  # job_max_raw ≤ 1 năm (Intern/Fresher)
    nmaiex_buffer_junior: int = 3  # job_max_raw 1-3 năm (Junior)
    nmaiex_buffer_middle: int = 4  # job_max_raw 3-5 năm (Middle)
    nmaiex_buffer_senior: int = 5  # job_max_raw 5-8 năm (Senior)
    nmaiex_buffer_lead_manager: int = 7  # job_max_raw > 8 năm (Lead/Manager)

    # ----------------------------------------------------------------
    # Salary Adjustment — C→J (Phase 2.5d)
    # Salary base theo địa điểm (VND/tháng), dùng fallback khi CV không có expected salary
    # ----------------------------------------------------------------
    nmaiex_salary_base_hanoi: int = 15_000_000
    nmaiex_salary_base_tphcm: int = 14_000_000
    nmaiex_salary_base_danang: int = 12_000_000
    nmaiex_salary_base_default: int = 13_000_000
    # Increment theo tier kinh nghiệm (VND/năm thêm)
    nmaiex_salary_increment_junior: int = 1_500_000  # 0-3 năm
    nmaiex_salary_increment_middle: int = 2_000_000  # 3-5 năm
    nmaiex_salary_increment_senior: int = 2_500_000  # 5-8 năm
    nmaiex_salary_increment_lead: int = 3_000_000  # >8 năm
    # Tolerance band: [expected*lower, expected*upper] → neutral zone
    nmaiex_salary_tolerance_lower: float = 0.8
    nmaiex_salary_tolerance_upper: float = 1.2
    nmaiex_salary_bonus_cap: float = 0.2  # Max bonus nếu lương cao hơn kỳ vọng

    # ----------------------------------------------------------------
    # Language Requirement Scoring — C→J (Phase 2.5g)
    # ----------------------------------------------------------------
    nmaiex_lang_required_penalty: float = 0.25  # Thiếu REQUIRED lang → -0.25
    nmaiex_lang_level_penalty: float = 0.10  # Có lang nhưng level không đủ → -0.10
    nmaiex_lang_preferred_bonus: float = 0.08  # Có PREFERRED lang đủ level → +0.08
    nmaiex_lang_bonus_cap: float = 0.15  # Tổng bonus ngôn ngữ tối đa

    # ----------------------------------------------------------------
    # Score Clipping Control
    # ----------------------------------------------------------------
    nmaiex_enable_score_clip: bool = True

    model_config = SettingsConfigDict(
        env_file=".env.nmaiex", env_file_encoding="utf-8", extra="ignore"
    )


nmaiex_settings = NMAIexSettings()

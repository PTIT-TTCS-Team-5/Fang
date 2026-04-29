# [NMAIex] Config loader — tái dùng pydantic_settings như FANG
from pydantic_settings import BaseSettings, SettingsConfigDict


class NMAIexSettings(BaseSettings):
    # Cloud Storage — Cloudinary dùng chung, chỉ tách folder
    # CLOUDINARY_CLOUD_NAME / API_KEY / API_SECRET đọc từ .env gốc qua FangSettings
    nmaiex_cloudinary_upload_folder: str = "nmaiex"

    # Weights J->C
    nmaiex_jc_weight_rrf: float = 0.30
    nmaiex_jc_weight_skill: float = 0.40
    nmaiex_jc_penalty_seniority_coef: float = 0.25

    # Weights C->J
    nmaiex_cj_weight_rrf: float = 0.35
    nmaiex_cj_weight_title: float = 0.15
    nmaiex_cj_penalty_salary_coef: float = 0.20

    # RRF
    nmaiex_rrf_k: int = 60
    nmaiex_ranking_default_limit: int = 20
    nmaiex_ranking_max_limit: int = 100

    model_config = SettingsConfigDict(
        env_file=".env.nmaiex", env_file_encoding="utf-8", extra="ignore"
    )


nmaiex_settings = NMAIexSettings()

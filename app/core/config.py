from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    embedding_dim: int = 1024
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = 32
    embedding_vector_type: str = "halfvec"
    log_level: str = "INFO"
    google_api_key: str | None = None
    openai_api_key: str | None = None
    claude_api_key: str | None = None
    parser_retry_enabled: bool = True
    parser_retry_attempts: int = 3
    parser_retry_base_seconds: float = 2.0
    parser_retry_max_seconds: float = 8.0
    parser_quality_min_rawtext_length: int = 120
    parser_quality_min_section_signals: int = 1

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    database_url: str

    # --- Embedding ---
    embedding_dim: int = 1024
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = 32
    embedding_vector_type: str = "halfvec"

    # --- Logging ---
    log_level: str = "INFO"

    # --- LLM Provider API Keys ---
    google_api_key: str | None = None
    openai_api_key: str | None = None
    claude_api_key: str | None = None

    # --- Parser retry policy ---
    parser_retry_enabled: bool = True
    parser_retry_attempts: int = 3
    parser_retry_base_seconds: float = 2.0
    parser_retry_max_seconds: float = 8.0
    parser_quality_min_rawtext_length: int = 120
    parser_quality_min_section_signals: int = 1

    # --- RAG Query (v2) ---
    rag_top_k_chunks: int = 3
    # Retry policy dùng chung cho cả generation (specific model mode)
    rag_generation_retry_enabled: bool = True
    rag_generation_retry_attempts: int = 3
    rag_generation_retry_base_seconds: float = 1.0
    rag_generation_retry_max_seconds: float = 6.0

    # --- Context Window Management (v2) ---
    # Budget (tokens) dành cho chat history, theo general model group
    context_budget_lite: int = 25_000  # Gemini Flash (smallest window)
    context_budget_pro: int = 960_000  # Gemini Pro / GPT-5.4 (1M window)
    context_budget_warning_threshold: float = 0.80  # Cảnh báo khi > 80%
    context_summarization_model: str = "gemini-flash"  # Model dùng để tóm tắt

    # --- CORS (v2) ---
    cors_allowed_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()

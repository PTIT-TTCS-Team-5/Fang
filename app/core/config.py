from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    database_url: str

    # --- Embedding ---
    embedding_dim: int = 1536  # gemini-embedding-001 native dim
    embedding_provider: str = "gemini"
    embedding_model: str = "gemini-embedding-001"
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
    parser_quality_min_self_confidence: float = 0.55

    # --- RAG Query (v2) ---
    rag_top_k_chunks: int = 3
    # Retry policy dùng chung cho cả generation (specific model mode)
    rag_generation_retry_enabled: bool = True
    rag_generation_retry_attempts: int = 3
    rag_generation_retry_base_seconds: float = 1.0
    rag_generation_retry_max_seconds: float = 6.0

    # --- Context Window Management (v2) ---
    # Budget (tokens) dành cho chat history, theo general model group
    context_budget_lite: int = 180_000  # Safe for Claude 4.5 Haiku (200k window)
    context_budget_pro: int = 960_000  # For Gemini Pro / GPT-5.5 (1M window)
    context_budget_warning_threshold: float = 0.80  # Cảnh báo khi > 80%
    # [CHAT_FULL_CV Phase 1.3] Hard limit: không gọi LLM khi vượt ngưỡng này,
    # trả deterministic response hướng dẫn HR summarize/branch/giảm prompt.
    context_budget_hard_limit: float = 0.95
    context_summarization_model: str = "gemini-flash"  # Model dùng để tóm tắt

    # --- JobPosting Agent (C3) ---
    jobposting_agent_enabled: bool = True
    jobposting_agent_model: str = "agent-lite"
    jobposting_agent_max_tool_steps: int = 8
    jobposting_agent_max_full_cv_loads: int = 3
    jobposting_agent_max_compare: int = 25
    jobposting_agent_default_top_n: int = 10
    jobposting_agent_hr_max_top_n: int = 25
    jobposting_agent_max_turn_seconds: int = 60
    jobposting_agent_temperature: float = 0.2
    jobposting_agent_max_output_tokens: int = 4096
    jobposting_agent_max_tool_result_chars: int = 120000

    # [CHAT_FULL_CV Phase 2] Giới hạn data đưa vào prompt cho từng source phụ.
    # Tránh prompt phình do offer/email lịch sử nhiều, và giảm bề mặt injection.
    chat_offer_history_limit: int = 3
    chat_email_history_limit: int = 5
    chat_email_body_char_limit: int = 300

    # --- CORS (v2) ---
    cors_allowed_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()

# ruff: noqa: E402
"""synthetic_data/config.py — Cấu hình cho Synthetic Data Pipeline."""

# ============================================================
# 9Router Configuration (cho LLM generation)
# ============================================================
NINE_ROUTER_URL = "http://localhost:20128/v1"
NINE_ROUTER_KEY = "sk-ad63867957b503e7-nrt4w0-b687b29d"

# Model tiering
MODEL_CV_GENERATION = "gemini/gemini-3-flash-preview"  # Batch CV sinh số lượng lớn (sử dụng model tốt hơn)
MODEL_JOB_GENERATION = "gemini/gemini-3.1-pro-preview"  # Job Description chất lượng cao
MODEL_QA_VALIDATE = "gemini/gemini-3.1-pro-preview"  # QA validate

# ============================================================
# Pipeline Parameters
# ============================================================
CV_BATCH_SIZE = 5  # Số CV mỗi LLM request (100 calls cho 500 CV)
JOB_BATCH_SIZE = 3  # Số Job mỗi LLM request

# Retry policy (exponential backoff)
MAX_RETRIES = 3
RETRY_BASE_SECONDS = 2.0
RETRY_MAX_SECONDS = 16.0

# ============================================================
# Output cache directory (gitignored)
# ============================================================
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
CV_OUTPUT_DIR = OUTPUT_DIR / "cvs"
JOB_OUTPUT_DIR = OUTPUT_DIR / "jobs"

# Auto-create output dirs
CV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
JOB_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# Timeout
# ============================================================
LLM_TIMEOUT_SECONDS = 60.0

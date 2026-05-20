"""List available Gemini models directly via Google GenAI SDK.

Usage:
    python scripts/list_gemini_models_direct.py

Loads GOOGLE_API_KEY from the environment/dotenv files and lists models with Display Name, Input Limit, and Output Limit.
"""

import os
import sys
from pathlib import Path

# Add project root to path so we can access app if needed, though we can load dotenv directly
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

try:
    import dotenv

    dotenv.load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass

try:
    import google.genai as genai
except ImportError:
    print("Error: The 'google-genai' package is not installed. Please run:")
    print("  pip install google-genai")
    sys.exit(1)


def format_limit(val):
    """Format token limits nicely with thousands separators."""
    if val is None or val == 0:
        return "N/A"
    return f"{val:,}"


def list_models_direct():
    """Fetch and display all available models via the direct Google GenAI SDK."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY environment variable not found.")
        print(
            "Please check your .env file or ensure GOOGLE_API_KEY is exported in your environment."
        )
        sys.exit(1)

    try:
        client = genai.Client(api_key=api_key)
        raw_models = list(client.models.list())
    except Exception as e:
        print(f"Error connecting to Gemini API: {e}")
        sys.exit(1)

    # Categorize
    gen_models = []
    embed_models = []
    other_models = []

    for m in raw_models:
        model_id = m.name.replace("models/", "")
        display_name = getattr(m, "display_name", "") or ""
        input_limit = getattr(m, "input_token_limit", None)
        output_limit = getattr(m, "output_token_limit", None)
        actions = getattr(m, "supported_actions", []) or []

        entry = {
            "id": model_id,
            "display_name": display_name,
            "input_limit": input_limit,
            "output_limit": output_limit,
            "actions": actions,
        }

        if "embed" in model_id.lower():
            embed_models.append(entry)
        elif (
            "gemini" in model_id.lower()
            or "gemma" in model_id.lower()
            or "generatecontent" in [a.lower() for a in actions]
        ):
            special_keywords = [
                "imagen",
                "veo",
                "lyria",
                "robotics",
                "computer-use",
                "antigravity",
                "deep-research",
            ]
            if any(kw in model_id.lower() for kw in special_keywords):
                other_models.append(entry)
            else:
                gen_models.append(entry)
        else:
            other_models.append(entry)

    # Print nicely formatted tables
    print("=" * 115)
    print(f"  MODELS DIRECTLY FROM GEMINI API (Total: {len(raw_models)})")
    print("=" * 115)

    headers_format = "  {:<42} | {:<32} | {:>14} | {:>14}"
    row_format = "  {:<42} | {:<32} | {:>14} | {:>14}"

    # 1. Generation Models
    print(f"\n{'-' * 115}")
    print(f"  [GEN] GENERATION MODELS ({len(gen_models)})")
    print(f"{'-' * 115}")
    print(
        headers_format.format("Model ID", "Display Name", "Input Limit", "Output Limit")
    )
    print(f"{'-' * 115}")
    for m in sorted(gen_models, key=lambda x: x["id"]):
        print(
            row_format.format(
                m["id"],
                m["display_name"][:32],
                format_limit(m["input_limit"]),
                format_limit(m["output_limit"]),
            )
        )

    # 2. Embedding Models
    print(f"\n{'-' * 115}")
    print(f"  [EMB] EMBEDDING MODELS ({len(embed_models)})")
    print(f"{'-' * 115}")
    print(
        headers_format.format("Model ID", "Display Name", "Input Limit", "Output Limit")
    )
    print(f"{'-' * 115}")
    for m in sorted(embed_models, key=lambda x: x["id"]):
        print(
            row_format.format(
                m["id"],
                m["display_name"][:32],
                format_limit(m["input_limit"]),
                format_limit(m["output_limit"]),
            )
        )

    # 3. Other/Specialist Models
    if other_models:
        print(f"\n{'-' * 115}")
        print(f"  [OTH] OTHER / SPECIALIST MODELS ({len(other_models)})")
        print(f"{'-' * 115}")
        print(
            headers_format.format(
                "Model ID", "Display Name", "Input Limit", "Output Limit"
            )
        )
        print(f"{'-' * 115}")
        for m in sorted(other_models, key=lambda x: x["id"]):
            print(
                row_format.format(
                    m["id"],
                    m["display_name"][:32],
                    format_limit(m["input_limit"]),
                    format_limit(m["output_limit"]),
                )
            )

    print(f"\n{'=' * 115}")


if __name__ == "__main__":
    list_models_direct()

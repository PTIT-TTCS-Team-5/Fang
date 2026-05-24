"""List available Gemini models via 9Router (OpenAI-compatible).

Usage:
    python scripts/list_gemini_models.py

Loads 9Router config from .env/environment.
"""

import os
import sys
from pathlib import Path

import httpx

ROOT_DIR = Path(__file__).resolve().parent.parent

try:
    import dotenv

    dotenv.load_dotenv(ROOT_DIR / ".env")
except ImportError:
    pass

DEFAULT_NINE_ROUTER_URL = "http://localhost:20128/v1"


def get_router_config() -> tuple[str, str]:
    """Return 9Router base URL and API key from environment."""
    url = (
        os.environ.get("NINE_ROUTER_URL")
        or os.environ.get("HUNG_9ROUTER_URL")
        or DEFAULT_NINE_ROUTER_URL
    ).strip()
    key = (
        os.environ.get("NINE_ROUTER_KEY")
        or os.environ.get("HUNG_9ROUTER_KEY")
        or os.environ.get("OPEN_ROUTER_KEY")
    )
    if not key:
        raise RuntimeError(
            "Missing 9Router key. Set NINE_ROUTER_KEY or HUNG_9ROUTER_KEY in .env."
        )
    return url.rstrip("/"), key.strip()


def list_models():
    """Fetch and display all available models via 9Router."""
    base_url, api_key = get_router_config()
    url = f"{base_url}/models"
    headers = {"Authorization": f"Bearer {api_key}"}

    resp = httpx.get(url, headers=headers, timeout=15.0)
    resp.raise_for_status()
    data = resp.json()

    models = data.get("data", data.get("models", []))

    # Categorize
    gen_models = []
    embed_models = []
    other_models = []

    for m in models:
        # OpenAI format uses "id", Google format uses "name"
        model_id = m.get("id", m.get("name", "")).replace("models/", "")
        owned_by = m.get("owned_by", "")

        entry = {
            "name": model_id,
            "owned_by": owned_by,
        }

        if "embed" in model_id.lower():
            embed_models.append(entry)
        elif any(
            kw in model_id.lower() for kw in ["gemini", "gpt", "claude", "flash", "pro"]
        ):
            gen_models.append(entry)
        else:
            other_models.append(entry)

    print("=" * 90)
    print(f"  MODELS VIA 9ROUTER (Total: {len(models)})")
    print("=" * 90)

    print(f"\n{'-' * 90}")
    print(f"  [GEN] GENERATION MODELS ({len(gen_models)})")
    print(f"{'-' * 90}")
    for m in gen_models:
        print(f"  {m['name']:<55} | {m['owned_by']}")

    print(f"\n{'-' * 90}")
    print(f"  [EMB] EMBEDDING MODELS ({len(embed_models)})")
    print(f"{'-' * 90}")
    for m in embed_models:
        print(f"  {m['name']:<55} | {m['owned_by']}")

    if other_models:
        print(f"\n{'-' * 90}")
        print(f"  [OTH] OTHER MODELS ({len(other_models)})")
        print(f"{'-' * 90}")
        for m in other_models:
            print(f"  {m['name']:<55} | {m['owned_by']}")

    print(f"\n{'=' * 90}")


if __name__ == "__main__":
    try:
        list_models()
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

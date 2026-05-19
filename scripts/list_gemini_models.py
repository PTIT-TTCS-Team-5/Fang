"""List available Gemini models via 9Router (OpenAI-compatible).

Usage:
    python scripts/list_gemini_models.py

Uses 9Router at localhost:20128 which has multiple Google API keys configured.
"""

import httpx

NINE_ROUTER_URL = "http://localhost:20128/v1"
NINE_ROUTER_KEY = "sk-ad63867957b503e7-nrt4w0-b687b29d"


def list_models():
    """Fetch and display all available models via 9Router."""
    url = f"{NINE_ROUTER_URL}/models"
    headers = {"Authorization": f"Bearer {NINE_ROUTER_KEY}"}

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
    list_models()

#!/usr/bin/env python3
"""
Fetch available models from OpenAI-compatible API endpoint
Supports any API provider using OpenAI SDK (orimise, local, etc.)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from openai import OpenAI


def fetch_models(api_key: str, base_url: str, output_file: str = None) -> dict:
    """
    Fetch available models from API and save to JSON file

    Args:
        api_key: API key for authentication
        base_url: Base URL of the API endpoint
        output_file: Optional output JSON file path. If None, prints to console

    Returns:
        Dictionary containing models data
    """
    print("=" * 70)
    print("FETCHING AVAILABLE MODELS")
    print("=" * 70)
    print(f"Base URL: {base_url}")
    print()

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)

        print("🔄 Querying API endpoint...")
        models_response = client.models.list()

        # Parse model data
        models_list = []
        model_ids = set()  # For deduplication

        for model in models_response.data:
            model_id = model.id
            if model_id not in model_ids:
                model_ids.add(model_id)
                models_list.append(
                    {
                        "id": model_id,
                        "created": model.created if hasattr(model, "created") else None,
                        "owned_by": (
                            model.owned_by if hasattr(model, "owned_by") else None
                        ),
                    }
                )

        models_list.sort(key=lambda x: x["id"])

        data = {
            "timestamp": datetime.now().isoformat(),
            "base_url": base_url,
            "total_models": len(models_list),
            "models": models_list,
        }

        print(f"✅ Successfully fetched {len(models_list)} unique models\n")

        # Display in console
        print("📋 Available Models:")
        print("-" * 70)
        for i, model in enumerate(models_list, 1):
            print(f"  {i:2d}. {model['id']}")

        # Save to file if specified
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print()
            print(f"💾 Saved to: {output_path}")

        print("=" * 70)
        return data

    except Exception as e:
        print(f"❌ Error fetching models: {e}", file=sys.stderr)
        print()
        print("💡 Tips:")
        print("  - Check your API key is correct")
        print("  - Verify the base URL is accessible")
        print("  - Ensure the API is currently running")
        return {}


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch and save available models from OpenAI-compatible API"
    )
    parser.add_argument(
        "--api-key",
        default="sk-cd825b23e3c530c07709d38e5fd9840c7aae70b7b023eb0a5639c477c6b76193",
        help="API key for authentication",
    )
    parser.add_argument(
        "--base-url",
        default="https://api.orimise.com/v1",
        help="Base URL of the API endpoint",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="models_available.json",
        help="Output JSON file path (default: models_available.json)",
    )

    args = parser.parse_args()

    fetch_models(args.api_key, args.base_url, args.output)


if __name__ == "__main__":
    main()

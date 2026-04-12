import asyncio
import json

from app.core.logging import logger
from app.services.cv_parser import get_last_parse_trace, parse_to_raw_and_json


async def run_test():
    pdf_path = "sample.pdf"

    try:
        with open(pdf_path, "rb") as file_obj:
            cv_bytes = file_obj.read()

        logger.info("Loaded sample PDF for parser test", extra={"pdfPath": pdf_path})
        logger.info("Starting parser pipeline test")
        raw_text, parsed_json = await parse_to_raw_and_json(cv_bytes)
        parser_trace = get_last_parse_trace() or {}

        print("\n" + "=" * 50)
        print("PARSE THANH CONG")
        print("=" * 50)
        print(f"parserVer: {parsed_json.get('parserVer')}")
        print(f"fallbackPath: {parser_trace.get('fallback_path')}")
        print("RAW TEXT (500 ky tu dau):")
        print(raw_text[:500] + "...\n")
        print("JSON OUTPUT:")
        print(json.dumps(parsed_json, indent=2, ensure_ascii=False))
        print("=" * 50)
    except FileNotFoundError:
        logger.error("sample.pdf was not found in the project root")
    except Exception:
        parser_trace = get_last_parse_trace() or {}
        if parser_trace.get("fallback_path"):
            print(f"fallbackPath: {parser_trace.get('fallback_path')}")
        logger.exception("Parser smoke test failed")


if __name__ == "__main__":
    asyncio.run(run_test())

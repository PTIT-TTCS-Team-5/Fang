import asyncio
import json

from app.core.logging import logger
from app.services.cv_parser import parse_to_raw_and_json


async def run_test():
    pdf_path = "sample.pdf"

    try:
        # Đọc file PDF lên thành bytes
        with open(pdf_path, "rb") as f:
            cv_bytes = f.read()

        logger.info(f"Đã đọc file {pdf_path}, kích thước: {len(cv_bytes)} bytes")

        # Bắn vào parser để test
        logger.info("Bắt đầu gọi Gemini API...")
        raw_text, parsed_json = await parse_to_raw_and_json(cv_bytes)

        # In kết quả ra xem
        print("\n" + "=" * 50)
        print("🎉 PARSE THÀNH CÔNG!")
        print("=" * 50)
        print("RAW TEXT (500 ký tự đầu):")
        print(raw_text[:500] + "...\n")

        print("JSON OUTPUT:")
        print(json.dumps(parsed_json, indent=2, ensure_ascii=False))
        print("=" * 50)

    except FileNotFoundError:
        logger.error(
            f"Không tìm thấy file {pdf_path}. Hãy để một file CV vào thư mục gốc nhé!"
        )
    except Exception:
        logger.exception("Có lỗi tày đình xảy ra trong quá trình test!")


if __name__ == "__main__":
    asyncio.run(run_test())

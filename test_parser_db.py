import asyncio
import json

from app.core.database import acquire_conn, db
from app.core.logging import logger
from app.services.cv_parser import parse_to_raw_and_json
from app.services.persistence import save_parsed_cv


async def setup_mock_data() -> int:
    """
    Tạo dữ liệu mẫu tối thiểu (Hardcode ID = 9999) để thỏa mãn
    các ràng buộc Foreign Key khi chèn vào bảng CVPARSED.
    """
    mock_id = 9999
    logger.info("Dang khoi tao Mock Data cho CSDL (Neu chua co)...")

    mock_queries = [
        # 1. Tạo User (Candidate)
        """INSERT INTO "user" (userId, userName, pwd, fName, lName, email, prov, ward, street, role)
           VALUES ($1, 'mock_candidate', 'mock_pwd', 'Candidate', 'Mock', 'mock@test.com', 'HN', 'CG', '123 Test', 'CANDIDATE')
           ON CONFLICT (userId) DO NOTHING;""",
        # 2. Tạo Candidate profile
        """INSERT INTO CANDIDATE (userId)
           VALUES ($1)
           ON CONFLICT (userId) DO NOTHING;""",
        # 3. Tạo Company
        """INSERT INTO COMPANY (compId, compName, prov, ward, street)
           VALUES ($1, 'Mock AI Company', 'HN', 'CG', '123 Test')
           ON CONFLICT (compId) DO NOTHING;""",
        # 4. Tạo Job Posting
        """INSERT INTO JOBPOSTING (jobPostId, title, description, expAt, compId)
           VALUES ($1, 'Mock AI Engineer', 'Mock Description', CURRENT_TIMESTAMP + INTERVAL '30 days', $1)
           ON CONFLICT (jobPostId) DO NOTHING;""",
        # 5. Tạo Job Application
        """INSERT INTO JOBAPPLICATION (jobAppId, candidateId, jobPostId, stat, cvSnapUrl)
           VALUES ($1, $1, $1, 'PENDING', 'http://mock-url.com/sample.pdf')
           ON CONFLICT (jobAppId) DO NOTHING;""",
    ]

    async with acquire_conn() as conn:
        for query in mock_queries:
            await conn.execute(query, mock_id)

    return mock_id


async def run_db_test():
    pdf_path = "sample.pdf"

    # 1. Khởi tạo Connection Pool tới DB
    await db.connect()

    try:
        # 2. Chuẩn bị Mock Data
        job_app_id = await setup_mock_data()

        # 3. Đọc và Parse PDF (Giống hệt file test cũ)
        with open(pdf_path, "rb") as f:
            cv_bytes = f.read()

        logger.info("Bat dau goi Gemini API de Parse CV...")
        raw_text, parsed_json = await parse_to_raw_and_json(cv_bytes)
        parser_ver = parsed_json.get("parserVer", "test_gemini")

        # 4. Lưu xuống Database!
        logger.info(f"Dang luu du lieu vao bang CVPARSED cho jobAppId={job_app_id}...")
        await save_parsed_cv(job_app_id, raw_text, parsed_json, parser_ver)

        # 5. Query ngược lại từ DB để Verify việc lưu JSONB
        logger.info("Kiem tra nguoc lai du lieu trong PostgreSQL...")
        async with acquire_conn() as conn:
            row = await conn.fetchrow(
                "SELECT parsedJson FROM CVPARSED WHERE jobAppId = $1", job_app_id
            )
            if row:
                # asyncpg trả về cột JSONB dạng chuỗi string, nên cần json.loads
                saved_json = json.loads(row["parsedjson"])
                print("\n" + "=" * 60)
                print("✅ LUU DATABASE THANH CONG!")
                print(
                    "📝 Du lieu JSONB doc nguoc tu PostgreSQL (Trich xuat field 'skills'):"
                )
                print(
                    json.dumps(
                        saved_json.get("skills", []), indent=2, ensure_ascii=False
                    )
                )
                print("=" * 60)
    except Exception:
        logger.exception("Co loi xay ra trong qua trinh Test DB!")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(run_db_test())

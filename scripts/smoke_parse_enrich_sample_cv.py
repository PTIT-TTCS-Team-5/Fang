"""Smoke-test the real parser + enrichment path on sample_2.pdf.

Default mode is non-destructive: it inserts a probe candidate inside a
transaction, runs enrichment, prints all important normalized fields, then
rolls back. Use --commit only if you intentionally want to keep the probe row.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.database import acquire_conn, db
from app.services.cv_parser import CVParserOrchestrator, get_last_parse_trace
from app.services.nmaiex_candidate_enrichment import enrich_candidate_structured_data


async def create_probe_candidate(conn) -> int:
    timestamp = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    user_id = await conn.fetchval(
        """
        INSERT INTO "user" (userName, pwd, fName, lName, email, phone, provId, ward, street, role)
        VALUES ($1, 'probe_hash', 'C3', 'Probe', $2, $3, 'HANOI', 'Probe Ward', 'Probe Street', 'CANDIDATE')
        RETURNING userId
        """,
        f"c3_probe_{timestamp}",
        f"c3_probe_{timestamp}@example.test",
        f"099{timestamp[-7:]}",
    )
    await conn.execute(
        """
        INSERT INTO CANDIDATE (userId, bio, cvUrl, dob, expyears)
        VALUES ($1, 'C3 parser/enrichment probe', $2, DATE '1995-01-01', 0)
        """,
        user_id,
        f"probe://sample_2/{timestamp}",
    )
    return user_id


async def load_probe_result(conn, candidate_id: int) -> dict:
    language_rows = await conn.fetch(
        """
        SELECT
            cl.candidateLangId,
            cl.userId,
            l.langCode,
            l.langName,
            cl.rawName,
            cl.proficiency,
            cl.rawProficiency,
            cl.certification,
            COALESCE(
                json_agg(
                    json_build_object(
                        'certCode', lc.certCode,
                        'certName', lc.certName,
                        'rawText', clc.rawText,
                        'normalizedScore', clc.normalizedScore
                    )
                    ORDER BY lc.certCode
                ) FILTER (WHERE lc.certId IS NOT NULL),
                '[]'::json
            ) AS certificates
        FROM CANDIDATELANGUAGE cl
        LEFT JOIN LANGUAGE l ON l.langId = cl.langId
        LEFT JOIN CANDIDATELANGUAGECERTIFICATE clc ON clc.candidateLangId = cl.candidateLangId
        LEFT JOIN LANGUAGECERTIFICATE lc ON lc.certId = clc.certId
        WHERE cl.userId = $1
        GROUP BY cl.candidateLangId, l.langCode, l.langName
        ORDER BY cl.candidateLangId
        """,
        candidate_id,
    )
    row = await conn.fetchrow(
        """
        SELECT c.expyears, u.provId, count(DISTINCT cs.skillId) AS skill_count
        FROM CANDIDATE c
        JOIN "user" u ON u.userId = c.userId
        LEFT JOIN CANDIDATESKILL cs ON cs.userId = c.userId
        WHERE c.userId = $1
        GROUP BY c.expyears, u.provId
        """,
        candidate_id,
    )
    raw_skill_count = await conn.fetchval(
        "SELECT count(*) FROM CANDIDATE_SKILL_RAW WHERE candId = $1",
        candidate_id,
    )
    return {
        "candidateId": candidate_id,
        "expyears": row["expyears"] if row else None,
        "provId": row["provid"] if row else None,
        "candidateSkillCount": row["skill_count"] if row else 0,
        "candidateRawSkillCount": raw_skill_count,
        "languages": [dict(item) for item in language_rows],
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default="sample_2.pdf")
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    if not settings.google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not configured; parser/embedding cannot run"
        )

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    parser_service = CVParserOrchestrator()
    parsed_raw_text, parsed_payload = await parser_service.parse(pdf_path.read_bytes())
    parse_trace = get_last_parse_trace()

    await db.connect()
    try:
        async with acquire_conn() as conn:
            tx = conn.transaction()
            await tx.start()
            try:
                candidate_id = await create_probe_candidate(conn)
                await enrich_candidate_structured_data(
                    candidate_id=candidate_id,
                    parsed_payload=parsed_payload,
                    conn=conn,
                )
                probe_result = await load_probe_result(conn, candidate_id)
                if args.commit:
                    await tx.commit()
                else:
                    await tx.rollback()
            except Exception:
                await tx.rollback()
                raise
    finally:
        await db.disconnect()

    output = {
        "committed": args.commit,
        "parser": {
            "trace": parse_trace,
            "candidateInfo": parsed_payload.get("candidateInfo"),
            "languages": parsed_payload.get("languages"),
            "certificates": parsed_payload.get("certificates"),
            "expectedSalaryMin": parsed_payload.get("expectedSalaryMin"),
            "expectedSalaryMax": parsed_payload.get("expectedSalaryMax"),
            "rawTextLength": len(parsed_raw_text or ""),
        },
        "enrichmentProbe": probe_result,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

"""Apply C3 language certificate catalog schema to the local database.

Idempotent operational helper:
- creates LANGUAGECERTIFICATE
- creates CANDIDATELANGUAGECERTIFICATE
- seeds common language certificate codes
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import acquire_conn, db
from app.core.logging import logger

DDL = """
CREATE TABLE IF NOT EXISTS LANGUAGECERTIFICATE (
    certId      SERIAL PRIMARY KEY,
    certCode    VARCHAR(30) NOT NULL UNIQUE,
    certName    VARCHAR(120) NOT NULL,
    langId      INT REFERENCES LANGUAGE(langId),
    description TEXT
);

CREATE TABLE IF NOT EXISTS CANDIDATELANGUAGECERTIFICATE (
    candidateLanguageCertId SERIAL PRIMARY KEY,
    candidateLangId INT NOT NULL,
    certId          INT NOT NULL,
    rawText         VARCHAR(200),
    normalizedScore VARCHAR(50),
    createdAt       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (candidateLangId) REFERENCES CANDIDATELANGUAGE(candidateLangId) ON DELETE CASCADE,
    FOREIGN KEY (certId) REFERENCES LANGUAGECERTIFICATE(certId)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_candidate_language_certificate
    ON CANDIDATELANGUAGECERTIFICATE (candidateLangId, certId, COALESCE(rawText, ''));

CREATE INDEX IF NOT EXISTS idx_candidate_language_cert_lang
    ON CANDIDATELANGUAGECERTIFICATE (candidateLangId);

CREATE INDEX IF NOT EXISTS idx_candidate_language_cert_cert
    ON CANDIDATELANGUAGECERTIFICATE (certId);
"""


SEED_SQL = """
WITH certs(certCode, certName, langCode, description) AS (
    VALUES
    ('IELTS', 'International English Language Testing System', 'en', 'Chứng chỉ tiếng Anh học thuật quốc tế'),
    ('TOEIC', 'Test of English for International Communication', 'en', 'Chứng chỉ tiếng Anh giao tiếp quốc tế'),
    ('TOEFL', 'Test of English as a Foreign Language', 'en', 'Chứng chỉ tiếng Anh quốc tế'),
    ('CAMBRIDGE', 'Cambridge English Qualifications', 'en', 'Nhóm chứng chỉ Cambridge English'),
    ('JLPT', 'Japanese-Language Proficiency Test', 'ja', 'Chứng chỉ năng lực tiếng Nhật'),
    ('HSK', 'Hanyu Shuiping Kaoshi', 'zh', 'Chứng chỉ năng lực tiếng Trung'),
    ('TOPIK', 'Test of Proficiency in Korean', 'ko', 'Chứng chỉ năng lực tiếng Hàn'),
    ('DELF', 'Diplôme d''études en langue française', 'fr', 'Chứng chỉ tiếng Pháp DELF'),
    ('DALF', 'Diplôme approfondi de langue française', 'fr', 'Chứng chỉ tiếng Pháp DALF'),
    ('GOETHE', 'Goethe-Zertifikat', 'de', 'Chứng chỉ tiếng Đức Goethe'),
    ('TESTDAF', 'Test Deutsch als Fremdsprache', 'de', 'Chứng chỉ tiếng Đức TestDaF')
)
INSERT INTO LANGUAGECERTIFICATE (certCode, certName, langId, description)
SELECT c.certCode, c.certName, l.langId, c.description
FROM certs c
LEFT JOIN LANGUAGE l ON l.langCode = c.langCode
ON CONFLICT (certCode) DO UPDATE
SET certName = EXCLUDED.certName,
    langId = EXCLUDED.langId,
    description = EXCLUDED.description;
"""


async def main() -> None:
    await db.connect()
    try:
        async with acquire_conn() as conn:
            await conn.execute(DDL)
            await conn.execute(SEED_SQL)
            cert_count = await conn.fetchval("SELECT count(*) FROM LANGUAGECERTIFICATE")
            logger.info(
                "[C3] Language certificate schema ready",
                extra={"certificateCount": cert_count},
            )
            print(f"LANGUAGECERTIFICATE rows: {cert_count}")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

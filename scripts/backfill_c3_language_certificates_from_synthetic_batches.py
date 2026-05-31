"""Backfill candidate languages/certificates from synthetic_data/output/cvs.

This is the cheap synthetic-data path. It processes 100 cached CV batch JSON
files instead of 2,001 CVPARSED rows, maps each CV back to its unique candidate
via CANDIDATE.cvUrl, and writes:

- CANDIDATELANGUAGE
- CANDIDATELANGUAGECERTIFICATE

The script can use one 9Router LLM call per synthetic batch, but also has a
deterministic mapper for common language/certificate strings.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import acquire_conn, db
from app.core.logging import logger

CV_DIR = Path("synthetic_data/output/cvs")
NINE_ROUTER_URL = os.environ.get("NINE_ROUTER_URL", "http://localhost:20128/v1")
NINE_ROUTER_KEY = os.environ.get(
    "NINE_ROUTER_KEY", "sk-ad63867957b503e7-nrt4w0-b687b29d"
)
MODEL_BACKFILL = os.environ.get("C3_BACKFILL_MODEL", "gemini/gemini-3.1-flash-lite")

LANGUAGE_ALIASES = {
    "english": "en",
    "tiếng anh": "en",
    "tieng anh": "en",
    "japanese": "ja",
    "tiếng nhật": "ja",
    "tieng nhat": "ja",
    "chinese": "zh",
    "mandarin": "zh",
    "tiếng trung": "zh",
    "tieng trung": "zh",
    "korean": "ko",
    "tiếng hàn": "ko",
    "tieng han": "ko",
    "vietnamese": "vi",
    "tiếng việt": "vi",
    "tieng viet": "vi",
    "french": "fr",
    "tiếng pháp": "fr",
    "german": "de",
    "tiếng đức": "de",
}

CERT_PATTERNS: dict[str, re.Pattern[str]] = {
    "IELTS": re.compile(r"\bIELTS\b(?:\s*[:\-]?\s*([0-9](?:\.[05])?))?", re.I),
    "TOEIC": re.compile(r"\bTOEIC\b(?:\s*[:\-]?\s*(\d{3,4}))?", re.I),
    "TOEFL": re.compile(r"\bTOEFL\b(?:\s*[:\-]?\s*(\d{2,3}))?", re.I),
    "CAMBRIDGE": re.compile(
        r"\b(CAMBRIDGE|KET|PET|FCE|CAE|CPE)\b(?:\s*[:\-]?\s*([A-C][12]?))?", re.I
    ),
    "JLPT": re.compile(r"\bJLPT\b\s*[:\-]?\s*(N[1-5])\b|\b(N[1-5])\b", re.I),
    "HSK": re.compile(r"\bHSK\b(?:\s*[:\-]?\s*([1-6]))?", re.I),
    "TOPIK": re.compile(r"\bTOPIK\b(?:\s*[:\-]?\s*([1-6]))?", re.I),
    "DELF": re.compile(r"\bDELF\b(?:\s*[:\-]?\s*([A-C][12]?))?", re.I),
    "DALF": re.compile(r"\bDALF\b(?:\s*[:\-]?\s*([A-C][12]?))?", re.I),
    "GOETHE": re.compile(
        r"\bGOETHE\b(?:[-\s]?ZERTIFIKAT)?(?:\s*[:\-]?\s*([A-C][12]?))?", re.I
    ),
    "TESTDAF": re.compile(r"\bTESTDAF\b(?:\s*[:\-]?\s*(TDN\s*[3-5]))?", re.I),
}


def clean_json_response(raw: str) -> str:
    raw = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    return match.group(1).strip() if match else raw


async def call_9router_json(
    *,
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 6,
) -> dict[str, Any]:
    payload = {
        "model": MODEL_BACKFILL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {NINE_ROUTER_KEY}",
        "Content-Type": "application/json",
    }
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    f"{NINE_ROUTER_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                )
            if resp.status_code == 429 or resp.status_code >= 500:
                delay = min(90.0, 2.0 * (2**attempt)) + random.uniform(0.1, 1.0)
                logger.warning(
                    "[BatchBackfill] 9Router HTTP %s, retrying in %.1fs",
                    resp.status_code,
                    delay,
                )
                await asyncio.sleep(delay)
                continue
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(clean_json_response(content))
        except (httpx.RequestError, json.JSONDecodeError, KeyError) as exc:
            delay = min(90.0, 2.0 * (2**attempt)) + random.uniform(0.1, 1.0)
            logger.warning(
                "[BatchBackfill] 9Router/JSON failure: %s. Retrying in %.1fs",
                exc,
                delay,
            )
            await asyncio.sleep(delay)
    raise RuntimeError("9Router batch mapping failed after retries")


async def test_9router_connection() -> None:
    result = await call_9router_json(
        system_prompt="Return only JSON.",
        user_prompt='Return {"ok": true}.',
        max_retries=2,
    )
    if result.get("ok") is not True:
        raise RuntimeError(f"Unexpected 9Router probe response: {result}")


def normalize_proficiency_offline(raw: str | None) -> str:
    text = (raw or "").strip().lower()
    if not text:
        return "BASIC"
    if any(token in text for token in ("native", "bản ngữ", "mother tongue")):
        return "NATIVE"
    if any(token in text for token in ("fluent", "thành thạo", "c2", "n1")):
        return "FLUENT"
    if re.search(r"ielts\s*(8(?:\.0)?|8\.5|9(?:\.0)?)", text):
        return "FLUENT"
    if any(token in text for token in ("advanced", "c1", "n2", "business")):
        return "ADVANCED"
    if re.search(r"ielts\s*([6-7](?:\.[05])?)", text):
        return "ADVANCED"
    if re.search(r"toeic\s*([7-9]\d{2})", text):
        return "ADVANCED"
    if any(
        token in text
        for token in ("intermediate", "giao tiếp", "khá", "b1", "b2", "n3")
    ):
        return "INTERMEDIATE"
    if any(token in text for token in ("basic", "cơ bản", "a1", "a2", "n4", "n5")):
        return "BASIC"
    return "BASIC"


def extract_certificates(raw_texts: list[str]) -> list[dict[str, str | None]]:
    results: list[dict[str, str | None]] = []
    seen: set[tuple[str, str]] = set()
    for raw in raw_texts:
        text = str(raw or "").strip()
        if not text:
            continue
        for cert_code, pattern in CERT_PATTERNS.items():
            for match in pattern.finditer(text):
                groups = [g for g in match.groups() if g]
                score = groups[-1].upper().replace(" ", "") if groups else None
                key = (cert_code, text.lower())
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    {"certCode": cert_code, "rawText": text, "normalizedScore": score}
                )
    return results


def map_language_code(raw_language: str | None) -> str | None:
    if not raw_language:
        return None
    text = raw_language.strip().lower()
    return LANGUAGE_ALIASES.get(text, text if len(text) <= 3 else None)


def deterministic_map_batch(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mapped: list[dict[str, Any]] = []
    for item in items:
        languages = []
        top_level_certs = item.get("certificates") or []
        for lang in item.get("languages") or []:
            raw_name = lang.get("language")
            raw_prof = lang.get("proficiency")
            raw_cert = lang.get("certification")
            cert_sources = [
                value for value in (raw_prof, raw_cert, *top_level_certs) if value
            ]
            languages.append(
                {
                    "rawName": raw_name,
                    "langCode": map_language_code(raw_name),
                    "proficiency": normalize_proficiency_offline(raw_prof),
                    "rawProficiency": raw_prof,
                    "certificationText": "; ".join(
                        cert["rawText"] for cert in extract_certificates(cert_sources)
                    )
                    or raw_cert,
                    "certificates": extract_certificates(cert_sources),
                }
            )
        mapped.append({"candidateId": item["candidateId"], "languages": languages})
    return mapped


async def llm_map_batch(
    items: list[dict[str, Any]],
    language_catalog: list[dict[str, Any]],
    certificate_catalog: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    system_prompt = (
        "You normalize CV language data for a recruitment database. "
        "Return strict JSON only. Do not invent languages or certificates."
    )
    user_prompt = json.dumps(
        {
            "instruction": (
                "For each item, map languages to langCode from languageCatalog, "
                "normalize proficiency to BASIC|INTERMEDIATE|ADVANCED|FLUENT|NATIVE, "
                "and extract language certificates from proficiency/certification/top-level certificates. "
                "Use certCode only from certificateCatalog. Include multiple certificates if present. "
                'Return {"items":[{"candidateId":int,"languages":[{"rawName":str,'
                '"langCode":str|null,"proficiency":str,"rawProficiency":str|null,'
                '"certificationText":str|null,"certificates":[{"certCode":str,'
                '"rawText":str,"normalizedScore":str|null}]}]}]}.'
            ),
            "languageCatalog": language_catalog,
            "certificateCatalog": certificate_catalog,
            "items": items,
        },
        ensure_ascii=False,
    )
    result = await call_9router_json(
        system_prompt=system_prompt, user_prompt=user_prompt
    )
    mapped = result.get("items")
    if not isinstance(mapped, list):
        raise ValueError(f"Invalid LLM batch mapping response: {result}")
    return mapped


def batch_number(batch_id: str) -> int:
    return int(batch_id.split("_", 1)[1])


async def load_catalogs(conn: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    language_rows = await conn.fetch(
        "SELECT langId, langCode, langName FROM LANGUAGE ORDER BY langId"
    )
    cert_rows = await conn.fetch("""
        SELECT lc.certId, lc.certCode, lc.certName, l.langCode
        FROM LANGUAGECERTIFICATE lc
        LEFT JOIN LANGUAGE l ON l.langId = lc.langId
        ORDER BY lc.certId
        """)
    languages = [dict(row) for row in language_rows]
    certs = [dict(row) for row in cert_rows]
    return languages, certs


async def map_candidate_ids(
    conn: Any, batch_id: str, cvs: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    start_index = (batch_number(batch_id) - 1) * len(cvs)
    items: list[dict[str, Any]] = []
    for idx, cv in enumerate(cvs):
        cv_index = start_index + idx
        cv_url = f"synth://pipeline/{batch_id}/{cv_index}"
        candidate_id = await conn.fetchval(
            "SELECT userId FROM CANDIDATE WHERE cvUrl = $1",
            cv_url,
        )
        if candidate_id is None:
            logger.warning("[BatchBackfill] Candidate not found for cvUrl=%s", cv_url)
            continue
        items.append(
            {
                "candidateId": candidate_id,
                "languages": cv.get("languages") or [],
                "certificates": cv.get("certificates") or [],
            }
        )
    return items


async def write_mapped_items(
    conn: Any,
    mapped_items: list[dict[str, Any]],
    *,
    language_id_by_code: dict[str, int],
    cert_id_by_code: dict[str, int],
) -> dict[str, int]:
    stats = {"candidates": 0, "language_rows": 0, "certificate_links": 0}
    for item in mapped_items:
        candidate_id = int(item["candidateId"])
        await conn.execute(
            "DELETE FROM CANDIDATELANGUAGE WHERE userId = $1", candidate_id
        )
        stats["candidates"] += 1
        for lang in item.get("languages") or []:
            raw_name = lang.get("rawName")
            lang_code = (lang.get("langCode") or "").strip().lower() or None
            lang_id = language_id_by_code.get(lang_code) if lang_code else None
            proficiency = lang.get("proficiency") or "BASIC"
            raw_prof = lang.get("rawProficiency")
            certification_text = lang.get("certificationText")
            candidate_lang_id = await conn.fetchval(
                """
                INSERT INTO CANDIDATELANGUAGE
                    (userId, langId, rawName, proficiency, rawProficiency, certification)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT DO NOTHING
                RETURNING candidateLangId
                """,
                candidate_id,
                lang_id,
                raw_name,
                proficiency,
                raw_prof,
                certification_text,
            )
            if candidate_lang_id is None:
                candidate_lang_id = await conn.fetchval(
                    """
                    SELECT candidateLangId
                    FROM CANDIDATELANGUAGE
                    WHERE userId = $1
                      AND (
                            (langId IS NOT NULL AND langId = $2)
                         OR (langId IS NULL AND $2 IS NULL AND LOWER(rawName) = LOWER($3))
                      )
                    ORDER BY candidateLangId DESC
                    LIMIT 1
                    """,
                    candidate_id,
                    lang_id,
                    raw_name,
                )
            if candidate_lang_id is None:
                continue
            stats["language_rows"] += 1
            for cert in lang.get("certificates") or []:
                cert_code = (cert.get("certCode") or "").strip().upper()
                cert_id = cert_id_by_code.get(cert_code)
                if not cert_id:
                    continue
                await conn.execute(
                    """
                    INSERT INTO CANDIDATELANGUAGECERTIFICATE
                        (candidateLangId, certId, rawText, normalizedScore)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT DO NOTHING
                    """,
                    candidate_lang_id,
                    cert_id,
                    (cert.get("rawText") or "")[:200],
                    cert.get("normalizedScore"),
                )
                stats["certificate_links"] += 1
    return stats


def execute_database_backup(db_url: str) -> str:
    Path("backups").mkdir(exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"backups/micareer_lite_db_before_c3_language_cert_{timestamp}.dump"
    result = subprocess.run(
        ["pg_dump", "--format=custom", "--file", backup_path, db_url],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "pg_dump failed")
    return backup_path


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="Commit DB writes")
    parser.add_argument("--dry-run", action="store_true", help="Rollback DB writes")
    parser.add_argument("--mapper", choices=["llm", "deterministic"], default="llm")
    parser.add_argument(
        "--no-deterministic-fallback",
        action="store_true",
        help="Fail instead of falling back when 9Router batch mapping is rate-limited.",
    )
    parser.add_argument("--limit-batches", type=int, default=None)
    parser.add_argument(
        "--batch", type=str, default=None, help="Specific batch id, e.g. batch_001"
    )
    parser.add_argument("--skip-connection-test", action="store_true")
    parser.add_argument(
        "--summary-path", default="scripts/backfill_language_cert_summary.json"
    )
    args = parser.parse_args()

    is_dry_run = args.dry_run or not args.yes
    if args.mapper == "llm" and not args.skip_connection_test:
        await test_9router_connection()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is required")

    backup_path = None
    if not is_dry_run:
        backup_path = execute_database_backup(db_url)

    batch_files = sorted(CV_DIR.glob("batch_*.json"))
    if args.batch:
        batch_files = [CV_DIR / f"{args.batch}.json"]
    if args.limit_batches is not None:
        batch_files = batch_files[: args.limit_batches]

    summary: dict[str, Any] = {
        "mapper": args.mapper,
        "dry_run": is_dry_run,
        "backup_path": backup_path,
        "batches_seen": 0,
        "candidates_seen": 0,
        "candidates_written": 0,
        "language_rows_written": 0,
        "certificate_links_written": 0,
        "failures": [],
    }

    await db.connect()
    try:
        async with acquire_conn() as conn:
            languages, certs = await load_catalogs(conn)
            language_id_by_code = {
                row["langcode"].lower(): row["langid"] for row in languages
            }
            cert_id_by_code = {row["certcode"].upper(): row["certid"] for row in certs}

            for batch_file in batch_files:
                batch_id = batch_file.stem
                cvs = json.loads(batch_file.read_text(encoding="utf-8"))
                items = await map_candidate_ids(conn, batch_id, cvs)
                summary["batches_seen"] += 1
                summary["candidates_seen"] += len(items)
                if args.mapper == "llm":
                    try:
                        mapped_items = await llm_map_batch(items, languages, certs)
                    except Exception as exc:
                        if args.no_deterministic_fallback:
                            raise
                        logger.warning(
                            "[BatchBackfill] LLM mapping failed for %s; using deterministic fallback: %s",
                            batch_id,
                            exc,
                        )
                        summary["failures"].append(
                            {
                                "batch": batch_id,
                                "stage": "llm_mapping",
                                "fallback": "deterministic",
                                "error": str(exc),
                            }
                        )
                        mapped_items = deterministic_map_batch(items)
                else:
                    mapped_items = deterministic_map_batch(items)

                tx = conn.transaction()
                await tx.start()
                try:
                    stats = await write_mapped_items(
                        conn,
                        mapped_items,
                        language_id_by_code=language_id_by_code,
                        cert_id_by_code=cert_id_by_code,
                    )
                    summary["candidates_written"] += stats["candidates"]
                    summary["language_rows_written"] += stats["language_rows"]
                    summary["certificate_links_written"] += stats["certificate_links"]
                    logger.info(
                        "[BatchBackfill] %s done: candidates=%s languages=%s certLinks=%s",
                        batch_id,
                        stats["candidates"],
                        stats["language_rows"],
                        stats["certificate_links"],
                    )

                    if is_dry_run:
                        await tx.rollback()
                    else:
                        await tx.commit()
                except Exception:
                    await tx.rollback()
                    raise
    finally:
        await db.disconnect()

    Path(args.summary_path).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

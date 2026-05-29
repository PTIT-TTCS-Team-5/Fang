import argparse
import asyncio
import datetime
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ---------------------------------------------------------------------------
# 9Router Mocking and Interception Setup (High-Speed OpenAI gpt-5-nano)
# ---------------------------------------------------------------------------
import httpx

import app.services.nmaiex_mapper_service
import app.services.rag_orchestrator
from app.core.database import acquire_conn, db
from app.core.logging import logger
from app.services.nmaiex_candidate_enrichment import (
    _coerce_enrichment_payload,
    _normalize_and_persist_languages,
    _normalize_and_update_province,
)
from app.services.rag_orchestrator import GenerationTrace, _GenerationAttempt

NINE_ROUTER_URL = os.environ.get("NINE_ROUTER_URL", "http://localhost:20128/v1")
NINE_ROUTER_KEY = os.environ.get(
    "NINE_ROUTER_KEY", "sk-ad63867957b503e7-nrt4w0-b687b29d"
)
MODEL_BACKFILL = "openai/gpt-5-nano"


async def mock_invoke_generation(
    messages: list[dict[str, str]], model_mode: str
) -> GenerationTrace:
    """Redirect LLM calls to 9Router-compatible local endpoint using gpt-5-nano."""
    payload = {
        "model": MODEL_BACKFILL,
        "messages": messages,
        "temperature": 0.3,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {NINE_ROUTER_KEY}",
        "Content-Type": "application/json",
    }

    start_time = datetime.datetime.now()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{NINE_ROUTER_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]

    latency_ms = int((datetime.datetime.now() - start_time).total_seconds() * 1000)

    return GenerationTrace(
        response=content,
        model=MODEL_BACKFILL,
        model_mode=model_mode,
        fallback_path="9router-backfill-intercept",
        latency_ms=latency_ms,
        attempts=[
            _GenerationAttempt(
                tier=1, provider="9router", model=MODEL_BACKFILL, status="succeeded"
            )
        ],
    )


# Apply monkeypatch to ensure both adapters use 9Router during run
app.services.rag_orchestrator.invoke_generation = mock_invoke_generation
app.services.nmaiex_mapper_service.invoke_generation = mock_invoke_generation


# ---------------------------------------------------------------------------
# DDL Verification
# ---------------------------------------------------------------------------
async def verify_ddl_and_tables(conn: Any) -> None:
    """Verify that the CANDIDATELANGUAGE table exists, raising an error if missing."""
    table_exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_name = 'candidatelanguage'
        )
        """)
    if not table_exists:
        logger.error(
            "[Backfill] CANDIDATELANGUAGE table is missing. Running the DDL auto-initializer..."
        )
        ddl = """
        CREATE TABLE IF NOT EXISTS CANDIDATELANGUAGE (
            candidateLangId SERIAL PRIMARY KEY,
            userId          INT NOT NULL,
            langId          INT,
            rawName         VARCHAR(100),
            proficiency     VARCHAR(20) CHECK (proficiency IN ('BASIC','INTERMEDIATE','ADVANCED','FLUENT','NATIVE')),
            rawProficiency  VARCHAR(100),
            certification   VARCHAR(200),
            createdAt       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updatedAt       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            FOREIGN KEY (userId) REFERENCES CANDIDATE(userId) ON DELETE CASCADE,
            FOREIGN KEY (langId) REFERENCES LANGUAGE(langId)
        );
        CREATE INDEX IF NOT EXISTS idx_candidate_language_user ON CANDIDATELANGUAGE (userId);
        CREATE INDEX IF NOT EXISTS idx_candidate_language_lang_level ON CANDIDATELANGUAGE (langId, proficiency);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_candidate_language_known ON CANDIDATELANGUAGE (userId, langId) WHERE langId IS NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS uq_candidate_language_unknown ON CANDIDATELANGUAGE (userId, lower(rawName)) WHERE langId IS NULL AND rawName IS NOT NULL;
        """
        await conn.execute(ddl)
        logger.info("[Backfill] CANDIDATELANGUAGE table created successfully.")


# ---------------------------------------------------------------------------
# Backup Executor (pg_dump)
# ---------------------------------------------------------------------------
def execute_database_backup(db_url: str) -> str:
    """Run pg_dump via subprocess to create a backup of the DB."""
    os.makedirs("backups", exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/micareer_lite_db_before_c3_reenrich_{ts}.dump"

    logger.info(f"[Backfill] Attempting database backup to {backup_file}...")
    cmd = ["pg_dump", "--format=custom", "--file", backup_file, db_url]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if result.returncode != 0:
            err_msg = result.stderr or result.stdout
            logger.error(f"[Backfill] pg_dump failed: {err_msg}")
            raise RuntimeError(f"Database backup failed: {err_msg}")
        logger.info(f"[Backfill] Database backup completed successfully: {backup_file}")
        return backup_file
    except FileNotFoundError:
        logger.error("[Backfill] pg_dump utility not found in PATH.")
        raise RuntimeError("pg_dump utility is not available in PATH. Backup failed.")
    except Exception as e:
        logger.error(f"[Backfill] Error executing backup: {e}")
        raise


# ---------------------------------------------------------------------------
# Main Controller Loop (Sequential / Deadlock-Safe)
# ---------------------------------------------------------------------------
async def run_backfill() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill C3 candidate language and province normalization from existing CVPARSED data safely."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Simulate changes and rollback transactions.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        default=False,
        help="Run in write mode (commits changes).",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of candidates to process."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="Batch size / output report status interval.",
    )
    parser.add_argument("--offset", type=int, default=0, help="Skip first N records.")
    parser.add_argument(
        "--candidate-id",
        type=int,
        default=None,
        help="Run backfill only for a specific candidate user ID.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=False,
        help="Skip candidates that already have rows in CANDIDATELANGUAGE.",
    )
    args = parser.parse_args()

    is_dry_run = args.dry_run or (not args.yes)
    if is_dry_run:
        logger.info(
            "[Backfill] RUNNING IN DRY-RUN (SIMULATION) MODE. No DB mutations will be committed."
        )
    else:
        logger.info(
            f"[Backfill] RUNNING IN WRITE MODE via {MODEL_BACKFILL} (DEADLOCK-SAFE). Changes will be committed."
        )

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        logger.error(
            "DATABASE_URL environment variable is not set. Cannot run backfill."
        )
        sys.exit(1)

    # Perform backup first
    backup_path = None
    if not is_dry_run:
        try:
            backup_path = execute_database_backup(db_url)
        except Exception as e:
            logger.critical(
                f"[Backfill] Safety backup failed. Aborting write operation! Error: {e}"
            )
            sys.exit(1)

    logger.info("Connecting to database...")
    await db.connect()

    summary = {
        "total_scanned": 0,
        "total_updated": 0,
        "total_skipped": 0,
        "language_rows_inserted": 0,
        "province_updates": 0,
        "failures": [],
    }

    try:
        async with acquire_conn() as conn:
            # Step 1: DDL Verification
            await verify_ddl_and_tables(conn)

            # Step 2: Query candidates with CVPARSED data
            query_parts = ["""
                SELECT cv.cvParsedId, cv.jobAppId, ja.candidateId, u.fName, u.lName, cv.parsedJson, u.provId AS current_prov_id
                FROM CVPARSED cv
                JOIN JOBAPPLICATION ja ON cv.jobAppId = ja.jobAppId
                JOIN "user" u ON ja.candidateId = u.userId
                """]
            params = []
            where_clauses = []

            if args.candidate_id is not None:
                params.append(args.candidate_id)
                where_clauses.append(f"ja.candidateId = ${len(params)}")

            if args.resume:
                where_clauses.append("""
                    NOT EXISTS (
                        SELECT 1 FROM CANDIDATELANGUAGE cl 
                        WHERE cl.userId = ja.candidateId
                    )
                    """)

            if where_clauses:
                query_parts.append("WHERE " + " AND ".join(where_clauses))

            query_parts.append("ORDER BY cv.cvParsedId ASC")

            if args.limit is not None:
                params.append(args.limit)
                query_parts.append(f"LIMIT ${len(params)}")

            if args.offset > 0:
                params.append(args.offset)
                query_parts.append(f"OFFSET ${len(params)}")

            sql = "\n".join(query_parts)
            rows = await conn.fetch(sql, *params)

            logger.info(f"[Backfill] Found {len(rows)} candidate CVs to process.")

            # Chunk candidates into batches for sequential processing (deadlock-safe)
            batch_size = args.batch_size
            for i in range(0, len(rows), batch_size):
                batch_rows = rows[i : i + batch_size]
                logger.info(
                    f"[Backfill] Processing batch {i // batch_size + 1} ({len(batch_rows)} rows)..."
                )

                for row in batch_rows:
                    cv_parsed_id = row["cvparsedid"]
                    candidate_id = row["candidateid"]
                    fname = row["fname"]
                    lname = row["lname"]
                    parsed_json = row["parsedjson"]
                    current_prov_id = row["current_prov_id"]
                    candidate_name = f"{lname} {fname}".strip()

                    summary["total_scanned"] += 1
                    logger.info(
                        f"[Backfill] Processing candidate {candidate_name} (ID: {candidate_id}, cvParsedId: {cv_parsed_id})"
                    )

                    tx = conn.transaction()
                    await tx.start()
                    try:
                        payload = _coerce_enrichment_payload(parsed_json)

                        if not payload.languages and not payload.candidate_location:
                            logger.info(
                                f"  -> Candidate {candidate_name} has no parsed language or location. Skipping."
                            )
                            summary["total_skipped"] += 1
                            await tx.rollback()
                            continue

                        # Normalize languages
                        language_rows_count = 0
                        if payload.languages:
                            await _normalize_and_persist_languages(
                                candidate_id=candidate_id,
                                raw_languages=payload.languages,
                                conn=conn,
                            )
                            written_count = await conn.fetchval(
                                "SELECT count(*) FROM CANDIDATELANGUAGE WHERE userId = $1",
                                candidate_id,
                            )
                            language_rows_count = written_count or 0
                            logger.info(
                                f"  -> Normalized languages: parsed {len(payload.languages)} -> persisted {language_rows_count} rows."
                            )

                        # Normalize province
                        province_updated = False
                        if payload.candidate_location:
                            await _normalize_and_update_province(
                                candidate_id=candidate_id,
                                raw_location=payload.candidate_location,
                                conn=conn,
                            )
                            new_prov_id = await conn.fetchval(
                                'SELECT provId FROM "user" WHERE userId = $1',
                                candidate_id,
                            )
                            if new_prov_id and new_prov_id != current_prov_id:
                                province_updated = True
                                logger.info(
                                    f"  -> Province updated: '{payload.candidate_location}' -> '{new_prov_id}' (was '{current_prov_id}')."
                                )
                            else:
                                logger.info(
                                    f"  -> Province unchanged or mapped to None/same (location: '{payload.candidate_location}')."
                                )

                        # Accumulate stats
                        summary["total_updated"] += 1
                        summary["language_rows_inserted"] += language_rows_count
                        if province_updated:
                            summary["province_updates"] += 1

                        if is_dry_run:
                            await tx.rollback()
                            logger.debug(
                                f"  -> [Dry-Run] Rolled back candidate {candidate_name}"
                            )
                        else:
                            await tx.commit()
                            logger.debug(f"  -> Committed candidate {candidate_name}")

                    except Exception as e:
                        await tx.rollback()
                        err_trace = traceback.format_exc()
                        logger.error(
                            f"  -> Failure processing candidate {candidate_name} (ID: {candidate_id}): {e}"
                        )
                        summary["failures"].append(
                            {
                                "candidate_id": candidate_id,
                                "candidate_name": candidate_name,
                                "cv_parsed_id": cv_parsed_id,
                                "reason": str(e),
                                "traceback": err_trace,
                            }
                        )

    finally:
        await db.disconnect()

    summary["backup_created"] = not is_dry_run
    summary["backup_path"] = backup_path

    # Save summary report to JSON
    summary_path = "scripts/backfill_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    logger.info(f"[Backfill] Machine-readable summary saved to {summary_path}")

    # Output Console Summary
    logger.info("=" * 60)
    logger.info(" BACKFILL RUN COMPLETED SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total Candidates Scanned:       {summary['total_scanned']}")
    logger.info(f"Total Candidates Updated:       {summary['total_updated']}")
    logger.info(f"Total Candidates Skipped:       {summary['total_skipped']}")
    logger.info(f"Language Rows Created:          {summary['language_rows_inserted']}")
    logger.info(f"Province updates performed:      {summary['province_updates']}")
    logger.info(f"Total Candidate Failures:       {len(summary['failures'])}")
    if backup_path:
        logger.info(f"Database Backup snapshot file:  {backup_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_backfill())

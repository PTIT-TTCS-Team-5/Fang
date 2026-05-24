"""NMAIex candidate enrichment tracking and retry helpers."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from typing import Any

from app.core.database import acquire_conn
from app.core.logging import logger
from app.core.nmaiex_config import nmaiex_settings
from app.models.nmaiex_schemas import SkillMappingResult
from app.services.embedding import embed_chunks
from app.services.nmaiex_mapper_service import map_skills

ENRICHMENT_STATUS_QUEUED = "QUEUED"
ENRICHMENT_STATUS_PROCESSING = "PROCESSING"
ENRICHMENT_STATUS_SUCCESS = "SUCCESS"
ENRICHMENT_STATUS_FAILED = "FAILED"


@dataclass(frozen=True)
class EnrichmentPayload:
    experience: list[Any]
    skills: list[str]


async def ensure_enrichment_schema(conn: Any | None = None) -> None:
    """Create the sidecar enrichment status table when a DB has not been reset."""

    ddl = """
        CREATE TABLE IF NOT EXISTS NMAIEX_CANDIDATE_ENRICHMENT_JOB (
          enrichmentJobId SERIAL PRIMARY KEY,
          indexJobId INT REFERENCES AIINDEXJOB(indexJobId) ON DELETE SET NULL,
          jobAppId INT NOT NULL UNIQUE REFERENCES JOBAPPLICATION(jobAppId) ON DELETE CASCADE,
          candidateId INT REFERENCES CANDIDATE(userId) ON DELETE CASCADE,
          cvParsedId INT REFERENCES CVPARSED(cvParsedId) ON DELETE CASCADE,
          stat VARCHAR(50) NOT NULL,
          retryCount INT NOT NULL DEFAULT 0,
          maxRetryCount INT NOT NULL DEFAULT 5,
          nextRunAt TIMESTAMPTZ,
          errorMsg TEXT,
          createdAt TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          startedAt TIMESTAMPTZ,
          finishedAt TIMESTAMPTZ,
          updatedAt TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_nmaiex_candidate_enrichment_due
          ON NMAIEX_CANDIDATE_ENRICHMENT_JOB(stat, nextRunAt, retryCount);
    """
    if conn is not None:
        await conn.execute(ddl)
        return

    async with acquire_conn() as owned_conn:
        await owned_conn.execute(ddl)


async def enqueue_candidate_enrichment(
    *,
    index_job_id: int | None,
    job_app_id: int,
    cv_parsed_id: int,
) -> int:
    """Upsert an enrichment job for a JobApplication and return its id."""

    async with acquire_conn() as conn:
        await ensure_enrichment_schema(conn)
        candidate_id = await conn.fetchval(
            "SELECT candidateId FROM JOBAPPLICATION WHERE jobAppId = $1",
            job_app_id,
        )
        if candidate_id is None:
            raise ValueError(f"JOBAPPLICATION not found for jobAppId={job_app_id}")

        return await conn.fetchval(
            """
            INSERT INTO NMAIEX_CANDIDATE_ENRICHMENT_JOB (
                indexJobId, jobAppId, candidateId, cvParsedId, stat,
                retryCount, maxRetryCount, nextRunAt, errorMsg,
                startedAt, finishedAt
            )
            VALUES ($1, $2, $3, $4, $5, 0, $6, NOW(), NULL, NULL, NULL)
            ON CONFLICT (jobAppId) DO UPDATE
            SET indexJobId = EXCLUDED.indexJobId,
                candidateId = EXCLUDED.candidateId,
                cvParsedId = EXCLUDED.cvParsedId,
                stat = EXCLUDED.stat,
                retryCount = 0,
                maxRetryCount = EXCLUDED.maxRetryCount,
                nextRunAt = EXCLUDED.nextRunAt,
                errorMsg = NULL,
                startedAt = NULL,
                finishedAt = NULL,
                updatedAt = NOW()
            RETURNING enrichmentJobId
            """,
            index_job_id,
            job_app_id,
            candidate_id,
            cv_parsed_id,
            ENRICHMENT_STATUS_QUEUED,
            nmaiex_settings.nmaiex_enrichment_retry_max_attempts,
        )


async def enqueue_and_run_candidate_enrichment(
    *,
    index_job_id: int | None,
    job_app_id: int,
    cv_parsed_id: int,
) -> int:
    """Run one best-effort enrichment attempt after the primary ingestion succeeds."""

    enrichment_job_id = await enqueue_candidate_enrichment(
        index_job_id=index_job_id,
        job_app_id=job_app_id,
        cv_parsed_id=cv_parsed_id,
    )
    await run_enrichment_job(enrichment_job_id)
    return enrichment_job_id


async def fetch_due_enrichment_jobs(limit: int) -> list[dict[str, Any]]:
    """Return queued/failed enrichment jobs that are ready for retry."""

    async with acquire_conn() as conn:
        await ensure_enrichment_schema(conn)
        rows = await conn.fetch(
            """
            SELECT enrichmentJobId, jobAppId, candidateId, cvParsedId, stat, retryCount
            FROM NMAIEX_CANDIDATE_ENRICHMENT_JOB
            WHERE stat IN ($1, $2)
              AND retryCount < maxRetryCount
              AND (nextRunAt IS NULL OR nextRunAt <= NOW())
            ORDER BY COALESCE(nextRunAt, createdAt), enrichmentJobId
            LIMIT $3
            """,
            ENRICHMENT_STATUS_QUEUED,
            ENRICHMENT_STATUS_FAILED,
            limit,
        )
        return [dict(row) for row in rows]


async def enqueue_missing_enrichment_jobs(limit: int) -> list[int]:
    """Create enrichment jobs for existing CVPARSED rows that have no sidecar job."""

    async with acquire_conn() as conn:
        await ensure_enrichment_schema(conn)
        rows = await conn.fetch(
            """
            INSERT INTO NMAIEX_CANDIDATE_ENRICHMENT_JOB (
                indexJobId, jobAppId, candidateId, cvParsedId, stat,
                retryCount, maxRetryCount, nextRunAt, errorMsg
            )
            SELECT latest_job.indexJobId,
                   cv.jobAppId,
                   ja.candidateId,
                   cv.cvParsedId,
                   $1,
                   0,
                   $2,
                   NOW(),
                   NULL
            FROM CVPARSED cv
            JOIN JOBAPPLICATION ja ON ja.jobAppId = cv.jobAppId
            LEFT JOIN LATERAL (
                SELECT indexJobId
                FROM AIINDEXJOB
                WHERE jobAppId = cv.jobAppId
                ORDER BY createdAt DESC, indexJobId DESC
                LIMIT 1
            ) latest_job ON TRUE
            LEFT JOIN NMAIEX_CANDIDATE_ENRICHMENT_JOB existing
                   ON existing.jobAppId = cv.jobAppId
            WHERE existing.jobAppId IS NULL
            ORDER BY cv.cvParsedId
            LIMIT $3
            RETURNING enrichmentJobId
            """,
            ENRICHMENT_STATUS_QUEUED,
            nmaiex_settings.nmaiex_enrichment_retry_max_attempts,
            limit,
        )
        return [row["enrichmentjobid"] for row in rows]


async def run_enrichment_job(enrichment_job_id: int) -> None:
    """Execute one enrichment job and persist SUCCESS/FAILED independently."""

    async with acquire_conn() as conn:
        await ensure_enrichment_schema(conn)
        row = await conn.fetchrow(
            """
            SELECT ej.enrichmentJobId, ej.jobAppId, ej.candidateId, ej.cvParsedId,
                   ej.retryCount, ej.maxRetryCount, cv.parsedJson AS parsedJson
            FROM NMAIEX_CANDIDATE_ENRICHMENT_JOB ej
            JOIN CVPARSED cv ON cv.cvParsedId = ej.cvParsedId
            WHERE ej.enrichmentJobId = $1
            """,
            enrichment_job_id,
        )
        if row is None:
            raise ValueError(f"Enrichment job not found: {enrichment_job_id}")

        if row["retrycount"] >= row["maxretrycount"]:
            logger.info(
                "[NMAIex] Skipping enrichment job with exhausted retries",
                extra={"enrichmentJobId": enrichment_job_id},
            )
            return

        await _mark_processing(conn, enrichment_job_id)

    try:
        await enrich_candidate_structured_data(
            candidate_id=row["candidateid"],
            parsed_payload=row["parsedjson"],
        )
    except Exception as exc:
        async with acquire_conn() as conn:
            await ensure_enrichment_schema(conn)
            await _mark_failed(
                conn,
                enrichment_job_id,
                error_msg=str(exc),
            )
        raise

    async with acquire_conn() as conn:
        await ensure_enrichment_schema(conn)
        await conn.execute(
            """
            UPDATE NMAIEX_CANDIDATE_ENRICHMENT_JOB
            SET stat = $2,
                errorMsg = NULL,
                nextRunAt = NULL,
                finishedAt = NOW(),
                updatedAt = NOW()
            WHERE enrichmentJobId = $1
            """,
            enrichment_job_id,
            ENRICHMENT_STATUS_SUCCESS,
        )


async def enrich_candidate_structured_data(
    *,
    candidate_id: int,
    parsed_payload: Any,
    conn: Any | None = None,
) -> None:
    """Update candidate expyears and NMAIex skills as an atomic DB write."""

    payload = _coerce_enrichment_payload(parsed_payload)
    computed_exp_years = compute_exp_years(payload.experience)
    mapping_result = await _map_skills_best_effort(payload.skills)
    raw_skill_records = await _build_raw_skill_records(mapping_result.unmatched_texts)

    async def _apply(target_conn: Any) -> None:
        async with target_conn.transaction():
            await target_conn.execute(
                "UPDATE CANDIDATE SET expyears = $1 WHERE userId = $2",
                computed_exp_years,
                candidate_id,
            )
            await target_conn.execute(
                "DELETE FROM CANDIDATESKILL WHERE userId = $1",
                candidate_id,
            )
            if mapping_result.matched_ids:
                await target_conn.executemany(
                    """
                    INSERT INTO CANDIDATESKILL (userId, skillId)
                    VALUES ($1, $2)
                    ON CONFLICT DO NOTHING
                    """,
                    [
                        (candidate_id, skill_id)
                        for skill_id in mapping_result.matched_ids
                    ],
                )

            await target_conn.execute(
                "DELETE FROM CANDIDATE_SKILL_RAW WHERE candId = $1",
                candidate_id,
            )
            if raw_skill_records:
                await target_conn.executemany(
                    """
                    INSERT INTO CANDIDATE_SKILL_RAW (candId, rawText, embedding)
                    VALUES ($1, $2, $3::vector)
                    """,
                    [
                        (candidate_id, raw_text, vector_text)
                        for raw_text, vector_text in raw_skill_records
                    ],
                )

    if conn is not None:
        await _apply(conn)
        return

    async with acquire_conn() as owned_conn:
        await _apply(owned_conn)


def compute_exp_years(experience_entries: list[Any]) -> int:
    """Compute full years from legacy or current parsed CV experience entries."""

    total_months = 0
    for exp in experience_entries:
        start_date_raw = _get_field(exp, "startDate")
        if not start_date_raw:
            continue
        try:
            start_year, start_month = map(int, str(start_date_raw).split("-"))
            start_date = dt.date(start_year, start_month, 1)

            end_date_raw = _get_field(exp, "endDate")
            if not end_date_raw or str(end_date_raw).lower() == "present":
                end_date = dt.date.today()
            else:
                end_year, end_month = map(int, str(end_date_raw).split("-"))
                end_date = dt.date(end_year, end_month, 1)

            months = (end_date.year - start_date.year) * 12 + (
                end_date.month - start_date.month
            )
            if months > 0:
                total_months += months
        except Exception:
            continue

    return max(0, total_months // 12)


def _coerce_enrichment_payload(parsed_payload: Any) -> EnrichmentPayload:
    if hasattr(parsed_payload, "model_dump"):
        parsed_payload = parsed_payload.model_dump()

    if isinstance(parsed_payload, str):
        parsed_payload = json.loads(parsed_payload)

    if not isinstance(parsed_payload, dict):
        raise ValueError("parsed_payload must be a dict-like ParsedCV payload")

    experience = parsed_payload.get("experience") or []
    if not isinstance(experience, list):
        experience = []

    raw_skills = parsed_payload.get("skills") or []
    skills = [str(skill).strip() for skill in raw_skills if str(skill).strip()]
    return EnrichmentPayload(experience=experience, skills=skills)


def _get_field(item: Any, field_name: str) -> Any:
    if isinstance(item, dict):
        return item.get(field_name)
    return getattr(item, field_name, None)


async def _map_skills_best_effort(skills: list[str]) -> SkillMappingResult:
    if not skills:
        return SkillMappingResult(matched_ids=[], unmatched_texts=[])
    return await map_skills(skills)


async def _build_raw_skill_records(unmatched_texts: list[str]) -> list[tuple[str, str]]:
    if not unmatched_texts:
        return []

    vectors = await embed_chunks(
        unmatched_texts,
        dimensions=nmaiex_settings.nmaiex_skill_embedding_dims,
    )
    if len(vectors) != len(unmatched_texts):
        raise ValueError(
            "raw skill vector count does not match unmatched skill text count"
        )
    return [
        (raw_text, f"[{','.join(f'{float(value):.12g}' for value in vector)}]")
        for raw_text, vector in zip(unmatched_texts, vectors)
    ]


async def _mark_processing(conn: Any, enrichment_job_id: int) -> None:
    await conn.execute(
        """
        UPDATE NMAIEX_CANDIDATE_ENRICHMENT_JOB
        SET stat = $2,
            startedAt = NOW(),
            updatedAt = NOW()
        WHERE enrichmentJobId = $1
        """,
        enrichment_job_id,
        ENRICHMENT_STATUS_PROCESSING,
    )


async def _mark_failed(conn: Any, enrichment_job_id: int, *, error_msg: str) -> None:
    row = await conn.fetchrow(
        """
        SELECT retryCount, maxRetryCount
        FROM NMAIEX_CANDIDATE_ENRICHMENT_JOB
        WHERE enrichmentJobId = $1
        """,
        enrichment_job_id,
    )
    if row is None:
        return

    next_retry_count = row["retrycount"] + 1
    retry_exhausted = next_retry_count >= row["maxretrycount"]
    next_run_at = None
    if not retry_exhausted:
        delay_seconds = nmaiex_settings.nmaiex_enrichment_retry_base_seconds * (
            2 ** max(0, next_retry_count - 1)
        )
        next_run_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(
            seconds=delay_seconds
        )

    await conn.execute(
        """
        UPDATE NMAIEX_CANDIDATE_ENRICHMENT_JOB
        SET stat = $2,
            retryCount = $3,
            nextRunAt = $4,
            errorMsg = $5,
            finishedAt = NOW(),
            updatedAt = NOW()
        WHERE enrichmentJobId = $1
        """,
        enrichment_job_id,
        ENRICHMENT_STATUS_FAILED,
        next_retry_count,
        next_run_at,
        error_msg[:2000],
    )

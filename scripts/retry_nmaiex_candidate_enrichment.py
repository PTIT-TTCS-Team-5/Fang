import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import db
from app.core.logging import logger
from app.services.nmaiex_candidate_enrichment import (
    enqueue_missing_enrichment_jobs,
    ensure_enrichment_schema,
    fetch_due_enrichment_jobs,
    run_enrichment_job,
)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retry queued/failed NMAIex candidate enrichment jobs."
    )
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument(
        "--enqueue-missing",
        action="store_true",
        help="Create enrichment jobs for existing CVPARSED rows before retrying due jobs.",
    )
    args = parser.parse_args()

    await db.connect()
    try:
        await ensure_enrichment_schema()
        if args.enqueue_missing:
            created_ids = await enqueue_missing_enrichment_jobs(max(1, args.limit))
            logger.info(f"[NMAIex] Enqueued {len(created_ids)} missing enrichment jobs")

        jobs = await fetch_due_enrichment_jobs(max(1, args.limit))
        logger.info(f"[NMAIex] Found {len(jobs)} enrichment jobs due for retry")

        succeeded = 0
        failed = 0
        for job in jobs:
            enrichment_job_id = job["enrichmentjobid"]
            try:
                await run_enrichment_job(enrichment_job_id)
                succeeded += 1
            except Exception as exc:
                failed += 1
                logger.error(
                    f"[NMAIex] Enrichment retry failed for enrichmentJobId={enrichment_job_id}: {exc}",
                    exc_info=True,
                )

        logger.info(
            f"[NMAIex] Enrichment retry completed: succeeded={succeeded}, failed={failed}"
        )
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

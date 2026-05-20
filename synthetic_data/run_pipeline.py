# ruff: noqa: E402
"""synthetic_data/run_pipeline.py — CLI entrypoint cho Synthetic Data Pipeline.

Usage:
    python -m synthetic_data.run_pipeline --help
    python -m synthetic_data.run_pipeline dry-run
    python -m synthetic_data.run_pipeline generate-cvs --total 500
    python -m synthetic_data.run_pipeline write-cvs
    python -m synthetic_data.run_pipeline generate-jobs
    python -m synthetic_data.run_pipeline write-jobs
    python -m synthetic_data.run_pipeline full --total 500
"""

import argparse
import asyncio
import logging

# --- Setup logging trước khi import project modules ---
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format='{"asctime": "%(asctime)s", "levelname": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# --- Monkey Patching Embedding Service to use 9Router ---
async def embed_chunks_9router(
    chunks: list[str],
    dimensions: int | None = None,
) -> list[list[float]]:
    """Monkey-patched embed_chunks that uses 9Router API proxy to bypass original API quotas."""
    if not chunks:
        return []

    import httpx

    from app.core.config import settings
    from synthetic_data.config import NINE_ROUTER_KEY, NINE_ROUTER_URL

    normalized_chunks = [c.strip() for c in chunks if isinstance(c, str) and c.strip()]
    if not normalized_chunks:
        return []

    effective_dims = dimensions if dimensions is not None else settings.embedding_dim
    batch_size = (
        settings.embedding_batch_size if settings.embedding_batch_size > 0 else 32
    )
    vectors: list[list[float]] = []

    logger.info(
        f"[9Router Monkey-Patch] Embedding {len(normalized_chunks)} chunks via 9Router proxy "
        f"({effective_dims} dimensions requested)"
    )

    async with httpx.AsyncClient() as http_client:
        for start_index in range(0, len(normalized_chunks), batch_size):
            batch = normalized_chunks[start_index : start_index + batch_size]
            headers = {
                "Authorization": f"Bearer {NINE_ROUTER_KEY}",
                "Content-Type": "application/json",
            }
            payload = {"model": settings.embedding_model, "input": batch}
            resp = await http_client.post(
                f"{NINE_ROUTER_URL}/embeddings",
                json=payload,
                headers=headers,
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data["data"]:
                v = item["embedding"]
                # Truncate to effective_dims to match pgvector expected size
                vectors.append(v[:effective_dims])

    if len(vectors) != len(normalized_chunks):
        raise RuntimeError(
            f"9Router returned {len(vectors)} vectors for {len(normalized_chunks)} chunks."
        )

    return vectors


import app.services.embedding
import app.services.job_ingestion_service
import app.services.nmaiex_mapper_service

app.services.embedding.embed_chunks = embed_chunks_9router
app.services.nmaiex_mapper_service.embed_chunks = embed_chunks_9router
app.services.job_ingestion_service.embed_chunks = embed_chunks_9router

# --- Project imports ---
from app.core.database import db
from synthetic_data.config import CV_OUTPUT_DIR, JOB_OUTPUT_DIR
from synthetic_data.db_writer import (
    fetch_company_ids,
    fetch_company_map,
    fetch_skill_id_map,
    write_candidate_cv,
    write_job_posting,
)
from synthetic_data.generator import generate_all_cvs, generate_all_jobs

# ============================================================
# Sub-commands
# ============================================================


async def cmd_dry_run(args) -> None:
    """Validate prompt generation without calling LLM or DB."""
    logger.info("=== DRY RUN MODE ===")
    await db.connect()

    try:
        from synthetic_data.config import CV_BATCH_SIZE
        from synthetic_data.personas import generate_manifest
        from synthetic_data.prompts import build_cv_batch_prompt

        manifest = generate_manifest(args.total)
        batch = manifest[:CV_BATCH_SIZE]
        system, user = build_cv_batch_prompt(batch)

        logger.info(f"CV Manifest: {len(manifest)} entries")
        logger.info(f"CV System Prompt length: {len(system)} chars")
        logger.info(f"CV User Prompt preview: {user[:200]}...")

        company_map = await fetch_company_map()
        company_ids = list(company_map.keys())
        logger.info(f"Companies in DB: {len(company_ids)}")

        logger.info("=== DRY RUN COMPLETE ===")
    finally:
        await db.disconnect()


async def cmd_generate_cvs(args) -> None:
    """Generate CVs via LLM and cache to output/cvs/."""
    logger.info(f"=== GENERATE CVS: total={args.total}, seed={args.seed} ===")
    results = await generate_all_cvs(
        total=args.total,
        seed=args.seed,
        dry_run=False,
        resume=not args.no_resume,
    )
    logger.info(f"Generated {len(results)} CV pairs. Cached in {CV_OUTPUT_DIR}")


async def cmd_write_cvs(args) -> None:
    """Load cached CVs and persist to DB."""
    logger.info("=== WRITE CVS TO DB ===")
    await db.connect()

    try:
        import json

        from app.models.cv_models import ParsedCV
        from synthetic_data.config import CV_BATCH_SIZE
        from synthetic_data.personas import generate_manifest

        manifest = generate_manifest(args.total, args.seed)

        # Load from cache
        written, failed = 0, 0
        for i in range(0, len(manifest), CV_BATCH_SIZE):
            batch = manifest[i : i + CV_BATCH_SIZE]
            batch_id = batch[0]["batch_id"]
            cache_path = CV_OUTPUT_DIR / f"{batch_id}.json"

            if not cache_path.exists():
                logger.warning(f"Cache missing for {batch_id}, skipping")
                failed += len(batch)
                continue

            data = json.loads(cache_path.read_text(encoding="utf-8"))
            cvs = [ParsedCV.model_validate(d) for d in data]

            for entry, cv in zip(batch, cvs):
                job_app_id = await write_candidate_cv(entry, cv)
                if job_app_id:
                    written += 1
                else:
                    failed += 1

        logger.info(f"=== WRITE CVS DONE: written={written}, failed={failed} ===")
    finally:
        await db.disconnect()


async def cmd_generate_jobs(args) -> None:
    """Generate Jobs via LLM and cache to output/jobs/."""
    logger.info("=== GENERATE JOBS ===")
    await db.connect()

    try:
        company_ids = await fetch_company_ids()
        company_map = await fetch_company_map()
    finally:
        await db.disconnect()

    jobs = await generate_all_jobs(
        company_ids=company_ids,
        company_map=company_map,
        dry_run=False,
    )
    logger.info(f"Generated {len(jobs)} jobs. Cached in {JOB_OUTPUT_DIR}")


async def cmd_write_jobs(args) -> None:
    """Load cached Jobs and persist to DB."""
    logger.info("=== WRITE JOBS TO DB ===")
    await db.connect()

    try:
        import json

        from synthetic_data.models import SyntheticJob

        skill_id_map = await fetch_skill_id_map()

        written, failed = 0, 0
        batch_num = 1

        while True:
            batch_id = f"job_batch_{batch_num:03d}"
            cache_path = JOB_OUTPUT_DIR / f"{batch_id}.json"
            if not cache_path.exists():
                break

            data = json.loads(cache_path.read_text(encoding="utf-8"))
            jobs = [SyntheticJob.model_validate(d) for d in data]

            for job in jobs:
                job_post_id = await write_job_posting(job, skill_id_map)
                if job_post_id:
                    written += 1
                else:
                    failed += 1

            batch_num += 1

        logger.info(f"=== WRITE JOBS DONE: written={written}, failed={failed} ===")
    finally:
        await db.disconnect()


async def cmd_full(args) -> None:
    """Full pipeline: generate CVs â†’ generate Jobs â†’ write Jobs â†’ write CVs."""
    logger.info(f"=== FULL PIPELINE: total_cv={args.total} ===")

    # Step 1: Generate CVs
    logger.info("Step 1: Generate CVs")
    await cmd_generate_cvs(args)

    # Step 2: Generate Jobs (needs DB for company info)
    logger.info("Step 2: Generate Jobs")
    await cmd_generate_jobs(args)

    # Step 3: Write Jobs first (so JOBAPPLICATION can reference them)
    logger.info("Step 3: Write Jobs to DB")
    await cmd_write_jobs(args)

    # Step 4: Write CVs
    logger.info("Step 4: Write CVs to DB")
    await cmd_write_cvs(args)

    logger.info("=== FULL PIPELINE COMPLETE ===")


# ============================================================
# CLI Parser
# ============================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="synthetic_data",
        description="FANG Synthetic Data Pipeline â€” NMAIex AI Ranking",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # dry-run
    p_dry = subparsers.add_parser(
        "dry-run", help="Validate prompts without LLM/DB calls"
    )
    p_dry.add_argument(
        "--total",
        type=int,
        default=10,
        help="Number of CV entries to preview (default: 10)",
    )
    p_dry.set_defaults(func=cmd_dry_run)

    # generate-cvs
    p_gen_cv = subparsers.add_parser(
        "generate-cvs", help="Generate CVs via LLM (cached)"
    )
    p_gen_cv.add_argument("--total", type=int, default=500)
    p_gen_cv.add_argument("--seed", type=int, default=42)
    p_gen_cv.add_argument(
        "--no-resume", action="store_true", help="Re-generate all (ignore cache)"
    )
    p_gen_cv.set_defaults(func=cmd_generate_cvs)

    # write-cvs
    p_write_cv = subparsers.add_parser("write-cvs", help="Write cached CVs to DB")
    p_write_cv.add_argument("--total", type=int, default=500)
    p_write_cv.add_argument("--seed", type=int, default=42)
    p_write_cv.set_defaults(func=cmd_write_cvs)

    # generate-jobs
    p_gen_job = subparsers.add_parser(
        "generate-jobs", help="Generate Jobs via LLM (cached)"
    )
    p_gen_job.set_defaults(func=cmd_generate_jobs)

    # write-jobs
    p_write_job = subparsers.add_parser("write-jobs", help="Write cached Jobs to DB")
    p_write_job.set_defaults(func=cmd_write_jobs)

    # full
    p_full = subparsers.add_parser("full", help="Run full pipeline end-to-end")
    p_full.add_argument("--total", type=int, default=500)
    p_full.add_argument("--seed", type=int, default=42)
    p_full.add_argument("--no-resume", action="store_true")
    p_full.set_defaults(func=cmd_full)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()

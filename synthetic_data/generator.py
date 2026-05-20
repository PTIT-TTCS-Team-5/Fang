"""synthetic_data/generator.py — LLM generation via 9Router (OpenAI-compatible).

Batch CV/Job generation với:
- Exponential backoff retry
- Output caching (resume-able)
- Pydantic validation
"""

import asyncio
import json
import logging
import re
from pathlib import Path

import httpx

from app.models.cv_models import ParsedCV
from synthetic_data.config import (
    CV_BATCH_SIZE,
    CV_OUTPUT_DIR,
    JOB_BATCH_SIZE,
    JOB_OUTPUT_DIR,
    LLM_TIMEOUT_SECONDS,
    MAX_RETRIES,
    MODEL_CV_GENERATION,
    MODEL_JOB_GENERATION,
    NINE_ROUTER_KEY,
    NINE_ROUTER_URL,
    RETRY_BASE_SECONDS,
    RETRY_MAX_SECONDS,
)
from synthetic_data.models import CVBatchResponse, JobBatchResponse, SyntheticJob
from synthetic_data.personas import CVManifestEntry, generate_manifest
from synthetic_data.prompts import build_cv_batch_prompt, build_job_batch_prompt

logger = logging.getLogger(__name__)


def clean_json_response(raw: str) -> str:
    """Clean markdown code block wrapping from LLM JSON response."""
    raw = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if match:
        return match.group(1).strip()
    return raw


# ============================================================
# Core LLM Call
# ============================================================


async def _call_llm(
    client: httpx.AsyncClient,
    model: str,
    system_prompt: str,
    user_prompt: str,
    attempt: int = 0,
) -> str:
    """Single LLM call via 9Router with exponential backoff."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.8,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {NINE_ROUTER_KEY}",
        "Content-Type": "application/json",
    }

    for retry in range(MAX_RETRIES):
        try:
            resp = await client.post(
                f"{NINE_ROUTER_URL}/chat/completions",
                json=payload,
                headers=headers,
                timeout=LLM_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            try:
                data = resp.json()
            except Exception as e:
                logger.error(
                    f"Failed to decode response as JSON. Status code: {resp.status_code}. Content: {resp.text}"
                )
                raise e
            content = data["choices"][0]["message"]["content"]
            return content
        except (
            httpx.HTTPStatusError,
            httpx.RequestError,
            KeyError,
            json.JSONDecodeError,
        ) as e:
            wait = min(RETRY_BASE_SECONDS * (2**retry), RETRY_MAX_SECONDS)
            logger.warning(
                f"LLM call failed (retry {retry+1}/{MAX_RETRIES}): {e}. Wait {wait}s"
                f" Details: {type(e).__name__}"
            )
            if retry < MAX_RETRIES - 1:
                await asyncio.sleep(wait)
            else:
                raise RuntimeError(
                    f"LLM call failed after {MAX_RETRIES} retries: {e}"
                ) from e
    raise RuntimeError("Unreachable")


# ============================================================
# CV Generation
# ============================================================


def _cv_cache_path(batch_id: str) -> Path:
    return CV_OUTPUT_DIR / f"{batch_id}.json"


def _load_cv_cache(batch_id: str) -> list[ParsedCV] | None:
    """Load cached CV batch nếu đã sinh."""
    p = _cv_cache_path(batch_id)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        result = CVBatchResponse.model_validate({"cvs": data})
        logger.info(f"Cache hit: {batch_id} ({len(result.cvs)} CVs)")
        return result.cvs
    except Exception as e:
        logger.warning(f"Cache invalid for {batch_id}: {e}. Re-generating.")
        return None


def _save_cv_cache(batch_id: str, cvs: list[ParsedCV]) -> None:
    p = _cv_cache_path(batch_id)
    p.write_text(
        json.dumps([cv.model_dump() for cv in cvs], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.debug(f"Cached {len(cvs)} CVs → {p}")


async def generate_cv_batch(
    client: httpx.AsyncClient,
    manifest_batch: list[CVManifestEntry],
    dry_run: bool = False,
) -> list[ParsedCV]:
    """Generate một batch CV từ manifest entries.

    Args:
        client: Shared httpx AsyncClient
        manifest_batch: 5 entries từ manifest
        dry_run: Nếu True, chỉ build prompt + validate, không gọi LLM

    Returns: List ParsedCV (validated)
    """
    batch_id = manifest_batch[0]["batch_id"]

    # Cache check
    cached = _load_cv_cache(batch_id)
    if cached is not None:
        return cached

    system_prompt, user_prompt = build_cv_batch_prompt(manifest_batch)

    if dry_run:
        logger.info(
            f"[DRY RUN] Would call LLM for {batch_id} with {len(manifest_batch)} CVs"
        )
        logger.debug(f"[DRY RUN] User prompt preview: {user_prompt[:300]}...")
        return []

    logger.info(f"Generating CV batch: {batch_id} ({len(manifest_batch)} CVs)")
    raw_response = await _call_llm(
        client, MODEL_CV_GENERATION, system_prompt, user_prompt
    )

    # Parse + validate
    try:
        clean_raw = clean_json_response(raw_response)
        parsed = CVBatchResponse.model_validate_json(clean_raw)
        cvs = parsed.cvs
    except Exception as e:
        logger.error(f"Pydantic validation failed for {batch_id}: {e}")
        logger.debug(f"Raw response: {raw_response[:500]}")
        raise ValueError(f"CV batch {batch_id} validation failed: {e}") from e

    if len(cvs) != len(manifest_batch):
        logger.warning(
            f"LLM returned {len(cvs)} CVs, expected {len(manifest_batch)} for {batch_id}"
        )

    # Cache
    _save_cv_cache(batch_id, cvs)
    logger.info(f"Generated + cached {len(cvs)} CVs for {batch_id}")
    return cvs


async def generate_all_cvs(
    total: int = 500,
    seed: int = 42,
    dry_run: bool = False,
    resume: bool = True,
) -> list[tuple[CVManifestEntry, ParsedCV]]:
    """Generate tất cả CVs theo manifest.

    Returns: List of (manifest_entry, parsed_cv) pairs
    """
    manifest = generate_manifest(total, seed)
    results: list[tuple[CVManifestEntry, ParsedCV]] = []

    # Group into batches
    batches: list[list[CVManifestEntry]] = []
    for i in range(0, len(manifest), CV_BATCH_SIZE):
        batches.append(manifest[i : i + CV_BATCH_SIZE])

    logger.info(
        f"Total CVs: {total}, Batches: {len(batches)}, Batch size: {CV_BATCH_SIZE}"
    )

    async with httpx.AsyncClient() as client:
        for batch in batches:
            batch_id = batch[0]["batch_id"]

            # Skip if cached and resume mode
            if resume and _load_cv_cache(batch_id) is not None:
                cached_cvs = _load_cv_cache(batch_id)
                for entry, cv in zip(batch, cached_cvs or []):
                    results.append((entry, cv))
                continue

            cvs = await generate_cv_batch(client, batch, dry_run=dry_run)
            for entry, cv in zip(batch, cvs):
                results.append((entry, cv))

            # Small delay to respect rate limits
            if not dry_run:
                await asyncio.sleep(0.5)

    logger.info(f"Total generated: {len(results)} CV pairs")
    return results


# ============================================================
# Job Generation
# ============================================================

# Job manifest — pre-defined structure for 20 jobs across companies
JOB_MANIFEST = [
    # (comp_id_idx 1-15, category_hint, level_hint, work_mode, salary_hint, prov override)
    {
        "comp_id_idx": 1,
        "category_hint": "Backend Development",
        "level_hint": "Junior/Middle",
        "work_mode": "HYBRID",
        "salary_hint": "15-25 triệu",
    },
    {
        "comp_id_idx": 1,
        "category_hint": "AI / Machine Learning",
        "level_hint": "Middle/Senior",
        "work_mode": "HYBRID",
        "salary_hint": "30-50 triệu",
    },
    {
        "comp_id_idx": 2,
        "category_hint": "Fullstack Development",
        "level_hint": "Junior/Middle",
        "work_mode": "ONSITE",
        "salary_hint": "15-30 triệu",
    },
    {
        "comp_id_idx": 2,
        "category_hint": "DevOps / Cloud",
        "level_hint": "Middle/Senior",
        "work_mode": "HYBRID",
        "salary_hint": "30-50 triệu",
    },
    {
        "comp_id_idx": 3,
        "category_hint": "Data Engineering",
        "level_hint": "Middle/Senior",
        "work_mode": "HYBRID",
        "salary_hint": "25-45 triệu",
    },
    {
        "comp_id_idx": 4,
        "category_hint": "Security / Pentest",
        "level_hint": "Senior",
        "work_mode": "ONSITE",
        "salary_hint": "40-70 triệu",
    },
    {
        "comp_id_idx": 5,
        "category_hint": "Backend Development",
        "level_hint": "Fresher/Junior",
        "work_mode": "HYBRID",
        "salary_hint": "8-15 triệu",
    },
    {
        "comp_id_idx": 6,
        "category_hint": "Mobile Development",
        "level_hint": "Junior/Middle",
        "work_mode": "ONSITE",
        "salary_hint": "15-25 triệu",
    },
    {
        "comp_id_idx": 7,
        "category_hint": "AI / Machine Learning",
        "level_hint": "Middle/Senior",
        "work_mode": "HYBRID",
        "salary_hint": "35-60 triệu",
    },
    {
        "comp_id_idx": 8,
        "category_hint": "Backend Development",
        "level_hint": "Senior",
        "work_mode": "ONSITE",
        "salary_hint": "40-65 triệu",
    },
    {
        "comp_id_idx": 9,
        "category_hint": "Mobile Development",
        "level_hint": "Middle",
        "work_mode": "HYBRID",
        "salary_hint": "20-35 triệu",
    },
    {
        "comp_id_idx": 10,
        "category_hint": "DevOps / Cloud",
        "level_hint": "Junior/Middle",
        "work_mode": "REMOTE",
        "salary_hint": "20-35 triệu",
    },
    {
        "comp_id_idx": 11,
        "category_hint": "Frontend Development",
        "level_hint": "Junior/Middle",
        "work_mode": "ONSITE",
        "salary_hint": "12-22 triệu",
    },
    {
        "comp_id_idx": 11,
        "category_hint": "Fullstack Development",
        "level_hint": "Middle",
        "work_mode": "HYBRID",
        "salary_hint": "20-30 triệu",
    },
    {
        "comp_id_idx": 12,
        "category_hint": "QA / Testing",
        "level_hint": "Junior/Middle",
        "work_mode": "ONSITE",
        "salary_hint": "10-20 triệu",
    },
    {
        "comp_id_idx": 13,
        "category_hint": "Backend Development",
        "level_hint": "Junior",
        "work_mode": "ONSITE",
        "salary_hint": "10-18 triệu",
    },
    {
        "comp_id_idx": 14,
        "category_hint": "ERP / SAP",
        "level_hint": "Middle/Senior",
        "work_mode": "ONSITE",
        "salary_hint": "25-45 triệu",
    },
    {
        "comp_id_idx": 15,
        "category_hint": "IT Support / SysAdmin",
        "level_hint": "Junior/Middle",
        "work_mode": "ONSITE",
        "salary_hint": "10-18 triệu",
    },
    {
        "comp_id_idx": 3,
        "category_hint": "Data Science",
        "level_hint": "Middle",
        "work_mode": "HYBRID",
        "salary_hint": "25-40 triệu",
    },
    {
        "comp_id_idx": 6,
        "category_hint": "Frontend Development",
        "level_hint": "Fresher/Junior",
        "work_mode": "ONSITE",
        "salary_hint": "8-15 triệu",
    },
]


def _job_cache_path(batch_id: str) -> Path:
    return JOB_OUTPUT_DIR / f"{batch_id}.json"


async def generate_all_jobs(
    company_ids: list[int],
    company_map: dict[int, dict],
    dry_run: bool = False,
) -> list[SyntheticJob]:
    """Generate tất cả Job Postings.

    Args:
        company_ids: List of compId từ DB (theo thứ tự insert, 1-15)
        company_map: {comp_id: {"comp_name": ..., "prov_id": ...}}
        dry_run: Nếu True, không gọi LLM

    Returns: List SyntheticJob
    """
    # Map comp_id_idx (1-based) → actual compId
    specs = []
    for spec in JOB_MANIFEST:
        idx = spec["comp_id_idx"]
        if idx <= len(company_ids):
            actual_comp_id = company_ids[idx - 1]
            comp_info = company_map.get(actual_comp_id, {})
            specs.append(
                {
                    **spec,
                    "comp_id": actual_comp_id,
                    "prov_id": comp_info.get("prov_id", "HANOI"),
                }
            )

    # Group into batches of JOB_BATCH_SIZE
    batches: list[list[dict]] = []
    for i in range(0, len(specs), JOB_BATCH_SIZE):
        batches.append(specs[i : i + JOB_BATCH_SIZE])

    all_jobs: list[SyntheticJob] = []

    async with httpx.AsyncClient() as client:
        for batch_num, batch in enumerate(batches):
            batch_id = f"job_batch_{batch_num+1:03d}"
            cache_path = _job_cache_path(batch_id)

            if cache_path.exists():
                try:
                    data = json.loads(cache_path.read_text(encoding="utf-8"))
                    cached = JobBatchResponse.model_validate({"jobs": data})
                    all_jobs.extend(cached.jobs)
                    logger.info(f"Cache hit: {batch_id}")
                    continue
                except Exception:
                    logger.warning(f"Job cache invalid for {batch_id}, re-generating")

            system_prompt, user_prompt = build_job_batch_prompt(batch, company_map)

            if dry_run:
                logger.info(
                    f"[DRY RUN] Would generate {len(batch)} jobs for {batch_id}"
                )
                continue

            logger.info(f"Generating Job batch: {batch_id} ({len(batch)} jobs)")
            raw = await _call_llm(
                client, MODEL_JOB_GENERATION, system_prompt, user_prompt
            )

            try:
                clean_raw = clean_json_response(raw)
                parsed = JobBatchResponse.model_validate_json(clean_raw)
                jobs = parsed.jobs
            except Exception as e:
                logger.error(f"Job validation failed for {batch_id}: {e}")
                raise

            # Cache
            cache_path.write_text(
                json.dumps(
                    [j.model_dump() for j in jobs], ensure_ascii=False, indent=2
                ),
                encoding="utf-8",
            )
            all_jobs.extend(jobs)
            logger.info(f"Generated {len(jobs)} jobs for {batch_id}")
            await asyncio.sleep(1.0)  # Respect rate limits for pro model

    logger.info(f"Total jobs generated: {len(all_jobs)}")
    return all_jobs

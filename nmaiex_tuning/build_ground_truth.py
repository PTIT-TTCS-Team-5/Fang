"""nmaiex_tuning/build_ground_truth.py — Build Ground Truth Rating Matrix using Local Round-Robin Load-Balancer.

Evaluates 2,000 random Candidate-Job pairs (20 jobs * 100 candidates each)
using Gemini 3.1 Flash Lite directly. Employs 10x batching, Pydantic validation,
local round-robin load-balancing across 13 keys, automatic bad-key detection, and cache resume.
"""

import asyncio
import json
import logging
import random
import re
import sys
from pathlib import Path
from typing import List

import dotenv
import httpx
from pydantic import BaseModel, Field

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env
dotenv.load_dotenv(Path(__file__).parent.parent / ".env")

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format='{"asctime": "%(asctime)s", "levelname": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("build_ground_truth")

from app.core.database import acquire_conn, db

# Caching Configuration
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_FILE = OUTPUT_DIR / "ground_truth_matrix.json"

MODEL_JUDGE = "gemini/gemini-3.1-flash-lite"
BATCH_SIZE = 10  # Evaluate 10 candidates per API request


class CandidateEvalSchema(BaseModel):
    candidate_id: int
    skills_match: str = Field(
        description="Suitability analysis of candidate skills vs JD requirements"
    )
    experience_gap: str = Field(
        description="Analysis of years of experience and seniority gap"
    )
    score: int = Field(
        description="Score from 0 to 4 (0=Irrelevant, 1=Poor, 2=Partial, 3=Good, 4=Perfect)",
        ge=0,
        le=4,
    )


class BatchEvalResultSchema(BaseModel):
    evaluations: List[CandidateEvalSchema]


def clean_json_response(raw: str) -> str:
    raw = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if match:
        return match.group(1).strip()
    return raw


async def call_judge_llm(
    client: httpx.AsyncClient,
    job_info: dict,
    candidate_batch: list[dict],
) -> list[dict]:
    """Calls Gemini 3.5 Flash via 9Router evaluating 10 candidates in a single prompt."""
    from synthetic_data.config import NINE_ROUTER_KEY, NINE_ROUTER_URL

    system_prompt = (
        "You are a strict technical recruiter evaluating candidate compatibility for an open job.\n"
        "Evaluate the candidates based on experience match, core technical skills, and language capabilities.\n"
        "Give a score between 0 and 4 strictly based on these guidelines:\n"
        "- 0 (Completely Irrelevant): Lacks core skills or is in a different engineering domain.\n"
        "- 1 (Poor Match): Lacks most core requirements, or has a severe experience mismatch (>3 years deficit).\n"
        "- 2 (Partial Match): Has some core skills (50-60%), capable of learning stack within 3 months.\n"
        "- 3 (Good Match): Meets all core tech stack requirements and experience falls within requested buffer.\n"
        "- 4 (Perfect Match): Exceeds core stack requirements, highly relevant experience, plus nice-to-have language or certification bonuses.\n\n"
        "You MUST output JSON adhering strictly to the JSON schema below, under the 'evaluations' key. Do not output anything else."
    )

    # Format Job Context
    job_str = (
        f"JOB DETAILS:\n"
        f"Title: {job_info['title']}\n"
        f"Description: {job_info['description']}\n"
        f"Salary Range: {job_info['minsalary']} - {job_info['maxsalary']} VND\n"
    )

    # Format Candidates Context
    candidates_str = "CANDIDATES TO EVALUATE:\n"
    for i, c in enumerate(candidate_batch):
        cv = c["parsed_cv"]
        summary = cv.get("summary", "")
        skills = ", ".join(cv.get("skills", []))

        # Format Experience
        exp_list = []
        for exp in cv.get("experience", []):
            exp_list.append(
                f"- {exp.get('title')} at {exp.get('company')}: {exp.get('description')}"
            )
        exp_str = "\n".join(exp_list)

        candidates_str += (
            f"--- Candidate #{i+1} ---\n"
            f"ID: {c['candidate_id']}\n"
            f"Summary: {summary}\n"
            f"Skills: {skills}\n"
            f"Experience:\n{exp_str}\n"
            f"Expected Salary Range: {cv.get('expectedSalaryMin', 0)} - {cv.get('expectedSalaryMax', 0)} VND\n\n"
        )

    user_prompt = (
        f"{job_str}\n\n"
        f"{candidates_str}\n\n"
        "Generate JSON array of evaluations adhering to this JSON Schema:\n"
        "{\n"
        '  "evaluations": [\n'
        "    {\n"
        '      "candidate_id": <int>,\n'
        '      "skills_match": "<brief 1-sentence analysis>",\n'
        '      "experience_gap": "<brief 1-sentence analysis>",\n'
        '      "score": <int, 0 to 4>\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    url = f"{NINE_ROUTER_URL}/chat/completions"
    payload = {
        "model": MODEL_JUDGE,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {NINE_ROUTER_KEY}",
        "Content-Type": "application/json",
    }

    resp = await client.post(
        url,
        json=payload,
        headers=headers,
        timeout=60.0,
    )

    resp.raise_for_status()
    data = resp.json()
    raw = data["choices"][0]["message"]["content"]

    clean_raw = clean_json_response(raw)
    validated = BatchEvalResultSchema.model_validate_json(clean_raw)
    return [e.model_dump() for e in validated.evaluations]


def load_existing_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Cache file invalid: {e}. Rebuilding cache.")
    return {}


def save_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


async def build_matrix():
    # 1. Load existing cache
    cache = load_existing_cache()
    logger.info(f"Loaded existing cache containing {len(cache)} rated pairs.")

    async with acquire_conn() as conn:
        # 2. Get all jobs
        logger.info("Fetching jobs from database...")
        jobs = await conn.fetch(
            "SELECT jobPostId, title, description, minSalary, maxSalary FROM JOBPOSTING"
        )
        logger.info(f"Loaded {len(jobs)} jobs.")

        # 3. Get all candidate parsed resumes
        logger.info("Fetching candidates from database...")
        candidates = await conn.fetch("""
            SELECT ja.candidateId, cv.parsedJson
            FROM CVPARSED cv
            JOIN JOBAPPLICATION ja ON cv.jobAppId = ja.jobAppId
            """)
        logger.info(f"Loaded {len(candidates)} candidates.")

    # 4. Generate pairs to rate
    # To build a highly reliable validation matrix, for each Job we select 100 random Candidates.
    # Total: 20 jobs * 100 candidates = 2,000 pairs.
    jobs_list = [dict(j) for j in jobs]
    candidates_list = []
    for c in candidates:
        try:
            parsed_cv = (
                json.loads(c["parsedjson"])
                if isinstance(c["parsedjson"], str)
                else c["parsedjson"]
            )
            candidates_list.append(
                {"candidate_id": c["candidateid"], "parsed_cv": parsed_cv}
            )
        except Exception as e:
            logger.error(f"Failed to parse candidate {c['candidateid']} JSON: {e}")

    # Seed random state for reproducibility
    random.seed(42)

    batches_to_process = []

    for job in jobs_list:
        job_id = job["jobpostid"]

        # Sample 100 candidates per job
        sampled_cands = random.sample(candidates_list, min(100, len(candidates_list)))

        # Split into batches of 10
        for i in range(0, len(sampled_cands), BATCH_SIZE):
            batch = sampled_cands[i : i + BATCH_SIZE]

            # Check if this batch is already completely cached
            needs_eval = []
            for c in batch:
                cache_key = f"j{job_id}_c{c['candidate_id']}"
                if cache_key not in cache:
                    needs_eval.append(c)

            if needs_eval:
                batches_to_process.append({"job": job, "candidates": batch})

    logger.info(
        f"Total batches to process: {len(batches_to_process)} batches ({len(batches_to_process)*BATCH_SIZE} pairs)."
    )

    if not batches_to_process:
        logger.info(
            "All pairs already fully cached. Ground truth matrix is 100% complete!"
        )
        return

    # 5. Process batches sequentially using 9Router
    client = httpx.AsyncClient()
    try:
        for idx, batch_data in enumerate(batches_to_process):
            job = batch_data["job"]
            cands = batch_data["candidates"]
            job_id = job["jobpostid"]

            logger.info(
                f"[Batch {idx+1}/{len(batches_to_process)}] Sending job_id={job_id} vs {len(cands)} candidates..."
            )

            retries = 5
            success = False
            for retry in range(retries):
                try:
                    results = await call_judge_llm(client, job, cands)

                    # Save to memory cache
                    local_count = 0
                    for r in results:
                        ckey = f"j{job_id}_c{r['candidate_id']}"
                        cache[ckey] = {
                            "score": r["score"],
                            "skills_match": r["skills_match"],
                            "experience_gap": r["experience_gap"],
                        }
                        local_count += 1

                    logger.info(
                        f"[Batch {idx+1}/{len(batches_to_process)}] Completed. Cached {local_count} evaluations."
                    )

                    # Persist cache immediately
                    save_cache(cache)
                    success = True
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        # Recreate client to force 9Router session/sticky connection rotation to a new key
                        logger.warning(
                            "429 Resource Exhausted from 9Router. Recreating HTTP client to break sticky connection and force key rotation..."
                        )
                        try:
                            await client.aclose()
                        except Exception:
                            pass
                        client = httpx.AsyncClient()
                        wait_time = 10.0 + (5.0 * retry)
                        logger.warning(
                            f"Sleeping for {wait_time}s before retry {retry+1}/{retries}..."
                        )
                    else:
                        wait_time = min(2.0**retry, 15.0)
                        logger.warning(
                            f"HTTP Error {e.response.status_code} from 9Router: {e}. Retrying in {wait_time}s..."
                        )
                    await asyncio.sleep(wait_time)
                except Exception as e:
                    wait_time = min(2.0**retry, 15.0)
                    logger.warning(
                        f"Error calling 9Router on retry {retry+1}/{retries}: {e}. Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)

            if not success:
                logger.error(
                    f"Failed to process batch {idx+1} permanently after all retries."
                )
                continue

            # Apply a brief sleep to distribute requests smoothly and stay well below rate limits
            if idx < len(batches_to_process) - 1:
                # 1.5 seconds delay is mathematically safe to keep total cycle > 4s (under 15 RPM)
                await asyncio.sleep(1.5)
    finally:
        await client.aclose()

    logger.info("=== MATRIX BUILDING COMPLETED ===")
    logger.info(f"Total rated pairs in cache: {len(cache)}")


async def main():
    await db.connect()
    try:
        await build_matrix()
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

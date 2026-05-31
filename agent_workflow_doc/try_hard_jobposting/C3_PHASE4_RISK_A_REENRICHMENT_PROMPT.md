# C3 Phase 4 Prompt — Risk A Old-Candidate Re-enrichment Backfill

You are working in the FANG repository at:

`C:\Users\os\Desktop\cur_prj\Fang`

Your task is narrowly scoped: create and verify an operational script to backfill C3 JobPosting Agent normalized language/province data for the existing local CV dataset. Do not implement frontend, do not remake synthetic data, do not regenerate CVs, do not redesign enrichment, and do not touch unrelated agent/runtime/API code.

## Recommended Model

Use Gemini Flash 3.5 or Claude Sonnet. If model calls are needed, prefer the same 9Router pattern already used by `synthetic_data/`.

## Context to Read First

Read these files before editing:

1. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_OFFICIAL_IMPLEMENTATION_PLAN.md`
2. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_FINAL_INTEGRATION_REVIEW_REPORT.md`
3. `app/services/nmaiex_candidate_enrichment.py`
4. `app/services/nmaiex_mapper_service.py`
5. `scripts/retry_nmaiex_candidate_enrichment.py`
6. `synthetic_data/config.py`
7. `synthetic_data/generator.py`
8. `synthetic_data/run_pipeline.py`

Key known facts:

- C3 already added `CANDIDATELANGUAGE` and province/language normalization inside enrichment.
- Existing old CV rows may already have old enrichment jobs marked successful, so `enqueue_missing_enrichment_jobs()` alone may not backfill them.
- The goal is to populate/update `CANDIDATELANGUAGE` and `"user".provId` for old candidates based on existing `CVPARSED.parsedJson`.
- Ingestion/enrichment remains best-effort. A failed candidate must be logged and skipped; the batch must continue.
- Synthetic data uses 9Router OpenAI-compatible endpoint:
  - `NINE_ROUTER_URL = "http://localhost:20128/v1"`
  - `MODEL_CV_GENERATION = "gemini/gemini-3.1-flash-lite"`
  - `MODEL_JOB_GENERATION = "gemini/gemini-3.5-flash"`
  - `MODEL_QA_VALIDATE = "gemini/gemini-3.5-flash"`

## Database

Use this local DB connection string for all DB operations and verification:

```powershell
$env:DATABASE_URL="postgresql://postgres:hungklv123@localhost:5432/micareer_lite_db"
```

## Deliverables

Create:

1. A backfill script, preferably under `scripts/`, with a clear name such as:
   - `scripts/backfill_c3_candidate_language_province.py`
2. A report under:
   - `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_RISK_A_REENRICHMENT_REPORT.md`

Do not create a migration framework or permanent scheduler unless the existing repo already has one and it is clearly the right place.

## Script Requirements

The script must:

1. Read existing rows from `CVPARSED` and associated candidate/user records.
2. Backfill only the C3 operational gap:
   - normalize/persist candidate languages into `CANDIDATELANGUAGE`
   - normalize/update province into `"user".provId`
3. Prefer the narrowest existing helper path:
   - Prefer reusing `_coerce_enrichment_payload()`, `_normalize_and_persist_languages()`, and `_normalize_and_update_province()` if they are stable enough.
   - If that path is impractical, reuse `enrich_candidate_structured_data()` but document the extra side effects clearly.
4. Avoid regenerating or reparsing CVs.
5. Avoid deleting or modifying unrelated data.
6. Replace `CANDIDATELANGUAGE` rows per candidate only if the existing helper already does that safely, or implement a scoped per-candidate replacement in one transaction.
7. Be resumable and bounded:
   - `--dry-run` default behavior or strongly recommended first mode
   - `--limit`
   - `--batch-size`
   - `--offset` or cursor/resume support
   - `--candidate-id` optional targeted run if cheap to add
   - `--yes` required for actual write mode
8. Produce a machine-readable summary artifact, such as JSON or CSV, containing:
   - total candidates scanned
   - candidates updated
   - candidates skipped
   - language rows inserted/replaced
   - province updates
   - failures with candidate id and reason
9. Continue on per-candidate failures and return non-zero only for setup/connection/backup/systemic failures.
10. Use repo logging style where practical.

## 9Router Requirement

If the script path invokes mapper/model calls, it must use the 9Router-compatible setup learned from `synthetic_data/`, not a different provider path.

Use:

- Base URL: `http://localhost:20128/v1`
- API key: load from existing config/env if available; do not hardcode new secrets.
- Preferred model for this bulk backfill: `gemini/gemini-3.1-flash-lite`

If current mapper helpers do not expose a clean way to select 9Router/model, add the smallest safe script-local adaptation. Do not broadly refactor provider architecture.

## Backup Requirement

Before any write-mode run, the script or documented runbook must create a database backup.

Preferred PowerShell command:

```powershell
New-Item -ItemType Directory -Force -Path backups
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
pg_dump --format=custom --file "backups\micareer_lite_db_before_c3_reenrich_$ts.dump" "$env:DATABASE_URL"
```

If `pg_dump` is unavailable or backup fails, stop. Do not proceed with writes.

## Required Verification Commands

After implementation, run at minimum:

```powershell
.\venv\Scripts\python.exe -m compileall app scripts
.\venv\Scripts\python.exe -m pytest tests/unit -q
```

Then run script dry-run first:

```powershell
$env:DATABASE_URL="postgresql://postgres:hungklv123@localhost:5432/micareer_lite_db"
.\venv\Scripts\python.exe scripts\backfill_c3_candidate_language_province.py --dry-run --limit 20
```

For the actual write run, do not run it unless backup has succeeded:

```powershell
$env:DATABASE_URL="postgresql://postgres:hungklv123@localhost:5432/micareer_lite_db"
.\venv\Scripts\python.exe scripts\backfill_c3_candidate_language_province.py --yes --batch-size 25
```

If you are not explicitly allowed to mutate the local DB in this session, stop after dry-run and report exact write command for the user.

## psql Verification

Use `psql` with the same connection string after dry-run or write-mode as appropriate.

Minimum queries:

```powershell
psql "$env:DATABASE_URL" -c "SELECT count(*) AS cvparsed_count FROM CVPARSED;"
psql "$env:DATABASE_URL" -c "SELECT count(DISTINCT candidateId) AS candidates_with_languages, count(*) AS language_rows FROM CANDIDATELANGUAGE;"
psql "$env:DATABASE_URL" -c "SELECT count(*) AS users_with_province FROM ""user"" WHERE provId IS NOT NULL;"
psql "$env:DATABASE_URL" -c "SELECT count(*) AS language_rows_without_langid FROM CANDIDATELANGUAGE WHERE langId IS NULL;"
psql "$env:DATABASE_URL" -c "SELECT candidateId, langId, rawName, proficiency, rawProficiency, source FROM CANDIDATELANGUAGE ORDER BY candidateLanguageId DESC LIMIT 10;"
```

Also include one query that estimates remaining candidates with parsed CV language entries but no `CANDIDATELANGUAGE` rows, based on the actual `CVPARSED.parsedJson` structure in the database.

## Safety Boundaries

You may modify:

- the new backfill script
- tests directly related to the new script, if useful
- the final report

Do not modify:

- agent runtime/tool behavior
- FastAPI route contracts
- frontend
- synthetic data generation logic, except reading/reusing its 9Router pattern
- database schema, unless you find a hard blocker and explain it first

Do not run destructive commands. Do not use `git reset --hard` or revert unrelated changes.

## Final Report Must Include

1. Exact script path.
2. Whether dry-run was executed and result summary.
3. Whether backup was created, with backup path.
4. Whether actual write-mode was executed.
5. psql verification outputs or summarized counts.
6. Tests/compile commands and results.
7. Remaining risks, especially candidates that failed normalization or need manual review.

## Expected Outcome

After this task, the local old candidate dataset should be ready for C3 JobPosting Agent language/province filtering, with `CANDIDATELANGUAGE` populated and `"user".provId` updated where best-effort normalization succeeds.

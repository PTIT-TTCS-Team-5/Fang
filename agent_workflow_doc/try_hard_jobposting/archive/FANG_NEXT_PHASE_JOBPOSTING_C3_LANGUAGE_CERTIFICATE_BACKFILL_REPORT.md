# FANG C3 — Language Certificate Schema + Synthetic Batch Backfill Report

Date: 2026-05-30  
DB: `micareer_lite_db`  
Scope: normalize language certificates for `CANDIDATELANGUAGE` without re-processing duplicated `CVPARSED` rows.

## Verdict

`DONE`

The expensive per-`CVPARSED` backfill path was replaced with an optimized synthetic-cache path for the generated dataset:

- Keep real parser/enrichment path for correctness smoke tests.
- Use `synthetic_data/output/cvs/batch_*.json` for bulk synthetic backfill.
- Map each cached CV to its unique candidate via `CANDIDATE.cvUrl = synth://pipeline/<batch>/<global_index>`.
- Write normalized language rows and N-N certificate links once per candidate, not once per job application/CVPARSED row.

## Why the Previous Backfill Was Too Expensive

The previous operational script reused the production enrichment helper against `CVPARSED`. This is useful as a correctness test, but inefficient for synthetic data:

- DB has `2001` `CVPARSED` rows.
- Synthetic data has only `500` generated candidate CVs.
- Candidates were applied across multiple job applications, so repeated `CVPARSED` rows often point back to the same candidate.
- Calling mapper/enrichment per `CVPARSED` caused repeated LLM calls for the same candidate data.

The new script processes `100` cached synthetic batch files instead.

## Schema Added

Added normalized language-certificate catalog and N-N link table:

- `LANGUAGECERTIFICATE`
  - `certId`
  - `certCode`
  - `certName`
  - `langId`
  - `description`
- `CANDIDATELANGUAGECERTIFICATE`
  - `candidateLanguageCertId`
  - `candidateLangId`
  - `certId`
  - `rawText`
  - `normalizedScore`
  - `createdAt`

`CANDIDATELANGUAGE.certification` is retained for backward compatibility and simple display.

Seeded certificate catalog rows:

- `IELTS`
- `TOEIC`
- `TOEFL`
- `CAMBRIDGE`
- `JLPT`
- `HSK`
- `TOPIK`
- `DELF`
- `DALF`
- `GOETHE`
- `TESTDAF`

## Production Enrichment Path Updated

`app/services/nmaiex_candidate_enrichment.py` now:

- extracts `ParsedCV.certificates`
- detects certificates from raw language proficiency text, e.g. `IELTS 8.0 | TOEIC 895`, `HSK 6`
- writes certificate links into `CANDIDATELANGUAGECERTIFICATE`
- supports multiple certificates for one `CANDIDATELANGUAGE` row

This means future real ingestion/enrichment runs will populate both language and certificate tables.

## Scripts Added

### 1. Schema Apply

`scripts/apply_c3_language_certificate_schema.py`

Purpose:

- create certificate tables idempotently
- seed certificate catalog idempotently

Executed successfully:

```powershell
$env:DATABASE_URL="postgresql://postgres:hungklv123@localhost:5432/micareer_lite_db"
.\venv\Scripts\python.exe scripts\apply_c3_language_certificate_schema.py
```

Result:

```text
LANGUAGECERTIFICATE rows: 11
```

### 2. Real Parser + Enrichment Smoke

`scripts/smoke_parse_enrich_sample_cv.py`

Purpose:

- parse `sample_2.pdf` with the real `CVParserOrchestrator`
- run real `enrich_candidate_structured_data`
- verify candidate language/province/skill/certificate fields inside a rollback transaction

Executed:

```powershell
$env:DATABASE_URL="postgresql://postgres:hungklv123@localhost:5432/micareer_lite_db"
.\venv\Scripts\python.exe scripts\smoke_parse_enrich_sample_cv.py --pdf sample_2.pdf
```

Result:

- parser selected tier: `tier1:google:gemini-3.1-flash-lite-preview(succeeded)`
- parsed languages:
  - `Tiếng Anh` / `IELTS 8.0 | TOEIC 895`
  - `Tiếng Trung` / `HSK 6`
- enrichment probe:
  - `provId = HANOI`
  - `candidateSkillCount = 12`
  - `candidateRawSkillCount = 18`
  - English certificate links: `IELTS 8.0`, `TOEIC 895`
  - Chinese certificate link: `HSK 6`
- transaction rolled back (`committed=false`)

### 3. Synthetic Batch Backfill

`scripts/backfill_c3_language_certificates_from_synthetic_batches.py`

Purpose:

- process `synthetic_data/output/cvs/batch_*.json`
- map each cached CV to `CANDIDATE.cvUrl`
- write `CANDIDATELANGUAGE`
- write `CANDIDATELANGUAGECERTIFICATE`
- avoid repeated calls over duplicate `CVPARSED` rows

The script supports:

- `--mapper llm`
- `--mapper deterministic`
- `--dry-run`
- `--yes`
- `--batch batch_001`
- `--limit-batches N`
- DB backup before write mode

9Router LLM mapping was tested and initially worked in dry-run, but later hit repeated `429` during write-mode. Because synthetic cached CVs have highly regular language/proficiency text, full backfill was completed with deterministic mapping to avoid further request waste.

## Trial Runs

### LLM Dry-Run

```powershell
.\venv\Scripts\python.exe scripts\backfill_c3_language_certificates_from_synthetic_batches.py --dry-run --limit-batches 1 --mapper llm
```

Result:

```json
{
  "mapper": "llm",
  "dry_run": true,
  "batches_seen": 1,
  "candidates_seen": 5,
  "candidates_written": 5,
  "language_rows_written": 5,
  "certificate_links_written": 1,
  "failures": []
}
```

### LLM Write Attempt

Write mode with LLM mapping created a backup but hit repeated `429` before any DB writes were made for the batch.

Backup:

`backups/micareer_lite_db_before_c3_language_cert_20260530_082354.dump`

### Deterministic Batch Write Trial

```powershell
.\venv\Scripts\python.exe scripts\backfill_c3_language_certificates_from_synthetic_batches.py --yes --batch batch_001 --mapper deterministic --skip-connection-test
```

Result:

```json
{
  "mapper": "deterministic",
  "dry_run": false,
  "backup_path": "backups/micareer_lite_db_before_c3_language_cert_20260530_082641.dump",
  "batches_seen": 1,
  "candidates_seen": 5,
  "candidates_written": 5,
  "language_rows_written": 5,
  "certificate_links_written": 1,
  "failures": []
}
```

Verified sample:

- user `19`
- `rawProficiency = IELTS 7.5`
- `CANDIDATELANGUAGE.certification = IELTS 7.5`
- `CANDIDATELANGUAGECERTIFICATE` link to `IELTS`
- `normalizedScore = 7.5`

## Full Synthetic Backfill Run

Command:

```powershell
$env:DATABASE_URL="postgresql://postgres:hungklv123@localhost:5432/micareer_lite_db"
.\venv\Scripts\python.exe scripts\backfill_c3_language_certificates_from_synthetic_batches.py --yes --mapper deterministic --skip-connection-test
```

Summary:

```json
{
  "mapper": "deterministic",
  "dry_run": false,
  "backup_path": "backups/micareer_lite_db_before_c3_language_cert_20260530_082714.dump",
  "batches_seen": 100,
  "candidates_seen": 500,
  "candidates_written": 500,
  "language_rows_written": 479,
  "certificate_links_written": 126,
  "failures": []
}
```

## DB Verification

```sql
SELECT count(*) AS candidate_count FROM CANDIDATE;
-- 501

SELECT count(*) AS cvparsed_count FROM CVPARSED;
-- 2001

SELECT count(DISTINCT userId) AS candidates_with_languages, count(*) AS language_rows
FROM CANDIDATELANGUAGE;
-- 462 candidates, 479 rows

SELECT count(*) AS cert_links FROM CANDIDATELANGUAGECERTIFICATE;
-- 126

SELECT lc.certCode, count(*) AS n
FROM CANDIDATELANGUAGECERTIFICATE clc
JOIN LANGUAGECERTIFICATE lc ON lc.certId = clc.certId
GROUP BY lc.certCode
ORDER BY n DESC, lc.certCode;
-- IELTS 95
-- TOEIC 24
-- JLPT 7

SELECT count(*) AS language_rows_without_langid
FROM CANDIDATELANGUAGE
WHERE langId IS NULL;
-- 0

SELECT count(*) AS cert_links_without_language
FROM CANDIDATELANGUAGECERTIFICATE clc
LEFT JOIN CANDIDATELANGUAGE cl ON cl.candidateLangId = clc.candidateLangId
WHERE cl.candidateLangId IS NULL;
-- 0

SELECT count(*) AS duplicate_cert_links
FROM (
  SELECT candidateLangId, certId, COALESCE(rawText, '') AS rawText, count(*)
  FROM CANDIDATELANGUAGECERTIFICATE
  GROUP BY candidateLangId, certId, COALESCE(rawText, '')
  HAVING count(*) > 1
) d;
-- 0
```

Synthetic candidates:

```sql
SELECT count(*) AS synthetic_candidates
FROM CANDIDATE
WHERE cvUrl LIKE 'synth://pipeline/%';
-- 500

SELECT count(DISTINCT c.userId) AS synthetic_with_language
FROM CANDIDATE c
JOIN CANDIDATELANGUAGE cl ON cl.userId = c.userId
WHERE c.cvUrl LIKE 'synth://pipeline/%';
-- 462

SELECT count(*) AS synthetic_without_language
FROM CANDIDATE c
LEFT JOIN CANDIDATELANGUAGE cl ON cl.userId = c.userId
WHERE c.cvUrl LIKE 'synth://pipeline/%'
  AND cl.userId IS NULL;
-- 38
```

The 38 synthetic candidates without language rows correspond to cached CVs whose `languages` list is empty, not failed backfill.

## Tests

```powershell
.\venv\Scripts\python.exe -m compileall app scripts
-- OK

.\venv\Scripts\python.exe -m pytest tests\unit\unit_test_nmaiex_candidate_enrichment.py -q
-- 20 passed

.\venv\Scripts\python.exe -m pytest tests\unit -q
-- 77 passed
```

## Notes

- The production parser/enrichment path remains the source of truth and now supports certificate linking.
- The synthetic batch path is an optimized operational shortcut for cached generated data only.
- 9Router batch mapping is implemented and dry-run tested, but deterministic mode is currently the practical default due rate limits.
- No background backfill process is currently required; the full deterministic run already completed.

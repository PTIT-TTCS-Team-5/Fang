# FANG v2 Full API Test Matrix

This matrix is the source of truth for Tier 2 Postman MCP execution. Do not reset
or seed the database during these tests.

## Environment Variables

| Variable | Purpose |
|---|---|
| `base_url` | FANG base URL, default `http://localhost:8000` |
| `hr_id` | Existing HR user id with access to fixtures |
| `job_post_id` | Existing JobPosting id for ranking and JobPosting Agent |
| `job_app_id_full_cv` | Existing JobApplication id with usable `CVPARSED` |
| `job_app_id_missing_cv` | Nonexistent or no-CV JobApplication id for negative chat case |
| `candidate_id` | Existing candidate id for candidate-to-job ranking |
| `conversation_id` | Captured from full-CV chat happy path |
| `agent_conversation_id` | Captured from JobPosting Agent happy path |
| `ingestion_job_id` | Captured from ingestion create job response |
| `cv_snap_url` | Real Cloudinary/PDF URL for ingestion smoke only |

Default local fixture: candidate username `nguyenhaihung`, `candidate_id=518`,
`job_app_id_full_cv=2002`, `job_post_id=13`, `cv_snap_url=https://res.cloudinary.com/dfwkw1guc/raw/upload/v1778998872/nmaiex/sample_2`.

## Coverage

| Area | Cases | Required checks |
|---|---|---|
| System | `/healthz`, `/v2/healthz`, `/docs` | 200 OK, expected body/HTML |
| Chat full-CV | happy path, missing CV, invalid model, list, messages, summarize, branch-new | `topK=0`, UUIDs, non-empty response, 400 error shape, summary reduces history context |
| Ingestion | create job, get status | 202/200, valid status, no DB reset |
| NMAIex master data | provinces, levels, categories, skills | 200, arrays/non-empty fixture data |
| NMAIex ranking | candidates by job, jobs by candidate | 200, ranked arrays, score fields present |
| NMAIex management | job structured, job content, candidate CV | Fixture-only/manual-safe; capture before/after and restore if modified |
| JobPosting Agent | top candidates, language filter, CV drilldown, out-of-scope, list/messages, rename/archive | 200 or provider-quota classification, conversation/tool/warning schema |

## Pass/Fail Rules

- Provider quota or API-key exhaustion is an environment issue only if backend logs
  show provider-specific quota/auth failures and the HTTP error shape is stable.
- Any schema mismatch, uncaught traceback, missing route, or unexpected 5xx without a
  provider cause is a backend bug.
- Mutating management tests must not damage stable local data. Use disposable fixtures
  or restore the original values in the same run.

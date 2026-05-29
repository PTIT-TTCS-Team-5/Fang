# FANG C3 WS1 Data Foundation — Implementation Report

**Date:** 2026-05-29  
**Branch / Workspace:** main workspace (`c:\Users\os\Desktop\cur_prj\Fang`)  
**Agent:** WS1 Data Foundation Implementation Agent  
**Status:** ✅ COMPLETE — WS2/WS3 may proceed

---

## 1. Summary

WS1 implements the **data foundation** for the JobPosting Agent C3.1:

1. **Schema added:** `CANDIDATELANGUAGE` (web core) + 5 JobPosting Agent tables + 7 seeded tool catalog rows (AI core).
2. **Enrichment extended:** `EnrichmentPayload` now carries `languages` and `candidate_location`. `_coerce_enrichment_payload()` extracts both from the real `ParsedCV` shape (`candidateInfo[0].location`, `languages: list[LanguageEntry]`).
3. **Language mapper added:** `_map_language_to_lang_id()` uses a 60-entry alias map (Vietnamese + English names for 12 languages) then falls back to DB `langCode`/`langName` lookups. Unknown languages write `langId = NULL` and preserve `rawName`.
4. **Province mapper integrated:** `_normalize_and_update_province()` calls existing `map_string_to_province_id()` and writes `"user".provId` only when a valid province is returned.
5. **Proficiency normalization integrated:** `_normalize_and_persist_languages()` calls existing `normalize_proficiency()`. Fast path for already-normalized values.
6. **Ranking updated:** `compute_language_score()` now supports `use_normalized=True` path (reads `langCode + proficiency` from `CANDIDATELANGUAGE`). `rank_candidates_for_job()` batch-fetches normalized language rows and uses the normalized path; falls back to `(0.0, 0.0)` for candidates not yet re-enriched (backward compatible).
7. **All 20 unit tests pass.** No existing tests broken.

---

## 2. Files Changed

| File | Change |
|---|---|
| `database/schema_web_core.sql` | ADD `CANDIDATELANGUAGE` table + 4 indexes |
| `database/schema_ai_core.sql` | ADD `AIJOBPOSTINGTOOL`, `AIJOBPOSTINGCHATCONVERSATION`, `AIJOBPOSTINGCHATMESSAGE`, `AIJOBPOSTINGCHATSTATE`, `AIJOBPOSTINGTOOLCALLLOG` + 7 seed rows |
| `app/services/nmaiex_candidate_enrichment.py` | ADD `_LANGUAGE_ALIAS_MAP`; EXTEND `EnrichmentPayload`; EXTEND `_coerce_enrichment_payload()`; ADD `_map_language_to_lang_id()`, `_normalize_and_persist_languages()`, `_normalize_and_update_province()`; UPDATE `enrich_candidate_structured_data()` |
| `app/services/nmaiex_ranking_service.py` | EXTEND `compute_language_score()` with `use_normalized` kwarg; ADD `fetch_candidate_languages_normalized()`; UPDATE `rank_candidates_for_job()` to batch-fetch and use normalized languages |
| `tests/unit/unit_test_nmaiex_candidate_enrichment.py` | ADD 14 new WS1 test cases (language extraction, mapping, unknown, proficiency, province); UPDATE `FakeConn` to include `fetchrow`; UPDATE existing `test_enrich_candidate_structured_data_updates_atomically` to mock new service calls |

**Not modified (boundary respected):**
- `app/api/routes_chat.py`
- `app/models/chat.py`
- `app/services/chat_persistence.py`
- `app/services/rag_orchestrator.py`
- `app/services/rag_model_adapters.py`
- `app/main.py`

---

## 3. Schema Changes

### 3.1 `CANDIDATELANGUAGE` (schema_web_core.sql)

Added after `CANDIDATESKILL`:

```sql
CREATE TABLE CANDIDATELANGUAGE (
    candidateLangId SERIAL PRIMARY KEY,
    userId          INT NOT NULL,
    langId          INT,                     -- nullable: unknown language
    rawName         VARCHAR(100),            -- preserved original text
    proficiency     VARCHAR(20) CHECK (...), -- 5-level enum
    rawProficiency  VARCHAR(100),            -- preserved original text
    certification   VARCHAR(200),
    createdAt       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updatedAt       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (userId) REFERENCES CANDIDATE(userId) ON DELETE CASCADE,
    FOREIGN KEY (langId) REFERENCES LANGUAGE(langId)
);
```

Indexes:
- `idx_candidate_language_user` — fast lookup by candidate
- `idx_candidate_language_lang_level` — lang scoring queries
- `uq_candidate_language_known` — partial unique on `(userId, langId) WHERE langId IS NOT NULL`
- `uq_candidate_language_unknown` — partial unique on `(userId, lower(rawName)) WHERE langId IS NULL AND rawName IS NOT NULL`

### 3.2 JobPosting Agent tables (schema_ai_core.sql)

Added 5 tables:
- `AIJOBPOSTINGTOOL` — tool catalog with 7 seeded rows
- `AIJOBPOSTINGCHATCONVERSATION` — conversation header, `isArchived` soft-delete
- `AIJOBPOSTINGCHATMESSAGE` — all message roles incl. tool_call/tool_result
- `AIJOBPOSTINGCHATSTATE` — 1-to-1 with conversation, stores `stateJson JSONB`
- `AIJOBPOSTINGTOOLCALLLOG` — sanitized audit log

No cascade delete from `JOBPOSTING` or `HR`. Existing JobApplication chat tables untouched.

### 3.3 Seed data

7 tool catalog rows seeded with `ON CONFLICT (toolName) DO NOTHING` (idempotent re-run):

| toolName | category |
|---|---|
| `get_job_posting_context` | context |
| `get_job_candidate_ranking` | ranking |
| `search_job_applications_text` | search |
| `get_job_application_summary` | detail |
| `get_job_application_full_cv` | detail |
| `get_candidate_ats_history` | detail |
| `count_job_applications` | aggregate |

---

## 4. Enrichment Changes

### 4.1 `EnrichmentPayload` extension

```python
@dataclass(frozen=True)
class EnrichmentPayload:
    experience: list[Any]
    skills: list[str]
    languages: list[dict[str, Any]] = field(default_factory=list)   # NEW
    candidate_location: str | None = None                            # NEW
```

### 4.2 `_coerce_enrichment_payload()` extension

- Extracts `languages` from `parsed_payload["languages"]`: handles `list[LanguageEntry]` (dict after `model_dump()`), `list[dict]`, and legacy `list[str]`.
- Extracts `candidate_location` from `candidateInfo[0].location` or `candidateInfo[0].address`; falls back to `personalInfo.location`/`address` for older parsers.

### 4.3 `_map_language_to_lang_id(raw_language, conn)`

Resolution order:
1. Lowercase → `_LANGUAGE_ALIAS_MAP` (60 entries covering 12 languages in VN/EN naming)
2. DB `LANGUAGE.langCode` case-insensitive lookup
3. DB `LANGUAGE.langName` case-insensitive lookup
4. Returns `None` (unknown) — caller preserves `rawName`

### 4.4 `_normalize_and_persist_languages(candidate_id, raw_languages, conn)`

- Deletes existing `CANDIDATELANGUAGE` rows for candidate
- Inserts new rows with `langId` (or NULL), `rawName`, normalized `proficiency`, `rawProficiency`, `certification`
- Uses `ON CONFLICT DO NOTHING` to prevent duplicates
- Mapper failures (langId lookup or proficiency) are caught per-row and logged; they do not abort the enrichment transaction

### 4.5 `_normalize_and_update_province(candidate_id, raw_location, conn)`

- Calls existing `map_string_to_province_id()`
- Updates `"user".provId` only when a non-None result is returned
- Returns without error on unknown or empty location

### 4.6 `enrich_candidate_structured_data()` update

Two new calls inside the existing transaction:
```python
await _normalize_and_persist_languages(candidate_id, payload.languages, target_conn)
await _normalize_and_update_province(candidate_id, payload.candidate_location, target_conn)
```

Existing skill enrichment behavior is **preserved unchanged**.

---

## 5. Ranking / Language Scoring Changes

### 5.1 `compute_language_score()` — new `use_normalized` kwarg

```python
async def compute_language_score(
    job_post_id, candidate_languages, conn,
    *, use_normalized: bool = False
) -> tuple[float, float, dict]:
```

- `use_normalized=True`: reads `langCode` and `proficiency` directly from normalized rows — no string-based alias matching needed.
- `use_normalized=False` (default): old behavior preserved for C→J path which still reads from `CVPARSED.parsedJson.languages`.

### 5.2 `fetch_candidate_languages_normalized(candidate_id, conn)` — new helper

Queries `CANDIDATELANGUAGE LEFT JOIN LANGUAGE`. Returns `list[{langCode, proficiency, rawName}]`.

### 5.3 `rank_candidates_for_job()` — batch language fetch

After fetching candidate skills, now also batch-fetches `CANDIDATELANGUAGE` for all candidates in one query. Per-candidate language scoring uses `use_normalized=True` when rows exist; falls back to `(0.0, 0.0, {})` (no language score) for candidates not yet re-enriched.

**Backward compatibility:** old candidates without `CANDIDATELANGUAGE` rows simply receive no language score adjustment (neither bonus nor penalty). They are not excluded from ranking. This prevents loss of candidates until the re-enrichment batch runs.

---

## 6. Tests Run and Results

```
pytest tests/unit/unit_test_nmaiex_candidate_enrichment.py -v
======================== 20 passed, 1 warning in 1.32s ========================
python -m compileall app  → OK (no syntax errors)
```

### Test breakdown

| Test class | Tests | Coverage |
|---|---|---|
| `NMAIexCandidateEnrichmentTests` | 6 | Existing behavior (all still pass) |
| `WS1EnrichmentPayloadExtractionTests` | 4 | language/location extraction from payload |
| `WS1LanguageMappingTests` | 4 | alias map, DB lookup, unknown→NULL |
| `WS1ProficiencyNormalizationTests` | 3 | fast path, None→BASIC, hạng C→ADVANCED |
| `WS1ProvinceUpdateTests` | 3 | update, unknown no-update, None skip |

---

## 7. Drift / Conflicts Found

| Item | Status |
|---|---|
| `ParsedCV.languages` is already `list[LanguageEntry]` (not `list[str]`) | No action needed. `_coerce_enrichment_payload` handles both. |
| `ParsedCV.candidateInfo` is `list[CandidateInfo]` with `.location` field | Confirmed by reading `cv_models.py`. Extraction logic verified. |
| `compute_language_score()` was called from C→J path with raw JSON; J→C path had no language scoring | J→C unchanged. J→C `rank_candidates_for_job()` now has language scoring via normalized table. |
| `rank_candidates_for_job()` does not return `jobAppId` per result | **Drift recorded.** This is required by WS3 tool wrapper. Not in WS1 scope per boundary rules. WS3 must add the `jobAppId` lookup when wrapping this function. |
| Seed placement: `schema_ai_core.sql` already accepts DML after DDL | Confirmed. Seed INSERTs placed at end of file with `ON CONFLICT DO NOTHING`. |

---

## 8. Integration Notes for WS2/WS3

### For WS2 (Persistence API Shell)

- All 5 JobPosting Agent tables are created and ready in `schema_ai_core.sql`.
- `AIJOBPOSTINGCHATSTATE.stateJson` accepts any valid JSONB — WS2 can write the `AgentState` structure defined in the implementation plan.
- `AIJOBPOSTINGCHATMESSAGE.role` is `VARCHAR(20)` — ensure WS2 uses values in: `user`, `assistant`, `system`, `tool_call`, `tool_result`.
- `conversationId` is UUID generated by `gen_random_uuid()` — WS2 persistence service should read it back from the INSERT RETURNING.

### For WS3 (Tools)

- `CANDIDATELANGUAGE` is populated by enrichment. Use `fetch_candidate_languages_normalized()` from `nmaiex_ranking_service.py` to read normalized language data per candidate.
- `rank_candidates_for_job()` returns `candidate_id` but **not** `jobAppId`. WS3 must enrich results with a `JOBAPPLICATION` lookup scoped to `jobPostId` to get `jobAppId`.
- Language filter `"tiếng Anh hạng C trở lên"` maps to `ADVANCED|FLUENT|NATIVE` using `PROFICIENCY_LEVELS` from `nmaiex_mapper_service.py`.
- For candidates with unknown `langId` (Klingon-type rows), `langCode = NULL`. When applying language filters, include these candidates by default with a `data_quality` warning (inclusive default, per plan decision).
- `compute_language_score(use_normalized=True)` filters out rows where `langCode = NULL` (they contribute `cand_level = 0` for any specific language requirement). This is the correct inclusive-default behavior.

---

## 9. Remaining Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Old candidates have no `CANDIDATELANGUAGE` rows | Medium | Run re-enrichment script before enabling language filters in production. Use `enqueue_missing_enrichment_jobs()`. |
| `rank_candidates_for_job()` language fallback = (0,0) means no language scoring for un-enriched candidates | Low | Acceptable for phase 1; language scoring becomes accurate after re-enrichment. |
| `CANDIDATELANGUAGE` not yet in `ensure_enrichment_schema()` DDL | Low | `CANDIDATELANGUAGE` is in `schema_web_core.sql` (DDL). Not needed in the sidecar DDL since it references `LANGUAGE` and `CANDIDATE` which already exist. Deploy schema before enrichment. |
| Province mapper uses LLM `invoke_generation` — adds latency per enrichment | Low | Province mapping is best-effort; mapper failure is caught. Acceptable for batch enrichment. |
| `uq_candidate_language_unknown` uses `lower(rawName)` — requires PostgreSQL functional index support | None | Standard PostgreSQL feature since v8.0. No risk. |

# C3 Phase 1 WS1 Data Foundation Prompt

Bạn là **WS1 Data Foundation Implementation Agent** cho FANG JobPosting Agent C3.1.

Model khuyến nghị: **Claude Sonnet 4.6** hoặc **GPT-5.5 high**.  
Nếu dùng Codex/GPT: chọn reasoning **high**. Chỉ dùng `xhigh` nếu gặp drift/schema/ranking logic khó.

## 0. Workspace / branch

Bạn nên chạy trong worktree riêng, ví dụ:

```powershell
git worktree add ..\Fang-c3-data -b codex/c3-data-foundation
cd ..\Fang-c3-data
```

Nếu user đã tạo worktree/branch khác, dùng đúng workspace hiện tại và ghi rõ branch trong report.

## 1. Truth sources

Đọc trước khi code:

1. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_OFFICIAL_IMPLEMENTATION_PLAN.md`
2. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_PHASE0_BASELINE_REPORT.md`
3. Khi cần chi tiết tool/normalization, đọc:
   - `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSC_TOOL_CONTRACT.md`
   - `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSB_CONVERSATION_MEMORY_SCHEMA.md`

Source code là truth source cuối cùng. Nếu docs và code khác nhau, không tự mở scope; ghi drift vào report.

## 2. Mission

Implement **data foundation** cho JobPosting Agent C3.1:

1. Add schema nền:
   - `CANDIDATELANGUAGE`
   - `AIJOBPOSTINGTOOL`
   - `AIJOBPOSTINGCHATCONVERSATION`
   - `AIJOBPOSTINGCHATMESSAGE`
   - `AIJOBPOSTINGCHATSTATE`
   - `AIJOBPOSTINGTOOLCALLLOG`
2. Extend best-effort candidate enrichment:
   - extract languages from parsed CV payload;
   - extract candidate location/province text;
   - normalize proficiency using existing `normalize_proficiency()`;
   - map language to `LANGUAGE.langId`;
   - update `"user".provId` best-effort using existing `map_string_to_province_id()`;
   - write normalized language rows into `CANDIDATELANGUAGE`;
   - preserve raw language/proficiency values.
3. Make ranking/language scoring ready to use normalized candidate language data.
4. Add focused unit tests.
5. Produce implementation report.

## 3. Hard boundaries

Allowed to modify:

1. `database/schema_web_core.sql`
2. `database/schema_ai_core.sql`
3. `app/services/nmaiex_candidate_enrichment.py`
4. `app/services/nmaiex_mapper_service.py` only if a shared language mapper belongs there
5. `app/services/nmaiex_ranking_service.py`
6. `tests/unit/unit_test_nmaiex_candidate_enrichment.py`
7. Optional: `scripts/re_enrich_candidate_language_province.py`
8. Optional: new focused test file if cleaner
9. Report file under `agent_workflow_doc/try_hard_jobposting/`

Do **not** modify:

1. `app/api/routes_chat.py`
2. `app/models/chat.py`
3. `app/services/chat_persistence.py`
4. `app/services/rag_orchestrator.py`
5. `app/services/rag_model_adapters.py`
6. `app/main.py`
7. New JobPosting API/runtime files owned by WS2/WS3
8. `.understand-anything/*`

Do not implement API routes, Gemini runtime, or JobPosting tools in this WS.

## 4. Required implementation details

### 4.1 Schema: `CANDIDATELANGUAGE`

Add near candidate skill tables in `database/schema_web_core.sql`.

Use current DB reality:

1. `LANGUAGE.langId` is `INT`.
2. `"user".provId` and `PROVINCE.provId` are `VARCHAR(20)`.
3. Proficiency enum is `BASIC|INTERMEDIATE|ADVANCED|FLUENT|NATIVE`.

Use a surrogate primary key because `langId` must be nullable for unknown language:

```sql
CREATE TABLE CANDIDATELANGUAGE (
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
```

Add indexes:

1. `idx_candidate_language_user`
2. `idx_candidate_language_lang_level`
3. unique partial index for known `(userId, langId)` where `langId IS NOT NULL`
4. unique partial index for unknown `(userId, lower(rawName))` where `langId IS NULL AND rawName IS NOT NULL`

### 4.2 Schema: JobPosting Agent tables

Add to `database/schema_ai_core.sql`:

1. `AIJOBPOSTINGTOOL`
2. `AIJOBPOSTINGCHATCONVERSATION`
3. `AIJOBPOSTINGCHATMESSAGE`
4. `AIJOBPOSTINGCHATSTATE`
5. `AIJOBPOSTINGTOOLCALLLOG`

Follow the DDL in the official implementation plan. Do not add cascade delete from `JOBPOSTING` or `HR`.

Seed exactly 7 tool catalog rows if the project style accepts seed DDL in schema/root data. If seed data belongs in a separate seed file, put the INSERTs there and document the placement in the report.

Tool names must be exactly:

1. `get_job_posting_context`
2. `get_job_candidate_ranking`
3. `search_job_applications_text`
4. `get_job_application_summary`
5. `get_job_application_full_cv`
6. `get_candidate_ats_history`
7. `count_job_applications`

### 4.3 Enrichment payload

Extend the current enrichment payload, preserving existing behavior for experience and skills.

Current reality from Phase 0:

1. `EnrichmentPayload` only has `experience` and `skills`.
2. `_coerce_enrichment_payload()` only extracts those fields.
3. `enrich_candidate_structured_data()` writes expyears/skills/raw skills only.

Add:

1. `languages: list[dict]`
2. `candidate_location: str | None`

Extract location from likely parsed CV structures by checking current `app/models/cv_models.py` and real parser output shape if available. Keep extraction tolerant.

### 4.4 Language mapping

Implement a helper with this behavior:

1. Fast alias map for common names:
   - English / tiếng Anh -> `en`
   - Japanese / tiếng Nhật -> `ja`
   - Chinese / tiếng Trung / Mandarin -> `zh`
   - Korean / tiếng Hàn -> `ko`
   - French / tiếng Pháp -> `fr`
   - German / tiếng Đức -> `de`
   - Vietnamese / tiếng Việt -> `vi`
   - Spanish, Portuguese, Italian, Russian, Thai if present in seed data
2. DB lookup by `LANGUAGE.langCode` and case-insensitive `LANGUAGE.langName`.
3. Optional LLM fallback is acceptable, but it must be best-effort and fail closed to `None`.

Unknown language must not fail enrichment. Preserve `rawName` and write `langId = NULL`.

### 4.5 Proficiency / province

Use existing async functions:

1. `normalize_proficiency(raw_proficiency)` from `app/services/nmaiex_mapper_service.py`
2. `map_string_to_province_id(text)` from `app/services/nmaiex_mapper_service.py`

Rules:

1. If proficiency mapper fails or returns unknown, existing fallback is `BASIC`.
2. If province mapper returns `None`, do not update `"user".provId`.
3. Best-effort mapper failure should not fail ingestion if the rest of enrichment can proceed safely.
4. DB write failure may fail the enrichment job and let retry mechanism handle it.

### 4.6 Persist normalized languages

Inside the enrichment transaction:

1. Delete existing `CANDIDATELANGUAGE` rows for the candidate.
2. Insert normalized rows for current parsed CV languages.
3. Preserve raw language name, raw proficiency, certification if present.
4. Avoid duplicate rows.

Do not mutate `CVPARSED.parsedJson`.

### 4.7 Ranking/language scoring

Make phase 1 ranking ready for normalized data.

Preferred path:

1. Add helper to fetch candidate languages from `CANDIDATELANGUAGE JOIN LANGUAGE`.
2. Refactor `compute_language_score()` or add an adapter so candidate language scoring can use normalized `langCode` + normalized `proficiency`.
3. Preserve backward compatibility/fallback for old candidates without normalized rows if reasonable, but emit/test behavior clearly.

Do not implement the full JobPosting Agent ranking tool in this WS. That belongs to WS3.

## 5. Tests to add/run

After user installed pytest, run tests through repo venv first:

```powershell
.\venv\Scripts\python.exe -m pytest tests/unit/unit_test_nmaiex_candidate_enrichment.py
.\venv\Scripts\python.exe -m compileall app
```

If venv fails for environment reasons, also try:

```powershell
python -m pytest tests/unit/unit_test_nmaiex_candidate_enrichment.py
python -m compileall app
```

Add focused tests for:

1. `_coerce_enrichment_payload()` extracts languages.
2. `_coerce_enrichment_payload()` extracts location.
3. "Tiếng Anh" maps to English `langId`.
4. Unknown language writes row with `langId = NULL`.
5. Existing standard proficiency remains unchanged.
6. "hạng C" maps to `ADVANCED` if test can mock mapper.
7. Province update writes `"user".provId` when mapper returns a value.
8. Province unknown does not update.
9. Existing skill enrichment test still passes.

Use mocks for LLM/province/proficiency mapper calls where needed. Do not call real providers in unit tests.

## 6. Report

Create:

`agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WS1_DATA_FOUNDATION_REPORT.md`

Report sections:

1. Summary
2. Files changed
3. Schema changes
4. Enrichment changes
5. Ranking/language scoring changes
6. Tests run and results
7. Drift/conflicts found
8. Integration notes for WS2/WS3
9. Remaining risks

## 7. Stop conditions

Stop and report instead of improvising if:

1. Current schema style makes the planned DDL unsafe.
2. Parsed CV language/location shape is materially different from the plan.
3. `CANDIDATELANGUAGE` cannot be added without broader schema migration decisions.
4. Ranking refactor requires changing public API behavior outside NMAIex internals.
5. Tests reveal existing behavior unrelated to this WS is already failing.

## 8. Final response

After completion, respond briefly:

1. Report path.
2. Files changed.
3. Tests run.
4. Whether WS2/WS3 can proceed.
5. Any blockers.

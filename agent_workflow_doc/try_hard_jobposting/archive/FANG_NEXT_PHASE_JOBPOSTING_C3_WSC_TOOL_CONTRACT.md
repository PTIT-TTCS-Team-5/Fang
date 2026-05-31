# WS-C — Read-only Tool Contract, Data Scope, and NMAIex Normalization Dependency

**Discovery Report — Input cho Official Implementation Plan**

> **Workstream**: WS-C  
> **Ngày**: 2026-05-28  
> **Trạng thái**: Discovery report — KHÔNG phải implementation plan, KHÔNG phải permission to code.

---

## 1. Executive Summary

WS-C chịu trách nhiệm thiết kế **tool contract cho 7 MVP read-only tools** của JobPosting Agent, **chính sách data scope/leak prevention**, và **phân tích + đề xuất fix NMAIex normalization bug** — bug hiện là blocker cho mọi filter/ranking dựa trên tỉnh, ngôn ngữ, trình độ ngôn ngữ.

**Kết luận chính**:

1. **7 MVP tools** đã được định nghĩa input/output schema chi tiết, tất cả đều scoped theo `jobPostId` (qua FK `JOBAPPLICATION.JOBPOSTID`).
2. **Normalization bug NGHIÊM TRỌNG HƠN DỰ KIẾN**: Enrichment pipeline (`enrich_candidate_structured_data()` trong `nmaiex_candidate_enrichment.py`) **HOÀN TOÀN BỎ QUA `languages` và `location`** — `_coerce_enrichment_payload()` chỉ extract `experience` và `skills`. Languages và location không chỉ thiếu normalize mà **không được extract ra khỏi parsedJson**.
3. **`normalize_proficiency()` và `map_string_to_province_id()` tồn tại** trong `nmaiex_mapper_service.py` nhưng có **zero callers** trong toàn bộ ingestion/enrichment pipeline.
4. **Ranking service đọc raw `parsedJson.languages` trực tiếp** từ `CVPARSED` table. Raw proficiency strings ("N3", "IELTS 7.5") không match `PROFICIENCY_LEVELS` dict (`BASIC|INTERMEDIATE|ADVANCED|FLUENT|NATIVE`) → **tất cả fallback về level 1 (BASIC)** → scoring sai hoàn toàn.
5. **`LANGUAGE` reference table CÓ tồn tại** trong `schema_web_core.sql` với `langId`, `langCode` (ISO 639-1), `langName`. Bảng `JOB_LANG_REQUIREMENT` đã dùng `langId` FK. Fix nên leverage bảng này.
6. **`APPSTATUSHISTORY` table CÓ tồn tại** → Tool 6 (`get_candidate_ats_history`) có data source sẵn.
7. **Fix phải nằm ở enrichment stage** — mở rộng `_coerce_enrichment_payload()` và `enrich_candidate_structured_data()` để extract + normalize languages và location.

---

## 2. Current Data and Tool Reality

### 2.1 Dữ liệu hiện tại — Luồng ingestion (verified từ code)

```
CV Upload (routes_ingestion.py: process_ingestion_task())
    │
    ├─ download_cv(cvSnapUrl) → raw bytes
    ▼
parse_to_raw_and_json() (cv_parser.py → cv_parser_adapters.py)
    │  → LLM extract → ParsedCV (raw strings)
    │  → CV_PARSE_PROMPT explicitly says: "Keep proficiency exactly as stated in CV
    │    (e.g. 'N3', 'IELTS 7.5', 'Fluent', 'B2'). Do NOT normalize"
    ▼
save_parsed_cv(jobAppId, raw_text, json_obj, parser_ver)
    │  → Lưu vào CVPARSED.parsedJson (JSONB, raw data preserved)
    │  → Markdown conversion → chunking → embedding → AIDOCUMENTCHUNK
    ▼
enqueue_and_run_candidate_enrichment()
    │  → run_enrichment_job() loads CVPARSED.parsedJson
    │  → _coerce_enrichment_payload() extracts ONLY:
    │       ✅ experience → compute_exp_years() → UPDATE CANDIDATE.expyears
    │       ✅ skills → _map_skills_best_effort() → CANDIDATESKILL + CANDIDATE_SKILL_RAW
    │       ❌ languages → COMPLETELY IGNORED (not extracted)
    │       ❌ location/province → COMPLETELY IGNORED (not extracted)
    │       ❌ CANDIDATE.provId → NEVER updated from CV data
    ▼
Ranking at query time (nmaiex_ranking_service.py)
    │  → rank_candidates_for_job() or rank_jobs_for_candidate()
    │  → compute_language_score() reads cv.parsedJson → 'languages' DIRECTLY from CVPARSED
    │  → PROFICIENCY_LEVELS = {BASIC:1, INTERMEDIATE:2, ADVANCED:3, FLUENT:4, NATIVE:5}
    │  → Raw proficiency "N3" → PROFICIENCY_LEVELS.get("N3", 1) → 1 (BASIC) ❌ WRONG
    │  → A candidate with JLPT N1 scores same as complete beginner
    ▼
Result: Language scoring and province filtering are BROKEN
```

> **⚠️ QUAN TRỌNG**: Bug nghiêm trọng hơn dự kiến ban đầu. Không chỉ thiếu normalization — enrichment pipeline **hoàn toàn bỏ qua** languages và location. Ranking phải đọc raw data từ `CVPARSED.parsedJson` mỗi lần, không có dữ liệu đã chuẩn hóa ở bất kỳ đâu.

### 2.2 Các bảng DB liên quan (verified từ SQL schema)

| Bảng | PK | Vai trò | Schema file |
|------|-----|---------|-------------|
| `JOBPOSTING` | `jobPostId SERIAL` | Anchor table, có `provId FK→PROVINCE`, `compId FK→COMPANY` | `schema_web_core.sql` |
| `JOBAPPLICATION` | `jobAppId SERIAL` | Link `candidateId`↔`jobPostId`, có `stat`, `cvSnapUrl` | `schema_web_core.sql` |
| `CANDIDATE` | `userId FK→user` | Ứng viên, có `expyears INT` (updated by enrichment) | `schema_web_core.sql` |
| `"user"` | `userId SERIAL` | User table, có `provId FK→PROVINCE` (CHƯA ĐƯỢC UPDATE từ CV) | `schema_web_core.sql` |
| `PROVINCE` | `provId VARCHAR(20)` | Reference 34 tỉnh/thành (post-2025 merger), có `mergedFrom` | `schema_web_core.sql` |
| `LANGUAGE` | `langId SERIAL` | Reference, có `langCode VARCHAR(10)` (ISO 639-1), `langName` | `schema_web_core.sql` |
| `JOB_LANG_REQUIREMENT` | `(jobPostId, langId)` | Yêu cầu ngôn ngữ job, có `reqType`, `minLevel` | `schema_web_core.sql` |
| `APPSTATUSHISTORY` | `histId SERIAL` | Lịch sử status changes, có `jobAppId`, `hrId`, `oldStat`, `newStat`, `changedAt` | `schema_web_core.sql` |
| `CVPARSED` | `cvParsedId SERIAL` | Parsed CV: `rawText TEXT`, `parsedJson JSONB`, `parserVer` | `schema_ai_core.sql` |
| `AIDOCUMENTCHUNK` | `chunkId SERIAL` | Vector chunks: `embedding halfvec(dim)`, HNSW index | `schema_ai_core.sql` |
| `NMAIEX_CANDIDATE_ENRICHMENT_JOB` | `enrichmentJobId SERIAL` | Job tracking: `stat`, `retryCount`, `maxRetryCount=5` | `schema_ai_core.sql` |
| `CANDIDATESKILL` | `(userId, skillId)` | Matched skills (from enrichment Tier 1) | `schema_web_core.sql` |
| `CANDIDATE_SKILL_RAW` | `rawId SERIAL` | Unmatched skills + embeddings (from enrichment Tier 2) | `schema_web_core.sql` |

### 2.3 Các function normalize hiện có (zero callers trong pipeline)

| Function | File | Signature | Trạng thái |
|----------|------|-----------|------------|
| `map_string_to_province_id(text)` | `nmaiex_mapper_service.py` (line ~23) | Fetches 34 provinces, LLM maps, returns `provId` or `"UNKNOWN"` | ✅ Fully implemented, ❌ ZERO callers in ingestion/enrichment |
| `normalize_proficiency(raw_proficiency)` | `nmaiex_mapper_service.py` (line ~228) | LLM-based → `BASIC\|INTERMEDIATE\|ADVANCED\|FLUENT\|NATIVE`, fallback `"BASIC"` | ✅ Fully implemented, ❌ ZERO callers in ingestion/enrichment |
| `map_skills(skills)` | `nmaiex_mapper_service.py` | 2-tier: Tier 1 closed-world LLM → Tier 2 embedding fallback | ✅ Called by enrichment, hoạt động đúng |

> **Note**: `map_language_name()` function **KHÔNG tồn tại** trong `nmaiex_mapper_service.py`. Tuy nhiên bảng `LANGUAGE` CÓ tồn tại với `langCode` (ISO 639-1) và `langName` → có thể map qua DB lookup.

### 2.4 Thực trạng DB schema — Quan sát quan trọng

- **`LANGUAGE` table CÓ tồn tại** (`langId SERIAL`, `langCode VARCHAR(10)` ISO 639-1, `langName VARCHAR(50)`).
- `JOB_LANG_REQUIREMENT` đã dùng `langId FK` + `minLevel CHECK (BASIC/INTERMEDIATE/ADVANCED/FLUENT/NATIVE)`.
- Ranking service `compute_language_score()` đã query `JOB_LANG_REQUIREMENT ↔ LANGUAGE` — mapping candidate language names to ISO codes.
- **Nhưng KHÔNG có bảng `CANDIDATELANGUAGE`** — dữ liệu ngôn ngữ ứng viên chỉ nằm trong `CVPARSED.parsedJson` (raw JSON).
- `PROVINCE.provId` là `VARCHAR(20)`, KHÔNG phải `INT`.
- `APPSTATUSHISTORY` tồn tại với `jobAppId`, `hrId`, `oldStat`, `newStat`, `changedAt` → Tool 6 có data source.

### 2.5 Proficiency Level System — Code reality

Hệ thống proficiency trong FANG sử dụng **5-level enum**, KHÔNG phải CEFR:

```python
# nmaiex_mapper_service.py
PROFICIENCY_LEVELS = {"BASIC": 1, "INTERMEDIATE": 2, "ADVANCED": 3, "FLUENT": 4, "NATIVE": 5}
```

`JOB_LANG_REQUIREMENT.minLevel` cũng dùng `CHECK (BASIC/INTERMEDIATE/ADVANCED/FLUENT/NATIVE)`.

> **Decision needed for tool contract**: Tool filter nên dùng enum `BASIC|INTERMEDIATE|ADVANCED|FLUENT|NATIVE` (match code reality) hay CEFR `A1-C2` (match HR expectation)? Recommendation: **dùng 5-level enum trong tool contract**, agent translate HR input ("hạng C" → `ADVANCED` hoặc `FLUENT`) thông qua system prompt instruction.

### 2.6 Tool calling — hiện tại KHÔNG có

- `invoke_generation()` trong `rag_orchestrator.py` returns `GenerationTrace` (text only) — 5-tier architecture với Google/OpenAI/Anthropic nhưng chỉ text generation.
- `rag_model_adapters.py` có 3 adapter classes (`GeminiGenerationAdapter`, `OpenAIGenerationAdapter`, `AnthropicGenerationAdapter`) — tất cả chỉ text, không tool calling.
- `google.genai` SDK hỗ trợ `FunctionDeclaration` natively, nhưng FANG chưa sử dụng.
- WS-A sẽ thiết kế tool-calling runtime; WS-C chỉ định nghĩa tool declarations/contracts.

### 2.7 Model architecture hiện tại (relevant context)

```
7 model modes:
  ├─ 5 specific: gemini-flash, gpt-mini, claude-haiku, gemini-pro, gpt-full
  └─ 2 auto chains:
       ├─ auto-lite: gemini-flash → gpt-5.4-mini → claude-4.5-haiku
       └─ auto-pro:  gemini-pro → gpt-5.5

Mapper service uses: auto-lite (for province/skill/proficiency mapping)
```

---

## 3. MVP Tool Contract

### 3.1 Tổng quan 7 tools

| # | Tool Name | Scope Key | Mô tả ngắn |
|---|-----------|-----------|-------------|
| 1 | `get_job_posting_context` | `jobPostId` | Lấy thông tin job posting + thống kê tổng quan |
| 2 | `get_job_candidate_ranking` | `jobPostId` | Lấy danh sách ứng viên ranked, có filter |
| 3 | `search_job_applications_text` | `jobPostId` | Full-text search ứng viên trong job posting |
| 4 | `get_job_application_summary` | `jobAppId` (verify scope) | Lấy summary 1 ứng viên |
| 5 | `get_job_application_full_cv` | `jobAppId` (verify scope) | Lấy full CV 1 ứng viên (drill-down) |
| 6 | `get_candidate_ats_history` | `jobAppId` (verify scope) | Lấy lịch sử ATS 1 ứng viên |
| 7 | `count_job_applications` | `jobPostId` | Đếm ứng viên theo filter |

### 3.2 Chi tiết từng tool

---

#### Tool 1: `get_job_posting_context`

**Mục đích**: Cung cấp context về job posting cho agent khi bắt đầu conversation hoặc khi cần hiểu yêu cầu job.

**Input Schema**:
```json
{
  "job_post_id": {
    "type": "integer",
    "required": true,
    "description": "ID của job posting cần lấy context"
  }
}
```

**Output Schema**:
```json
{
  "job_posting": {
    "id": "int",
    "title": "string",
    "description": "string (truncated to 2000 chars)",
    "requirements": "string (truncated to 2000 chars)",
    "province": "string (tên tỉnh canonical)",
    "salary": "string",
    "status": "string",
    "created_at": "datetime",
    "hr_company": "string"
  },
  "statistics": {
    "total_applications": "int",
    "applications_by_status": {
      "pending": "int",
      "reviewed": "int",
      "shortlisted": "int",
      "rejected": "int"
    },
    "avg_ranking_score": "float | null",
    "has_ranking_data": "bool"
  },
  "source": {
    "table": "JOBPOSTING",
    "id": "int"
  }
}
```

**Error cases**:
- `NOT_FOUND`: Job posting không tồn tại.
- `ACCESS_DENIED`: HR user không phải owner của job posting.

**Underlying services**: Truy vấn `JOBPOSTING` table (JOIN `COMPANY`, `PROVINCE`), `JOBAPPLICATION` aggregate queries. Tham khảo `rag_query._fetch_job_posting()` pattern nhưng cần mở rộng cho job-level context.

---

#### Tool 2: `get_job_candidate_ranking`

**Mục đích**: Lấy danh sách ứng viên đã được rank cho job posting, có hỗ trợ limit và filter.

**Input Schema**:
```json
{
  "job_post_id": {
    "type": "integer",
    "required": true,
    "description": "ID của job posting"
  },
  "limit": {
    "type": "integer",
    "required": false,
    "default": 10,
    "min": 1,
    "max": 25,
    "description": "Số ứng viên tối đa trả về (max 25)"
  },
  "filters": {
    "type": "object",
    "required": false,
    "properties": {
      "min_overall_score": {"type": "float", "description": "Điểm tổng tối thiểu (0.0-1.0)"},
      "language": {"type": "string", "description": "Tên ngôn ngữ canonical (e.g., 'English')"},
      "min_language_proficiency": {"type": "string", "enum": ["BASIC","INTERMEDIATE","ADVANCED","FLUENT","NATIVE"], "description": "Trình độ ngôn ngữ tối thiểu (5-level enum)"},
      "province_id": {"type": "integer", "description": "ID tỉnh canonical"},
      "status": {"type": "string", "description": "Trạng thái ứng tuyển (pending/reviewed/shortlisted/rejected)"}
    }
  }
}
```

**Output Schema**:
```json
{
  "candidates": [
    {
      "job_app_id": "int",
      "candidate_id": "int",
      "candidate_name": "string",
      "ranking_position": "int",
      "overall_score": "float",
      "dimension_scores": {
        "skills_match": "float",
        "experience_relevance": "float",
        "education_fit": "float",
        "language_fit": "float",
        "location_fit": "float"
      },
      "summary": {
        "top_skills": ["string"],
        "years_experience": "int | null",
        "education_level": "string | null",
        "languages": [
          {"name": "string (normalized)", "proficiency": "string (CEFR normalized)"}
        ],
        "province": "string (canonical) | null"
      }
    }
  ],
  "total_available": "int",
  "filters_applied": "object | null",
  "warnings": ["string"],
  "source": {
    "service": "nmaiex_ranking_service",
    "ranking_model": "string"
  }
}
```

**Guardrails**:
- `limit` capped tại 25. Nếu HR request > 25 → trả warning và cap.
- Filter `min_language_proficiency` yêu cầu normalized data → **phụ thuộc normalization fix**.
- `province_id` filter yêu cầu normalized province → **phụ thuộc normalization fix**.
- Nếu `total_available` > 25 và không có filter → thêm warning "Tập ứng viên lớn, nên sử dụng filter hoặc giới hạn top N".

**Proficiency ordering cho filter** (match `PROFICIENCY_LEVELS` trong `nmaiex_mapper_service.py`):
```
BASIC(1) < INTERMEDIATE(2) < ADVANCED(3) < FLUENT(4) < NATIVE(5)
```

**Agent translate HR input**:
- "hạng C trở lên" → agent maps to `min_language_proficiency = "ADVANCED"` (hoặc `"FLUENT"` tùy context)
- "sơ cấp" → `"BASIC"`
- "thành thạo" → `"FLUENT"`

Agent dùng system prompt instruction để translate, KHÔNG phải tool contract logic.

**Underlying services**: `nmaiex_ranking_service.rank_candidates_for_job(job_id, limit, province_id, work_mode)`. Hiện tại hàm này KHÔNG hỗ trợ language filter — cần wrapper mới hoặc post-filter trên normalized data.

**Dependency quan trọng**: Tool này **KHÔNG THỂ lọc language/province chính xác** cho đến khi:
1. Enrichment pipeline extract + normalize languages và location.
2. Dữ liệu normalized được lưu ở đâu đó queryable (CANDIDATELANGUAGE table hoặc trong enriched JSON).
3. Ranking service hoặc tool wrapper có khả năng filter trên normalized data.

---

#### Tool 3: `search_job_applications_text`

**Mục đích**: Tìm kiếm ứng viên theo text query trong phạm vi job posting.

**Input Schema**:
```json
{
  "job_post_id": {
    "type": "integer",
    "required": true
  },
  "query": {
    "type": "string",
    "required": true,
    "max_length": 500,
    "description": "Từ khóa tìm kiếm (skills, kinh nghiệm, trường, etc.)"
  },
  "limit": {
    "type": "integer",
    "required": false,
    "default": 10,
    "max": 25
  },
  "filters": {
    "type": "object",
    "required": false,
    "properties": {
      "status": {"type": "string"},
      "province_id": {"type": "integer"},
      "language": {"type": "string"},
      "min_language_proficiency": {"type": "string", "enum": ["BASIC","INTERMEDIATE","ADVANCED","FLUENT","NATIVE"]}
    }
  }
}
```

**Output Schema**:
```json
{
  "results": [
    {
      "job_app_id": "int",
      "candidate_name": "string",
      "relevance_score": "float",
      "matched_snippets": ["string (max 200 chars each, max 3 snippets)"],
      "summary": {
        "top_skills": ["string"],
        "province": "string | null",
        "languages": [{"name": "string", "proficiency": "string"}]
      }
    }
  ],
  "total_matches": "int",
  "query_used": "string",
  "source": {
    "service": "rag_query (vector search)",
    "scope": "JOBAPPLICATION.JOBPOSTID = {job_post_id}"
  }
}
```

**Underlying services**: `rag_query._vector_search(prompt_embedding, job_app_id, top_k)` hiện scoped theo single `jobAppId`. Cần wrapper mới thực hiện:
1. Lấy tất cả `jobAppId` thuộc `jobPostId`.
2. Vector search trên `AIDOCUMENTCHUNK` với filter `jobAppId IN (...)` hoặc cross-application search.
3. Group kết quả theo `jobAppId` → candidate.

Alternatively, dùng PostgreSQL full-text search (`ts_rank`) trên `CVPARSED.rawText` — pattern đã có trong `rank_candidates_for_job()` (VectorRank CTE + full-text rank).

---

#### Tool 4: `get_job_application_summary`

**Mục đích**: Lấy summary của 1 ứng viên cụ thể (không phải full CV).

**Input Schema**:
```json
{
  "job_app_id": {
    "type": "integer",
    "required": true,
    "description": "ID của job application"
  }
}
```

**Output Schema**:
```json
{
  "job_app_id": "int",
  "candidate_name": "string",
  "application_status": "string",
  "applied_at": "datetime",
  "summary": {
    "education_highlights": ["string (max 3)"],
    "experience_highlights": ["string (max 3)"],
    "top_skills": ["string (max 10)"],
    "years_experience": "int | null",
    "languages": [
      {"name": "string (normalized)", "proficiency": "string (CEFR)", "certification": "string | null"}
    ],
    "province": "string (canonical) | null",
    "certifications": ["string (max 5)"]
  },
  "ranking": {
    "position": "int | null",
    "overall_score": "float | null",
    "dimension_scores": "object | null"
  },
  "source": {
    "tables": ["JOBAPPLICATION", "CVPARSED", "CANDIDATESKILL"],
    "job_app_id": "int"
  }
}
```

**Scope verification**: Tool PHẢI verify `JOBAPPLICATION.JOBPOSTID` khớp với `jobPostId` hiện tại của conversation, không cho truy cập application ngoài job.

**Policy summary-first**: Trả về summary đã xử lý, KHÔNG trả full `PARSEDCVJSON`. Full CV chỉ qua tool 5.

**Underlying services**: `rag_query._fetch_candidate_profile(job_app_id)` (candidate info), `CVPARSED.parsedJson` (summary fields from parsed CV), ranking data from `rank_candidates_for_job()` hoặc cached scores.

---

#### Tool 5: `get_job_application_full_cv`

**Mục đích**: Drill-down lấy full CV của 1 ứng viên cụ thể.

**Input Schema**:
```json
{
  "job_app_id": {
    "type": "integer",
    "required": true
  }
}
```

**Output Schema**:
```json
{
  "job_app_id": "int",
  "candidate_name": "string",
  "full_cv": {
    "personal_info": {
      "full_name": "string",
      "email": "string (masked: first 3 chars + ***@domain)",
      "phone": "string (masked: last 4 digits only)",
      "province": "string (canonical) | null",
      "address": "REDACTED"
    },
    "education": ["Education objects"],
    "work_experience": ["WorkExperience objects"],
    "skills": ["string"],
    "languages": [
      {"name": "string (normalized)", "proficiency": "string (CEFR)", "certification": "string | null"}
    ],
    "certifications": ["Certification objects"],
    "summary": "string"
  },
  "warnings": ["Dữ liệu CV chứa thông tin cá nhân. Chỉ sử dụng cho mục đích tuyển dụng."],
  "source": {
    "table": "CVPARSED",
    "job_app_id": "int"
  }
}
```

**Policies**:
- **Single application only**: Tool nhận `jobAppId`, KHÔNG nhận danh sách.
- **PII masking**: Email masked, phone masked, address REDACTED.
- **Scope check**: Verify `JOBAPPLICATION.JOBPOSTID` khớp với conversation scope.
- **No bulk load**: Agent KHÔNG ĐƯỢC gọi tool này trong loop cho nhiều ứng viên. Nếu agent cần so sánh, phải dùng summary (tool 4).

**Underlying services**: Query `CVPARSED.parsedJson` cho `jobAppId` → full `ParsedCV` data. Áp dụng PII masking trước khi trả về. Tham khảo `rag_query._fetch_candidate_profile()` cho candidate base info.

---

#### Tool 6: `get_candidate_ats_history`

**Mục đích**: Lấy lịch sử ATS (Application Tracking System) của ứng viên cho job application.

**Input Schema**:
```json
{
  "job_app_id": {
    "type": "integer",
    "required": true
  }
}
```

**Output Schema**:
```json
{
  "job_app_id": "int",
  "candidate_name": "string",
  "current_status": "string",
  "history": [
    {
      "status": "string",
      "changed_at": "datetime",
      "changed_by": "string (HR name) | null",
      "notes": "string | null"
    }
  ],
  "source": {
    "tables": ["JOBAPPLICATION", "APPSTATUSHISTORY", "INTERVIEW", "INTERVIEWFEEDBACK"],
    "job_app_id": "int"
  }
}
```

**Scope check**: Verify `JOBAPPLICATION.JOBPOSTID` khớp.

**Data sources confirmed**:
- `APPSTATUSHISTORY` table **CÓ tồn tại** trong `schema_web_core.sql` với `jobAppId`, `hrId`, `oldStat`, `newStat`, `changedAt`.
- `INTERVIEW` table có `jobAppId`, `startAt`, `endAt`, `mode`, `linkMeet`, `loc`.
- `INTERVIEWFEEDBACK` table có `intervId FK`, `hrId FK`, `score INT`, `cmt TEXT`.
- `rag_query._fetch_ats_history(job_app_id)` đã tồn tại — query `INTERVIEW ↔ INTERVIEWFEEDBACK` cho interview dates, types, scores, notes.

**Extended output** (ngoài status history): Có thể include interview schedule + feedback summary nếu HR cần.

---

#### Tool 7: `count_job_applications`

**Mục đích**: Đếm ứng viên theo filter, giúp agent kiểm tra kích thước tập dữ liệu trước khi quyết định thao tác.

**Input Schema**:
```json
{
  "job_post_id": {
    "type": "integer",
    "required": true
  },
  "filters": {
    "type": "object",
    "required": false,
    "properties": {
      "status": {"type": "string"},
      "province_id": {"type": "integer"},
      "language": {"type": "string"},
      "min_language_proficiency": {"type": "string", "enum": ["BASIC","INTERMEDIATE","ADVANCED","FLUENT","NATIVE"]},
      "min_overall_score": {"type": "float"}
    }
  }
}
```

**Output Schema**:
```json
{
  "job_post_id": "int",
  "total_count": "int",
  "filtered_count": "int",
  "filters_applied": "object | null",
  "too_large_warning": "bool (true if filtered_count > 25)",
  "source": {
    "tables": ["JOBAPPLICATION", "CVPARSED"],
    "scope": "JOBAPPLICATION.JOBPOSTID = {job_post_id}"
  }
}
```

**Guardrails**: Nếu `filtered_count > 25` → set `too_large_warning = true`. Agent nên sử dụng warning này để tư vấn HR dùng filter hoặc top N.

**Underlying services**: `rag_query.count_job_applications_for_posting()`, mở rộng với filter support.

---

### 3.3 Cross-Tool: Source Metadata Convention

Mọi tool response PHẢI có field `source` để agent có thể cite nguồn dữ liệu:

```json
{
  "source": {
    "table": "string | string[]",
    "id": "int | null",
    "service": "string | null",
    "scope": "string"
  }
}
```

### 3.4 Cross-Tool: Error Response Convention

Mọi tool khi lỗi trả:

```json
{
  "error": {
    "type": "NOT_FOUND | ACCESS_DENIED | TOO_MANY_RESULTS | NORMALIZATION_FAILED | INTERNAL_ERROR",
    "message": "string (human-readable, tiếng Việt)",
    "details": "object | null"
  }
}
```

Agent xử lý error types:
- `NOT_FOUND` → thông báo HR dữ liệu không tồn tại.
- `ACCESS_DENIED` → thông báo HR không có quyền.
- `TOO_MANY_RESULTS` → tư vấn dùng filter/limit.
- `NORMALIZATION_FAILED` → warning rằng filter kết quả có thể không chính xác, fallback về tìm kiếm text.
- `INTERNAL_ERROR` → thông báo lỗi hệ thống, thử lại sau.

---

## 4. Deferred Tools

Các tools sau **KHÔNG nằm trong Phase 1** (read-only):

| Tool | Lý do defer |
|------|-------------|
| `shortlist_candidate(job_app_id)` | Write operation — Phase 2 |
| `reject_candidate(job_app_id, reason)` | Write operation — Phase 2 |
| `update_application_status(job_app_id, status)` | Write operation — Phase 2 |
| `schedule_interview(job_app_id, datetime)` | Write operation + external integration — Phase 3+ |
| `send_candidate_email(job_app_id, template)` | Write + communication — Phase 3+ |
| `export_candidate_report(job_post_id, format)` | Reporting feature — Phase 2+ |
| `compare_candidates(job_app_ids[])` | Complex analysis — Phase 2 (agent có thể tự so sánh bằng summary data trong Phase 1) |
| `cross_job_search(candidate_id)` | Multi-job scope — Phase 3+ |

---

## 5. Data Scope and Leak Prevention

### 5.1 Nguyên tắc scope

**Tất cả tools scoped theo `jobPostId`** thông qua:

```sql
-- Mọi query application data phải JOIN hoặc WHERE
JOBAPPLICATION.JOBPOSTID = :current_job_post_id
```

### 5.2 Scope verification cho tools nhận `jobAppId`

Tools 4, 5, 6 nhận `jobAppId` trực tiếp. PHẢI verify scope:

```python
# Pseudo-code cho scope check
def verify_job_app_scope(job_app_id: int, expected_job_post_id: int, db: Session) -> bool:
    """Verify application thuộc đúng job posting của conversation."""
    result = db.execute(
        "SELECT jobPostId FROM JOBAPPLICATION WHERE jobAppId = :id",
        {"id": job_app_id}
    ).first()
    if not result:
        raise ToolError("NOT_FOUND", f"Job application {job_app_id} không tồn tại")
    if result.jobPostId != expected_job_post_id:
        raise ToolError("ACCESS_DENIED", f"Job application {job_app_id} không thuộc job posting hiện tại")
    return True
```

### 5.3 Những gì KHÔNG ĐƯỢC leak

| Dữ liệu | Policy |
|----------|--------|
| Application ngoài job posting | Scope check chặn |
| Full email/phone | PII masking trong tool 5 |
| Full address | REDACTED trong tool 5 |
| CV file content gốc (binary) | KHÔNG bao giờ trả về |
| Ranking model internals | Chỉ trả scores, không trả model weights |
| Dữ liệu HR/company khác | Không query ngoài scope |

### 5.4 HR ownership verification

Mọi tool call đầu tiên trong conversation PHẢI verify:

```sql
-- JOBPOSTING không có HRID trực tiếp; cần JOIN qua COMPANY
SELECT 1 FROM JOBPOSTING jp
JOIN COMPANY c ON jp.compId = c.compId
JOIN HR h ON h.compId = c.compId
WHERE jp.jobPostId = :job_post_id AND h.userId = :hr_user_id
```

HR chỉ thao tác được job posting thuộc company của mình. Check này nằm ở API layer (WS-D scope) nhưng tool layer cũng PHẢI defensive check.

---

## 6. Full CV and ATS Policies

### 6.1 Full CV Policy — Summary-first

| Rule | Chi tiết |
|------|----------|
| Default response | Luôn dùng `get_job_application_summary` (tool 4) trước |
| Full CV trigger | Chỉ khi HR explicitly yêu cầu xem chi tiết 1 ứng viên cụ thể |
| Bulk prohibition | KHÔNG gọi `get_job_application_full_cv` (tool 5) trong loop |
| Agent behavior | Nếu HR hỏi "xem CV của 5 người" → agent gọi 5x `get_job_application_summary`, KHÔNG gọi 5x `get_job_application_full_cv` |
| Drill-down ok | Nếu HR hỏi "cho tôi xem chi tiết CV của ứng viên Nguyễn Văn A" → 1x `get_job_application_full_cv` là hợp lệ |

### 6.2 ATS History Policy

- `APPSTATUSHISTORY` table **đã tồn tại** — trả lịch sử status changes đầy đủ.
- `INTERVIEW` + `INTERVIEWFEEDBACK` tables cũng có — có thể include interview schedule + scores.
- `rag_query._fetch_ats_history(job_app_id)` đã tồn tại và query `INTERVIEW ↔ INTERVIEWFEEDBACK`.
- KHÔNG trả HR internal notes nếu chứa nội dung sensitive.

---

## 7. Count and Too-large Guardrails

### 7.1 Ngưỡng mặc định

| Param | Giá trị | Cấu hình |
|-------|---------|----------|
| `DEFAULT_TOP_N` | 10 | Env var `AGENT_DEFAULT_TOP_N` |
| `MAX_TOP_N` | 25 | Env var `AGENT_MAX_TOP_N` |
| `TOO_LARGE_THRESHOLD` | 25 | Env var `AGENT_TOO_LARGE_THRESHOLD` |

### 7.2 Agent behavior khi tập quá lớn

**Scenario: HR hỏi "so sánh tất cả ứng viên"**

1. Agent gọi `count_job_applications(job_post_id)` → nhận `total_count`.
2. Nếu `total_count > TOO_LARGE_THRESHOLD`:
   - Agent KHÔNG gọi ranking/search cho toàn bộ.
   - Agent trả response: *"Job posting này có {total_count} ứng viên. Để phân tích hiệu quả, tôi đề xuất: (1) xem top 10 ứng viên rank cao nhất, (2) lọc theo tiêu chí cụ thể (ngôn ngữ, tỉnh, trạng thái), hoặc (3) tìm kiếm theo từ khóa."*
3. Nếu `total_count <= TOO_LARGE_THRESHOLD`: Agent có thể gọi `get_job_candidate_ranking(limit=total_count)` và phân tích.

### 7.3 Working set guardrail

- Working set (lưu bởi WS-B state) tối đa 25 `jobAppId`.
- Nếu agent cố lưu > 25, chỉ giữ top 25 theo ranking score.

---

## 8. Language Filter Semantics

### 8.1 Vấn đề hiện tại

HR hỏi: *"Trong 10 ông này lọc ra tiếng Anh hạng C trở lên"*

Agent cần:
1. Hiểu "tiếng Anh" = map to `langId` qua bảng `LANGUAGE` (ISO code `en`).
2. Hiểu "hạng C trở lên" = proficiency `>= ADVANCED` (trong 5-level enum).
3. Filter working set theo normalized language data.

**Hiện tại KHÔNG THỂ** vì:
- Enrichment **hoàn toàn bỏ qua** `languages` data từ `ParsedCV`.
- Không có bảng `CANDIDATELANGUAGE` — dữ liệu ngôn ngữ ứng viên chỉ nằm trong `CVPARSED.parsedJson` (raw JSON).
- Ranking `compute_language_score()` đọc `parsedJson → 'languages'` trực tiếp — raw proficiency strings ("N3", "IELTS 7.5") fallback về `BASIC` (level 1) trong `PROFICIENCY_LEVELS` dict.

### 8.2 Proficiency Mapping (5-level enum — code reality)

| Input variations | Normalized enum |
|-----------------|-----------------|
| "beginner", "sơ cấp", "elementary", "A1", "A2" | `BASIC` (1) |
| "intermediate", "trung cấp", "B1", "B2", "N3" | `INTERMEDIATE` (2) |
| "advanced", "hạng C", "cao cấp", "C1", "N2" | `ADVANCED` (3) |
| "fluent", "proficient", "thành thạo", "C2", "N1" | `FLUENT` (4) |
| "native", "bản ngữ", "mother tongue" | `NATIVE` (5) |

**Ordinal comparison**: `BASIC(1) < INTERMEDIATE(2) < ADVANCED(3) < FLUENT(4) < NATIVE(5)`

**"Hạng C trở lên"** → agent maps to `min_language_proficiency = "ADVANCED"` → filter: level ≥ 3 → `ADVANCED`, `FLUENT`, `NATIVE`.

> **Note**: `normalize_proficiency()` trong `nmaiex_mapper_service.py` dùng LLM để map các input variations về 5-level enum. Fallback là `"BASIC"` khi LLM fail.

### 8.3 Language Name Resolution (đề xuất)

Bảng `LANGUAGE` **CÓ tồn tại** trong DB với `langId`, `langCode` (ISO 639-1), `langName`:

**Strategy**: Tạo `map_language_to_lang_id(raw_language, conn)` function:
1. **DB lookup**: Query `LANGUAGE` table bằng `langName` (exact match, case-insensitive).
2. **Hardcoded alias map** cho Vietnamese variations:

```python
LANGUAGE_ALIAS_MAP = {
    # Vietnamese name → langCode (ISO 639-1)
    "tiếng anh": "en", "anh": "en", "english": "en", "eng": "en",
    "tiếng nhật": "ja", "nhật": "ja", "japanese": "ja",
    "tiếng trung": "zh", "trung": "zh", "chinese": "zh", "mandarin": "zh",
    "tiếng hàn": "ko", "hàn": "ko", "korean": "ko",
    "tiếng pháp": "fr", "pháp": "fr", "french": "fr",
    "tiếng đức": "de", "đức": "de", "german": "de",
    "tiếng việt": "vi", "vietnamese": "vi",
    "tiếng tây ban nha": "es", "spanish": "es",
    "tiếng bồ đào nha": "pt", "portuguese": "pt",
    "tiếng ý": "it", "italian": "it",
    "tiếng nga": "ru", "russian": "ru",
    "tiếng thái": "th", "thai": "th",
}
```

3. **Fallback**: alias map → `langCode` → query `LANGUAGE` table by `langCode` → get `langId`.
4. **LLM fallback**: Nếu không match → LLM extract ISO code → lookup.
5. **Final fallback**: `None` + log warning.

**Ưu điểm so với canonical list trong code**: Leverage bảng `LANGUAGE` sẵn có + `langId` FK cho future `CANDIDATELANGUAGE` table.

### 8.4 Khi nào filter hoạt động

| Condition | Filter chính xác? |
|-----------|-------------------|
| Normalization fix deployed + re-enrich done | ✅ Yes |
| Fix deployed, chưa re-enrich dữ liệu cũ | ⚠️ Chỉ chính xác cho CV mới |
| Chưa fix | ❌ No — mọi non-standard proficiency fallback về BASIC |

**Recommendation**: Sau khi fix normalization trong enrichment, cần **batch re-enrich** toàn bộ ứng viên hiện có. `routes_ingestion.py` đã có `enqueue_missing_enrichment_jobs(limit)` có thể leverage.

---

## 9. NMAIex Normalization Bug Analysis

### 9.1 Root Cause — Confirmed (verified từ code line-by-line)

**File chính**: `app/services/nmaiex_candidate_enrichment.py` (444 lines)

**Bug 1 — `_coerce_enrichment_payload()` HOÀN TOÀN BỎ QUA languages và location** (line ~341-357):
- Function chỉ extract `experience` và `skills` từ `parsedJson`.
- `languages` field bị **completely ignored** — không trích xuất, không xử lý.
- `candidateInfo[].location` bị **completely ignored** — không trích xuất.
- Không có `process_location()` hay `process_languages()` function tồn tại trong file.

**Bug 2 — `enrich_candidate_structured_data()` chỉ xử lý exp + skills**:
- `compute_exp_years(experience)` → UPDATE `CANDIDATE.expyears` ✅
- `_map_skills_best_effort(skills)` → INSERT `CANDIDATESKILL` + `CANDIDATE_SKILL_RAW` ✅
- Languages → NOTHING ❌
- Location/Province → NOTHING ❌ (không UPDATE `user.provId` hay `CANDIDATE` province)

**Bug 3 — Ranking reads raw data trực tiếp** (line ~556 trong `nmaiex_ranking_service.py`):
- `compute_language_score()` reads `cv.parsedJson → 'languages'` trực tiếp từ `CVPARSED`.
- `PROFICIENCY_LEVELS = {"BASIC": 1, "INTERMEDIATE": 2, "ADVANCED": 3, "FLUENT": 4, "NATIVE": 5}`
- Raw proficiency "N3" → `PROFICIENCY_LEVELS.get("N3", 1)` → 1 (BASIC) → **SAI HOÀN TOÀN**.
- Candidate có JLPT N1 (nên là FLUENT=4) bị scoring ngang beginner.

**Bug 4 — `map_language_name()` function KHÔNG tồn tại**:
- Chỉ có `map_string_to_province_id()`, `normalize_proficiency()`, `map_skills()` trong mapper service.
- Cần tạo mới `map_language_to_lang_id()` hoặc `map_language_name()` để normalize tên ngôn ngữ.

### 9.2 Impact Chain (updated — more severe than initially reported)

```
Bug location: nmaiex_candidate_enrichment.py → _coerce_enrichment_payload()
    │ languages + location HOÀN TOÀN BỊ BỎ QUA (not just unnormalized)
    ↓
No candidate-level language table populated
    │ CVPARSED.parsedJson is the ONLY source of language/location data
    ↓
nmaiex_ranking_service.py → compute_language_score()
    │ Reads raw parsedJson → languages → proficiency
    │ PROFICIENCY_LEVELS.get(raw_string, 1) → fallback 1 for all non-standard strings
    ↓
Language scoring: ALL candidates with non-standard proficiency strings → BASIC (level 1)
    │ "N3" → 1, "IELTS 7.5" → 1, "B2" → 1, "Fluent" → 1 (unless exact match "FLUENT")
    ↓  
rank_candidates_for_job() → language component of score unreliable
    ↓
User.provId NEVER updated from CV → province filtering on candidate side BROKEN
    ↓
JobPosting Agent tools: language filter + province filter → KẾT QUẢ SAI
    ↓
HR "lọc tiếng Anh hạng C trở lên" → agent CANNOT produce correct results
```

### 9.3 Dữ liệu hiện tại vs. Dữ liệu cần

**Hiện tại** (trong `CVPARSED.parsedJson`):
```json
{
  "languages": [
    {"language": "English", "proficiency": "N3"},
    {"language": "tiếng Nhật", "proficiency": "IELTS 7.5"}
  ],
  "candidateInfo": [{"location": "Hồ Chí Minh"}]
}
```
→ Không có candidate-level normalized data ở bất kỳ đâu.

**Cần** (sau fix — trong enriched candidate data hoặc new `CANDIDATELANGUAGE` table):

**Option A — Enrich into JSON + update user.provId:**
```
CANDIDATE.expyears = computed ✅ (đã có)
user.provId = mapped via map_string_to_province_id() ← THÊM MỚI
Enriched language data stored somewhere queryable ← THÊM MỚI
```

**Option B — Tạo `CANDIDATELANGUAGE` table (recommended):**
```sql
CREATE TABLE CANDIDATELANGUAGE (
    candLangId SERIAL PRIMARY KEY,
    userId INT NOT NULL REFERENCES "user"(userId),
    langId INT REFERENCES LANGUAGE(langId),  -- NULL if unmapped
    rawName VARCHAR(100),                     -- preserved raw
    proficiency VARCHAR(20) CHECK (proficiency IN ('BASIC','INTERMEDIATE','ADVANCED','FLUENT','NATIVE')),
    rawProficiency VARCHAR(100),              -- preserved raw
    certification VARCHAR(200),               -- e.g., "IELTS 7.5"
    cvParsedId INT REFERENCES CVPARSED(cvParsedId),
    enrichedAt TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_cand_lang_user ON CANDIDATELANGUAGE(userId);
CREATE INDEX idx_cand_lang_lang ON CANDIDATELANGUAGE(langId);
```

> **Recommendation**: Option B — tạo `CANDIDATELANGUAGE` table. Pattern tương tự `CANDIDATESKILL` (đã tồn tại). Cho phép SQL-level filter hiệu quả, JOIN với `JOB_LANG_REQUIREMENT`, và consistent với data model hiện tại.

---

## 10. Normalization Fix Input for Official Implementation Plan

### 10.1 Quyết định stage normalize

**Recommended**: Normalize trong **enrichment stage** (`nmaiex_candidate_enrichment.py`), KHÔNG phải trong parser.

**Lý do**:
- `ParsedCV` nên giữ raw data gốc (source of truth từ LLM). `CV_PARSE_PROMPT` explicitly says "Do NOT normalize" — đây là design intent.
- `CVPARSED.parsedJson` lưu raw data — không nên modify.
- Enrichment service đã có DB connection (`conn`), thuận tiện gọi mapper functions.
- Pattern đã có tiền lệ: `_map_skills_best_effort()` normalize skills trong enrichment.
- Nếu normalize trong parser (`cv_parser.py`), sẽ mix trách nhiệm parse vs. normalize.

### 10.2 Scope mở rộng cho `_coerce_enrichment_payload()` và `enrich_candidate_structured_data()`

Hiện tại `_coerce_enrichment_payload()` chỉ extract `experience` và `skills`. Cần mở rộng:

```python
# TRƯỚC (hiện tại — line ~341-357)
def _coerce_enrichment_payload(parsed_payload: dict) -> EnrichmentPayload:
    # Chỉ extract experience + skills
    experience = parsed_payload.get("experience", [])
    skills = parsed_payload.get("skills", [])
    return EnrichmentPayload(experience=experience, skills=skills)

# SAU (proposed — mở rộng dataclass + extraction)
@dataclass
class EnrichmentPayload:
    experience: list[Any]
    skills: list[str]
    languages: list[dict]           # THÊM MỚI
    candidate_location: str | None  # THÊM MỚI

def _coerce_enrichment_payload(parsed_payload: dict) -> EnrichmentPayload:
    experience = parsed_payload.get("experience", [])
    skills = parsed_payload.get("skills", [])
    
    # THÊM MỚI: Extract languages
    languages = parsed_payload.get("languages", [])
    
    # THÊM MỚI: Extract location from candidateInfo
    candidate_info = parsed_payload.get("candidateInfo", [{}])
    location = candidate_info[0].get("location") if candidate_info else None
    
    return EnrichmentPayload(
        experience=experience,
        skills=skills,
        languages=languages,
        candidate_location=location
    )
```

### 10.3 Thêm logic trong `enrich_candidate_structured_data()`

```python
# Trong enrich_candidate_structured_data() — SAU skills processing, THÊM:

# --- LANGUAGE NORMALIZATION (THÊM MỚI) ---
if payload.languages:
    _normalize_and_persist_languages(
        candidate_id, payload.languages, conn
    )

# --- PROVINCE NORMALIZATION (THÊM MỚI) ---
if payload.candidate_location:
    _normalize_and_update_province(
        candidate_id, payload.candidate_location, conn
    )
```

### 10.4 Proposed new functions

```python
# Trong nmaiex_candidate_enrichment.py

def _normalize_and_persist_languages(
    candidate_id: int,
    raw_languages: list[dict],
    conn
) -> None:
    """Normalize và persist languages vào CANDIDATELANGUAGE table.
    
    Pattern tương tự _map_skills_best_effort() → CANDIDATESKILL.
    """
    from app.services.nmaiex_mapper_service import normalize_proficiency
    
    # Clear existing records for this candidate
    conn.execute(
        "DELETE FROM CANDIDATELANGUAGE WHERE userId = $1",
        [candidate_id]
    )
    
    for lang_entry in raw_languages:
        raw_name = lang_entry.get("language", "")  # Note: ParsedCV uses "language" not "name"
        raw_prof = lang_entry.get("proficiency", "")
        certification = lang_entry.get("certification")
        
        # Normalize proficiency via existing function
        norm_prof = normalize_proficiency(raw_prof) if raw_prof else None
        
        # Map language name to langId via LANGUAGE table
        lang_id = _map_language_to_lang_id(raw_name, conn)
        
        conn.execute(
            """INSERT INTO CANDIDATELANGUAGE
               (userId, langId, rawName, proficiency, rawProficiency, certification)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            [candidate_id, lang_id, raw_name, norm_prof, raw_prof, certification]
        )


def _normalize_and_update_province(
    candidate_id: int,
    raw_location: str,
    conn
) -> None:
    """Map location string → provId và UPDATE user.provId."""
    from app.services.nmaiex_mapper_service import map_string_to_province_id
    
    prov_id = map_string_to_province_id(raw_location)
    if prov_id and prov_id != "UNKNOWN":
        conn.execute(
            "UPDATE \"user\" SET provId = $1 WHERE userId = $2",
            [prov_id, candidate_id]
        )
```

### 10.5 Function mới cần tạo: `_map_language_to_lang_id()`

```python
# Trong nmaiex_candidate_enrichment.py hoặc nmaiex_mapper_service.py

LANGUAGE_ALIAS_MAP = {
    "tiếng anh": "en", "anh": "en", "english": "en", "eng": "en",
    "tiếng nhật": "ja", "nhật": "ja", "japanese": "ja",
    "tiếng trung": "zh", "trung": "zh", "chinese": "zh", "mandarin": "zh",
    "tiếng hàn": "ko", "hàn": "ko", "korean": "ko",
    "tiếng pháp": "fr", "pháp": "fr", "french": "fr",
    "tiếng đức": "de", "đức": "de", "german": "de",
    "tiếng việt": "vi", "vietnamese": "vi",
    "tiếng tây ban nha": "es", "spanish": "es",
    "tiếng bồ đào nha": "pt", "portuguese": "pt",
    "tiếng ý": "it", "italian": "it",
    "tiếng nga": "ru", "russian": "ru",
    "tiếng thái": "th", "thai": "th",
}

def _map_language_to_lang_id(raw_language: str, conn) -> int | None:
    """Map raw language name → langId via LANGUAGE table.
    
    Strategy: alias map → langCode → DB lookup.
    """
    if not raw_language:
        return None
    
    normalized = raw_language.strip().lower()
    
    # Step 1: Alias map to ISO code
    lang_code = LANGUAGE_ALIAS_MAP.get(normalized)
    
    if not lang_code:
        # Step 2: Try direct DB lookup by langName
        row = conn.execute(
            "SELECT langId FROM LANGUAGE WHERE LOWER(langName) = $1",
            [normalized]
        ).fetchone()
        if row:
            return row[0]
        
        # Step 3: LLM fallback
        try:
            from app.services.rag_orchestrator import invoke_generation
            result = invoke_generation(
                [{"role": "user", "content": 
                  f"Map this language name to its ISO 639-1 code (2 letters). "
                  f"Return ONLY the code, nothing else. Input: '{raw_language}'"}],
                "auto-lite"
            )
            lang_code = result.response.strip().lower()[:2]
        except Exception:
            return None
    
    if lang_code:
        row = conn.execute(
            "SELECT langId FROM LANGUAGE WHERE langCode = $1",
            [lang_code]
        ).fetchone()
        if row:
            return row[0]
    
    return None
```

### 10.4 (removed — merged into 10.2/10.3 above)

> Note: Section 10.2 đã mô tả signature changes cần thiết cho `_coerce_enrichment_payload()` và `enrich_candidate_structured_data()`.

### 10.6 Batch re-enrichment cho dữ liệu cũ

Sau khi fix code:
1. Cần re-run enrichment cho tất cả candidates có `CVPARSED` records.
2. `nmaiex_candidate_enrichment.py` đã có `enqueue_missing_enrichment_jobs(limit)` — có thể leverage.
3. Re-enrichment chỉ chạy lại phần language + province mới thêm, KHÔNG cần re-parse CV.
4. Cần endpoint admin hoặc management command: `POST /api/ingestion/re-enrich-languages`.

### 10.7 Fallback behavior khi mapper fail

| Scenario | Fallback | Hành vi |
|----------|----------|---------|
| `map_string_to_province_id()` fail (LLM error) | `provId` not updated | `user.provId` giữ nguyên (NULL hoặc giá trị cũ), log warning |
| `normalize_proficiency()` fail | fallback `"BASIC"` | `normalize_proficiency()` đã có fallback `"BASIC"` built-in (code reality) |
| `_map_language_to_lang_id()` fail | `langId = None` | `CANDIDATELANGUAGE.langId` = NULL, raw name preserved, log warning |
| DB connection error trong mapper | Raise exception | Enrichment fail, retry later |

**Quan trọng**: Khi `normalized_*` = `None`, tool filter PHẢI quyết định:
- **Inclusive** (default recommended): Include candidates có `None` normalized value trong kết quả filter + warning "*Một số ứng viên có dữ liệu ngôn ngữ/tỉnh chưa được chuẩn hóa*".
- **Exclusive**: Loại bỏ candidates có `None` — chỉ dùng nếu HR explicitly yêu cầu strict filter.

---

## 11. Tests Required

### 11.1 Unit tests cho normalization fix

| Test | File | Mô tả |
|------|------|-------|
| `test_normalize_province_updates_user_provid` | `unit_test_nmaiex_candidate_enrichment.py` | Input location "HCM" → `user.provId` updated |
| `test_normalize_province_unknown` | `unit_test_nmaiex_candidate_enrichment.py` | Input "XYZ" → `user.provId` NOT updated, log warning |
| `test_normalize_province_empty` | `unit_test_nmaiex_candidate_enrichment.py` | Input "" → `user.provId` unchanged |
| `test_persist_languages_normalizes_proficiency` | `unit_test_nmaiex_candidate_enrichment.py` | Input "Intermediate" → `CANDIDATELANGUAGE.proficiency = "INTERMEDIATE"` |
| `test_persist_languages_maps_lang_id` | `unit_test_nmaiex_candidate_enrichment.py` | Input "Tiếng Anh" → `CANDIDATELANGUAGE.langId` = english langId |
| `test_persist_languages_already_standard` | `unit_test_nmaiex_candidate_enrichment.py` | Input "FLUENT" → `proficiency = "FLUENT"` |
| `test_persist_languages_jlpt_n3` | `unit_test_nmaiex_candidate_enrichment.py` | Input "N3" → `proficiency = "INTERMEDIATE"` (via LLM) |
| `test_persist_languages_unknown_proficiency` | `unit_test_nmaiex_candidate_enrichment.py` | Input "gibberish" → `proficiency = "BASIC"` (fallback) |
| `test_persist_languages_empty_list` | `unit_test_nmaiex_candidate_enrichment.py` | Input `[]` → no `CANDIDATELANGUAGE` records created |
| `test_coerce_enrichment_payload_extracts_languages` | `unit_test_nmaiex_candidate_enrichment.py` | parsedJson with languages → `payload.languages` populated |
| `test_coerce_enrichment_payload_extracts_location` | `unit_test_nmaiex_candidate_enrichment.py` | parsedJson with candidateInfo → `payload.candidate_location` populated |
| `test_map_language_to_lang_id_alias` | `unit_test_nmaiex_candidate_enrichment.py` | "tiếng nhật" → langId for Japanese |
| `test_map_language_to_lang_id_unknown` | `unit_test_nmaiex_candidate_enrichment.py` | "Klingon" → None |
| `test_normalize_proficiency_hang_c` | existing test file | "hạng C" → "ADVANCED" (via LLM) |

### 11.2 Integration tests

| Test | Mô tả |
|------|-------|
| `test_full_ingestion_produces_candidatelanguage` | Upload CV → parse → enrich → verify `CANDIDATELANGUAGE` records created with `langId` + normalized `proficiency` |
| `test_full_ingestion_updates_user_provid` | Upload CV → parse → enrich → verify `user.provId` updated |
| `test_ranking_uses_normalized_proficiency` | Enrich 3 candidates (BASIC, INTERMEDIATE, FLUENT) → ranking language scores differ correctly |
| `test_ranking_filter_by_province` | Enrich 3 candidates (HCM, HN, ĐN) → filter `provId` HCM → chỉ trả 1 |
| `test_re_enrich_updates_candidatelanguage` | Có record cũ (no language records) → re-enrich → verify `CANDIDATELANGUAGE` populated |

### 11.3 Tool contract tests (sau khi implement)

| Test | Mô tả |
|------|-------|
| `test_get_job_candidate_ranking_respects_limit` | Request limit=5 → trả max 5 |
| `test_get_job_candidate_ranking_caps_at_25` | Request limit=100 → capped tại 25 + warning |
| `test_get_job_candidate_ranking_filter_language` | Filter "English" + "ADVANCED" → chỉ trả matching candidates |
| `test_get_job_application_full_cv_pii_masking` | Full CV response có email/phone masked |
| `test_tool_scope_check_blocks_wrong_job` | Call tool với jobAppId thuộc job khác → ACCESS_DENIED |
| `test_count_too_large_warning` | Count > 25 → `too_large_warning = true` |

---

## 12. Impact on Other Workstreams

### 12.1 Impact on WS-A (Agent Runtime)

| Aspect | Impact |
|--------|--------|
| Tool declarations | WS-C cung cấp 7 `FunctionDeclaration` schemas cho WS-A đăng ký với agent runtime |
| Error handling | WS-A agent loop phải handle structured tool errors từ WS-C error convention |
| Max steps | 7 tools × possible chaining → WS-A nên set max 5-8 tool calls per turn |
| Model requirement | Agent model phải translate HR input ("hạng C") → 5-level enum ("ADVANCED") trong tool calls |

### 12.2 Impact on WS-B (Conversation & Memory)

| Aspect | Impact |
|--------|--------|
| Working set | WS-B state JSON phải lưu `current_working_set: List[int]` (max 25 jobAppIds) do tool 2 trả về |
| Tool call log | WS-B phải log tool name, input, output size (KHÔNG log full output — có thể chứa PII) |
| State update | Sau mỗi `get_job_candidate_ranking` call, WS-B phải update working set |

### 12.3 Impact on WS-D (API & UI)

| Aspect | Impact |
|--------|--------|
| Tool visibility | UI cần hiển thị tools used, source IDs, warnings từ tool responses |
| Error display | UI cần map error types sang user-friendly messages |
| Too-large warning | UI cần hiển thị agent suggestion khi tập quá lớn |
| Filter UI | UI có thể cần filter controls matching tool filter schema (future) |

### 12.4 Dependency trên P1-A/P1-B (Full-CV Chat)

- Full-CV Chat hiện dùng `rag_query` pipeline + `CVPARSED.parsedJson` — dữ liệu raw.
- Normalization fix KHÔNG ảnh hưởng `CVPARSED` (raw preserved).
- Full-CV Chat có thể benefít từ `CANDIDATELANGUAGE` table cho display, nhưng không bắt buộc.

### 12.5 Impact of new `CANDIDATELANGUAGE` table

| Aspect | Impact |
|--------|--------|
| Schema migration | Cần CREATE TABLE + indexes trước khi deploy enrichment fix |
| Ranking service | `compute_language_score()` có thể query `CANDIDATELANGUAGE` thay vì raw `parsedJson` (improvement nhưng không bắt buộc Phase 1) |
| Tool queries | Language filter tools query `CANDIDATELANGUAGE JOIN LANGUAGE` trực tiếp |
| Data consistency | Pattern tương tự `CANDIDATESKILL` — consistent với data model |

---

## 13. Open Questions for Synthesis

| # | Question | Owner | Impact | Status |
|---|----------|-------|--------|--------|
| 1 | ~~`map_language_name()` tồn tại chưa?~~ | WS-C | — | ✅ RESOLVED: KHÔNG tồn tại. Cần tạo `_map_language_to_lang_id()` (Section 10.5) |
| 2 | ~~Có bảng `LANGUAGE` trong DB không?~~ | WS-C | — | ✅ RESOLVED: CÓ tồn tại với `langId`, `langCode`, `langName` |
| 3 | Khi filter language mà `langId = None`, policy mặc định là inclusive hay exclusive? | Synthesis + product | UX: miss candidates vs. false positives | ⏳ OPEN |
| 4 | ~~ATS history table tồn tại không?~~ | WS-C | — | ✅ RESOLVED: `APPSTATUSHISTORY` + `INTERVIEW` + `INTERVIEWFEEDBACK` đều tồn tại |
| 5 | Batch re-enrichment: reuse `enqueue_missing_enrichment_jobs()` hay tạo endpoint riêng cho language/province only? | Synthesis decision | Deployment strategy | ⏳ OPEN |
| 6 | Có nên tạo `CANDIDATELANGUAGE` table hay lưu normalized language vào JSON column? | Synthesis decision | Schema migration + query efficiency | ⏳ OPEN (recommendation: CANDIDATELANGUAGE table) |
| 7 | Text search tool (tool 3) dùng vector search (AIDOCUMENTCHUNK) hay full-text (ts_rank trên CVPARSED.rawText)? | WS-C → WS-A | Performance vs. accuracy | ⏳ OPEN |
| 8 | Tool output size limit là bao nhiêu tokens? Agent context window budget? | WS-A → WS-C | Output truncation strategy | ⏳ OPEN |
| 9 | `rank_candidates_for_job()` trả `jobAppId` trong output không? Nếu không, tool 2 cần wrapper. | WS-C verify | Tool 2 implementation | ⏳ OPEN |
| 10 | `compute_language_score()` nên được refactor để query `CANDIDATELANGUAGE` (nếu tạo) thay vì raw `parsedJson`? Phase 1 hay defer? | Synthesis | Ranking accuracy improvement | ⏳ OPEN |

---

## 14. Acceptance Criteria

### 14.1 Normalization fix

- [ ] `_coerce_enrichment_payload()` extract `languages` và `candidateInfo[].location` từ `parsedJson`.
- [ ] `enrich_candidate_structured_data()` gọi `_normalize_and_persist_languages()` để normalize + persist vào `CANDIDATELANGUAGE`.
- [ ] `enrich_candidate_structured_data()` gọi `_normalize_and_update_province()` để map location → `user.provId`.
- [ ] `_map_language_to_lang_id()` function tồn tại với alias map + DB lookup + LLM fallback.
- [ ] `CANDIDATELANGUAGE` table created (nếu synthesis chọn Option B).
- [ ] Raw values preserved trong `CANDIDATELANGUAGE.rawName` và `rawProficiency`.
- [ ] Proficiency normalized theo 5-level enum `BASIC|INTERMEDIATE|ADVANCED|FLUENT|NATIVE`.
- [ ] Fallback khi mapper fail: `langId = None`, `proficiency = "BASIC"` (fallback built-in), KHÔNG crash enrichment.
- [ ] Batch re-enrichment mechanism tồn tại và đã test.
- [ ] All unit tests pass (Section 11.1).
- [ ] All integration tests pass (Section 11.2).

### 14.2 Tool contracts

- [ ] 7 MVP tools có input/output schema documented và agreed.
- [ ] Tất cả tools scoped theo `jobPostId`.
- [ ] Tools nhận `jobAppId` verify scope trước khi trả data.
- [ ] `get_job_application_full_cv` có PII masking.
- [ ] `get_job_candidate_ranking` cap limit tại 25.
- [ ] Error response convention thống nhất cross tools.
- [ ] Source metadata có trong mọi tool response.
- [ ] Too-large guardrail hoạt động với threshold 25.

### 14.3 Data quality

- [ ] Filter "tiếng Anh hạng C trở lên" trả kết quả chính xác (ADVANCED, FLUENT, NATIVE).
- [ ] Filter theo tỉnh trả kết quả chính xác (dùng `user.provId`).
- [ ] `compute_language_score()` produces accurate scores for non-standard proficiency strings ("N3", "IELTS 7.5", etc.).
- [ ] `CANDIDATELANGUAGE` records created for all enriched candidates.
- [ ] `user.provId` updated from CV location data for all enriched candidates.

---

## Recommended Decisions For Synthesis

1. **Normalize tại enrichment stage** (`nmaiex_candidate_enrichment.py`), KHÔNG phải parser, KHÔNG phải agent runtime. Mở rộng `_coerce_enrichment_payload()` và `enrich_candidate_structured_data()`.
2. **Tạo `CANDIDATELANGUAGE` table** — pattern tương tự `CANDIDATESKILL` (đã tồn tại). Cho phép SQL-level filter, JOIN với `JOB_LANG_REQUIREMENT`, và consistent với data model.
3. **Tạo `_map_language_to_lang_id()` function** với alias map + DB lookup (`LANGUAGE` table) + LLM fallback.
4. **Dùng 5-level enum** `BASIC|INTERMEDIATE|ADVANCED|FLUENT|NATIVE` (match `PROFICIENCY_LEVELS` trong code và `JOB_LANG_REQUIREMENT.minLevel`). Agent translate HR input qua system prompt.
5. **Update `user.provId`** từ CV location data qua `map_string_to_province_id()` trong enrichment.
6. **Inclusive filter default** khi `langId = None` hoặc `provId = None` — include candidate + warning.
7. **7 tools đúng như danh sách MVP** — không thêm, không bớt cho Phase 1.
8. **PII masking bắt buộc** cho `get_job_application_full_cv`.
9. **Batch re-enrichment** cho dữ liệu cũ phải là phần của implementation plan.

## Risks If Ignored

| Risk | Impact | Severity |
|------|--------|----------|
| Không fix enrichment pipeline (languages/location completely skipped) | ALL language scoring defaults to BASIC(1), ALL province filtering BROKEN → sản phẩm không dùng được | 🔴 Critical |
| Không tạo `CANDIDATELANGUAGE` table (hoặc equivalent) | Không có queryable normalized language data → filter impossible | 🔴 Critical |
| Không re-enrich dữ liệu cũ | Dữ liệu cũ vẫn raw → filter chỉ đúng cho CV mới | 🟡 High |
| Không tạo `_map_language_to_lang_id()` | Không thể map raw language names → `langId` → filter broken | 🔴 Critical |
| Không update `user.provId` từ CV | Province filtering trên candidate side broken | 🟡 High |
| Không có scope check trên `jobAppId` tools | Data leak giữa job postings | 🔴 Critical |
| Không có PII masking | PII leak qua agent responses | 🟡 High |
| Không có too-large guardrail | Agent cố xử lý 1000 ứng viên → timeout/hallucination | 🟡 High |

## Inputs Needed From Other Workstreams

| From | Input needed | Lý do |
|------|-------------|-------|
| WS-A | Tool declaration format (Google `FunctionDeclaration` exact structure) | WS-C tool schemas cần conform to WS-A runtime format |
| WS-A | Max tool output token budget | WS-C phải biết để truncate tool output nếu cần |
| WS-A | Agent model ID confirmed | Agent phải translate HR proficiency input → 5-level enum |
| WS-B | State JSON structure cho working set | WS-C tools cần biết working set để filter in-memory |
| WS-B | Tool call log schema | WS-C cần biết log gì, không log gì |
| WS-D | Error message format cho UI | WS-C error convention phải align với UI display |
| WS-D | Route cho `jobPostId` context verification | WS-C scope check phụ thuộc API layer |

## Checklist For Official Implementation Plan

- [ ] Incorporate normalization fix vào implementation plan — note: bug nghiêm trọng hơn dự kiến (enrichment HOÀN TOÀN BỎ QUA languages/location)
- [ ] List exact files modified: `nmaiex_candidate_enrichment.py` (primary), optionally `nmaiex_mapper_service.py`
- [ ] Include `CANDIDATELANGUAGE` table creation (migration task)
- [ ] Include `_map_language_to_lang_id()` creation task
- [ ] Include `_normalize_and_persist_languages()` creation task
- [ ] Include `_normalize_and_update_province()` creation task
- [ ] Include `_coerce_enrichment_payload()` expansion (add `languages` + `candidate_location`)
- [ ] Include batch re-enrichment mechanism task
- [ ] Include all 15 unit tests + 5 integration tests from Section 11
- [ ] Include 7 tool implementation tasks with exact schemas from this report
- [ ] Include scope verification utility function task
- [ ] Include PII masking utility function task
- [ ] Include too-large guardrail configuration task
- [ ] Define implementation order: `CANDIDATELANGUAGE` migration → enrichment fix → tools → tests
- [ ] Mark enrichment fix as BLOCKER for tool 2, 3, 7 (filter-dependent tools)
- [ ] Include migration/re-enrichment in deployment plan
- [ ] Coordinate with WS-A on FunctionDeclaration format
- [ ] Coordinate with WS-B on state/working set schema
- [ ] Coordinate with WS-D on error display and source metadata

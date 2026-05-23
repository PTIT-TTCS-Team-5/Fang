# P0-A Repo Reality Audit Report

* NOTE FROM USER:
  - Có những phần trong này được mình chỉ định là bao gồm trong phần việc của người làm P1-A/B, nghĩa là vấn đề được nêu ra sẽ do thành viên này trực tiếp xử lý. Mình đánh mã "P1_A_B_inc" và bạn hãy "Ctrl + f" để tìm cho nhanh
  - Tương tự: Mình đánh mã CHAT_FULL_CV cho những phần liên quan đến phần việc sửa JobApplication chat thành Full CV

Ngày audit: 23/05/2026
Phạm vi: `README.md`, `docs/system_architecture.md`, `docs/strategy`, `docs/guide`, `docs/testing_guide.md`, `agent_workflow_doc`, `app/`, `database/`, `tests/unit`, `smoke_tests`, `scripts`. Không đọc sâu `docs/research` theo note của user vì research dài và không phải current runtime truth.

## 1. Executive summary

FANG hiện là FastAPI backend v2, có 4 cụm runtime chính:

1. CV ingestion: nhận `jobAppId` + `cvSnapUrl`, parse CV bằng multi-provider parser, chuyển JSON sang markdown, chunk, embed và lưu vào PostgreSQL/pgvector.
2. RAG chat theo `JobApplication`: dùng vector search trên `AIDOCUMENTCHUNK`, ghép thêm `JobPosting`, `Candidate profile`, một phần ATS history, gọi LLM generation qua 7 `modelMode`, lưu conversation/message/query log.
3. NMAIex ranking: đã được mount trực tiếp vào FANG tại `/v2/nmaiex`, có ranking hai chiều J->C và C->J, master data API, skill mapper, language/salary/seniority scoring.
4. NMAIex management/job ingestion: có API cập nhật job/candidate và background re-ingest job/CV, nhưng đang tồn tại hai bề mặt route song song và một route content update trả `queued` nhưng chưa thực sự re-ingest.

Những drift quan trọng nhất:

- NMAIex trong docs vẫn có chỗ gọi là "extension" hoặc "tách biệt hoàn toàn khỏi TTCS", nhưng code hiện tại cho thấy NMAIex là một phần chính thức của FANG core: `app/main.py`, `app/api/nmaiex_routes_*.py`, `app/services/nmaiex_*`, `database/schema_web_core.sql`.
- Embedding reality đã chuyển sang Gemini `gemini-embedding-001` mặc định 1536 dims trong `app/core/config.py`, trong khi nhiều docs/test vẫn mô tả OpenAI `text-embedding-3-small` 1024 dims.
- README nói Parser và Generator cùng dùng 5-tier fallback + ProTierGate, nhưng code generation tách `auto-lite` và `auto-pro`; không có cơ chế auto-lite tự leo Pro.
- Testing guide mô tả các unit test RAG/chat manager chưa tồn tại. Unit test hiện tại chạy bằng `venv\Scripts\python` có 1 lỗi thật do `unit_test_embedding.py` vẫn patch `AsyncOpenAI`, trong khi `embedding.py` đã chuyển sang Google Gemini SDK.
- Quyết định mới trong `agent_workflow_doc/FANG_NEXT_PHASE_DECISIONS.md` đã chốt JobApplication chat sẽ chuyển sang full CV markdown context, nhưng code/docs runtime hiện vẫn là fixed chunk-RAG theo `topK`.

## 2. Current architecture reality

### 2.1 API runtime

`app/main.py` tạo FastAPI app với async lifespan, connect/disconnect DB pool qua `app.core.database.db`. Router đang mount:

- `/v2/ingestion` từ `app/api/routes_ingestion.py`.
- `/v2/chat` từ `app/api/routes_chat.py`.
- `/v2/nmaiex` từ `app/api/nmaiex_routes_ranking.py`.
- `/v2/nmaiex/management` từ `app/api/nmaiex_routes_management.py`.
- `/v1/ingestion` vẫn được giữ backward-compatible bằng cách mount lại ingestion router dưới prefix `/v1`.

Health check hiện có `/v2/healthz` và legacy `/healthz`. Không có auth layer; docs cũng ghi phase sau mới thêm API key/JWT.

### 2.2 Database reality

DB access dùng `asyncpg` pool trong `app/core/database.py`. Nếu pool chưa init, `acquire_conn()` raise `RuntimeError("Database pool is not initialized")`.

Schema chia 2 nhóm:

- `database/schema_web_core.sql`: web/ATS core plus NMAIex master data và mapping tables (`REGION`, `PROVINCE`, `JOBLEVEL`, `JOBCATEGORY`, `LANGUAGE`, `JOB_LEVEL_MAP`, `JOB_CATEGORY_MAP`, `JOB_LANG_REQUIREMENT`, `CANDIDATE_SKILL_RAW`, `JOB_SKILL_RAW`).
- `database/schema_ai_core.sql`: AI ingestion/chat tables (`AIINDEXJOB`, `CVPARSED`, `AIDOCUMENTCHUNK`, `AIQUERYLOG`, `AICHATCONVERSATION`, `AICHATMESSAGE`).

`scripts/reset_and_seed_db.py` là source hiện tại để inject vector dimensions vào schema bằng placeholders `__TTCS_EMBEDDING_DIM__` và `__NMAIEX_SKILL_EMBEDDING_DIM__`, rồi chạy `schema_web_core.sql`, `schema_ai_core.sql`, `root_data.sql`, `seed_synth.sql`.

### 2.3 Ingestion reality

`app/api/routes_ingestion.py`:

- `POST /v2/ingestion/jobs`: tạo `AIINDEXJOB` với `QUEUED`, chạy `process_ingestion_task` trong `BackgroundTasks`.
- `GET /v2/ingestion/jobs/{indexJobId}`: đọc status.
- `process_ingestion_task`: `download_cv` -> `parse_to_raw_and_json` -> validate `ParsedCV` -> `save_parsed_cv` -> markdown builder -> chunking -> `embed_chunks` -> `save_chunk_payloads`.
- Sau khi lưu chunks, task cố update NMAIex data: tính `CANDIDATE.expyears`, gọi `map_skills`, cập nhật `CANDIDATESKILL` và `CANDIDATE_SKILL_RAW`.

Rủi ro: block update NMAIex expyears/skills được catch riêng và chỉ log lỗi, ingestion vẫn có thể set `SUCCESS`. Điều này có thể làm Chat RAG unlock nhưng ranking thiếu dữ liệu skill/exp.

* NOTE FROM USER: Ghi nhận, dự tính giao cho thành viên quản lý JobApplication sửa phần này

### 2.4 Parser and LLM generation reality

Parser:

- `app/services/cv_parser.py` có 5 tiers: `gemini-flash`, `gpt-5.4-mini`, `claude-4.5-haiku`, `gemini-pro`, `gpt-5.5`.
- ProTierGate chỉ leo Pro khi ít nhất một Lite tier trả output chất lượng thấp; nếu lỗi hạ tầng chiếm đa số thì skip Pro.
- Prompt parser nằm trong `app/services/cv_parser_adapters.py`, có rules cho CV extraction, language extraction, expected salary extraction.

Generation:

- `app/services/rag_model_adapters.py` định nghĩa 7 `modelMode`: 5 specific modes và 2 auto modes.
- `auto-lite`: Gemini Flash -> GPT mini -> Claude Haiku.
- `auto-pro`: Gemini Pro -> GPT full.
- Specific mode retry nhưng không fallback.
- `app/services/rag_orchestrator.py` có generation quality gate heuristic, nhưng không có Lite-to-Pro escalation trong generation.

* NOTE FROM USER: ProTierGate nên được cân nhắc dựa trên việc xác định các chỉ số tự trả về từ Model (ví dụ configure thêm confident/error_val)

### 2.5 RAG chat reality

`app/services/rag_query.py` là pipeline chính:

1. Kiểm tra `AIINDEXJOB` mới nhất của `jobAppId` phải `SUCCESS`.
2. Tạo hoặc load conversation.
3. Lưu user message.
4. Embed prompt qua `embed_chunks`.
5. Vector search `AIDOCUMENTCHUNK WHERE jobAppId = $2 LIMIT top_k`.
6. Fetch context: `JobPosting` chỉ lấy `title`, `description`; `Candidate profile` lấy tên/email/phone/bio/expyears/location; ATS history hiện chỉ lấy interview + feedback.
7. Build system prompt với retrieved chunks, không phải full CV.
8. Check budget dựa trên history messages.
9. Vẫn gọi LLM và trả `contextWarning` nếu gần ngưỡng.
10. Lưu assistant message và `AIQUERYLOG`.

* NOTE FROM USER:
  - Fetch content phải lấy cả Offer
  - Đã quyết định Chat = full CV markdown trong JobApplication

### 2.6 NMAIex reality

NMAIex đã là phần runtime chính thức của FANG:

- `app/main.py` mount NMAIex routers.
- `app/services/nmaiex_ranking_service.py` chứa ranking J->C/C->J.
- `app/services/nmaiex_mapper_service.py` dùng `invoke_generation(..., "auto-lite")` để map province, skill, language proficiency.
- `app/core/nmaiex_config.py` đọc `.env.nmaiex`.
- `database/schema_web_core.sql` có NMAIex tables và master data dependencies.
- `routes_ingestion.py` gọi NMAIex mapper để cập nhật skill/exp ngay trong ingestion.

J->C ranking reality:

- Fetch job, skills, levels.
- Embed `title + description`.
- Tính vector distance trên `AIDOCUMENTCHUNK`, text rank trên `CVPARSED.rawText`, RRF, skill score, seniority penalty.

C->J ranking reality:

- Không dùng vector search; dùng `ts_rank` job text/title, skill score, salary adjustment, language score.
- Loại bỏ job đã ứng tuyển.

Management reality:

- `app/api/nmaiex_routes_ranking.py` có các endpoint detail/update trực tiếp dưới `/v2/nmaiex/jobs/...` và `/v2/nmaiex/candidates/...`.
- `app/api/nmaiex_routes_management.py` có endpoint tương tự dưới `/v2/nmaiex/management/...`.
- Route `/v2/nmaiex/jobs/{job_id}/content` trong `nmaiex_routes_ranking.py` có TODO re-ingest nhưng vẫn trả `reingestion_status: "queued"`.
- Route `/v2/nmaiex/management/jobs/{job_id}/content` thật sự gọi `process_job_ingestion_task`.

## 3. Feature reality map

### 3.1 Implemented

| Feature | Reality | References |
|---|---|---|
| FastAPI v2 core, health, CORS | Implemented | `app/main.py`, `app/core/config.py` |
| Ingestion async background task | Implemented | `app/api/routes_ingestion.py`, `app/services/persistence.py` |
| 5-tier CV parser + ProTierGate | Implemented | `app/services/cv_parser.py`, `app/services/cv_parser_adapters.py` |
| Markdown builder + deterministic chunking | Implemented | `app/services/markdown_builder.py`, `app/services/chunking.py` |
| Gemini embedding service with configurable dimensions | Implemented | `app/services/embedding.py`, `app/core/config.py` |
| Chat conversation/message persistence | Implemented | `app/api/routes_chat.py`, `app/services/chat_persistence.py`, `database/schema_ai_core.sql` |
| RAG chat with top-k vector search | Implemented | `app/services/rag_query.py` |
| Generation adapters + 7 model modes | Implemented | `app/services/rag_model_adapters.py`, `app/services/rag_orchestrator.py` |
| NMAIex ranking J->C and C->J | Implemented | `app/api/nmaiex_routes_ranking.py`, `app/services/nmaiex_ranking_service.py` |
| NMAIex master data API | Implemented for provinces/levels/categories/skills | `app/api/nmaiex_routes_ranking.py` |
| NMAIex mapper and raw skill embeddings | Implemented | `app/services/nmaiex_mapper_service.py`, `database/schema_web_core.sql` |
| DB reset/seed with dimension injection | Implemented | `scripts/reset_and_seed_db.py` |

### 3.2 Partial

| Feature | Reality | References |
|---|---|---|
| Multi-source RAG context | Partial: Job title/description, candidate basic fields, interview feedback only; no skills in prompt, no offer/email context | `app/services/rag_query.py`, `docs/strategy/rag_query_strategy.md` |
| Context window management | Partial: returns warning but still calls LLM; budget is Lite/Pro group, not per-model map | `app/services/rag_query.py`, `app/services/rag_model_adapters.py`, `docs/strategy/rag_query_strategy.md`, `docs/guide/rag_query_guide.md` |
| NMAIex job content re-ingestion | Partial: works under `/management`, not under root `/v2/nmaiex/jobs/{id}/content` route | `app/api/nmaiex_routes_management.py`, `app/api/nmaiex_routes_ranking.py` |
| NMAIex language system | Partial: DB + scoring exists; master language endpoint documented as not implemented | `database/schema_web_core.sql`, `app/services/nmaiex_ranking_service.py`, `docs/guide/nmaiex_ranking_guide.md` |
| Test suite | Partial: several unit tests exist, but RAG/chat unit tests documented are missing; one current unit test fails | `tests/unit`, `docs/testing_guide.md` |
| Synthetic data/tuning workflow | Historical/archived: user confirmed synthetic data, ground-truth labeling and tuning are done; old checklists are not current execution truth | `agent_workflow_doc/archive/task_data_set.md`, `synthetic_data/`, `nmaiex_tuning/` |

* NOTE FROM USER:
  - "Multi-source RAG context": Phải cân nhắc lại về prompt eng (cái này đã bao gồm skill + thêm Offer/Email content và trong phần việc của người làm P1-A/B P1_A_B_inc )
  - "Context window management": P1_A_B_inc
  - "NMAIex job content re-ingestion": Chưa hiểu lắm, cần giải thích
  - "NMAIex language system": Sửa docs theo Code
  - "Test suite": Mình sẽ trực tiếp dùng Model tier 2 làm
  - "Synthetic data/tuning workflow": Tất cả syntheic data + gán nhãn (build_ground_truth) + tuning đã xong -> Mình sẽ trực tiếp dùng Model tier 2 làm

### 3.3 Documented-only or decision-only

| Feature/decision | Reality | References |
|---|---|---|
| JobApplication chat full-CV markdown context | Decision is chốt, code still uses fixed top-k chunks | `agent_workflow_doc/FANG_NEXT_PHASE_DECISIONS.md`, `app/services/rag_query.py`, `docs/guide/rag_query_guide.md` |
| JobPosting Agent / tool-based retrieval / MCP | Decision track only, no implementation | `agent_workflow_doc/FANG_NEXT_PHASE_DECISIONS.md` |
| Per-model context budget map | Docs recommend, code uses Lite/Pro group budget | `docs/strategy/rag_query_strategy.md`, `docs/guide/rag_query_guide.md`, `app/services/rag_model_adapters.py` |
| Auth/API key/JWT | Docs phase sau, no runtime middleware | `docs/strategy/integration_strategy.md`, `app/main.py` |
| `/v2/nmaiex/master/languages` | Explicitly documented as not implemented | `docs/strategy/nmaiex_ranking_strategy.md`, `docs/guide/nmaiex_ranking_guide.md` |

* NOTE FROM USER:
  - "JobApplication chat full-CV markdown context": CHAT_FULL_CV
  - "JobPosting Agent / tool-based retrieval / MCP": Mình sẽ trực tiếp làm
  - "Per-model context budget map": P1_A_B_inc (nếu nhiều việc quá thì báo mình nhé)
  - "Auth/API key/JWT": Vẫn chỉ note trong docs, được coi là tính năng nâng cao chưa cần thiết
  - "/v2/nmaiex/master/languages": Mình sẽ sửa trong P0-C


### 3.4 Stale or legacy

| Item | Why stale | References |
|---|---|---|
| Embedding docs/tests mention OpenAI `text-embedding-3-small` 1024 dims as default | Runtime default is Gemini `gemini-embedding-001` 1536 dims | `app/core/config.py`, `app/services/embedding.py`, `docs/strategy/embedding_strategy.md`, `docs/guide/embedding_guide.md`, `docs/guide/database_guide.md`, `.env.example`, `tests/unit/unit_test_embedding.py` |
| Testing guide lists `unit_test_rag_orchestrator.py` and `unit_test_chat_manager.py` | Files do not exist in `tests/unit` | `docs/testing_guide.md`, `tests/unit/` |
| README says NMAIex config copy `.env.nmaiex.example`, and docs mention template in `app/core` too | Repo has both root `.env.nmaiex.example` and `app/core/.env.nmaiex.example`; cần chọn truth source | `README.md`, `docs/guide/nmaiex_ranking_guide.md`, `app/core/.env.nmaiex.example`, `.env.nmaiex.example` |
| AI_WORKFLOW_INIT says NMAIex đang nghiên cứu/extension | User quyết định đã gộp NMAIex vào FANG chính thức; code cũng thể hiện điều này | `agent_workflow_doc/AI_WORKFLOW_INIT.md`, `app/main.py`, `database/schema_web_core.sql` |
| NMAIex docs say tách biệt hoàn toàn khỏi TTCS/router không bị sửa | Ingestion core đã gọi NMAIex mapper và update candidate expyears/skills | `docs/strategy/nmaiex_ranking_strategy.md`, `docs/guide/nmaiex_ranking_guide.md`, `app/api/routes_ingestion.py` |
| Smoke script and e2e constants assume old IDs/dims | `smoke_tests/test_e2e_pipeline.py` expects `EXPECTED_EMBEDDING_DIM = 1024`, while current config default is 1536 | `smoke_tests/test_e2e_pipeline.py`, `app/core/config.py` |

* NOTE FROM USER:
  - "Embedding docs/tests mention OpenAI text-embedding-3-small 1024 dims as default": Sửa lại docs theo Code
  - "Testing guide lists unit_test_rag_orchestrator.py and unit_test_chat_manager.py: Như đã nói bên trên, mình sẽ trực tiếp dùng Model tier 2 sửa test
  - "README says NMAIex config copy .env.nmaiex.example, and docs mention template in app/core too": Thống nhất dùng .env.nmaiex.example, xóa "app/core/.env.nmaiex.example"
  - "AI_WORKFLOW_INIT says NMAIex đang nghiên cứu/extension" và "NMAIex docs say tách biệt hoàn toàn khỏi TTCS/router không bị sửa": Cập nhật docs, nmaiex là một phần chính thức của FANG. Giữ lại tên gọi đặc thù nmaiex để dễ phân biệt
  - "Smoke script and e2e constants assume old IDs/dims": Mình sẽ trực tiếp dùng Model tier 2 để sửa

## 4. Code-doc drift map

| ID | Drift/conflict | Code reality | Doc reality | Why it matters | Suggested handling |
|---|---|---|---|---|---|
| D01 | NMAIex status | Mounted in core app and DB; ingestion updates NMAIex data | Some docs still call NMAIex extension/tách biệt | P0-C may keep wrong architecture boundary | Update docs: NMAIex is official FANG module, old name kept for recognizability |
| D02 | Embedding provider/dim | Gemini provider, `embedding_dim=1536`, model `gemini-embedding-001` | Many docs/tests say OpenAI `text-embedding-3-small`, 1024 dims | DB schema, vector search, tests and costs depend on dim/model | P0-C should reconcile docs; tests need update |
| D03 | Generator ProTierGate | Generation has `auto-lite` and `auto-pro`, no automatic Lite->Pro gate | README says Parser and Generator share 5-tier + ProTierGate | Misleads cost/fallback expectations | Decide if docs should say two auto chains or code should add escalation |
| D04 | JobApplication chat context | Code retrieves top-k chunks | Next-phase decision says move to full CV markdown | Important upcoming feature, but not implemented yet | Keep as decision-only until a feature guide exists |
| D05 | Context budget behavior | Code returns warning and still calls LLM; group Lite/Pro budget | Strategy says if over threshold return warning/no LLM and recommends per-model budget | UX and cost behavior differ from docs | Decide behavior before docs rewrite |
| D06 | RAG multi-source context | Code only has job title/description, candidate basic fields, interview feedback | Strategy mentions job requirements/salary/work mode/level, candidate skills, offers, emails | HR answer completeness and grounding affected | Create scoped implementation/test package |
| D07 | NMAIex management route duplication | Root and `/management` routes both exist; behavior differs | README/strategy mostly list ranking/master only; frontend checklist references root paths | Frontend may call route that returns queued without re-ingest | Choose canonical management API and deprecate/align the other |
| D08 | Testing guide vs files | Current files: chunking, embedding, ingestion flow, parser policy, persistence | Guide lists RAG orchestrator/chat manager unit tests absent | False confidence for verification | Update testing guide after adding or removing entries |
| D09 | Unit embedding test stale | Test patches `app.services.embedding.AsyncOpenAI`; module no longer has it | Test expected OpenAI flow | CI/unit suite fails | Update test to fake Gemini SDK or abstract provider |
| D10 | Ingestion test hides NMAIex update failure | Unit run logs DB pool error inside swallowed NMAIex block yet still passes | No doc/test states NMAIex post-ingestion update can fail silently | Ranking data may be missing after SUCCESS ingestion | Add explicit test and decide status semantics |
| D11 | Score clipping note unresolved | Code clips scores to `[0,1]` | User note in strategy questions whether clipping loses ranking signal outside bounds | Ranking/tuning semantics unresolved | Decision memo before tuning/doc reconciliation |
| D12 | `.env.nmaiex.example` truth source | Root and `app/core` examples both exist | Docs reference template inconsistently | Onboarding/config drift | Choose one template path |

* NOTE FROM USER:
  - DO1: như đã nhắc tới ở các NOTE bên trên. Accept suggested handling (ASH)
  - D02: như đã nhắc tới ở NOTE trên -> Sửa docs theo Code. ASH
  - D03: Sửa docs theo Code. Chỉ parser có 5 tier fallback + ProtierGate. Generation still 7 model Mode.
  - D04: Như đã quyết bên trên, là phần việc của CHAT_FULL_CV -> Chat bằng full CV markdown
  - D05: Nằm trong phần việc của CHAT_FULL_CV -> Sửa Code theo docs
  - D06: Sửa code theo docs
  - D07: ASH, chọn /v2/nmaiex/management/jobs/{id}/content. Sau đó sửa docs theo Code
  - D08: Như đã nói bên trên, mình sẽ dùng Model Tier 2 xử lý
  - D09: Như đã nói bên trên trong các Node, dùng hoàn toàn gemini-embedding-001 cho embedding -> Sửa Code và Sửa docs theo Code.
  - D10: ASH, sẽ dùng Model tier 1 cân nhắc.
  - D11: Chốt không Clip -> Sửa Code & sửa docs theo Code
  - D12: Như NOTE bên trên, bỏ app/core/.env.nmaiex.example

## 5. Test and verification reality map

### 5.1 Unit tests present

Current files in `tests/unit`:

- `unit_test_chunking.py`
- `unit_test_embedding.py`
- `unit_test_ingestion_flow.py`
- `unit_test_parser_policy.py`
- `unit_test_persistence.py`

Run results:

- `python -m unittest discover -s tests/unit -p "unit_test_*.py"` with global Python failed immediately due missing installed packages (`pydantic`, `pydantic_settings`, `fastapi`).
- `venv\Scripts\python -m unittest discover -s tests/unit -p "unit_test_*.py"` ran 12 tests, failed 1 error:
  - `unit_test_embedding.EmbeddingTests.test_embed_chunks_uses_configured_model_dimensions_and_batching` fails because test patches `app.services.embedding.AsyncOpenAI`, but current `app/services/embedding.py` uses `google.genai`.

Important observation: during `unit_test_ingestion_flow.py`, the NMAIex expyears/skills update block logs `Database pool is not initialized`, but the test still passes because production code swallows that block. This is a behavior risk, not just test noise.

* NOTE FROM USER:
  - Ghi nhận, sẽ dùng Model tier 2 xử lý

### 5.2 Smoke/integration tests present

Current files in `smoke_tests`:

- `test_parser.py`
- `test_parser_db.py`
- `test_e2e_pipeline.py`
- `test_chunking.py`
- `test_chat_api.py`

They require combinations of DB, server, API keys, local sample PDFs or env IDs. I did not run them in P0-A because this audit should not mutate DB or call external providers casually.

Potential stale item:

- `smoke_tests/test_e2e_pipeline.py` hard-codes `EXPECTED_EMBEDDING_DIM = 1024`, conflicting with current default `settings.embedding_dim = 1536`.

* NOTE FROM USER: Không quá quan trọng, có thể bỏ, ưu tiên các việc khác trước. Nếu còn thời gian mình sẽ dùng tier 2 làm

### 5.3 Missing tests relative to behavior

- No current unit test file for `rag_orchestrator.py` despite docs.
- No current unit test file for `chat_persistence.py`/chat manager despite docs.
- No focused unit tests for NMAIex ranking formulas, score clipping, language score, salary adjustment, management route canonical behavior, or ingestion NMAIex post-processing failure semantics.
- No minimal eval cases for prompts; this belongs to P1-A/P1-B but should use P0-B inventory first.

* NOTE FROM USER: đã NOTE nhiều ở trên. Mình sẽ dùng Model tier 2 để giải quyết

## 6. Risk list

| Risk | Severity | Evidence | Impact |
|---|---:|---|---|
| Embedding dim/provider drift between runtime, schema, docs, tests | High | `app/core/config.py`, `database/schema_ai_core.sql`, `docs/guide/embedding_guide.md`, `.env.example`, `tests/unit/unit_test_embedding.py` | Vector insert/search/test failures or wrong operational docs |
| NMAIex post-ingestion update can fail silently while ingestion becomes SUCCESS | High | `app/api/routes_ingestion.py`, unit test logs | Chat unlock/ranking data inconsistent |
| Management route duplication with different re-ingest behavior | High | `app/api/nmaiex_routes_ranking.py`, `app/api/nmaiex_routes_management.py` | Frontend may call stale route and ranking uses old job embeddings |
| RAG answer grounding is narrower than strategy claims | Medium | `app/services/rag_query.py`, `docs/strategy/rag_query_strategy.md` | HR may expect salary/skills/offers context that model never receives |
| Docs say generator 5-tier ProTierGate but code does not | Medium | `README.md`, `app/services/rag_orchestrator.py`, `app/services/rag_model_adapters.py` | Cost/quality debugging confusion |
| Unit suite currently red in venv | Medium | test run result | Future changes cannot rely on baseline tests |
| Score clipping unresolved while tuning may optimize clipped scores | Medium | `app/services/nmaiex_ranking_service.py`, `docs/strategy/nmaiex_ranking_strategy.md` note | Ranking calibration may hide bad/great outliers |
| Workflow docs status not machine-readable | Low | `agent_workflow_doc` mixed checklists/specs | Handoff friction for tier 2 |

* NOTE FROM USER:
  - "Embedding dim/provider drift between runtime, schema, docs, tests": đã NOTE để xử lý bên trên
  - "NMAIex post-ingestion update can fail silently while ingestion becomes SUCCESS": đã NOTE để xử lý bên trên
  - "Management route duplication with different re-ingest behavior": đã NOTE để xử lý bên trên
  - "RAG answer grounding is narrower than strategy claims": đã NOTE để xử lý bên trên
  - "Docs say generator 5-tier ProTierGate but code does not": đã NOTE để xử lý bên trên
  - "Unit suite currently red in venv": đã NOTE để xử lý bên trên
  - "Score clipping unresolved while tuning may optimize clipped scores": đã NOTE để xử lý bên trên
  - "Workflow docs status not machine-readable": ? Sẽ cải thiện sau, cái này không liên quan đến dự án cho lắm

## 7. agent_workflow_doc status map

This table addresses the user note "đánh dấu những file trong agent_workflow_doc đã xong" without editing old source prompts in P0-A.

| File/group | Status from audit | Reason |
|---|---|---|
| `FANG_NEXT_PHASE_DECISIONS.md` | Done as current decision source | Defines P0/P1 ordering and decisions; should remain the source until superseded |
| `FANG_NEXT_PHASE_P0A_REPO_REALITY_AUDIT.md` | Input spec done; execution report is this file | Source prompt/spec read and used |
| `FANG_NEXT_PHASE_P0B_AI_LLM_INVENTORY.md` | Not executed yet | Spec exists; should run after P0-A |
| `FANG_NEXT_PHASE_P0C_DOC_RECONCILIATION.md` | Not executed yet | Must wait for P0-A/P0-B and decisions |
| `FANG_NEXT_PHASE_P1A_PROMPT_REVIEW_AND_MIN_EVAL.md` | Not executed yet | Depends on P0-B/P0-C and prompt inventory |
| `KINH_NGHIEM.md` | Current guidance/read | Useful workflow guidance, not an execution checklist |
| `AI_WORKFLOW_INIT.md` | Stale/needs update | Still describes NMAIex as "đang nghiên cứu" and instructs reading research for NMAIex by default |
| `[NMAIex]_TASK_CHECKLIST_BACKEND.md` | Mostly done, but should be reconciled | Many `[x]`; some entries do not fully match current code (route mount note, parsedJson naming, management routes) |
| `[NMAIex]_TASK_CHECKLIST_FRONTEND.md` | Not done | Many unchecked frontend items |
| `archive/task_data_set.md` | Archived/historical | User confirmed work is actually done; old unchecked boxes are historical noise, not open work |
| `archive/task_nmaiex_tuning_6h.md` | Archived/done | Completed tuning checklist, kept only for history |
| `archive/task_nmaiex_tuning.md` / implementation plans | Archived/historical | Keep as background; do not treat as current runtime truth |

* NOTE FROM USER:
  - "AI_WORKFLOW_INIT.md": đồng ý, cần update
  - "[NMAIex]_TASK_CHECKLIST_BACKEND.md" và "[NMAIex]_TASK_CHECKLIST_FRONTEND.md": không cố quay lại sửa, mark as archive hoặc tạo thư mục archive trong agent_workflow_docs và chuyển vào.
  - "task_data_set.md": unchecked but actually done -> vào archive
  - "task_nmaiex_tuning_6h.md" và "task_nmaiex_tuning.md": Done -> vào archive

## 8. Work packages

### WP-01: Embedding docs/tests reconciliation

- Goal: Chốt và đồng bộ embedding provider/dim/type hiện tại.
- Why: Runtime đang dùng Gemini 1536, nhiều docs/tests vẫn OpenAI 1024.
- Scope: `app/core/config.py`, `app/services/embedding.py`, `.env.example`, `database/schema_ai_core.sql`, `docs/strategy/embedding_strategy.md`, `docs/guide/embedding_guide.md`, `docs/guide/database_guide.md`, `docs/guide/input_processing_guide.md`, `docs/strategy/rag_query_strategy.md`, `tests/unit/unit_test_embedding.py`, `smoke_tests/test_e2e_pipeline.py`.
- Out of scope: đổi provider/model một lần nữa nếu chưa có decision.
- Output: drift resolution patch or decision memo if keeping docs as historical.
- Acceptance criteria: unit embedding test passes; docs state one canonical default; `.env.example` matches code or explicitly overrides code default.
- Owner/model tier: Tier 2 for patch after user confirms default; tier 1 review if default itself is contested.
- Review requirement: user/tier 1 must approve model/dim truth source before broad doc rewrite.

### WP-02: NMAIex management route canonicalization

- Goal: Chọn một API surface cho job/candidate management and make behavior consistent.
- Why: Root `/v2/nmaiex/jobs/{id}/content` returns queued without re-ingest, while `/v2/nmaiex/management/jobs/{id}/content` re-ingests.
- Scope: `app/api/nmaiex_routes_ranking.py`, `app/api/nmaiex_routes_management.py`, `docs/guide/nmaiex_ranking_guide.md`, `docs/strategy/nmaiex_ranking_strategy.md`, frontend checklist docs.
- Out of scope: frontend implementation.
- Output: decision memo + patch plan; optionally deprecate duplicate route or make it delegate to canonical service.
- Acceptance criteria: one route behavior is canonical; docs list exact route; content update actually re-ingests or explicitly does not claim so.
- Owner/model tier: Tier 1 for decision, tier 2 for implementation.
- Review requirement: API contract review before frontend work.

### WP-03: Ingestion status semantics for NMAIex post-processing

- Goal: Decide whether failed NMAIex expyears/skill mapping should fail ingestion, produce partial status, or remain best-effort.
- Why: Current code logs failure but still sets `SUCCESS`.
- Scope: `app/api/routes_ingestion.py`, `tests/unit/unit_test_ingestion_flow.py`, `app/services/nmaiex_mapper_service.py`, `app/services/persistence.py`, `database/schema_ai_core.sql` if status needs extension.
- Out of scope: ranking formula changes.
- Output: behavior decision + tests.
- Acceptance criteria: unit test covers mapper/db failure; docs describe ingestion success vs partial enrichment semantics.
- Owner/model tier: Tier 1 decision, tier 2 implementation.
- Review requirement: user decides product semantics before code change.

### WP-04: RAG current reality vs full-CV chat implementation guide

- Goal: Produce a tier 1 implementation guide for switching JobApplication chat from fixed top-k chunk RAG to full CV markdown context.
- Why: Decision is already chốt, but code still uses top-k vector retrieval.
- Scope: `app/services/rag_query.py`, `app/services/markdown_builder.py`, `app/services/persistence.py`, `database/schema_ai_core.sql`, `docs/guide/rag_query_guide.md`, `docs/strategy/rag_query_strategy.md`, `agent_workflow_doc/FANG_NEXT_PHASE_DECISIONS.md`.
- Out of scope: JobPosting Agent.
- Output: implementation plan with data source for full CV markdown, fallback, token budget, tests, migration/docs.
- Acceptance criteria: plan says exactly whether full markdown is generated from `CVPARSED.parsedJson`, stored markdown, or recomputed; includes unit/smoke tests.
- Owner/model tier: Tier 1.
- Review requirement: user approves before implementation.

### WP-05: RAG multi-source context coverage

- Goal: Align actual system prompt context with documented multi-source context.
- Why: Docs claim richer context than code currently fetches.
- Scope: `app/services/rag_query.py`, `database/schema_web_core.sql`, `database/schema_ai_core.sql`, `docs/strategy/rag_query_strategy.md`, `docs/guide/rag_query_guide.md`.
- Out of scope: full-CV switch unless WP-04 is approved.
- Output: gap report or patch adding missing fields (`skills`, salary/work mode/level, offers/emails if required).
- Acceptance criteria: each context block in docs maps to a query or is marked future.
- Owner/model tier: Tier 2 audit/report, tier 1 review for adding context.
- Review requirement: prompt/security review because context changes affect LLM behavior.

### WP-06: Test baseline repair

- Goal: Make unit test baseline green and testing guide truthful.
- Why: Current venv run fails 1 test; docs list absent tests.
- Scope: `tests/unit`, `docs/testing_guide.md`, `requirements.txt`, `smoke_tests`.
- Out of scope: new large eval framework.
- Output: green unit test run + updated testing guide.
- Acceptance criteria: `venv\Scripts\python -m unittest discover -s tests/unit -p "unit_test_*.py"` passes; testing guide only lists existing tests or includes tasks to add missing ones.
- Owner/model tier: Tier 2.
- Review requirement: tier 1 checks that tests do not encode stale architecture.

### WP-07: NMAIex scoring decision memo

- Goal: Resolve score clipping and tuning semantics before more calibration.
- Why: User note questions clipping to `[0,1]`; code currently clips all final scores.
- Scope: `app/services/nmaiex_ranking_service.py`, `app/core/nmaiex_config.py`, `docs/strategy/nmaiex_ranking_strategy.md`, `nmaiex_tuning/`.
- Out of scope: route/API restructuring.
- Output: decision memo with options: keep clip, expose raw_score + display_score, or bounded formula by construction.
- Acceptance criteria: user picks one; docs and tuning target align.
- Owner/model tier: Tier 1.
- Review requirement: user decision required.

### WP-08: agent_workflow_doc cleanup status pass

- Goal: Make workflow docs status explicit and less stale.
- Why: Current folder mixes specs, historical plans, partial checklists.
- Scope: `agent_workflow_doc/AI_WORKFLOW_INIT.md`, `agent_workflow_doc/[NMAIex]_TASK_CHECKLIST_BACKEND.md`, `agent_workflow_doc/[NMAIex]_TASK_CHECKLIST_FRONTEND.md`, `agent_workflow_doc/archive/task_data_set.md`, `agent_workflow_doc/FANG_NEXT_PHASE_*.md`.
- Out of scope: editing strategy/guide docs before P0-C.
- Output: status table or small header marker per file; no broad rewrite.
- Acceptance criteria: reader can tell "spec/input", "done", "partial", "stale/historical" without guessing.
- Owner/model tier: Tier 2 after P0-A accepted.
- Review requirement: avoid rewriting decision docs before P0-C.

## 9. Decision memos user/tier 1 should chốt

1. Embedding truth source: current Gemini 1536 default vs earlier OpenAI 1024 design. Decide before P0-C and before fixing tests/docs.
2. NMAIex boundary wording: update all docs to "official FANG module" while preserving NMAIex name, or keep "extension" only as historical label.
3. Generation fallback: should generation remain two auto chains (`auto-lite`, `auto-pro`) or implement Lite-to-Pro escalation similar parser?
4. JobApplication chat: confirm full-CV markdown context as implementation target and define data source/storage.
5. NMAIex management API canonical path: root `/v2/nmaiex/jobs/...` vs `/v2/nmaiex/management/jobs/...`.
6. Ingestion partial enrichment semantics: does failed NMAIex skill/exp mapping block `SUCCESS`?
7. Score clipping: keep strict `[0,1]` or expose raw score/normalized display score.
8. Testing priority: repair unit baseline first, then add RAG/chat/NMAIex unit tests before docs claim coverage.

* NOTE FROM USER: tất cả đã NOTE để xử lý bên trên

## 10. Recommended next order

* NOTE FROM USER:
  - actually reviewed all

1. User reviews this P0-A report and resolves only the high-impact decisions: embedding truth, NMAIex wording, management API canonical route, ingestion status semantics.
2. Run P0-B AI/LLM Inventory using `agent_workflow_doc/FANG_NEXT_PHASE_P0B_AI_LLM_INVENTORY.md`, with special attention to parser prompt, RAG system prompt, NMAIex mapper prompts, language normalizer, and model routing.
3. Use P0-A + P0-B to run P0-C, not before. P0-C should archive stale docs where needed instead of overwriting history blindly.
4. Only after P0-C, assign WP-04 JobApplication Full-CV Chat and P1-A/P1-B Prompt Review + Minimal Eval.

# Branch Reconciliation Report (develop vs main)

Date: 2026-04-11
Repository: Fang

## 1) Baseline

- Current merge-base(develop, main): `ec2924e168f02074fa12997cfa0cafa7c8aa7c48`
- Commits unique to develop: `10`
- Commits unique to main: `3`

Unique commits (develop -> main not included):
- `882fe59` Merge pull request #4 from feat/embedding-phase
- `0b4f953` docs embedding updates
- `282dac3` unicode fix in E2E script
- `eba856a` vector type config + docs update
- `5298eb6` add E2E pipeline script
- `eaca4ab` chunk parent header enhancement
- `05d2107` ingestion flow for chunking/embedding
- `37dba77` OpenAI embedding batch integration
- `5494c5f` normalize vector config + embedding persistence
- `7109061` Merge pull request #2 from ai-core-chunking

Unique commits (main -> develop not included):
- `ed6aee0` Merge pull request #3 from feat/parser-multi-provider-3tier
- `ba86f52` README parser 3-tier update
- `ec33be2` parser 3-tier + retry + quality gate

## 2) Confirmed confusion points (old version retained)

Parser-related docs are older on develop and newer on main:
- `docs/system_architecture.md` -> develop still 2-tier (Gemini Flash -> Gemini Pro), main has 3-tier architecture update
- `docs/cv_parser_guide.md` -> develop old parser guide, main updated with 3-tier strategy
- `docs/cau_truc_thu_muc.txt` -> parser/doc structure updates present on main

## 3) Newer work on develop (not yet in main)

Embedding/chunking lane is newer on develop:
- `app/services/chunking.py`
- `app/services/embedding.py`
- `app/core/config.py` (vector config additions)
- `app/services/persistence.py` (embedding persistence updates)
- `database/schema_ai_core.sql` (vector-related schema updates)
- `docs/embedding_guide.md`
- `docs/embedding_strategy.md`
- `docs/input_processing_guide.md`
- `docs/fang-project-context-packaged.md`
- `test_chunking.py`
- `test_e2e_pipeline.py`
- `test_embedding.py`
- `test_ingestion_flow.py`
- `test_persistence.py`

## 4) Dry-run merge result (performed safely)

Action executed:
1. Created branch `reconcile/develop-main` from `main`
2. Ran `git merge --no-commit --no-ff develop`
3. Captured conflicts
4. Aborted merge via `git merge --abort`

Observed real conflicts:
- `app/api/routes_ingestion.py`
- `requirements.txt`

Interpretation:
- `routes_ingestion.py` is expected conflict hotspot (parser lane + embedding lane both touched orchestration)
- `requirements.txt` conflict is expected (main added parser deps, develop added embedding deps)

## 5) Recommended implementation path (safe)

### Phase A: parser lane keep from main
Keep parser 3-tier baseline from main for these files:
- `app/services/cv_parser.py`
- `app/services/cv_parser_adapters.py`
- `test_parser.py`
- `test_parser_db.py`
- `test_parser_policy.py`
- parser docs (`docs/system_architecture.md`, `docs/cv_parser_guide.md`, `docs/cau_truc_thu_muc.txt`)
- parser README section

### Phase B: embedding/chunking lane bring from develop
Integrate embedding/chunking updates from develop:
- `app/services/chunking.py`
- `app/services/embedding.py`
- vector config in `app/core/config.py`
- embedding persistence and schema updates
- embedding/chunking docs and tests

### Phase C: resolve hotspots manually
1. `app/api/routes_ingestion.py`
- keep parser 3-tier fallback behavior
- keep chunking/embedding pipeline steps
- verify end-to-end order: parse -> persist parsed -> chunk -> embed -> persist chunks

2. `requirements.txt`
- union dependencies from both lanes
- remove duplicates
- pin versions consistently

## 6) Verification checklist after each phase

Parser checks:
- `python -m unittest test_parser_policy.py`
- `python test_parser.py`
- `python test_parser_db.py`

Chunking/embedding checks:
- `python test_chunking.py`
- `python test_embedding.py`
- `python test_ingestion_flow.py`
- `python test_e2e_pipeline.py`
- `python test_persistence.py`

Quality checks:
- `ruff check .`

## 7) Root cause hypothesis

Most likely workflow issue:
- PR #2 (chunking lane) merged into develop
- PR #3 (parser 3-tier lane) merged into main
- develop did not receive PR #3 back, while main did not receive full embedding lane from develop

So this is branch divergence due to merge order asymmetry, not random reverse.

## 8) Next concrete step

Start real reconciliation on `reconcile/develop-main` with phased conflict resolution and checkpoint tests. Do not merge directly to main/develop before passing all checks.

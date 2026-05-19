# Synthetic Data Pipeline — Task Tracker

## Phase 0: Chuyển Embedding sang Gemini
- [x] Install `google-genai` SDK
- [x] Sửa `app/services/embedding.py` → Gemini provider
- [x] Sửa `app/core/config.py` → defaults Gemini
- [x] Sửa `.env` → EMBEDDING_PROVIDER=gemini
- [x] Test embedding trên 1-2 câu text

## Phase 0b: DB Reset Strategy
- [x] Tạo `database/seed_synth.sql` (companies + HRs + admin)
- [x] Sửa `scripts/reset_and_seed_db.py` → dùng seed_synth.sql
- [x] Chạy DB reset thành công (15 companies + 15 HRs)

## Phase 1-2: Pipeline Scaffolding + Models
- [x] Tạo `synthetic_data/` directory structure
- [x] `synthetic_data/__init__.py`
- [x] `synthetic_data/config.py`
- [x] `synthetic_data/models.py` (SyntheticCV, CVBatchResponse, SyntheticJob, JobBatchResponse)

## Phase 3-4: Personas + Prompts
- [x] `synthetic_data/personas.py` (8 personas + manifest generator, deterministic seed=42)
- [x] `synthetic_data/prompts.py` (CV + Job prompt templates với JSON schema embed)

## Phase 5: Generator
- [x] `synthetic_data/generator.py` (LLM client via 9Router, exponential backoff, cache)

## Phase 6: DB Writer
- [x] `synthetic_data/db_writer.py` (thin client, reuse FANG services)

## Phase 7: Embedder
- [x] Embedded trong db_writer.py (dùng `embed_chunks` từ app.services)

## Phase 8: CLI + Verifier
- [x] `synthetic_data/run_pipeline.py` (6 sub-commands: dry-run, generate-cvs, write-cvs, generate-jobs, write-jobs, full)
- [ ] `synthetic_data/verifier.py` (smoke test ranking sau khi write)

## Phase 9: Testing
- [x] Dry Run thành công (prompt validation + DB company check = 15)
- [ ] Generate CVs thực tế (--total 500)
- [ ] Write CVs to DB
- [ ] Generate Jobs (20 job postings)
- [ ] Write Jobs to DB
- [ ] Ranking smoke test (NMAIex J→C và C→J)

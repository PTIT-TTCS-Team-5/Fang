# Task Tracker

## Pha 0 — Chiến lược (Strategy Docs) ✔️
- [x] `FANG/docs/strategy/rag_query_strategy.md` — RAG query v2, 5-tier, 7 modelMode, ProTierGate, quality gate, context window (không sliding), context đa nguồn, system prompt
- [x] `FANG/docs/strategy/integration_strategy.md` — API contract v2 (đầy đủ), CORS, contextWarning, summarize/branch-new
- [x] `miCareer-mini/docs/candidate_apply_strategy.md` — Luồng ứng viên, Cloudinary, FANG v2 endpoints
- [x] Archive `rag_strategy.md` và `hr_guide.md` cũ vào `docs/archive/`
- [x] Cập nhật README của cả 2 dự án (FANG v2, thin client)
- [x] Commit: `feature/docs-strategy-v2` trên cả 2 repo

## Pha 1 — Nền tảng FANG ✔️
- [x] Cụm 5: Nâng parser 3→5 tier, mở rộng MODEL_CANDIDATES (Pro tier: gemini-pro, gpt-5.4)
- [x] Cụm 5: ProTierGate — `_should_escalate_to_pro()` trong `cv_parser.py`
- [x] Cụm 5: Tạo `rag_model_adapters.py` (Gemini/OpenAI/Anthropic generation adapter, MODEL_MODE_REGISTRY)
- [x] Cụm 5: Tạo `rag_orchestrator.py` (auto-lite / auto-pro / specific mode + quality gate)
- [x] Cụm 5: Mở rộng `config.py` với RAG query + CORS + context window settings
- [x] Commit: `feature/docs-strategy-v2` FANG
- [x] Cụm 1: Tạo schema `AICHATCONVERSATION` + `AICHATMESSAGE` + cập nhật `AIQUERYLOG`
- [x] Cụm 1: Tạo `models/chat.py` (request/response) + `routes_chat.py` (5 endpoints)
- [x] Cụm 1: Tạo `rag_query.py` (12-step pipeline: context đa nguồn + vector search + system prompt)
- [x] Cụm 1: Tạo `chat_persistence.py` (conversation + message CRUD + audit log)
- [x] Cụm 1: Cập nhật `main.py` — CORS middleware + v2 routes + v1 backward-compatible
- [x] Commit: `feature/docs-strategy-v2` FANG — Pha 1 Cụm 1
- [x] Guide docs: `rag_query_guide.md`, `integration_guide.md` — Cẩm nang vận hành v2

## Pha 2 — Tích hợp miCareer-mini ✔️
- [x] Cụm 3: Tạo `core/fang_client.py` (chat_query, list_conversations, get_messages, summarize, branch-new, trigger_ingestion, poll)
- [x] Cụm 3: Xóa `core/ai.py`, refactor `core/db.py` (giữ relational, thêm candidate queries, xóa vector/log)
- [x] Cụm 3: Rewrite `app.py` — HR chat gọi FANG API, 7 modelMode selectbox, context warning + summarize/branch-new UI
- [x] Cụm 3: Cập nhật `.env` (FANG_API_URL, Cloudinary vars) + `requirements.txt` (bỏ langchain/openai/anthropic)

## Pha 3 — Luồng Candidate ✔️
- [x] Cụm 4: Tạo `core/cloudinary_upload.py` (upload PDF, trả secure URL)
- [x] Cụm 4: Thêm candidate login + jobs browsing (page_login_candidate, page_candidate_jobs)
- [x] Cụm 4: Implement apply flow + CV upload (page_candidate_apply, check CV cũ, upload mới)
- [x] Cụm 4: Polling trạng thái ingestion (progress bar, timeout handling)
- [x] Cụm 4: HR xem trạng thái CV processing (ingestion badge trong app_detail)
- [x] Guide: `candidate_apply_guide.md`

## Verification
- [ ] Smoke test: chat API E2E
- [ ] Smoke test: candidate apply → HR chat
- [ ] Unit tests: rag_orchestrator, chat_manager

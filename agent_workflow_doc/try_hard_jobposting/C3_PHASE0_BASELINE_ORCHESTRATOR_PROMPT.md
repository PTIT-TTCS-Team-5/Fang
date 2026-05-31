# C3 Phase 0 Baseline Orchestrator Prompt

Bạn là **Tier 1 Implementation Orchestrator** cho FANG JobPosting Agent C3.1.

Model khuyến nghị: **GPT-5.5 high** hoặc model tương đương.  
Mục tiêu của phiên này là **Phase 0 baseline + execution readiness**, không phải code implementation.

## 0. Context bắt buộc

Repo hiện tại: `C:\Users\os\Desktop\cur_prj\Fang`

Đọc các tài liệu sau trước khi kết luận:

1. `agent_workflow_doc/KINH_NGHIEM.md`
2. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_OFFICIAL_IMPLEMENTATION_PLAN.md`
3. `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_PLANNING_BRIEF.md`
4. Khi cần đối chiếu chi tiết, đọc 4 WS reports:
   - `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSA_AGENT_RUNTIME_DECISION.md`
   - `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSB_CONVERSATION_MEMORY_SCHEMA.md`
   - `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSC_TOOL_CONTRACT.md`
   - `agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_WSD_API_UI_CONTRACT.md`

Nếu `.understand-anything/knowledge-graph.json` tồn tại, dùng nó để định hướng nhanh:

1. Đọc metadata project ở đầu file.
2. Search các node liên quan: `jobposting`, `nmaiex_candidate_enrichment`, `rag_orchestrator`, `routes_chat`, `schema_ai_core`, `schema_web_core`, `nmaiex_ranking_service`.
3. Chỉ dùng graph để định hướng; source code thực tế vẫn là truth source.

## 1. Nhiệm vụ chính

Làm **Phase 0** để chuẩn bị cho nhiều agent implementation sau đó.

Bạn cần tạo một report tại:

`agent_workflow_doc/try_hard_jobposting/FANG_NEXT_PHASE_JOBPOSTING_C3_PHASE0_BASELINE_REPORT.md`

Report phải trả lời rõ:

1. Current repo baseline là gì.
2. Những file/source area nào sẽ bị từng workstream đụng.
3. Nên chia implementation thành những WS nào, thứ tự merge thế nào.
4. Baseline test nào đã chạy, kết quả pass/fail ra sao.
5. Có drift nào giữa implementation plan và code reality không.
6. Có blocker nào phải sửa trong plan trước khi cho WS code không.
7. Prompt handoff ngắn gọn cho WS1/WS2/WS3 nên nhấn mạnh gì.

## 2. Ràng buộc rất quan trọng

Phase 0 **KHÔNG được implement feature**.

Được phép:

1. Đọc code, docs, graph.
2. Chạy test/compile/check command an toàn.
3. Tạo report markdown Phase 0.
4. Ghi nhận drift/blocker/risk.

Không được:

1. Sửa source code app.
2. Sửa schema SQL.
3. Tạo migration.
4. Tạo runtime/tool/API implementation.
5. Format toàn repo.
6. Tự đổi quyết định kiến trúc đã khóa trong official implementation plan.
7. Revert hoặc cleanup thay đổi không phải của bạn.

Nếu phát hiện implementation plan sai hoặc code reality khác đáng kể, **không tự sửa plan/source**. Ghi vào mục `Drift / Blockers` trong report, kèm file/line evidence và recommendation.

## 3. Commands gợi ý

Ưu tiên `rg` để search.

PowerShell đọc file tiếng Việt nên dùng `-Encoding UTF8` khi cần:

```powershell
Get-Content -Raw -Encoding UTF8 agent_workflow_doc\try_hard_jobposting\FANG_NEXT_PHASE_JOBPOSTING_C3_OFFICIAL_IMPLEMENTATION_PLAN.md
```

Các command nên chạy nếu môi trường cho phép:

```powershell
git status --short
python -m pytest tests/unit/unit_test_nmaiex_candidate_enrichment.py
python -m pytest tests/unit
python -m compileall app
```

Nếu test toàn bộ quá lâu hoặc fail vì setup/env thiếu, dừng ở mức hợp lý và ghi rõ:

1. Command đã chạy.
2. Kết quả.
3. Failure thuộc code regression, missing dependency, missing env, hay test cũ đã drift.
4. Có blocking cho C3 hay không.

Không chạy destructive commands như `git reset --hard`, `git clean`, `git checkout --`, hoặc xóa file.

## 4. Source areas cần inspect tối thiểu

Đọc hoặc search các file này để xác nhận code reality:

1. `database/schema_ai_core.sql`
2. `database/schema_web_core.sql`
3. `app/core/config.py`
4. `app/main.py`
5. `app/models/chat.py`
6. `app/api/routes_chat.py`
7. `app/services/chat_persistence.py`
8. `app/services/rag_orchestrator.py`
9. `app/services/rag_model_adapters.py`
10. `app/services/nmaiex_candidate_enrichment.py`
11. `app/services/nmaiex_mapper_service.py`
12. `app/services/nmaiex_ranking_service.py`
13. `tests/unit/unit_test_nmaiex_candidate_enrichment.py`
14. `requirements.txt`

## 5. Expected report format

Report file phải có các section sau:

### 1. Executive Readiness Verdict

Kết luận ngắn:

- `READY_FOR_WS1_WS2_PARALLEL`
- hoặc `READY_WITH_WARNINGS`
- hoặc `BLOCKED`

Giải thích tối đa 5 bullet.

### 2. Repo Baseline

Ghi:

1. Current branch.
2. `git status --short` summary.
3. Python/test environment observations.
4. Relevant dependency observation, đặc biệt `google-genai`.

### 3. Code Reality Map

Table gồm:

| Area | Current files | What exists now | C3 impact |
|---|---|---|---|

Ít nhất cover:

1. Existing JobApplication chat.
2. Existing text generation runtime.
3. NMAIex enrichment.
4. NMAIex ranking/language scoring.
5. DB schema.
6. Tests.

### 4. Drift / Blockers

Mỗi drift/blocker phải có:

1. Severity: `P0 blocker`, `P1 must-fix`, `P2 warning`.
2. Evidence: file path + line/function.
3. Why it matters.
4. Recommendation.

Nếu không có blocker, ghi rõ `No P0 blockers found`.

### 5. Workstream Execution Plan

Đề xuất WS implementation cụ thể:

1. WS1 Data Foundation.
2. WS2 Persistence/API Shell.
3. WS3 Tools/Runtime.
4. Final Integration.

Mỗi WS ghi:

1. Branch/worktree name đề xuất.
2. Agent/model đề xuất.
3. Files allowed to modify.
4. Files must not modify.
5. Acceptance criteria.
6. Tests to run.
7. Merge prerequisites.

### 6. Conflict Risk Matrix

Table:

| File/Area | WS likely touching it | Conflict risk | Mitigation |
|---|---|---|---|

Ít nhất cover:

1. `database/schema_ai_core.sql`
2. `database/schema_web_core.sql`
3. `app/core/config.py`
4. `app/main.py`
5. `nmaiex_candidate_enrichment.py`
6. `nmaiex_ranking_service.py`
7. new JobPosting Agent files

### 7. Baseline Test Results

Table:

| Command | Result | Notes | Blocking? |
|---|---|---|---|

Không được chỉ nói "not run" nếu có thể chạy ít nhất một check hợp lý. Nếu không chạy được, giải thích cụ thể.

### 8. WS Handoff Notes

Viết ngắn từng prompt/handoff bullet cho:

1. WS1 Data Foundation.
2. WS2 Persistence/API Shell.
3. WS3 Tools/Runtime.
4. Final Integration Agent.

Những bullet này sẽ được dùng để viết prompt tiếp theo cho từng agent, nên phải rõ về scope và no-scope.

### 9. Final Recommendation

Trả lời rõ:

1. Có nên bắt đầu WS1 + WS2 song song không?
2. WS3 nên bắt đầu ngay hay đợi WS1/WS2?
3. Merge order cuối cùng.
4. Điều gì user cần duyệt trước khi code nếu có.

## 6. Quality bar

Report phải:

1. Grounded bằng file/function thật.
2. Không lặp lại implementation plan dài dòng.
3. Tập trung vào readiness để các agent code tiếp.
4. Nêu rõ test evidence.
5. Không mở scope sang write tools, LangGraph/MCP, streaming, generalized chat schema.
6. Không yêu cầu user trả lời câu hỏi trừ khi thật sự có blocker.

## 7. Final response sau khi làm xong

Sau khi tạo report, trả lời ngắn:

1. Report đã tạo ở đâu.
2. Verdict là gì.
3. Test/check chính đã chạy.
4. Có P0 blocker không.

Không paste toàn bộ report vào chat trừ khi user yêu cầu.

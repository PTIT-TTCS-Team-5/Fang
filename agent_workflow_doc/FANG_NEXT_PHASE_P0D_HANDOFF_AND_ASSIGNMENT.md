# P0-D Handoff and Assignment Synthesis

## Brief

P0-D là bước tổng hợp sau P0-A/B/C để chốt rằng repo đã đủ rõ cho handoff, tạo file giao việc trực tiếp cho thành viên, và giữ lại các quyết định còn mở.

Trạng thái hiện tại: P0-A/B/C đủ tốt để giao hai cụm việc chính:

1. `P1_A_B_inc` - Prompt Review + Minimal Eval.
2. `CHAT_FULL_CV` - JobApplication Full-CV Chat.

## P0-A/B/C final check

### P0-A - Repo Reality Audit

Kết luận: Oke để dùng làm input handoff.

Điểm đã xử lý hoặc đã có quyết định:

1. Current runtime reality đã được dựng lại: ingestion, RAG chat hiện tại, parser, generation, embedding, NMAIex ranking/management.
2. User notes đã được gom trong `FANG_NEXT_PHASE_P0A_USER_NOTE_TRIAGE.md`.
3. Các mục giao cho `P1_A_B_inc` và `CHAT_FULL_CV` đã được tách riêng.
4. Các checklist historical NMAIex đã được archive, không còn là truth source active.

Rủi ro còn lại không chặn handoff:

1. Một số nội dung trong P0-A report vẫn mô tả trạng thái cũ tại thời điểm audit. Khi giao việc, dùng P0-A report để truy vết, không dùng làm status mới nhất.
2. JobPosting Agent vẫn là decision track riêng, chưa giao implementation.

### P0-B - AI/LLM Inventory

Kết luận: Oke để làm input chính cho P1-A/B.

Điểm mạnh:

1. Có master use-case inventory.
2. Có prompt location index P1-P10.
3. Có model/fallback map.
4. Có structured output/schema index.
5. Có failure handling gaps và observability gaps.
6. Có priority prompt list cho P1-A.

Rủi ro còn lại không chặn handoff:

1. Line references có thể drift nếu code đổi sau report, nên owner P1-A/B phải verify lại bằng code hiện tại.
2. P0-B là inventory, không phải prompt strategy cuối cùng. Owner P1-A/B phải nộp strategy-level doc mới.

### P0-C - Documentation Reconciliation

Kết luận: Oke để dùng làm baseline docs hiện tại.

Điểm đã reconcile:

1. NMAIex là module chính thức trong FANG.
2. Embedding docs đã chuyển sang Gemini `gemini-embedding-001`, 1536 dims mặc định.
3. Parser và generation đã được tách rõ trong docs: parser 5-tier + ProTierGate, generation 7 `modelMode`.
4. NMAIex enrichment sidecar đã được ghi nhận.
5. Canonical route management đã được document.
6. RAG docs đã note full-CV là quyết định đã chốt nhưng chưa implement.
7. AI workflow init đã cập nhật, research docs không còn là mandatory runtime truth.

Rủi ro còn lại không chặn handoff:

1. RAG docs vẫn mô tả top-k pipeline hiện tại vì `CHAT_FULL_CV` chưa implement.
2. Context budget và multi-source context vẫn là drift D2, đã giao cho `CHAT_FULL_CV` + `P1_A_B_inc`.
3. Một vài references historical cần được giữ rõ là archive, không phải source hiện tại.

## Verification vừa chạy

Ngày kiểm tra: 2026-05-24.

Lệnh đã chạy:

```powershell
venv\Scripts\python -m unittest discover -s tests/unit -p "unit_test_*.py"
venv\Scripts\python -m compileall app scripts tests\unit
```

Kết quả:

1. Unit suite pass: 29 tests.
2. Compile `app`, `scripts`, `tests/unit` sạch.
3. Không chạy smoke/API/DB trong P0-D này vì scope là handoff docs; full system test trước đó đã được archive tại `agent_workflow_doc/archive/walkthrough_full_system_test.md`.

## Assignment đã sẵn sàng

### 1. P1_A_B_inc

File giao việc:

`agent_workflow_doc/FANG_NEXT_PHASE_P1A_PROMPT_REVIEW_AND_MIN_EVAL.md`

Yêu cầu bắt buộc:

1. Nộp prompt review report.
2. Nộp tài liệu strategy-level cho prompt engineering.
3. Nộp minimal eval seed cases.
4. Phối hợp với `CHAT_FULL_CV` cho prompt/eval của luồng full-CV.

### 2. CHAT_FULL_CV

File giao việc:

`agent_workflow_doc/FANG_NEXT_PHASE_CHAT_FULL_CV_ASSIGNMENT.md`

Yêu cầu bắt buộc:

1. Implement chuyển JobApplication chat sang full CV markdown context.
2. Nộp implementation report.
3. Nộp strategy-level document.
4. Nộp guide-level document.
5. Cập nhật tests/docs/UI client nếu cần.

## Thành viên thứ ba nên làm gì?

Khuyến nghị: chưa giao JobPosting Agent implementation cho thành viên thứ ba. Track đó vẫn cần user/tier 1 quyết định kiến trúc.

### Option A - miCareer-mini + API contract readiness (khuyến nghị)

Giao thành viên thứ ba rà và chuẩn bị `miCareer-mini` cho hai workstream đang chạy:

1. Kiểm tra UI hiện tại có wording nào nói "RAG chunks" hoặc giả định top-k không.
2. Kiểm tra client xử lý `contextWarning`, `topK=0`, model/fallback/latency như thế nào.
3. Chuẩn bị UI smoke checklist cho `CHAT_FULL_CV`.
4. Cập nhật docs frontend nếu cần.
5. Không tự đổi backend FANG.

Lý do nên chọn: ít đụng core, giảm conflict với hai thành viên chính, nhưng trực tiếp giúp nghiệm thu full-CV chat.

### Option B - Test/QA pack cho CHAT_FULL_CV

Giao thành viên thứ ba viết checklist/test plan trước, chờ backend branch của `CHAT_FULL_CV` để chạy:

1. Case chat từ full CV.
2. Case thiếu dữ liệu.
3. Case prompt injection trong CV/JD/email.
4. Case context budget vượt ngưỡng.
5. Case legacy parsed CV thiếu field mới.

Lý do nên chọn: tốt nếu thành viên này mạnh kiểm thử hơn code.

### Option C - NMAIex language/proficiency gap analysis

Giao một report nhỏ về gap `normalize_proficiency()` chưa được gọi trong scoring:

1. Đọc `nmaiex_mapper_service.py`, `nmaiex_ranking_service.py`, NMAIex docs.
2. Viết report + strategy-level mini doc về cách đưa normalization vào ranking/enrichment.
3. Chưa implement nếu chưa có user duyệt.

Lý do nên chọn: độc lập với full-CV chat, nhưng có giá trị cho ranking quality.

### Option D - JobPosting Agent decision research

Chỉ nên giao nếu thành viên đủ mạnh phân tích kiến trúc và user muốn mở track này:

1. Không implement.
2. Viết decision memo so sánh dừng ở AI Ranking + JobApplication Full-CV Chat với mở JobPosting Agent.
3. Phân tích tool boundary, permission, data access, token cost, MCP/LangGraph/adapter options.

Lý do chưa khuyến nghị mặc định: đây là quyết định tier 1, dễ kéo team vào framework/agent khi core full-CV và prompt eval chưa xong.

## Quy tắc handoff chung cho mọi thành viên

1. Phải đọc `agent_workflow_doc/README.md` trước.
2. Phải nộp report bằng tiếng Việt.
3. Với workstream có thay đổi architecture/behavior, phải nộp tài liệu strategy-level tương đương chất lượng `docs/strategy/*`.
4. Không dùng `docs/research` hoặc `archive` làm current runtime truth.
5. Không tự mở rộng scope sang JobPosting Agent, 9Router hoặc framework mới nếu assignment không ghi rõ.
6. Nếu phát hiện conflict giữa docs và code, ưu tiên code hiện tại và ghi conflict trong report.

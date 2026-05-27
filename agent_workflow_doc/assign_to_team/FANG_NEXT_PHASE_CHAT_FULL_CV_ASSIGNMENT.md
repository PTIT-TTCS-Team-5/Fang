# CHAT_FULL_CV Assignment - JobApplication Full-CV Chat

## Brief

Bạn phụ trách cụm `CHAT_FULL_CV`: chuyển luồng chat trên một `JobApplication` từ fixed top-k chunk RAG sang full CV markdown context.

Đây là feature/change package riêng. Mục tiêu là giữ luồng chat JobApplication đơn giản, đầy đủ evidence hơn top-k chunks, và vẫn bảo toàn ingestion/chunking/embedding cho ranking và các use case khác (ví dụ nmaiex ranking vẫn cần các CV embedded chunk đó nhé)

## Cách đọc tài liệu

Đọc theo thứ tự dưới đây trước khi sửa code:

1. `agent_workflow_doc/README.md`
2. `agent_workflow_doc/KINH_NGHIEM.md`
3. `README.md`
4. `../miCareer-mini/README.md`
5. `docs/system_architecture.md`
6. `agent_workflow_doc/FANG_NEXT_PHASE_DECISIONS.md`
7. `agent_workflow_doc/FANG_NEXT_PHASE_P0A_USER_NOTE_TRIAGE.md`
8. `agent_workflow_doc/P0B_AI_LLM_INVENTORY_REPORT.md`
9. `agent_workflow_doc/P0C_DOC_RECONCILIATION_PLAN.md`
* NOTE FROM HƯNG: Cái 6-7-8-9 này khuyên ng ae dùng AI để hỗ trợ đọc hiểu nhé
10. RAG/API docs:
    - `docs/strategy/rag_query_strategy.md`
    - `docs/guide/rag_query_guide.md`
    - `docs/strategy/integration_strategy.md`
    - `docs/guide/integration_guide.md`
11. Code entry points:
* NOTE FROM HƯNG: Cái này cũng thế, đọc hết code là chớ đấy =)) 
    - `app/api/routes_chat.py`
    - `app/services/rag_query.py`
    - `app/services/markdown_builder.py`
    - `app/services/chat_persistence.py`
    - `app/services/rag_orchestrator.py`
    - `app/services/rag_model_adapters.py`
    - `app/models/chat.py`
    - `database/schema_ai_core.sql`
    - `database/schema_web_core.sql`
12. Frontend/client liên quan:
* NOTE FROM HƯNG: Cái này cũng thế
    - `../miCareer-mini/core/fang_client.py`
    - `../miCareer-mini/app.py`

Nếu cần truy vết note ban đầu của user, đọc thêm `agent_workflow_doc/FANG_NEXT_PHASE_P0A_REPO_REALITY_AUDIT_REPORT.md` và tìm `CHAT_FULL_CV`.
* NOTE FROM HƯNG: Ý là vào file này Ctrl + f nhé, những chỗ mình đánh dấu là chỗ mình chỉ định thuộc phần việc này đấy

## Nguồn chuẩn

1. Quyết định đã chốt: `JobApplication` chat dùng full CV markdown context, không còn fixed top-k chunk RAG cho câu hỏi đơn ứng viên.
2. P0-B inventory là nguồn chuẩn cho prompt/model/fallback và rủi ro LLM.
3. Code hiện tại vẫn là truth source cho schema/API thực tế.
4. `docs/research` và tài liệu archive không phải runtime truth.

## Scope bắt buộc

1. Đổi `process_chat_query()` để chat JobApplication lấy full CV markdown thay vì embed prompt rồi vector search top-k chunks.
2. Giữ ingestion/chunking/embedding hiện tại cho lưu trữ, ranking và các use case khác. Không xóa `AIDOCUMENTCHUNK`.
3. Dựng full CV markdown từ `CVPARSED.parsedJson` bằng `app/services/markdown_builder.py:convert_json_to_markdown()`.
4. Có fallback rõ nếu parsed JSON legacy/invalid:
   - ưu tiên parse `parsedJson` thành `ParsedCV` rồi convert sang markdown,
   - nếu không convert được nhưng có `rawText`, dùng `rawText` làm degraded context và ghi warning/log,
   - nếu không có cả hai, trả lỗi rõ thay vì gọi LLM với context rỗng.
5. Fetch thêm context ngoài CV:
   - JobPosting: title, description và các field có sẵn liên quan tới salary/work mode/location/level/skill nếu schema hỗ trợ.
   - Candidate profile: thông tin cơ bản và skills.
   - ATS history: interview feedback hiện có.
   - Offer và EmailLog: user đã note phải đưa vào scope, nhưng cần kiểm tra kỹ schema và giới hạn số lượng nội dung đưa vào prompt.
6. Thiết kế prompt mới cho full-CV chat:
   - CV/JD/ATS/email là untrusted input.
   - Model chỉ trả lời dựa trên evidence.
   - Khi thiếu dữ liệu phải nói rõ.
   - Không ra quyết định tuyển dụng tuyệt đối hoặc suy đoán nhạy cảm.
* NOTE FROM HƯNG: mình bổ sung là phải xác định phạm vi AI có thể hỗ trợ nhé. Luồng chat cũ bảo nó viết Code nó cũng viết đấy =)) -> Rủi ro user abuse -> phải fix. Mà về Prompt eng thì phối hợp với người làm P1_A_B_inc nha ( Mai )
7. Context budget phải tính cả system prompt/full CV context, history và user prompt. Không chỉ tính history.
8. Khi vượt budget threshold, behavior phải rõ:
   - không âm thầm gọi LLM với context quá lớn,
   - trả `contextWarning` và response deterministic hướng dẫn HR tóm tắt/branch/new conversation nếu cần,
   - giữ response schema backward-compatible nhất có thể.
* NOTE FROM HƯNG: Hoặc có thể là cơ chế auto-compact như Codex, thấy cũng khá tiện HR đỡ phải đọc warining rồi chọn làm gì cho mệt. Nhưng mà thôi có sẵn rồi thì bro có thể tận dụng, sao cho UI/UX hợp lý là đc.
9. Cập nhật tests và docs tương ứng.
10. Kiểm tra `miCareer-mini` có cần chỉnh hiển thị `topK`, `contextWarning`, hoặc wording "RAG chunks" không.

## Scope nên giữ nhỏ

1. Không implement JobPosting Agent.
2. Không đưa LangGraph/MCP/agent framework vào luồng này.
3. Không đổi provider/model routing ngoài những gì cần cho budget/prompt.
4. Không xóa route/API cũ nếu không cần.
5. Không làm prompt review toàn hệ thống; phần đó thuộc `P1_A_B_inc`.

## Data source decision cho phase này

Phase này dùng cách ít rủi ro nhất: rebuild markdown tại query time từ `CVPARSED.parsedJson`.

Lý do:

1. Không cần migration DB ngay.
2. Tái dùng converter đã có.
3. Dễ test bằng unit test.
4. Nếu sau này cần performance/observability tốt hơn, có thể thêm cột hoặc artifact lưu `cvMarkdown` sau.

Nếu khi implement phát hiện legacy `parsedJson` không parse được qua `ParsedCV`, ghi rõ case đó trong report và dùng fallback `rawText` có kiểm soát.

## Deliverables

Bạn phải nộp report và tài liệu strategy-level, không chỉ code patch.

1. **Implementation report**
   - Việc đã làm.
   - File/code paths đã sửa.
   - Behavior trước/sau.
   - Test đã chạy.
   - Rủi ro còn lại và open questions.
2. **Strategy-level document**
   - Đề xuất file: `docs/strategy/job_application_full_cv_chat_strategy.md`.
   - Nội dung phải tương đương tài liệu strategy hiện có: mục tiêu, quyết định, data source, prompt policy, context budget, fallback, security, API compatibility, frontend impact, tests và risks.
3. **Guide-level document**
   - Đề xuất file: `docs/guide/job_application_full_cv_chat_guide.md`.
   - Nội dung hướng dẫn vận hành/dev: request flow, DB source, response behavior, troubleshooting, cách test.
4. **Tests**
   - Unit test cho full-CV context source.
   - Unit test xác nhận chat path không gọi embedding/vector search trong luồng JobApplication full-CV.
   - Unit test cho fallback `rawText`.
   - Unit test cho context budget tính cả system prompt.
   - Nếu sửa UI/client, có test/checklist smoke tương ứng.
5. **Docs update**
   - Cập nhật `docs/strategy/rag_query_strategy.md` và `docs/guide/rag_query_guide.md` để không còn mô tả full-CV như future-only sau khi code đã đổi.
   - Nếu thay API response behavior, cập nhật `docs/strategy/integration_strategy.md` và `docs/guide/integration_guide.md`.

## Acceptance criteria

1. `/v2/chat/query` vẫn hoạt động với `jobAppId` đã ingestion `SUCCESS`.
2. Luồng chat không còn embed prompt + vector search top-k chunks cho JobApplication full-CV.
3. Full CV markdown xuất hiện trong system prompt/context theo data source đã chốt.
4. Offer/EmailLog được đưa vào context hoặc có report giải thích rõ vì sao chưa đưa được trong phase này.
5. Context budget tính cả system prompt và có behavior rõ khi vượt ngưỡng.
6. Response schema không làm hỏng `miCareer-mini` hoặc đã có patch frontend/client đi kèm.
7. Unit tests pass và compile sạch.
8. Có implementation report, strategy-level doc và guide-level doc.
9. Không claim JobPosting Agent đã implement.

## Phối hợp với P1_A_B_inc

Owner `CHAT_FULL_CV` tự đảm bảo prompt mức cơ bản để feature chạy an toàn. Sau đó owner `P1_A_B_inc` review/nâng cấp prompt và bổ sung eval seed.

Nếu hai người làm song song, `CHAT_FULL_CV` cần cung cấp sớm:

1. Draft system prompt full-CV.
2. Context blocks thực tế.
3. Budget behavior.
4. API response behavior khi over budget.

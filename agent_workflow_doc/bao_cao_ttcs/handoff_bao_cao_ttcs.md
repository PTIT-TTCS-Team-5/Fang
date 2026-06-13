# Handoff - Báo cáo TTCS FANG AI Core

> Mục đích: tài liệu chuyển tiếp cho chat mới tiếp tục làm báo cáo.
> Cập nhật gần nhất: 2026-06-13.
> Phạm vi hiện tại: lập cấu trúc báo cáo, blueprint evidence/sơ đồ, chưa viết bản hoàn chỉnh lần 1 cho chương nào.

## 1. Bối cảnh làm việc

Người dùng đang chuẩn bị báo cáo cuối kỳ môn Thực tập cơ sở PTIT cho dự án FANG. Báo cáo ưu tiên viết theo phong cách học thuật, có cấu trúc, có evidence từ code/tài liệu/test, không viết quá ngắn, không cần cố định số trang. Slide và phân công thành viên để sau.

Sản phẩm chính cần trình bày là **FANG - backend/AI Core**. `miCareer-mini` chỉ là frontend mỏng/dev-test UI để chứng minh FANG có thể tích hợp vào frontend thật qua API. Không nên mô tả `miCareer-mini` như sản phẩm trung tâm của nhóm.

Luận điểm nền:

- FANG là AI Core API-first, xử lý ingestion, ranking, chat và agent.
- Frontend thật chỉ cần gọi API, gửi URL/CV, polling trạng thái và hiển thị kết quả.
- Workflow HR hiện tại được "supercharge" bằng AI layer, nhưng FANG không thay thế quyết định tuyển dụng của HR.
- Các claim về AI phải thận trọng: synthetic data, LLM judge, prompt/model dependency và tuning chỉ là bằng chứng thử nghiệm trong phạm vi dự án.

## 1.1. Quy ước viết chương trong chat mới

Không gọi sản phẩm viết là "nháp" theo nghĩa làm sơ sài. Workflow đúng là:

1. Viết **bản hoàn chỉnh lần 1** cho từng chương hoặc từng cụm mục.
2. Người dùng review về giọng văn, độ dài, mức chi tiết, cách dẫn evidence và cách gọi FANG/`miCareer-mini`.
3. Nhận xét của người dùng trở thành style guide cho các chương sau.
4. Sau khi đã học được gu viết, mới viết các chương tiếp theo với cùng chuẩn.

Khi viết nội dung báo cáo để người dùng copy sang DOCX, không viết bằng Markdown. Nên tạo file `.txt` hoặc trả plain text theo cấu trúc rõ ràng. Các đối tượng không phải văn xuôi phải đánh dấu rõ:

- `[BẢNG - tên bảng]`: sau đó đưa nội dung bảng hoặc mô tả bảng.
- `[HÌNH - tên hình]`: sau đó mô tả hình/screenshot/sơ đồ cần chèn.
- `[SƠ ĐỒ - tên sơ đồ]`: sau đó đưa Mermaid/text description hoặc prompt tạo hình.
- `[GHI CHÚ EVIDENCE]`: ghi file/code/test dùng làm căn cứ, không nhất thiết đưa vào thân bài nếu làm báo cáo DOCX.

File quy ước riêng đã tạo: `agent_workflow_doc/bao_cao_ttcs/quy_uoc_viet_bao_cao.txt`.

## 2. File đã tạo/sửa trong thư mục `bao_cao_ttcs`

Thư mục làm việc:

`C:\Users\os\Desktop\cur_prj\Fang\agent_workflow_doc\bao_cao_ttcs`

File hiện có:

1. `bao_cao_ttcs_outline.md`
   - Bản outline cấp cao.
   - Đã có phần mở đầu đặc biệt và 5 chương chính.
   - Đã thêm candidate-side NMAIex ranking trước khi apply.
   - Đã thêm Chương 4 về kiến trúc mã nguồn/tổ chức code.

2. `bao_cao_ttcs_blueprint.md`
   - Bản chi tiết hơn: mục lục cấp 2/cấp 3, evidence matrix, sơ đồ Mermaid/text, danh sách ảnh demo nên chụp.
   - Đã có sơ đồ FANG-centered, code architecture, ingestion, NMAIex hai chiều, candidate pre-apply ranking, JobApplication Chat, JobPosting Agent, QA workflow.

3. `handoff_bao_cao_ttcs.md`
   - File handoff hiện tại.

## 3. Cấu trúc báo cáo đã chốt

### Phần mở đầu - Động lực xây dựng FANG

Không gọi là chương. Mục đích là đặt tone cho báo cáo:

- Mô tả workflow HR: quản lý job, nhận hồ sơ, đọc CV, lọc/so sánh ứng viên, hỏi đáp, theo dõi trạng thái.
- Nêu điểm nghẽn: CV nhiều, thông tin thiếu chuẩn hóa, khó truy xuất evidence, khó so sánh nhất quán.
- Dẫn vào FANG như AI Core hỗ trợ workflow này.

### Chương 1 - Phạm vi dự án và kiến trúc FANG AI Core

Nói về runtime/system architecture:

- FANG là sản phẩm chính.
- `miCareer-mini` là thin client/dev-test UI.
- API-first, thin client.
- Kiến trúc tổng thể FANG.
- FANG ingestion.
- Thiết kế dữ liệu AI Core.

### Chương 2 - Các năng lực AI chính của FANG

Nói về các module AI:

- NMAIex Ranking hai chiều.
- Candidate-side NMAIex flow trước khi apply.
- Synthetic data, ground truth và tuning.
- JobApplication Chat theo `jobAppId`.
- JobPosting Agent theo `jobPostId`.
- Trade-off giữa ranking/chat/agent.

### Chương 3 - Quy trình kỹ thuật, tài liệu và kiểm thử

Nói về engineering process:

- Hệ thống tài liệu: `docs/strategy`, `docs/guide`, `agent_workflow_doc`, `docs/research`.
- Unit tests và smoke/E2E tests.
- Postman API verification.
- Playwright/Chrome DevTools full-app QA qua `miCareer-mini`.
- AI-specific QA: grounding, scope, prompt injection, PII masking, provider stop, cost control.

### Chương 4 - Kiến trúc mã nguồn và tổ chức triển khai

Đây là phần mới được thêm sau nhận xét cuối. Phần này là cần thiết trong báo cáo kỹ thuật.

Phân biệt với Chương 1:

- Chương 1: hệ thống chạy như thế nào ở mức runtime/API/data flow.
- Chương 4: codebase được tổ chức như thế nào, module nào chịu trách nhiệm gì, code-docs-tests trace ra sao.

Nội dung:

- Cấu trúc thư mục backend FANG: `app/api`, `app/models`, `app/services`, `app/core`, `database`, `tests`, `smoke_tests`, `docs`, `agent_workflow_doc`.
- Mapping API -> service -> data.
- Module boundary theo scope: `jobAppId`, `jobPostId`, J->C/C->J.
- Quan hệ giữa code, docs và tests.

### Chương 5 - Demo tích hợp, đánh giá và định hướng phát triển

Demo dùng `miCareer-mini` như client tích hợp, không làm lệch trọng tâm khỏi FANG.

Thứ tự demo đã chỉnh:

1. Candidate xem hồ sơ/CV hiện có.
2. Candidate dùng NMAIex C->J ranking để xem job gợi ý trước khi apply.
3. Candidate chọn job, apply bằng CV hiện có hoặc upload CV mới.
4. FANG ingestion xử lý CV.
5. HR chạy NMAIex J->C ranking cho job.
6. HR chọn ứng viên nổi bật từ ranking, mở application detail, dùng JobApplication Chat.
7. HR dùng JobPosting Agent theo `jobPostId` để hỏi top candidates/compare/filter.

Lý do đổi thứ tự: ranking trước rồi chọn ứng viên để chat sẽ liên kết mạch demo tốt hơn.

## 4. Evidence anchors quan trọng

### FANG architecture/integration

- `README.md`
- `docs/system_architecture.md`
- `docs/strategy/integration_strategy.md`
- `app/main.py`
- `app/api/routes_ingestion.py`
- `app/api/routes_chat.py`
- `app/api/nmaiex_routes_ranking.py`
- `app/api/routes_jobposting_agent.py`

### Data/ingestion

- `app/models/ingestion.py`
- `database/schema_ai_core.sql`
- `database/schema_web_core.sql`
- `docs/guide/database_guide.md`
- `docs/guide/input_processing_guide.md`

### NMAIex ranking

- `docs/strategy/nmaiex_ranking_strategy.md`
- `docs/guide/nmaiex_ranking_guide.md`
- `app/services/nmaiex_ranking_service.py`
- `app/api/nmaiex_routes_ranking.py`
- `app/models/nmaiex_schemas.py`
- `nmaiex_tuning/tune_nmaiex_hyperparams.py`
- `synthetic_data/`

### JobApplication Chat

- `docs/strategy/job_application_full_cv_chat_strategy.md`
- `docs/guide/job_application_full_cv_chat_guide.md`
- `app/services/rag_query.py`
- `app/api/routes_chat.py`
- `tests/unit/unit_test_chat_full_cv.py`

### JobPosting Agent

- `app/services/jobposting_agent_runtime.py`
- `app/services/jobposting_tools.py`
- `app/api/routes_jobposting_agent.py`
- `app/models/jobposting_agent.py`
- `tests/unit/unit_test_jobposting_agent_runtime.py`
- `tests/unit/unit_test_jobposting_agent_tools.py`
- `agent_workflow_doc/try_hard_jobposting/`

### Docs/testing/QA

- `docs/testing_guide.md`
- `docs/strategy/README.md`
- `docs/guide/README.md`
- `agent_workflow_doc/README.md`
- `postman/FANG_v2_Collection.postman_collection.json`
- `postman/FANG_V2_FULL_API_TEST_MATRIX.md`
- `agent_workflow_doc/tier2/FANG_TIER2_POSTMAN_MCP_FULL_API_TEST_PROMPT.md`
- `agent_workflow_doc/tier2/MICAREER_TIER2_CHROME_DEVTOOLS_PLAYWRIGHT_FULL_APP_TEST_PROMPT.md`
- `agent_workflow_doc/tier2/MICAREER_TIER2_FULL_SYSTEM_QA_ADDENDUM_PROMPT.md`
- `agent_workflow_doc/tier2/MICAREER_TIER2_JOBPOSTING_AGENT_QA_ADDENDUM_PROMPT.md`

### `miCareer-mini` integration evidence

- `..\miCareer-mini\README.md`
- `..\miCareer-mini\app.py`
- `..\miCareer-mini\core\fang_client.py`
- `..\miCareer-mini\core\nmaiex_client.py`
- `..\miCareer-mini\core\db.py`
- `..\miCareer-mini\core\cloudinary_upload.py`
- `..\miCareer-mini\docs\candidate_apply_strategy.md`

## 5. Sơ đồ đã đề xuất trong blueprint

Trong `bao_cao_ttcs_blueprint.md` đã có Mermaid/text cho các sơ đồ:

1. Kiến trúc tổng thể FANG-centered.
2. Kiến trúc mã nguồn FANG.
3. FANG ingestion.
4. NMAIex ranking hai chiều.
5. Candidate dùng NMAIex trước khi apply.
6. JobApplication Chat theo `jobAppId`.
7. JobPosting Agent theo `jobPostId`.
8. Quy trình kiểm thử/QA.

Người dùng có thể dùng Mermaid để render trực tiếp hoặc dùng phần "Mô tả ảnh" làm prompt cho AI image model.

## 6. Những caveat phải giữ khi viết báo cáo

- Không claim FANG thay thế HR.
- Không claim ranking chính xác tuyệt đối.
- Ranking gains nếu nhắc đến phải ghi rõ là từ synthetic/LLM-judged benchmark.
- Full-CV chat grounded nhưng phụ thuộc parse quality, prompt quality và token budget.
- JobPosting Agent có tool-calling/scope validation/PII masking, nhưng vẫn cần eval/guardrails nếu production.
- `AIINDEXJOB.SUCCESS` là readiness/telemetry của ingestion; full-CV chat mới quan trọng nhất là `CVPARSED` usable.
- `miCareer-mini` không phải sản phẩm chính, chỉ là UI test/dev và minh họa tích hợp.

## 7. Việc nên làm tiếp trong chat mới

Khuyến nghị tiếp tục theo thứ tự:

1. Đọc nhanh `bao_cao_ttcs_outline.md` và `bao_cao_ttcs_blueprint.md`.
2. Duyệt lại Chương 4 mới về kiến trúc-code xem có cần đổi tên thành "Tổ chức mã nguồn và triển khai" hay giữ "Kiến trúc mã nguồn".
3. Bắt đầu viết bản hoàn chỉnh lần 1 cho Chương 1 trước, vì đây là nền hệ thống.
4. Sau Chương 1, viết Chương 2 thành nhiều lượt nhỏ:
   - Ranking + candidate-side ranking.
   - Synthetic/tuning.
   - JobApplication Chat.
   - JobPosting Agent.
5. Chương 3 và 4 viết sau khi đã có đủ evidence.
6. Chương 5 viết sau cùng khi chọn được ảnh demo/test evidence.
7. Phần mở đầu và kết luận nên viết cuối để đảm bảo giọng văn nhất quán.

## 8. Prompt gợi ý cho chat mới

```text
Bạn đang tiếp tục hỗ trợ tôi chuẩn bị báo cáo cuối kỳ môn Thực tập cơ sở PTIT cho dự án FANG.

Bối cảnh:
- Sản phẩm chính là FANG backend/AI Core.
- miCareer-mini chỉ là frontend mỏng/dev-test UI để chứng minh tích hợp API.
- Tôi muốn văn phong học thuật, rõ ràng, có evidence từ code/tài liệu/test.
- Không claim quá đà về AI; synthetic data, LLM judge và tuning chỉ là benchmark thử nghiệm.

Hãy đọc các file:
- C:\Users\os\Desktop\cur_prj\Fang\agent_workflow_doc\bao_cao_ttcs\bao_cao_ttcs_outline.md
- C:\Users\os\Desktop\cur_prj\Fang\agent_workflow_doc\bao_cao_ttcs\bao_cao_ttcs_blueprint.md
- C:\Users\os\Desktop\cur_prj\Fang\agent_workflow_doc\bao_cao_ttcs\handoff_bao_cao_ttcs.md

Nhiệm vụ tiếp theo:
1. Kiểm tra nhanh cấu trúc 5 chương đã chốt.
2. Bắt đầu viết bản hoàn chỉnh lần 1 cho Chương 1: Phạm vi dự án và kiến trúc FANG AI Core.
3. Viết bằng plain text/.txt để copy sang DOCX; không dùng Markdown cho phần nội dung báo cáo.
4. Đánh dấu rõ phần nào là [BẢNG], [HÌNH], [SƠ ĐỒ], [GHI CHÚ EVIDENCE].
5. Nếu cần thêm bằng chứng, dùng understand-chat/knowledge graph và đọc file code/tài liệu liên quan.
```

## 9. Ghi chú phong cách

- Người dùng thích gọi là "phần" trong trao đổi, nhưng cấu trúc báo cáo dùng "chương" là ổn.
- Ưu tiên giải thích có hệ thống, học thuật, không quá marketing.
- Khi có công thức/metric, giải thích ý nghĩa nghiệp vụ trước, công thức sau, code reference cuối.
- Ranking phải tách rõ J->C và C->J.
- Chat và Agent phải tách rõ `jobAppId` và `jobPostId`.

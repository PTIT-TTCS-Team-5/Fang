# Khung cấu trúc báo cáo Thực tập cơ sở - FANG AI Core

> Trạng thái: bản outline định hướng.
> Mục tiêu: chốt cấu trúc chương/phần trước khi viết chi tiết báo cáo.

## Quan điểm viết báo cáo

Báo cáo nên trình bày FANG như sản phẩm chính của nhóm: một backend/AI Core được thiết kế theo hướng API-first để có thể tích hợp vào nhiều frontend hoặc hệ thống tuyển dụng thật. `miCareer-mini` không nên được mô tả như sản phẩm trung tâm, mà là một UI thử nghiệm/dev-test client giúp chứng minh cách một frontend thực tế có thể gọi API của FANG.

Phần mở đầu không nên đặt nặng kiểu "bài toán tuyển dụng" quá chung chung. Cách mở tốt hơn là mô tả workflow HR hiện tại: đọc nhiều CV, lọc ứng viên, đối chiếu job requirement, hỏi đáp về hồ sơ, so sánh ứng viên, theo dõi trạng thái tuyển dụng. Từ đó dẫn vào động lực xây dựng FANG: dùng AI layer để tăng tốc, chuẩn hóa và hỗ trợ ra quyết định, nhưng không thay thế HR.

Các claim về AI phải được viết thận trọng. Synthetic data, LLM judge, prompt/model dependency và kết quả tuning chỉ nên được trình bày như bằng chứng thử nghiệm trong phạm vi dự án, không phải cam kết chất lượng production.

## Cấu trúc tổng thể

Báo cáo gồm một phần mở đầu đặc biệt và năm chương chính:

1. Phần mở đầu: Động lực xây dựng FANG.
2. Chương 1: Phạm vi dự án và kiến trúc FANG AI Core.
3. Chương 2: Các năng lực AI chính của FANG.
4. Chương 3: Quy trình kỹ thuật, tài liệu và kiểm thử.
5. Chương 4: Kiến trúc mã nguồn và tổ chức triển khai.
6. Chương 5: Demo tích hợp, đánh giá và định hướng phát triển.

## Phần mở đầu - Động lực xây dựng FANG

### Mục tiêu

Đặt bối cảnh và tạo động lực cho dự án. Phần này trả lời câu hỏi: vì sao nhóm xây FANG, và FANG giúp workflow tuyển dụng tốt hơn ở điểm nào.

### Nội dung chính

- Mô tả workflow HR hiện tại: xem danh sách job, nhận hồ sơ, đọc CV, đánh giá mức độ phù hợp, so sánh ứng viên, trao đổi nội bộ, theo dõi trạng thái ứng tuyển.
- Nêu các điểm nghẽn thường gặp: nhiều CV, thông tin không đồng nhất, khó so sánh ứng viên, khó truy xuất nhanh chi tiết trong CV, việc xếp hạng thủ công tốn thời gian.
- Giới thiệu FANG như một AI Core hỗ trợ workflow này bằng ingestion, ranking, chat và agent.
- Nhấn mạnh FANG hỗ trợ HR, không tự động thay thế quyết định tuyển dụng.

### Luận điểm cần giữ

FANG được xây dựng để "supercharge" workflow tuyển dụng bằng một AI layer có thể tích hợp qua API, thay vì chỉ tạo một giao diện demo đơn lẻ.

## Chương 1 - Phạm vi dự án và kiến trúc FANG AI Core

### Vai trò của chương

Chương này định nghĩa ranh giới hệ thống và nền tảng kiến trúc. Người đọc cần hiểu FANG là gì, `miCareer-mini` là gì, dữ liệu đi qua hệ thống như thế nào, và tại sao kiến trúc API-first phù hợp với mục tiêu tích hợp vào website thật.

### Các phần con

#### 1.1. Phạm vi dự án và vai trò của FANG

- FANG là backend/AI Core chính.
- `miCareer-mini` là frontend mỏng dùng cho test/dev/demo tích hợp.
- Frontend thực tế có thể thay thế `miCareer-mini` nếu tuân theo API contract của FANG.
- Trọng tâm báo cáo là FANG, không phải xây dựng một sản phẩm frontend hoàn chỉnh.

Evidence dự kiến:

- `README.md`
- `docs/system_architecture.md`
- `docs/strategy/integration_strategy.md`
- `../miCareer-mini/README.md`

#### 1.2. Quan điểm thiết kế API-first và thin client

- FANG xử lý logic AI, ingestion, ranking, chat, agent.
- Frontend chỉ gọi API, hiển thị trạng thái và kết quả.
- Thiết kế này giảm coupling giữa AI backend và UI.
- Dễ tích hợp với Streamlit, Java Servlet, Spring Boot hoặc web app khác.

Evidence dự kiến:

- `app/main.py`
- `app/api/routes_ingestion.py`
- `app/api/routes_chat.py`
- `app/api/nmaiex_routes_ranking.py`
- `app/api/routes_jobposting_agent.py`

#### 1.3. Kiến trúc tổng thể

- FastAPI làm API layer.
- PostgreSQL/pgvector lưu dữ liệu AI và vector.
- LLM/model adapters phục vụ parse, embedding, generation.
- Cloudinary/local/S3 chỉ là nguồn file bên ngoài; FANG chỉ cần nhận URL hoặc nguồn CV hợp lệ.

Hình nên có:

- Component diagram: Frontend client -> FANG API -> service layer -> database/vector store -> model providers.

#### 1.4. Luồng FANG ingestion

- Frontend tạo `JOBAPPLICATION` và truyền `jobAppId`, `cvSnapUrl` cho FANG.
- FANG tải CV, parse, chuẩn hóa, tạo markdown, chunk, embedding và lưu dữ liệu.
- Luồng dữ liệu chính: `cvSnapUrl -> FANG ingestion -> CVPARSED -> AIDOCUMENTCHUNK -> AIINDEXJOB -> ranking/chat/agent`.
- Với báo cáo này, có thể nói `miCareer-mini` hiện dùng Cloudinary để cung cấp `cvSnapUrl`, nhưng cơ chế lưu file của frontend không phải trọng tâm kiến trúc FANG.

Evidence dự kiến:

- `app/models/ingestion.py`
- `app/api/routes_ingestion.py`
- `database/schema_ai_core.sql`
- `database/schema_web_core.sql`
- `docs/guide/input_processing_guide.md`
- `docs/guide/database_guide.md`

Hình nên có:

- Sequence/activity diagram cho ingestion.

#### 1.5. Thiết kế dữ liệu AI Core

- `AIINDEXJOB`: trạng thái/telemetry cho ingestion job.
- `CVPARSED`: raw text và parsed JSON của CV.
- `AIDOCUMENTCHUNK`: các chunk và embedding phục vụ search/ranking/use case khác.
- Các bảng chat/agent lưu hội thoại, message, tool call, state.

Lưu ý quan trọng:

- `AIINDEXJOB.SUCCESS` là readiness/telemetry cho pipeline ingestion; với full-CV chat mới, điều kiện cứng quan trọng là `CVPARSED` usable.

## Chương 2 - Các năng lực AI chính của FANG

### Vai trò của chương

Chương này là trọng tâm kỹ thuật AI của báo cáo. Cần trình bày các năng lực chính như các module có scope rõ ràng, dữ liệu đầu vào rõ ràng và giới hạn rõ ràng.

### Các phần con

#### 2.1. NMAIex Ranking hai chiều

- J->C: HR tìm ứng viên phù hợp cho một job.
- C->J: Candidate tìm job phù hợp.
- Hai chiều có mục tiêu khác nhau, không nên gộp thành một bài toán search chung.
- `score_breakdown` giúp kết quả ranking có khả năng giải thích ở mức vận hành.

Evidence dự kiến:

- `docs/strategy/nmaiex_ranking_strategy.md`
- `docs/guide/nmaiex_ranking_guide.md`
- `app/services/nmaiex_ranking_service.py`
- `app/api/nmaiex_routes_ranking.py`
- `app/models/nmaiex_schemas.py`

Bảng nên có:

- So sánh J->C và C->J theo actor, mục tiêu, retrieval, metric, rủi ro.

#### 2.2. Synthetic data, ground truth và tuning

- Synthetic data dùng khi chưa có đủ dữ liệu tuyển dụng thật.
- Ground truth/LLM judge giúp tạo benchmark thử nghiệm.
- Optuna tuning dùng để tìm trọng số phù hợp hơn cho ranking.
- MRR phù hợp với nhu cầu HR thấy ứng viên tốt sớm.
- nDCG@10 phù hợp với chất lượng top-k trong gợi ý job/candidate.

Evidence dự kiến:

- `synthetic_data/`
- `nmaiex_tuning/`
- `nmaiex_tuning/tune_nmaiex_hyperparams.py`
- `docs/research/`
- `agent_workflow_doc/archive/task_nmaiex_tuning.md`

Lưu ý diễn đạt:

- Không viết rằng kết quả tuning chứng minh hệ thống chính xác trong production.
- Nên viết rằng kết quả tuning được đo trên synthetic/LLM-judged benchmark trong phạm vi dự án.

#### 2.3. JobApplication Chat theo `jobAppId`

- Chat tập trung vào một `JobApplication`.
- Full-CV context giúp HR hỏi sâu về một hồ sơ cụ thể.
- Guardrails giới hạn phạm vi: tuyển dụng, CV, JD, ATS context.
- Token budget và conversation summary giúp kiểm soát context window.

Evidence dự kiến:

- `docs/strategy/job_application_full_cv_chat_strategy.md`
- `docs/guide/job_application_full_cv_chat_guide.md`
- `app/services/rag_query.py`
- `app/api/routes_chat.py`
- `tests/unit/unit_test_chat_full_cv.py`

Hình nên có:

- Flow: HR question -> `/v2/chat/query` -> load CV/JD/context -> build prompt -> model -> response -> persistence.

#### 2.4. JobPosting Agent theo `jobPostId`

- Agent tập trung vào một `JobPosting`.
- Tool-calling giúp agent truy vấn dữ liệu có kiểm soát thay vì nhồi toàn bộ dữ liệu vào prompt.
- Working set giúp duy trì tập ứng viên đang xét qua nhiều lượt hỏi.
- Scope validation ngăn truy cập ứng viên ngoài job hiện tại.
- PII masking và read-only tools là ràng buộc quan trọng.

Evidence dự kiến:

- `app/services/jobposting_agent_runtime.py`
- `app/services/jobposting_tools.py`
- `app/api/routes_jobposting_agent.py`
- `app/models/jobposting_agent.py`
- `tests/unit/unit_test_jobposting_agent_runtime.py`
- `tests/unit/unit_test_jobposting_agent_tools.py`
- `agent_workflow_doc/try_hard_jobposting/`

Hình nên có:

- Agent runtime -> allowed tools -> DB/ranking -> result preview -> grounded response.

## Chương 3 - Quy trình kỹ thuật, tài liệu và kiểm thử

### Vai trò của chương

Chương này chứng minh dự án không chỉ có code tính năng, mà còn có quy trình kỹ thuật: tài liệu chiến lược, guide vận hành, assignment/report, test matrix, QA criteria và bằng chứng kiểm thử.

### Các phần con

#### 3.1. Hệ thống tài liệu kỹ thuật

- `docs/strategy/`: quyết định kiến trúc, trade-off, phạm vi và rủi ro.
- `docs/guide/`: hướng dẫn triển khai/vận hành theo runbook.
- `agent_workflow_doc/`: tài liệu điều phối, assignment, report, acceptance criteria, QA prompt.
- `docs/research/`: tài liệu nghiên cứu và tham khảo, không nên xem là runtime truth nếu mâu thuẫn với code hiện tại.

Evidence dự kiến:

- `docs/strategy/README.md`
- `docs/guide/README.md`
- `agent_workflow_doc/README.md`
- `agent_workflow_doc/current_workflow/`
- `agent_workflow_doc/try_hard_jobposting/`

Luận điểm:

Hệ thống tài liệu giúp trace quyết định kỹ thuật, tách strategy khỏi guide, và giảm rủi ro mâu thuẫn giữa ý tưởng, code và kiểm thử.

#### 3.2. Unit tests và smoke/E2E tests

- Unit tests kiểm tra logic cô lập: chunking, embedding, ingestion flow, parser policy, persistence, full-CV chat, ranking, JobPosting Agent.
- Smoke/E2E tests kiểm tra API thật, DB thật hoặc pipeline tích hợp.
- Một số test cần môi trường và dữ liệu fixture rõ ràng.

Evidence dự kiến:

- `docs/testing_guide.md`
- `tests/unit/`
- `smoke_tests/`
- `pytest.ini`

#### 3.3. Postman API verification

- Postman collection/test matrix kiểm tra API contract.
- Các nhóm test: health, chat, ingestion, NMAIex ranking/master data, JobPosting Agent.
- Với JobPosting Agent cần ghi tool routing, result preview, status, warning, scope behavior.

Evidence dự kiến:

- `postman/FANG_v2_Collection.postman_collection.json`
- `postman/FANG_V2_FULL_API_TEST_MATRIX.md`
- `agent_workflow_doc/tier2/FANG_TIER2_POSTMAN_MCP_FULL_API_TEST_PROMPT.md`

#### 3.4. Playwright/Chrome DevTools full-app QA qua `miCareer-mini`

- `miCareer-mini` dùng để kiểm tra tích hợp end-to-end từ góc nhìn UI.
- Các test case bao phủ auth, HR job management, full-CV chat, ranking UI, JobPosting Agent, candidate browse/apply smoke, visual/session/error regression.
- Đây là kiểm thử tích hợp client, không làm thay đổi trọng tâm sản phẩm chính là FANG.

Evidence dự kiến:

- `agent_workflow_doc/tier2/MICAREER_TIER2_CHROME_DEVTOOLS_PLAYWRIGHT_FULL_APP_TEST_PROMPT.md`
- `agent_workflow_doc/tier2/MICAREER_TIER2_FULL_SYSTEM_QA_ADDENDUM_PROMPT.md`
- `agent_workflow_doc/tier2/MICAREER_TIER2_JOBPOSTING_AGENT_QA_ADDENDUM_PROMPT.md`
- `../miCareer-mini/test_playwright.py`
- `../miCareer-mini/test_playwright_full.py`
- `../miCareer-mini/test_playwright_job_agent.py`

#### 3.5. Tiêu chí QA đặc thù cho hệ thống AI

- Provider stop rule và kiểm soát chi phí API.
- Prompt injection resistance.
- Scope boundary theo `jobAppId` hoặc `jobPostId`.
- PII masking với JobPosting Agent.
- Evidence grounding: câu trả lời phải dựa trên dữ liệu tool/context.
- Visual stability và session persistence trong UI tích hợp.

Luận điểm:

Với hệ thống AI, kiểm thử không chỉ là HTTP 200 hoặc UI render được; cần kiểm tra grounding, scope, tool routing, dữ liệu nhạy cảm, provider failure và chi phí vận hành.

## Chương 4 - Kiến trúc mã nguồn và tổ chức triển khai

### Vai trò của chương

Chương này bổ sung góc nhìn "kiến trúc-code" cho báo cáo. Nếu Chương 1 trả lời hệ thống chạy như thế nào ở mức runtime/API/data flow, thì Chương 4 trả lời codebase được tổ chức ra sao, module nào chịu trách nhiệm gì, và cách các lớp router, schema, service, persistence, test, docs liên kết với nhau.

Phần này là cần thiết trong báo cáo kỹ thuật vì nó giúp người đọc thấy sản phẩm không chỉ có ý tưởng và demo, mà có cấu trúc mã nguồn đủ rõ để bảo trì, mở rộng và kiểm thử.

### Các phần con

#### 4.1. Cấu trúc thư mục backend FANG

- `app/api/`: HTTP route handlers và API surface.
- `app/models/`: Pydantic schemas/request-response models.
- `app/services/`: logic nghiệp vụ và AI workflows.
- `app/core/`: cấu hình, database, logging, shared runtime settings.
- `database/`: schema và seed data.
- `tests/` và `smoke_tests/`: kiểm thử unit/integration.
- `docs/` và `agent_workflow_doc/`: tài liệu chiến lược, guide, QA, report.

Evidence dự kiến:

- `README.md`
- `docs/cau_truc_thu_muc.txt`
- `app/main.py`
- `app/api/`
- `app/models/`
- `app/services/`
- `database/`

#### 4.2. Mapping giữa API layer, service layer và data layer

- Ingestion: `routes_ingestion.py` -> parser/chunking/embedding/persistence services -> `CVPARSED`, `AIDOCUMENTCHUNK`, `AIINDEXJOB`.
- Ranking: `nmaiex_routes_ranking.py` -> `nmaiex_ranking_service.py` -> web/AI database tables.
- JobApplication Chat: `routes_chat.py` -> `rag_query.py`/persistence -> chat tables.
- JobPosting Agent: `routes_jobposting_agent.py` -> `jobposting_agent_runtime.py`/`jobposting_tools.py` -> agent tables/tool call logs.

Hình nên có:

- Code architecture diagram: API routes -> models -> services -> database/tests/docs.

#### 4.3. Cách tách module theo scope nghiệp vụ

- `jobAppId` scope cho JobApplication Chat.
- `jobPostId` scope cho JobPosting Agent.
- Ranking có hai hướng J->C và C->J nhưng cùng nằm trong NMAIex module.
- Ingestion là nền dữ liệu chung cho các use case phía sau.

Luận điểm:

Codebase được tổ chức theo các boundary nghiệp vụ rõ ràng, giúp tránh trộn lẫn ranking, chat và agent.

#### 4.4. Quan hệ giữa code, tài liệu và test

- Strategy docs giải thích quyết định thiết kế.
- Guide docs hướng dẫn vận hành/triển khai.
- Unit/smoke/Postman/Playwright tests xác minh behavior.
- `agent_workflow_doc` ghi lại assignment, report, acceptance criteria và QA matrix.

Luận điểm:

Một quyết định kỹ thuật mạnh trong FANG không chỉ nằm ở code, mà còn có tài liệu giải thích và test/QA để kiểm chứng.

## Chương 5 - Demo tích hợp, đánh giá và định hướng phát triển

### Vai trò của chương

Chương này trình bày bằng chứng vận hành và tổng kết. Demo dùng `miCareer-mini` như một client tích hợp, không làm lệch trọng tâm khỏi FANG.

### Các phần con

#### 5.1. Môi trường và điều kiện demo

- Backend FANG chạy local.
- Database có dữ liệu seed/synthetic/fixture.
- `miCareer-mini` cấu hình `FANG_API_URL=http://localhost:8000/v2`.
- Nếu demo gọi LLM, cần nêu provider/API key/quota là điều kiện môi trường.

#### 5.2. Demo flow đề xuất

Flow demo nên chọn ít nhưng đại diện:

1. Candidate xem hồ sơ hiện có, CV hiện tại, dùng NMAIex C->J ranking để xem danh sách job được gợi ý trước khi apply.
2. Candidate chọn job phù hợp, xem job detail, apply bằng CV sẵn có hoặc upload CV mới.
3. FANG ingestion xử lý CV từ `JobApplication`.
4. HR chạy NMAIex J->C ranking cho job vừa có ứng viên hoặc job fixture.
5. HR chọn ứng viên nổi bật từ ranking, mở application detail và hỏi JobApplication Chat.
6. HR mở JobPosting Agent theo `jobPostId` để hỏi top candidates/compare/filter.

Ảnh minh họa nên có:

- FANG API/health hoặc log ingestion.
- Màn hình candidate profile/CV hiện có.
- Màn hình candidate-side NMAIex job recommendation trước khi apply.
- Màn hình ranking result.
- Màn hình application detail/full-CV chat sau khi chọn ứng viên từ ranking.
- Màn hình JobPosting Agent với tool trace/working set.

#### 5.3. Đánh giá kết quả trong phạm vi dự án

- Đánh giá chức năng: module chạy được theo API/UI flow.
- Đánh giá kỹ thuật: kiến trúc tách frontend/backend, dữ liệu AI được lưu đúng, test có nhiều tầng.
- Đánh giá AI: ranking/chat/agent có cơ chế grounding và kiểm soát scope, nhưng chất lượng phụ thuộc dữ liệu, model, prompt, benchmark.

#### 5.4. Hạn chế

- Dữ liệu synthetic chưa thay thế dữ liệu production.
- LLM judge có bias và phụ thuộc prompt/model.
- Parse quality phụ thuộc chất lượng CV và provider.
- Token budget/context window giới hạn độ dài hội thoại.
- API cost/quota/rate limit ảnh hưởng demo và vận hành.
- PII/privacy cần hardening thêm nếu đưa vào môi trường thật.
- Monitoring, observability và security production chưa phải trọng tâm hiện tại.

#### 5.5. Hướng phát triển

- Chuẩn hóa thêm evaluation dataset với dữ liệu thật hoặc bán thật.
- Cải thiện monitoring/logging/trace cho AI requests.
- Hoàn thiện security/privacy policy cho CV và ATS data.
- Tối ưu ranking bằng thêm feedback loop từ HR/candidate.
- Mở rộng frontend tích hợp thật ngoài `miCareer-mini`.
- Hoàn thiện CI/test automation cho Postman/Playwright/unit tests.

## Mapping 13 phần nội dung vào cấu trúc chương

| Nội dung ban đầu | Vị trí mới |
|---|---|
| 1. Động lực xây dựng FANG | Phần mở đầu |
| 2. Phạm vi dự án và quan điểm thiết kế | Chương 1 |
| 3. Kiến trúc tổng thể | Chương 1 |
| 4. Luồng dữ liệu và ingestion pipeline | Chương 1 |
| 5. Thiết kế dữ liệu AI Core | Chương 1 |
| 6. NMAIex Ranking hai chiều | Chương 2 |
| 7. Synthetic data, ground truth và tuning | Chương 2 |
| 8. JobApplication Chat | Chương 2 |
| 9. JobPosting Agent | Chương 2 |
| 10. Hệ thống tài liệu và quy trình kỹ thuật | Chương 3 |
| 11. Kiểm thử, QA và tiêu chí nghiệm thu | Chương 3 |
| 12. Kiến trúc mã nguồn và tổ chức triển khai | Chương 4 |
| 13. Demo tích hợp và kết quả minh họa | Chương 5 |
| 14. Hạn chế và hướng phát triển | Chương 5 |

## Bước tiếp theo sau khi duyệt outline

1. Chốt mục lục cấp 2/cấp 3 của từng chương.
2. Lập evidence matrix: mỗi mục cần file nào, code path nào, test nào, ảnh demo nào.
3. Chọn sơ đồ cần vẽ: component diagram, ingestion sequence, ranking pipeline, chat/agent scope diagram.
4. Viết bản hoàn chỉnh lần 1 cho từng chương theo thứ tự: Chương 1 -> Chương 2 -> Chương 3 -> Chương 4 -> Chương 5 -> Phần mở đầu.
5. Rà soát claim quá đà, thuật ngữ, tên bảng/API và tính nhất quán giữa FANG và `miCareer-mini`.

Các bước 1-3 đã được tách sang file blueprint chi tiết trong cùng thư mục để phục vụ bước viết báo cáo.

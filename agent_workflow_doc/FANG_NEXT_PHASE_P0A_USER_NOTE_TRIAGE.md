# FANG Next Phase P0-A User Note Triage

Ngày gom nhóm: 23/05/2026

Tài liệu này gom các `NOTE FROM USER` trong `FANG_NEXT_PHASE_P0A_REPO_REALITY_AUDIT.md` và `FANG_NEXT_PHASE_P0A_REPO_REALITY_AUDIT_REPORT.md`. Mục tiêu là tách rõ việc nào user đã chốt, việc nào giao cho `P1_A_B_inc`, việc nào giao cho `CHAT_FULL_CV`, việc nào user/tier 1 xử lý, việc nào tier 2 có thể làm ngay, và việc nào có thể bỏ qua hoặc để sau.

## 1. Quyết định đã chốt

Các điểm này không cần hỏi lại trong P0-B, chỉ cần truyền như constraint/context:

| Chủ đề | Quyết định |
|---|---|
| NMAIex boundary | NMAIex là một phần chính thức của FANG core. Giữ tên gọi NMAIex để dễ phân biệt, nhưng không còn mô tả như extension tách biệt. |
| Research docs | Không dùng `docs/research` làm current runtime truth. Research chỉ là nguồn tham khảo quyết định, nhiễu cao, không phản ánh chắc chắn hệ thống thật. |
| Embedding default | Dùng Gemini `gemini-embedding-001`, mặc định 1536 dims. Docs/tests cũ nói OpenAI 1024 phải sửa theo code. |
| Generator fallback | Chỉ parser có 5-tier fallback + ProTierGate. Generation hiện là 7 `modelMode`, gồm `auto-lite` và `auto-pro`; sửa docs theo code, không mặc định thêm Lite-to-Pro escalation. |
| JobApplication chat | Chuyển sang full CV markdown context. Fixed top-k chunk RAG hiện tại là trạng thái cũ cần thay. |
| NMAIex management content route | Chọn canonical route `/v2/nmaiex/management/jobs/{id}/content`; route root trả `queued` nhưng không re-ingest cần align/deprecate/sửa docs. |
| Score clipping | Chốt không clip ranking score; cần sửa code và docs theo hướng không clip. |
| NMAIex env template | Dùng root `.env.nmaiex.example`; bỏ `app/core/.env.nmaiex.example`. |
| Auth/API key/JWT | Chỉ là note/tính năng nâng cao, chưa cần làm. |

## 2. Giao cho `P1_A_B_inc`

Nhóm này thuộc người làm P1-A/P1-B Prompt Review + Minimal Eval. Nên chạy sau P0-B vì cần inventory prompt/use case đầy đủ.

| Item | Việc cần làm | Ghi chú phụ thuộc |
|---|---|---|
| Multi-source RAG context | Review prompt engineering cho context gồm skill, Offer/Email content và các nguồn context liên quan. | Nên nhận đầu vào từ P0-B prompt inventory và từ guide `CHAT_FULL_CV`. |
| Context window management | Review/sửa prompt + eval cho behavior context budget, warning, per-model budget. | Có liên quan `CHAT_FULL_CV`; đừng chốt độc lập nếu full CV làm thay đổi budget lớn. |
| Per-model context budget map | Đưa vào P1-A/B nếu workload chịu được; nếu quá tải thì tách lại cho user/tier 1. | Phụ thuộc model/fallback map từ P0-B. |
| Prompt/eval tối thiểu | Parser, JobApplication full-CV chat, NMAIex mapper, language proficiency normalization. | Đây là mục tiêu chính của P1-A/B theo `FANG_NEXT_PHASE_DECISIONS.md`. |

Nhận xét: không nên cho P1_A_B_inc bắt đầu trước P0-B. P0-B chính là bản đồ entry point/prompt/model/fallback để người này không bỏ sót.

## 3. Giao cho `CHAT_FULL_CV`

Nhóm này thuộc người làm JobApplication Full-CV Chat. Đây là một feature/change package riêng, không nên trộn lẫn với P0-B.

| Item | Việc cần làm | Ghi chú phụ thuộc |
|---|---|---|
| D04 JobApplication chat context | Đổi chat từ fixed top-k chunks sang full CV markdown. | Cần guide tier 1 trước khi giao implementation. |
| D05 Context budget behavior | Sửa code theo docs/decision: nếu context vượt ngưỡng thì behavior phải rõ, không chỉ warning mơ hồ. | Cần thiết kế cùng full CV vì token budget là rủi ro chính. |
| Fetch Offer | Khi fetch context, phải lấy thêm Offer. | Cần xác định table/source chính xác trong guide implementation. |
| RAG prompt mới | Prompt phải phù hợp full CV, không chỉ thay retrieval data source. | P1_A_B_inc review/nâng cấp sau hoặc song song ở mức rubric. |

Nhận xét: `CHAT_FULL_CV` có thể chuẩn bị guide sau khi P0-B xong. Không nên để thành viên code ngay khi chưa có quyết định rõ về data source của full markdown: lấy từ `CVPARSED.parsedJson`, lưu markdown riêng, hay recompute từ parser JSON.

## 4. User / Tier 1 xử lý trực tiếp

Những điểm cần tier 1 vì là quyết định kiến trúc, semantic/product behavior, hoặc cần nghiên cứu sâu.

| Item | Quyết định/hành động |
|---|---|
| P0-B AI/LLM Inventory | Chạy bằng Claude Opus 4.6 hoặc GPT-5.5. Nên feed P0-A report + triage này làm context, nhưng yêu cầu P0-B vẫn đọc code trước. |
| NMAIex post-ingestion semantics | Quyết định failed NMAIex expyears/skill mapping có làm ingestion fail, partial, hay best-effort. User đã ghi nhận và dự tính giao cho thành viên quản lý JobApplication sửa, nhưng semantic nên được tier 1 chốt trước. |
| ProTierGate cải tiến | Cân nhắc thêm self-reported confidence/error value từ model. Đây là design decision cho parser quality gate, chưa nên giao tier 2 tự nghĩ. |
| JobPosting Agent / tool-based retrieval / MCP | User trực tiếp làm decision track riêng. Không giao implementation trước khi có decision memo. |
| Score clipping | User đã chốt không clip; tier 1 nên review impact để tránh làm vỡ ranking API/UX/tuning trước khi tier 2 sửa code. |
| P0-C Documentation Reconciliation | Chạy sau P0-A + P0-B + các quyết định chính. |

* NOTE FROM USER:
   - "NMAIex post-ingestion semantics" : Phần chính (parser → chunks → embed → save for RAG) chỉ auto-retry ngắn cho transient errors rồi HR manual re-run nếu fail lâu; phần phụ (map skills/expyears → update NMAIex)  NMAIex enrichment nên có scheduled retry/backfill hoặc re-enrichment batch, không chặn chat.

## 5. User dùng tier 2 xử lý ngay hoặc sau P0-B/P0-C

Trạng thái hiện tại: đã giao tier 2 xử lý và đã review/cleanup xong trong ngày 23/05/2026. Các prompt giao việc đã được chuyển vào `agent_workflow_doc/archive/tier2_completed_tasks/` để giữ lịch sử, không còn là task mở.

| Item | Status | Kết quả |
|---|---|---|
| Unit embedding test stale | Done | `tests/unit/unit_test_embedding.py` đã chuyển sang mock Google Gemini SDK; unit suite pass. |
| Testing guide vs files | Done | `docs/testing_guide.md` chỉ liệt kê test thật, chuyển RAG/chat unit tests sang known gaps. |
| Unit suite red in venv | Done | `venv\Scripts\python -m unittest discover -s tests/unit -p "unit_test_*.py"` pass 17 tests. |
| Smoke e2e dim 1024 | Done | `smoke_tests/test_e2e_pipeline.py` đã đổi expected embedding dim sang 1536. |
| Synthetic data/tuning checklist | Done | Checklist/implementation plan cũ đã chuyển vào `agent_workflow_doc/archive/`. |
| NMAIex language docs | Done | Docs đã ghi rõ DB/scoring có, `normalize_proficiency()` chưa được gọi trong ranking, `/v2/nmaiex/master/languages` chưa triển khai. |
| `.env.nmaiex.example` duplicate | Done | Root `.env.nmaiex.example` là canonical; `app/core/.env.nmaiex.example` đã bỏ. |

## 6. P0-C / docs reconciliation

Nhóm này nên để P0-C xử lý, không làm lẻ tẻ quá sớm nếu đang muốn giữ docs nhất quán.

| Item | Hành động trong P0-C |
|---|---|
| D01 NMAIex status | Sửa docs: NMAIex là official FANG module, không phải extension tách biệt. |
| D02 Embedding docs | Sửa docs theo Gemini 1536. |
| D03 Generator fallback docs | Sửa README/docs: parser có 5-tier + ProTierGate; generation có 7 model modes. |
| D07 Management route docs | Docs dùng canonical `/v2/nmaiex/management/jobs/{id}/content`. |
| `/v2/nmaiex/master/languages` | User sẽ sửa trong P0-C. |
| AI_WORKFLOW_INIT.md | Update vì đang stale về NMAIex/research. |
| Workflow docs status | Cải thiện sau; không quan trọng với runtime. |

## 7. Archive / không quay lại sửa

Các file/checklist cũ nên đưa vào archive hoặc mark historical, tránh tốn công reconcile từng dòng.

| File/group | Hành động |
|---|---|
| `[NMAIex]_TASK_CHECKLIST_BACKEND.md` | Archive/mark historical, không cố quay lại sửa. |
| `[NMAIex]_TASK_CHECKLIST_FRONTEND.md` | Archive/mark historical, không cố quay lại sửa. |
| `archive/task_data_set.md` | User xác nhận thực tế đã done; đưa vào archive. |
| `archive/task_nmaiex_tuning_6h.md` | Done; đưa vào archive. |
| `archive/task_nmaiex_tuning.md` | Done/historical; đưa vào archive. |
| Implementation plans tuning/data set | Nếu còn hữu ích thì di chuyển vào archive; không dùng làm current truth. |

## 8. Ít quan trọng / để sau

| Item | Lý do để sau |
|---|---|
| Auth/API key/JWT | Tính năng nâng cao, chưa cần thiết. |
| Smoke/integration tests stale | Có giá trị nhưng không nên chặn P0-B/P0-C; cần DB/server/API keys nên tốn setup. |
| Workflow docs status machine-readable | Handoff tốt hơn nhưng không ảnh hưởng trực tiếp runtime/product. |
| JobPosting Agent implementation | Chưa chốt architecture; chỉ làm decision analysis trước. |

## 9. P0-A có phải feed cho P0-B không?

Có, nhưng không phải theo nghĩa P0-B phụ thuộc cứng vào P0-A đã được sửa hết.

P0-B nên nhận:

1. `FANG_NEXT_PHASE_DECISIONS.md`
2. `FANG_NEXT_PHASE_P0A_REPO_REALITY_AUDIT_REPORT.md`
3. `FANG_NEXT_PHASE_P0A_USER_NOTE_TRIAGE.md`
4. `FANG_NEXT_PHASE_P0B_AI_LLM_INVENTORY.md`

P0-B vẫn phải đọc code hiện tại làm ground truth. P0-A chỉ giúp:

- biết chỗ nào đang drift để không tin docs cũ;
- biết quyết định user đã chốt, ví dụ full-CV chat, Gemini embedding, NMAIex official module;
- biết use case nào P1-A/B và CHAT_FULL_CV sẽ cần inventory kỹ hơn;
- tránh mất thời gian vào research/archive/checklist cũ.

## 10. Có thể chạy song song không?

Có thể chạy song song có kiểm soát:

1. Chạy P0-B bằng Claude Opus 4.6 ngay, với P0-A report + triage này làm context.
2. Song song, user/tier 2 có thể xử lý các việc ít ảnh hưởng P0-B:
   - sửa unit embedding test theo Gemini;
   - sửa test baseline;
   - archive checklist cũ;
   - dọn `.env.nmaiex.example` duplicate nếu chỉ là docs/config cleanup;
   - chuẩn bị note cho P0-C.
3. Không nên song song sửa mạnh các file prompt/LLM behavior trước khi P0-B inventory xong:
   - `app/services/cv_parser_adapters.py`
   - `app/services/rag_query.py`
   - `app/services/rag_orchestrator.py`
   - `app/services/rag_model_adapters.py`
   - `app/services/nmaiex_mapper_service.py`
4. Nếu bắt buộc sửa code AI/LLM trong lúc P0-B đang chạy, ghi changelog ngắn cho Claude hoặc rerun phần inventory liên quan.

Kết luận điều phối: P0-B không cần chờ bạn xử lý hết NOTE P0-A. Nhưng P0-B nên được feed P0-A + note triage để không inventory theo giả định cũ. Việc xử lý NOTE P0-A có thể chạy song song nếu tránh thay đổi prompt/model routing/retrieval trong lúc P0-B đang đọc.

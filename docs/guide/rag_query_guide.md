# Hướng Dẫn Vận Hành RAG Query (v2)

Tài liệu này hướng dẫn chi tiết về cách thức hoạt động, cấu hình và tinh chỉnh hệ thống RAG Query trong FANG v2.

> [!IMPORTANT]
> **Cập nhật 2026-05-29 (CHAT_FULL_CV merged):** Luồng `/v2/chat/query` cho 1 `JobApplication` đã chuyển sang full CV markdown context — không còn embed prompt + vector search top-k chunks. Pipeline mới (11 bước) ở `job_application_full_cv_chat_guide.md` §1. Phần dưới đây giữ làm reference kiến trúc chung của chat system (conversation manager, model modes, summarize/branch-new) — vẫn áp dụng cho mọi luồng.

## 1. Pipeline Thực Thi (Legacy 12 Bước — chunk RAG)

> [!NOTE]
> Pipeline 12 bước dưới đây là kiến trúc **chunk RAG cũ**, không còn được thực thi cho JobApplication chat. Pipeline 11 bước mới (full-CV) xem `job_application_full_cv_chat_guide.md` §1.

Khi một request gửi đến `/v2/chat/query` (kiến trúc cũ):

1.  **Validate**: Kiểm tra xem ứng viên đã được ingestion thành công chưa.
2.  **Conversation Manager**: Khởi tạo hoặc tải hội thoại từ DB.
3.  **Embed Prompt**: Chuyển câu hỏi của HR thành vector (1536-dim, Gemini `gemini-embedding-001`).
4.  **Vector Search**: Tìm kiếm $K$ chunks (mặc định $K=3$) có độ tương đồng cosine cao nhất.
5.  **Multi-source Context Fetching**: Tải dữ liệu bổ trợ (JobPosting, Candidate Profile, ATS History).

> [!NOTE]
> **Cập nhật 2026-05-29:** Multi-source context đã được mở rộng trong full-CV path: thêm Offer (3 versions), EmailLog (5 emails với body trunc 300), skills cho cả JD và candidate, salary range, work mode, location, levels, categories. Xem `job_application_full_cv_chat_strategy.md` §3.2.

6.  **Context Assembly**: Lắp ghép dữ liệu vào System Prompt Template.
7.  **History Loading**: Tải toàn bộ lịch sử hội thoại (không dùng sliding window).
8.  **Budget Check**: Tính toán token dự kiến và kiểm tra ngưỡng cảnh báo (80%).
9.  **Message Building**: Tạo danh sách tin nhắn chuẩn OpenAI/Gemini format.
10. **LLM Invocation**: Gọi `rag_orchestrator` để thực thi (có retry và fallback).
11. **Persistence**: Lưu tin nhắn mới và ghi Audit Log.
12. **Response**: Trả kết quả về client kèm `contextWarning` (nếu có).

## 2. Các Chế Độ Model (modelMode)
Hệ thống hỗ trợ 7 chế độ lựa chọn model:

| modelMode | Loại | Chiến Lược | Ghi Chú |
| :--- | :--- | :--- | :--- |
| `auto-lite` | Auto | Fallback: Tier 1 → 2 → 3 | Ưu tiên chi phí và tốc độ |
| `auto-pro` | Auto | Fallback: Tier 4 → 5 | Ưu tiên chất lượng tuyệt đối |
| `gemini-flash` | Specific | Cố định Tier 1 | Nhanh, rẻ, phù hợp tóm tắt |
| `gpt-mini` | Specific | Cố định Tier 2 | Cân bằng |
| `claude-haiku` | Specific | Cố định Tier 3 | Hiểu tiếng Việt tốt |
| `gemini-pro` | Specific | Cố định Tier 4 | Reasoning mạnh |
| `gpt-full` | Specific | Cố định Tier 5 | High-end model |

## 3. Quản Lý Context Window & Budget

FANG v2 bỏ cơ chế **Sliding Window** để tránh mất ngữ cảnh. Thay vào đó, hệ thống sử dụng **Token Budget**:

- **Nguồn chuẩn để đồng bộ budget**: tham chiếu `../strategy/rag_query_strategy.md` mục **10.2 / 10.4** và `job_application_full_cv_chat_strategy.md` §5.
- **Nguyên tắc áp dụng**: hiện dùng group budget (Lite `180_000` / Pro `960_000`). Per-model thực sự là decision track sau, sẽ kích hoạt nếu dữ liệu vận hành cho thấy cần.

### Cơ chế 3 ngưỡng (cập nhật 2026-05-29):

| Ngưỡng | Threshold | Action |
|---|---|---|
| Proceed | `< 0.80` | Gọi LLM bình thường |
| Warn proceed | `[0.80, 0.95)` | Gọi LLM + trả `contextWarning.type = "budget_near_limit"` |
| Block | `>= 0.95` | **KHÔNG** gọi LLM, trả deterministic response, `contextWarning.type = "budget_over_hard_limit"` |

Budget được tính cho **toàn bộ payload** (system prompt + history + user prompt), không chỉ history.

Khi `contextWarning` xuất hiện, response trả về:
```json
"contextWarning": {
  "type": "budget_near_limit",     // hoặc "budget_over_hard_limit"
  "usedPercent": 85,
  "options": ["summarize_and_continue", "new_conversation_with_summary"]
}
```
HR chọn tóm tắt (`POST /v2/chat/conversations/{id}/summarize`) hoặc sang hội thoại mới (`POST /v2/chat/conversations/{id}/branch-new`).

## 4. System Prompt Design

> [!IMPORTANT]
> **Cập nhật 2026-05-29:** System prompt cho JobApplication chat đã được rewrite thành full-CV version với 8 guardrails + untrusted markers + chống prompt injection. Format mới ở `job_application_full_cv_chat_strategy.md` §4 và `job_application_full_cv_chat_guide.md`. Phần dưới là kiến trúc cũ (chunk RAG), giữ làm reference.

System prompt cũ (chunk RAG) chia block:
- `[VỊ TRÍ TUYỂN DỤNG]`: Ngữ cảnh job.
- `[HỒ SƠ ỨNG VIÊN]`: Thông tin định danh.
- `[NỘI DUNG CV — Top K chunks]`: Các đoạn CV retrieved qua vector search (KHÔNG còn dùng cho JobApplication chat).
- `[LỊCH SỬ TUYỂN DỤNG]`: Interview feedback.

System prompt mới (full-CV, JobApplication) thay đổi:
- `[UNTRUSTED JD — JOB POSTING]` (kèm salary, work mode, location, levels, categories, required skills)
- `[UNTRUSTED CANDIDATE — HỒ SƠ CƠ BẢN]` (kèm skills)
- `[UNTRUSTED CV — FULL MARKDOWN (parsed)]` hoặc `[UNTRUSTED CV — RAW TEXT FALLBACK]`
- `[UNTRUSTED ATS — LỊCH SỬ TUYỂN DỤNG]`
- `[UNTRUSTED OFFER — DANH SÁCH OFFER]` (mới)
- `[UNTRUSTED EMAIL — LỊCH SỬ EMAIL]` (mới)
- `[END OF CONTEXT]`

## 5. Cấu Hình (Environment Variables)
Các biến quan trọng trong `.env`:
- `RAG_TOP_K_CHUNKS=3`: Số lượng chunk lấy từ Vector DB. **Không còn dùng cho JobApplication chat** sau 2026-05-29 — giữ cho các use case khác (vẫn hợp lệ).
- `CONTEXT_BUDGET_WARNING_THRESHOLD=0.8`: Ngưỡng cảnh báo (warn proceed).
- `CONTEXT_BUDGET_HARD_LIMIT=0.95`: Ngưỡng chặn (block, không gọi LLM) — **mới 2026-05-29**.
- `CONTEXT_SUMMARIZATION_MODEL=gemini-flash`: Model dùng để chạy tác vụ tóm tắt.
- `RAG_GENERATION_RETRY_ENABLED=true`: Bật/tắt retry cho chatbot.
- `CHAT_OFFER_HISTORY_LIMIT=3`: Số version Offer đưa vào context — **mới Phase 2**.
- `CHAT_EMAIL_HISTORY_LIMIT=5`: Số EmailLog đưa vào context — **mới Phase 2**.
- `CHAT_EMAIL_BODY_CHAR_LIMIT=300`: Cắt body email theo chars — **mới Phase 2**.

---
*Tài liệu này thuộc hệ thống FANG v2.*

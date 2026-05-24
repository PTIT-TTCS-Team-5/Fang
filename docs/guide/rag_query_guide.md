# Hướng Dẫn Vận Hành RAG Query (v2)

Tài liệu này hướng dẫn chi tiết về cách thức hoạt động, cấu hình và tinh chỉnh hệ thống RAG Query trong FANG v2.

## 1. Pipeline Thực Thi 12 Bước
Khi một request gửi đến `/v2/chat/query`, hệ thống thực hiện pipeline sau:

1.  **Validate**: Kiểm tra xem ứng viên đã được ingestion thành công chưa.
2.  **Conversation Manager**: Khởi tạo hoặc tải hội thoại từ DB.
3.  **Embed Prompt**: Chuyển câu hỏi của HR thành vector (1536-dim, Gemini `gemini-embedding-001`).
4.  **Vector Search**: Tìm kiếm $K$ chunks (mặc định $K=3$) có độ tương đồng cosine cao nhất.
5.  **Multi-source Context Fetching**: Tải dữ liệu bổ trợ (JobPosting, Candidate Profile, ATS History).

> [!WARNING]
> **Trạng thái hiện tạ:** Code chỉ fetch: job title/description, candidate basic fields (tên/email/phone/bio/expyears/location), interview feedback. Các nguồn bổ sung (skills, salary/work mode/level, offers, emails) thuộc phần việc CHAT_FULL_CV và P1_A_B_inc.
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

- **Nguồn chuẩn để đồng bộ budget**: tham chiếu `../strategy/rag_query_strategy.md` tại mục **10.2 Context Window Budget theo Model** và mục **10.4 Cấu hình per-model budget**.
- **Nguyên tắc áp dụng**: ưu tiên budget **theo từng model** (per-model), không hard-code theo 2 nhóm Lite/Pro để tránh lệch tài liệu khi model/limit thay đổi.

### Cơ chế cảnh báo:
Khi dung lượng hội thoại chiếm >80% budget của model hiện tại, response sẽ trả về:
```json
"contextWarning": {
  "usedPercent": 85,
  "options": ["summarize_and_continue", "new_conversation_with_summary"]
}
```
HR cần chọn tóm tắt để giải phóng budget hoặc bắt đầu hội thoại mới.

## 4. System Prompt Design
System prompt được chia thành các block rõ rệt:
- `[VỊ TRÍ TUYỂN DỤNG]`: Ngữ cảnh để AI biết đang tuyển cho job nào.
- `[HỒ SƠ ỨNG VIÊN]`: Thông tin định danh và kỹ năng tổng quát.
- `[NỘI DUNG CV]`: Các đoạn CV **được truy xuất (retrieved chunks)** qua vector search theo câu hỏi hiện tại, **không phải toàn bộ full CV gốc**.

> [!IMPORTANT]
> **Quyết định đã chốt:** JobApplication chat sẽ chuyển từ fixed chunk-RAG sang full CV markdown context. Xem `agent_workflow_doc/FANG_NEXT_PHASE_DECISIONS.md`. Code và tài liệu chi tiết sẽ cập nhật khi implementation hoàn tất (work package CHAT_FULL_CV).

- `[LỊCH SỬ TUYỂN DỤNG]`: Ghi chú từ các vòng phỏng vấn trước.

## 5. Cấu Hình (Environment Variables)
Các biến quan trọng trong `.env`:
- `RAG_TOP_K_CHUNKS=3`: Số lượng chunk lấy từ Vector DB.
- `CONTEXT_BUDGET_WARNING_THRESHOLD=0.8`: Ngưỡng bắt đầu cảnh báo HR.
- `CONTEXT_SUMMARIZATION_MODEL=gemini-flash`: Model dùng để chạy tác vụ tóm tắt.
- `RAG_GENERATION_RETRY_ENABLED=true`: Bật/tắt retry cho chatbot.

---
*Tài liệu này thuộc hệ thống FANG v2.*

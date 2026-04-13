# 🚀 Handover Context: FANG v2 Upgrade (Migration to Pha 2)

Tài liệu này dành cho AI Agent tiếp theo để tiếp quản dự án FANG và miCareer-mini, tập trung vào việc triển khai **Pha 2: Tích hợp miCareer-mini**.

## 1. Bối Cảnh Hệ Thống (Thin Client Architecture)
Chúng ta đang chuyển đổi hệ thống sang kiến trúc **AI Core tập trung**:
- **FANG (AI Core)**: Đóng vai trò là trung tâm xử lý. Mọi logic về Embedding, Vector Search, LLM Selection (5-tier fallback), Context Window (Token Budget) và Chat History đều nằm ở đây.
- **miCareer-mini (UI)**: Đang được refactor để trở thành "Thin Client". Nhiệm vụ duy nhất là render giao diện và gọi JSON API của FANG.

## 2. Các Công Việc Đã Hoàn Thành (Pha 0 & Pha 1)
- [x] **Documentation**: Đã viết toàn bộ `strategy` và `guide` cho RAG v2, Integration v2 và Candidate Flow.
- [x] **AI Core (FANG)**:
    - Nâng cấp Parser lên 5-tier (Lite: Gemini Flash, GPT-5.4 mini, Claude 4.5 Haiku; Pro: Gemini Pro, GPT-5.4).
    - Triển khai `rag_orchestrator.py` với cơ chế auto-fallback và quality gate.
    - Hoàn thiện API v2 (`/v2/chat/query`, `/v2/chat/conversations`, v.v.).
    - Tích hợp quản lý Context Window bằng Token Budget (tự động trả về `contextWarning` khi sắp hết dung lượng).
    - Hỗ trợ lưu trữ hội thoại tập trung vào DB (PostgreSQL).

## 3. Nhiệm Vụ Pha 2: Tích Hợp miCareer-mini (BẮT ĐẦU TỪ ĐÂY)
Agent mới cần chuyển sang repo `miCareer-mini` và thực hiện:
1.  **Cụm 3 (Client Layer)**:
    - Tạo `core/fang_client.py`: Client HTTP gọi FANG API v2.
    - Loại bỏ LangChain và logic gọi LLM trực tiếp trong `core/ai.py`.
    - Refactor `core/db.py`: Chỉ giữ lại các hàm đọc dữ liệu quan hệ (HR, Job, App), chuyển việc ghi log AI sang FANG.
2.  **Cụm 3 (UI Layer)**:
    - Refactor `app.py`: Giao diện Chat phải gọi `fang_client.py`.
    - Hỗ trợ hiển thị danh sách hội thoại cũ (`GET /v2/chat/conversations`).
    - Hỗ trợ 7 chế độ `modelMode` (auto-lite, auto-pro, và 5 model cụ thể).
    - **Xử lý `contextWarning`**: Khi nhận cảnh báo từ API, hiển thị Dialog cho HR chọn "Tóm tắt & Tiếp tục" (`/summarize`) hoặc "Sang hội thoại mới" (`/branch-new`).
3.  **Cụm 4 (Candidate Flow)**:
    - Cho phép ứng viên upload CV lên Cloudinary và trigger Ingestion API v2 của FANG.

## 4. Danh Sách File Agent Mới NÊN ĐỌC
Để nắm bắt nhanh kiến trúc, hãy đọc các file sau theo thứ tự:

### Tại FANG Repo:
- **`agent_workflow_doc/implementation_plan.md`**: Bản kế hoạch tổng thể (bản cập nhật nhất).
- **`task.md`**: Theo dõi tiến độ chi tiết.
- **`docs/rag_query_strategy.md`**: Chi tiết thuật toán RAG, fallback và quản lý context.
- **`docs/integration_strategy.md`**: Hợp đồng API giữa FANG và UI.
- **`docs/rag_query_guide.md` & `docs/integration_guide.md`**: Hướng dẫn thực hành.
- **`app/api/routes_chat.py`**: Xem API Contract thực tế đã code.

### Tại miCareer-mini Repo:
- **`app.py`**: UI hiện tại (cần refactor).
- **`core/ai.py`**: Logic cũ (cần xóa).
- **`core/db.py`**: Data access layer hiện tại.

## 5. Lưu Ý Kỹ Thuật Quan Trọng
- **CORS**: FANG v2 đã bật CORS. miCareer-mini sẽ gọi FANG qua URL cấu hình trong `.env`.
- **UUID**: Toàn bộ `conversationId` dùng định dạng UUID.
- **Token Budget**: Không được lạm dụng sliding window. Khi hết context, bắt buộc phải qua bước Summarization của FANG.
- **Branching**: Mọi thay đổi code mới nên thực hiện trên các feature branch từ `develop`.

---
*Dữ liệu bàn giao được gói gọn tại thời điểm Pha 1 hoàn thành 100%.*

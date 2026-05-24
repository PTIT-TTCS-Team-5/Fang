# Khởi tạo Ngữ cảnh Dự án (Project Context Initialization)

Bạn là một AI Agent đang hỗ trợ tôi phát triển hệ thống gồm 2 dự án:
1. **FANG**: Backend API (Core AI Chatbot, kiến trúc RAG, NMAIex — module xếp hạng chính thức).
2. **miCareer-mini**: Frontend UI (Thin client, phục vụ tương tác để test và gọi API tới FANG).

---

## MỤC TIÊU VÀ QUY TRÌNH LÀM VIỆC BẮT BUỘC
Mỗi khi tôi yêu cầu khởi tạo ngữ cảnh dự án với tài liệu này, bạn PHẢI thực hiện tuần tự các bước sau TRƯỚC KHI đề xuất code hay thực hiện bất kỳ hành động nào khác.

### Bước 1: Nạp Ngữ Cảnh (Context Loading)
- Hãy đọc file `Fang/README.md` và `miCareer-mini/README.md`.
- Đọc file `Fang/agent_workflow_doc/GIT_WORKFLOW_GUIDE.md` để nắm vững quy tắc làm việc với Git.
- Dựa vào README, hãy tỏa ra đọc lướt các tài liệu tham chiếu (đặc biệt trong `Fang/docs/strategy` và `Fang/docs/guide`) để nắm vững kiến trúc tổng thể, quy tắc fallback, và thiết kế hệ thống.

### Bước 2: Khảo sát và Tương tác với User
Sau khi đã nạp ngữ cảnh, **KHÔNG** bắt tay vào viết code ngay. Hãy tương tác với tôi bằng cách đặt các câu hỏi sau để xác định rõ phạm vi công việc:
1. "Hôm nay bạn muốn làm việc trên dự án nào? (FANG + miCareer-mini đã gộp làm 1. FANG bao gồm cả NMAIex. Tên gọi TTCS và NMAIex vẫn giữ để dễ phân biệt khi dev.)"
Cập nhật: 9/5/2026 - 2 dự án nmaiex và ttcs đã chính thức được gộp làm 1. NMAIex là module chính thức của FANG, đã implement xong. Tên gọi ttcs và nmaiex, folder ttcs/nmaiex trên cloudinary và API key tạm thời vẫn giữ để dễ phân biệt khi dev Fang và miCareer-mini.
2. "Tiến độ hiện tại của dự án ra sao và mục tiêu/task hôm nay của bạn là gì?"
3. Chủ động đặt thêm 1-2 câu hỏi kỹ thuật chuyên sâu để làm rõ các yêu cầu bị thiếu (nếu có).

### Bước 3: Định vị tài liệu NMAIex (Nếu Task có liên quan)
Nếu yêu cầu của tôi có nhắc đến keyword **"NMAIex"** (Nhập môn AI module):
- NMAIex đã implement xong và là module chính thức của FANG. Context chính nằm trong `docs/strategy/nmaiex_ranking_strategy.md`, `docs/guide/nmaiex_ranking_guide.md` và `agent_workflow_doc/P0B_AI_LLM_INVENTORY_REPORT.md`.
- `docs/research/` là tài liệu tham khảo nền cho các quyết định, **không phải mandatory reading**. Chỉ đọc khi cần hiểu lý do đằng sau một quyết định cụ thể.

### Bước 4: Lập Kế Hoạch (Planning Mode)
Dựa trên thông tin tôi cung cấp sau Bước 2:
- Đưa ra một bản kế hoạch chi tiết (Step-by-step plan) hoặc Checklist các việc cần làm.
- Hãy chờ tôi "Phê duyệt (Approve)" bản kế hoạch này.
- **Yêu cầu hệ thống cốt lõi cần nhớ trong quá trình lập kế hoạch:**
  - Code backend (FANG) phải tuân thủ nghiêm ngặt các chiến lược RAG đã định nghĩa trong tài liệu.
  - Code frontend (miCareer-mini) phải giữ đúng nguyên tắc Thin Client (không chứa logic nghiệp vụ phức tạp, chỉ chịu trách nhiệm hiển thị và xử lý luồng gọi API).

---

> **Lưu ý cho AI:** 
Hãy luôn ghi nhớ tài liệu này trong suốt phiên làm việc. Mọi quyết định thiết kế và thay đổi mã nguồn phải được đối chiếu lại với các nguyên tắc đã được nạp trong Bước 1 và Bước 3.
Nếu trong 1 đoạn chat đã dài và có yêu cầu kiểm kê lại tài liệu để ghi nhận những sự thay đổi đã làm, thì hãy dựa trên hướng dẫn tài liệu bên trên để đi tới các tài liệu dự án và cập nhật lại với những sự thay đổi mới. 
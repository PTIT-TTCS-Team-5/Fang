File duy nhất trong dự án được viết thủ công :b

## Để làm dự án:
1. Đọc README của FANG và miCareer-mini, từ đó tỏa ra đọc các file strategy quan trọng. Cốt lõi để hiểu được cơ bản 2 code base này
2. Tùy vào việc cần làm trong phiên, thường me chọn sử dụng AI như Gemini FLask hay CLaude Haiku để hỗ trợ hiểu dự án + check tiến độ
3. Khi đã hiểu cơ bản và xác định được việc muốn làm. Trước hết vẫn phải dùng mô hình nhẹ (Flask, Haiku) để trình bày ra việc mình muốn làm -> hỏi để làm rõ hơn về ý định, yêu cầu và cân đo đong đếm cơ bản v.v Cần thiết thì gom cụm vấn đề và dùng Google Deep research để nghiên cứu sâu.
4. Sau khi đã thấy oke về task và có nền tảng nghiên cứu vững chắc, sử dụng Claude Sonnet để xây dựng chiến lược + bản kế hoạch thực thi chi tiết (sửa DB nào, sửa thế nào, sửa hàm nào, sửa thế nào, làm hàm mới nào, hàm mới đó làm gì, liên kết tất cả chúng với nhau v.v Cơ bản là nhìn vào là Code được ngay) 
5. Triển khai, thông thường me sẽ chia kế hoạch thành các pha, thường là 3-5 đối với một tính năng to ví dụ như NMAIex. Cơ bản kế hoạch có chiến lược rõ ràng, có kiến trúc và tài liệu triển khai nhìn là Code được thì:
    - Đối với các task đơn giản kiểu CRUD hoặc chỉ định rất rõ không cần tư duy gì thêm thì cho Gemini Flask làm (hoặc Haiku nhưng me chưa thử)
    - Khó hơn tý mà bắt đầu code đến nhiều hàm, nhiều file thì dùng GPT Codex hoặc Gemini Pro (low-high tùy biến)
    - Đối với các task mà các Model trước bất lực hoặc review code thấy chúng nó không đủ trình làm thì mới sử dụng Claude Sonnet để code (Căng nữa thì dùng hẳn Opus nhưng me chưa bao giờ dùng đến cả) (Thực ra nếu có dư thfi ae cứ bào Sonnet thật mạnh chứ gần như task phải khá dễ, tư duy ít thì mới tin Gemini hay Codex được. Sonnet code thì miễn chê, mỗi tội Anthropic bóp token nên hay bị over token limit)
6. Khi xong rồi thì thường me sẽ dùng một Model nhỏ đến tầm trung để cập nhật toàn bộ tài liệu dự án (Các tài liệu quan trọng như strategy hoặc guide thì vẫn nên dùng Sonnet để biết, cập nhật nhỏ không tư duy nhiều thì dùng đến Gemini Pro thôi)
7. Có 2 phương án, một là xong hẳn thì nghỉ ngơi thôi. Còn chưa xong mà hết token thì cũng nghỉ sớm :b (hoặc cần lắm thì bào credit bằng overages)

## Mấy thứ lặt vặt
- Thi thoảng làm việc 1-2 tuần thì me sẽ ngồi vui vui xem lại quá trình mình dev và nghĩ đến làm Skill. Những việc lặt vặt hoặc những prompt phải dạy đi dạy lại thì mình sẽ gom lại vào 1 skill để trong agent_workflow_doc. Ví dụ:
    - 'AI_MANUAL_UPDATE' để Agent tự lên mạng kiếm thông tin về các Model LLM dự án dùng và sau đó tự động cập nhật tại các tài liệu Code liên quan (cập nhật context size, thông báo deprecation v.v )
    - 'GIT_WORKFLOW_GUIDE' để Agent tự biết cách rẽ nhánh, commit theo chuẩn mình yêu cầu 
    - 'AI_WORKFLOW_INIT' để Agent khởi tạo ngữ cảnh, tự biết đi tìm tài liệu đọc hiểu dự án v.v

## Quan trọng lắm này
- Làm việc với Agent, ít nhất là ở thời điểm hiện tại thì chưa thể tin tưởng được chúng nó đâu =))
    - Phải duyệt phương án triển khai, chiến lược rất kỹ. Đôi khi sửa đi sửa lại chục lần
    - Trong quá trình nó thực thi (tự đọc code, search web, triển khai v.v) phải ngồi đọc suy nghĩ nó liên tục. Để nó tự làm thì mất ổ C lúc nào không biết đâu :b. Đùa thôi nhưng mà thực sự giám sát liên tục lúc nó làm việc mới thấy vẫn còn phải chỉnh khá nhiều, nhất là khi nó bị hallucination mà mình không chặn kịp thì nó quậy cho hỏng hết.
    - Nhất là lúc chúng nó đưa ra phương án xong bảo là đợi mình duyệt mà toàn tự duyệt r làm luôn. Lúc đấy mà không quan sát thì nó tự triển khai lung tung thì ăn đủ :b Tốn token chỉ để sửa r làm lại từ đầu
- À cách dùng bên trên lấy bối cảnh là mình dùng Antigravity có gói google AI pro, github copilot trong vs code có gói pro student nhé. Claude gọi ở bên Antigravity còn Haiku, Codex gọi bên GitHub Copilot


## Prompt mồi mình rất hay dùng 
"Đọc AI_WORKFLOW_INIT để hiểu dự án, đọc [NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md để biết phương án triển khai mới nhất. Đọc [NMAIex]_TASK_CHECHLIST_BACKEND.md và [NMAIex]_TASK_CHECHLIST_FRONTEND.md để biết tiến độ."
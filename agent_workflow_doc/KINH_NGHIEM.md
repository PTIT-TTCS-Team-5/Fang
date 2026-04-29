File duy nhất trong dự án được viết thủ công :b

## Để làm dự án:
1. Đọc README của FANG và miCareer-mini, từ đó tỏa ra đọc các file strategy quan trọng. Cốt lõi để hiểu được cơ bản 2 code base này
2. Tùy vào việc cần làm trong phiên, thường me chọn sử dụng AI như Gemini FLask hay CLaude Haiku để hỗ trợ hiểu dự án + check tiến độ
3. Khi đã hiểu cơ bản và xác định được việc muốn làm. Trước hết vẫn phải dùng mô hình nhẹ (Flask, Haiku) để trình bày ra việc mình muốn làm -> hỏi để làm rõ hơn về ý định, yêu cầu và cân đo đong đếm cơ bản v.v Cần thiết thì gom cụm vấn đề và dùng Google Deep research để nghiên cứu sâu.
4. Sau khi đã thấy oke về task và có nền tảng nghiên cứu vững chắc, sử dụng Claude Sonnet để xây dựng chiến lược + bản kế hoạch thực thi chi tiết (sửa DB nào, sửa thế nào, sửa hàm nào, sửa thế nào, làm hàm mới nào, hàm mới đó làm gì, liên kết tất cả chúng với nhau v.v Cơ bản là nhìn vào là Code được ngay) 
5. Triển khai, thông thường me sẽ chia kế hoạch thành các pha, thường là 3-5 đối với một tính năng to ví dụ như NMAIex. Cơ bản kế hoạch có chiến lược rõ ràng, có kiến trúc và tài liệu triển khai nhìn là Code được thì:
    - Đối với các task đơn giản kiểu CRUD hoặc chỉ định rất rõ không cần tư duy gì thêm thì cho Gemini Flask làm (hoặc Haiku nhưng me chưa thử)
    - Khó hơn tý mà bắt đầu code đến nhiều hàm, nhiều file thì dùng GPT Codex hoặc Gemini Pro (low-high tùy biến)
    - Đối với các task mà các Model trước bất lực hoặc review code thấy chúng nó không đủ trình làm thì mới sử dụng Claude Sonnet để code (Căng nữa thì dùng hẳn Opus nhưng me chưa bao giờ dùng đến cả)
6. Khi xong rồi thì thường me sẽ dùng một Model nhỏ đến tầm trung để cập nhật toàn bộ tài liệu dự án (Thừa token thì dùng tụi Model cao cấp nhưng mà khả năng là phí)
7. Có 2 phương án, một là xong hẳn thì nghỉ ngơi thôi. Còn chưa xong mà hết token thì cũng nghỉ sớm :b (hoặc cần lắm thì bào credit bằng overages)

## Mấy thứ lặt vặt
- Thi thoảng làm việc 1-2 tuần thì me sẽ ngồi vui vui xem lại quá trình mình dev và nghĩ đến làm Skill. Những việc lặt vặt hoặc những prompt phải dạy đi dạy lại thì mình sẽ gom lại vào 1 skill để trong agent_workflow_doc. Ví dụ:
    - 'AI_MANUAL_UPDATE' để Agent tự lên mạng kiếm thông tin về các Model LLM dự án dùng và sau đó tự động cập nhật tại các tài liệu Code liên quan (cập nhật context size, thông báo deprecation v.v )
    - 'GIT_WORKFLOW_GUIDE' để Agent tự biết cách rẽ nhánh, commit theo chuẩn mình yêu cầu 
    - 'AI_WORKFLOW_INIT' để Agent khởi tạo ngữ cảnh, tự biết đi tìm tài liệu đọc hiểu dự án v.v
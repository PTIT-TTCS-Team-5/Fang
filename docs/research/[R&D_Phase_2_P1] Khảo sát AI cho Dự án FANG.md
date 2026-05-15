# **Báo cáo Nghiên cứu Khảo sát Thị trường Mô hình AI và Thiết kế Kiến trúc Tối ưu cho Dự án FANG (Cập nhật Tháng 5/2026)**

Quá trình chuyển đổi số trong lĩnh vực công nghệ nhân sự (HR Tech) đang chứng kiến sự thay đổi hệ sinh thái vô cùng mạnh mẽ vào giai đoạn nửa đầu năm 2026\. Sự ra đời của các mô hình ngôn ngữ lớn (LLM) thế hệ mới, cùng với những bước tiến đột phá trong công nghệ vector hóa và kỹ thuật nén dữ liệu, đã định hình lại hoàn toàn cách các hệ thống tuyển dụng phân tích và đánh giá ứng viên. Báo cáo nghiên cứu này được thực hiện nhằm cung cấp một khảo sát thị trường toàn diện về các mô hình AI tính đến tháng 5/2026, được đối chiếu trực tiếp với các nhu cầu kỹ thuật và những ràng buộc khắt khe của dự án FANG (FastAPI Backend AI Core).

Hệ thống FANG hoạt động với mục tiêu học thuật và trình diễn thực tế, sở hữu nguồn tài nguyên phần cứng giới hạn (GPU RTX 2050 4GB VRAM) và một ngân sách vô cùng thắt chặt (tài khoản OpenAI Tier 1 với $5 credit, cùng hai khóa API Google Gemini Free Tier). Tài khoản Anthropic hiện trong trạng thái không khả dụng. Những yếu tố này đòi hỏi một chiến lược kiến trúc phải đạt đến độ tinh giản tối đa, khai thác triệt để các dịch vụ miễn phí (Free Tier) có độ trễ thấp, kết hợp với kỹ thuật tối ưu hóa bộ nhớ hệ thống (Prompt Caching và Scalar Quantization). Toàn bộ các mô hình trên 7 tỷ tham số sẽ bị loại trừ khỏi phương án triển khai cục bộ (local inference), mọi tương tác xử lý nhận thức đều phải được định tuyến thông qua các API đám mây.

## ---

**Đánh giá Chuyên sâu: Nghịch lý của RAG trong Xử lý Tài liệu Đơn lẻ**

Trước khi tiến hành khảo sát các mô hình AI cụ thể, báo cáo cần giải quyết một thắc mắc mang tính quyết định về mặt kiến trúc từ nhóm phát triển: *Liệu phương pháp Retrieval-Augmented Generation (RAG) có thực sự cần thiết khi truy vấn trong phạm vi một hồ sơ ứng viên (Job Application) đơn lẻ, so với việc cung cấp toàn bộ nội dung CV đã được làm phẳng dưới dạng Markdown?*

Phân tích dữ liệu thực tiễn và các nghiên cứu đánh giá hiệu năng (benchmark) trong năm 2026 chỉ ra rằng, việc áp dụng RAG cho một tài liệu đơn lẻ như CV đang dần trở thành một thiết kế nghịch lý (anti-pattern) gây lãng phí tài nguyên và làm suy giảm độ chính xác của hệ thống.1 Dưới đây là những phân tích đa chiều về vấn đề này:

Thứ nhất, xét về bài toán kinh tế học token và độ trễ hệ thống (Latency). Trong quá khứ, RAG được sinh ra để khắc phục điểm yếu của các mô hình ngôn ngữ có cửa sổ ngữ cảnh (context window) hạn hẹp. Tuy nhiên, tính đến tháng 5/2026, các mô hình hạng nhẹ (Lite) tiêu chuẩn như gemini-3.1-flash-lite-preview hay gpt-5.4-mini đều đã hỗ trợ cửa sổ ngữ cảnh khổng lồ, trải dài từ 400.000 đến hơn 1.000.000 token.3 Một bản CV trung bình sau quá trình trích xuất và chuyển đổi sang định dạng Markdown hiếm khi vượt quá ngưỡng 2.000 đến 3.000 token. Việc gửi toàn bộ văn bản này vào một mô hình có sức chứa một triệu token là hoàn toàn khả thi và không gây ra hiện tượng tràn bộ nhớ. Quan trọng hơn, với sự phổ cập của cơ chế Prompt Caching (Lưu bộ nhớ đệm ngữ cảnh), chi phí đầu vào đã được các nhà cung cấp cắt giảm từ 50% đến 90%.5 Ví dụ, chi phí gửi 2.000 token văn bản vào gpt-5.4-mini thông qua bộ nhớ đệm chỉ tiêu tốn khoảng $0.00015 cho mỗi lượt truy vấn.3 Trái lại, quy trình RAG yêu cầu tài liệu phải đi qua nhiều công đoạn phức tạp: phân mảnh (chunking), tạo vector nhúng (embedding API call), tìm kiếm qua mạng lưới HNSW trong PostgreSQL, và dung hợp kết quả bằng thuật toán RRF. Sự phức tạp này đẩy độ trễ hệ thống lên cao, trung bình mất hơn một giây cho mỗi truy vấn, trong khi việc truyền trực tiếp văn bản Markdown giúp hệ thống phản hồi gần như ngay lập tức.7

Thứ hai, xét về mức độ toàn vẹn của dữ liệu và hiện tượng "Suy thoái RAG" (RAG Decay). Các nghiên cứu thực nghiệm cảnh báo rằng khi tương tác với một lượng thông tin nhỏ nhưng có độ cô đặc ngữ nghĩa cao như CV, thuật toán tìm kiếm vector rất dễ bỏ sót các chi tiết mang tính "mò kim đáy bể" (needle-in-a-haystack).2 Các bộ chia văn bản (text splitters), dù được tinh chỉnh để nhận diện cấu trúc, vẫn có rủi ro chia cắt các chuỗi logic ngầm định liên kết giữa kinh nghiệm làm việc và kỹ năng tích lũy.9 Ngược lại, khi toàn bộ CV Markdown được nạp trực tiếp vào System Prompt, cơ chế tự chú ý (Self-Attention) của mạng Transformer sẽ có cái nhìn toàn cảnh (holistic view).10 Mô hình có thể đối chiếu chéo các kỹ năng được đề cập ở cuối CV với các dự án thực tế nằm ở phần đầu, mang lại khả năng phân tích sự phù hợp sâu sắc hơn nhiều so với việc chỉ đọc các đoạn văn bản bị cắt rời.1

**Khuyến nghị tái cấu trúc:** Đối với Module TTCS (RAG-based Chat), khi một ứng viên hoặc chuyên viên nhân sự (HR) chỉ đang chất vấn về một hồ sơ ứng viên hoặc một mô tả công việc (Job Posting) đơn lẻ, hệ thống FANG nên loại bỏ hoàn toàn bước tìm kiếm vector. Thay vào đó, toàn bộ nội dung Markdown của CV và JD sẽ được nạp trực tiếp vào ngữ cảnh hệ thống (Full Context Injection). RAG chỉ nên được giữ lại và tối ưu hóa cho Module NMAIex, nơi hệ thống phải thực hiện quét và đối chiếu chéo hàng ngàn CV khác nhau để tìm ra top ứng viên phù hợp nhất cho một vị trí tuyển dụng, vì không một cửa sổ ngữ cảnh nào có đủ không gian và khả năng kinh tế để chứa đựng hàng ngàn CV cùng lúc.11

**NOTE FROM HƯNG**: Xác nhận - 10/05/2026
- Đối với Chat trong 1 JobApplication -> Bỏ RAG, kéo trực tiếp CV (parsed) markdown + JD info + interview/feedback info + offer info.
- Đối với ranking system thuộc nmaiex -> Giữ RAG (Có thể cải tiến) để  tối ưu hóa

## ---

**Phần A — Khảo sát Thị trường Mô hình Ngôn ngữ Lớn (Tháng 5/2026)**

Bức tranh thị trường AI đầu năm 2026 đánh dấu sự chuyển dịch mạnh mẽ từ các mô hình siêu tham số sang các mô hình nhỏ gọn, được tinh chỉnh cho các tác vụ suy luận phân tích ngách (agentic tasks) với tốc độ phản hồi cực thấp. Dưới đây là các bảng khảo sát và đối chiếu năng lực mô hình, phục vụ trực tiếp cho từng module chức năng của dự án FANG.

### **Bảng 1: Trích xuất Dữ liệu CV (CV Parsing) và Chuẩn hóa Kỹ năng (Skill Mapping)**

Tác vụ phân tích CV là nút thắt cổ chai đầu tiên của hệ thống. Dữ liệu CV mang tính phi cấu trúc cao, đa dạng về định dạng và chứa nhiều thuật ngữ công nghệ viết tắt. Do đó, mô hình lý tưởng phải sở hữu khả năng tuân thủ mệnh lệnh (instruction-following) tuyệt đối, năng lực tạo JSON có cấu trúc (Structured Outputs) ổn định và am hiểu sâu sắc ngữ pháp tiếng Việt để ánh xạ kỹ năng một cách chuẩn xác.

| Model | Provider | Giá Input ($/1M token) | Giá Output ($/1M token) | Context Window | Hỗ trợ JSON Mode | Điểm mạnh tiếng Việt | Ghi chú |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| gemini-3.1-flash-lite-preview | Google | $0.25 (Có Free Tier) | $1.50 (Có Free Tier) | 1,048,576 | Có | Rất tốt (MTEB: 68.32) | Ra mắt tháng 3/2026, mô hình hiệu năng/chi phí xuất sắc, tốc độ 363 tokens/giây, hỗ trợ RAG đa ngôn ngữ.4 |
| gpt-5.4-mini | OpenAI | $0.75 (Cached: $0.075) | $4.50 | 400,000 | Có | Tốt | Tối ưu hóa suy luận, vượt trội về mã hóa JSON, thay thế dòng GPT-4o-mini.3 |
| claude-4.5-haiku | Anthropic | $1.00 (Cached: $0.10) | $5.00 | 200,000 | Có | Tốt | Mô hình nhanh nhất của Anthropic, lý tưởng cho dữ liệu phi cấu trúc.15 |
| gemini-3.1-pro-preview | Google | $2.00 (Có Free Tier) | $12.00 | 1,000,000+ | Có | Xuất sắc | Sở hữu khả năng suy luận mạnh mẽ, phù hợp giải quyết các CV phức tạp, nhiễu dữ liệu.17 |
| gpt-5.4 | OpenAI | $2.50 (Cached: $0.25) | $15.00 | 272,000 | Có | Xuất sắc | Dòng flagship thay thế GPT-4.1, chuyên gia trong tuân thủ định dạng ngặt nghèo.19 |
| gpt-5.5 | OpenAI | $5.00 (Cached: $0.50) | $30.00 | 1,050,000 | Có | Xuất sắc (SOTA) | Mô hình tiên tiến nhất ra mắt tháng 4/2026, vượt quá ngân sách dự án.20 |

*(Dữ liệu giá và Context Window được xác minh từ trang chủ OpenAI Platform, Google AI Studio và Anthropic Console tính đến 10/05/2026).*

**Khuyến nghị cho dự án FANG:**

Với rào cản kỹ thuật là tài khoản Anthropic đã bị khóa, toàn bộ các điểm cuối API của Claude (như claude-4.5-haiku hay claude-4.6-sonnet) sẽ bị loại bỏ khỏi danh sách triển khai thực tiễn. Kiến trúc **5-Tier Fallback** của Parser cần được tái quy hoạch để tối đa hóa hiệu suất của Google Free Tier và ngân sách $5 của OpenAI:

1. **Tier 1 (Lite mặc định):** Khuyến nghị sử dụng gemini-3.1-flash-lite-preview. Đây là khối động cơ hoàn hảo vì nó hoàn toàn miễn phí qua Google AI Studio, đạt tốc độ 363 tokens/giây và có độ tin cậy trích xuất JSON đáng nể.4  
2. **Tier 2 (Lite dự phòng):** Sử dụng gpt-5.4-mini. Với ngân sách $5, hệ thống có thể mua được hơn 6,6 triệu token đầu vào, hoặc 66 triệu token nếu ứng dụng tốt Prompt Caching.3 Điều này biến OpenAI thành một mạng lưới an toàn tuyệt đối khi Google API gặp hiện tượng thắt cổ chai (Rate Limit).  
3. **Tier 3 (Lite thay thế):** gemini-3.1-flash. Phiên bản mạnh hơn bản Lite, lấp đầy chỗ trống do Claude để lại.22  
4. **Tier 4 (ProTierGate):** gemini-3.1-pro-preview. Nhờ giới hạn miễn phí của Google, FANG có thể truy cập mô hình có trí thông minh ngang ngửa GPT-5.4 mà không mất phí để giải cứu các CV không đạt chuẩn Quality Gate.17  
5. **Tier 5 (Giải pháp cuối cùng):** gpt-5.4. Chi phí của mô hình này khá đắt đỏ so với ngân sách ($2.50/$15.00), do đó chỉ nên gọi trong các trường hợp CV mang tính dị biệt cao.19

**NOTE FROM HƯNG**: Xác nhận -  10/05/2026
- Trông hơi xấu so với mô hình 5 tier [Gemini Flask -> ChatGPT-mini -> Claude Haiku -> Gemini Pro -> ChatGPT 5.4] ban đầu. Nhưng kết quả phân tích cho thấy hợp lý -> Áp dụng.
- Có nhiều Model Trung Quốc có kết quả bench rất tốt + siêu rẻ nhưng lại không được sử dụng chút nào trong hệ thống? -> Có nhiều lý do, một vài điểm quan trọng được kể đến như: Tính ổn định - Hỗ trợ tiếng Việt - JSON ouput -> Nghe hay thật nhưng mà trong dự án này, chưa thể dùng. 

### **Bảng 2: Chuyển đổi Ngữ nghĩa (Semantic Embedding)**

Tác vụ Embedding đóng vai trò quyết định trong sự thành bại của pha tìm kiếm vector. Hệ thống cần các mô hình đa ngôn ngữ thực thụ, phản ứng nhạy bén với cấu trúc danh từ tiếng Việt và hỗ trợ tính năng cắt giảm số chiều (Matryoshka) để tối ưu lưu trữ.

| Model | Provider | Giá ($/1M token) | Dimensions (Số chiều) | Multilingual (Hỗ trợ tiếng Việt) | VN-MTEB / MTEB Score | Matryoshka? | Ghi chú |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| gemini-embedding-001 (Gemini 2\) | Google | $0.15 (Miễn phí qua AI Studio) | 3072 (Linh hoạt giảm xuống 1024, 768, 256\) | Xuất sắc (100+ ngôn ngữ) | 68.32 | Có (MRL) | Mô hình nhúng SOTA hiện tại, hiểu ngữ nghĩa đa phương thức, tối ưu cho Retrieval tiếng Việt.24 |
| text-embedding-3-small | OpenAI | $0.02 | 1536 (Linh hoạt giảm xuống 1024, 512\) | Tốt | 62.3 | Có | Phổ biến, chi phí rẻ, nhưng yếu thế khi xử lý ngữ cảnh đa ngôn ngữ chuyên sâu.26 |
| voyage-3-large | Voyage AI | $0.18 (200M token miễn phí) | 2048 (Linh hoạt giảm xuống 1024\) | Tốt | \~67.1 | Có | Tối ưu hóa cực tốt cho tài liệu kỹ thuật, code và HR data.26 |
| jina-embeddings-v3 | Jina AI | $0.018 (10M token miễn phí) | 1024 (Linh hoạt giảm xuống 32\) | Xuất sắc | 65.5 | Có | Cung cấp các adapter chuyên biệt, kiến trúc open-weights linh hoạt.26 |

**Khuyến nghị về Dimension và Loại lưu trữ cho FANG:** Hiện tại, FANG đang ứng dụng mô hình text-embedding-3-small với 1024 chiều, lưu trữ dạng halfvec.9 Đây là một quyết định kiến trúc rất đúng đắn khi áp dụng cùng kỹ thuật Matryoshka Representation Learning (MRL). MRL không chỉ đơn thuần là cắt gọt vector; nó ép mạng nơ-ron học cách cô đặc những đặc trưng ngữ nghĩa quan trọng nhất vào những chiều đầu tiên.29 Do đó, việc giảm từ 3072 hay 1536 chiều xuống 1024 chiều gây ra sự thất thoát dữ liệu vô cùng nhỏ, nhưng lại mang đến lợi ích vật lý khổng lồ.

Khi lưu trữ 1024 chiều dưới dạng halfvec (lượng tử hóa vô hướng giảm độ chính xác từ float32 xuống float16), dung lượng bộ nhớ cho mỗi vector giảm xuống chỉ còn khoảng 2KB. Một trang đĩa tiêu chuẩn (page) của PostgreSQL có kích thước 8KB. Bằng cách giảm dung lượng, cơ sở dữ liệu có thể nạp nhiều vector hơn vào một trang đĩa, giảm triệt để số lượng các thao tác I/O đọc/ghi, đồng thời tăng tốc độ xây dựng đồ thị HNSW lên 23%.30

**Đề xuất:** FANG **không nên** đổi sang kiểu vector (float32) ở môi trường phát triển lẫn production, vì halfvec(1024) đã đạt đến điểm cân bằng Pareto hoàn hảo giữa giới hạn phần cứng (4GB VRAM, 16GB RAM) và độ nhạy của thuật toán tìm kiếm Cosine Similarity.9

Tuy nhiên, về mặt mô hình, dự án nên chuyển từ text-embedding-3-small sang **gemini-embedding-001**. Mô hình của Google vượt trội hơn hẳn về khả năng hiểu tiếng Việt (điểm MTEB 68.32 so với 62.3) 25, khả năng tương thích API miễn phí và sự kết hợp mượt mà với kỹ thuật MRL ở mức 1024 chiều.32

**NOTE FROM HƯNG**: Xác nhận -  10/05/2026
- Chuyển đổi mô hình embedding từ text-embedding-3-small sang gemini-embedding-001
- Rank trên https://huggingface.co/spaces/mteb/leaderboard - 10/05/2026:
    - Top 5 overall, retrieval top 9 Nhưng cơ bản nó free, dễ dùng qua Google API và tốt hơn nhiều so với mô hình cũ :b -> Chọn

### **Bảng 3: Sinh văn bản và Quản lý Hội thoại (RAG Generation)**

Tác vụ này yêu cầu mô hình đóng vai trò là một Agent trung tâm, có khả năng xử lý hợp nhất (Late Fusion) các nguồn ngữ cảnh đa dạng (CV Chunks, Job Posting, Candidate Profile, ATS History), duy trì cửa sổ hội thoại dài hạn và trích dẫn thông tin chuẩn xác.

| Model | Provider | Giá Input ($) | Giá Output ($) | Context Window | Khả năng Grounding / Citation | Ghi chú |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| gemini-3.1-flash-lite-preview | Google | $0.25 | $1.50 | 1,048,576 | Google Search / Maps (Miễn phí 5k query/tháng) | Phản hồi thông tin dưới 1 giây, giữ được ngữ cảnh hội thoại lớn với chi phí siêu rẻ.4 |
| gpt-5.4-mini | OpenAI | $0.75 | $4.50 | 400,000 | Web Search / File Search | Tối ưu hóa suy luận nội bộ, giá rẻ, là hệ thống lõi dự phòng hiệu quả.3 |
| gemini-3.1-pro-preview | Google | $2.00 | $12.00 | 1,000,000+ | Google Search | Năng lực phân tích đa nguồn xuất sắc, vượt trội khi xử lý các ATS History phức tạp.17 |
| gpt-5.4 | OpenAI | $2.50 | $15.00 | 272,000 | Web Search | Phù hợp đưa ra các kết luận nhân sự mang tính quyết định nhờ khả năng lý luận (reasoning) nâng cao.19 |

**Khuyến nghị cho dự án FANG:** Với đặc thù kiến trúc "Context Window Management" của FANG sử dụng Token Budget kết hợp Summarization thay vì Sliding Window 9, các mô hình có Context lớn (1M+) và hỗ trợ Prompt Caching là chìa khóa sống còn. Gemini 3.1 Flash-Lite cung cấp một cơ chế Caching với giá cực rẻ (0.025 đô/1M token đầu vào).23 Hệ thống FANG nên tự động nạp Job Posting và cấu trúc System Prompt vào bộ nhớ cache. Mỗi khi người dùng hỏi một câu mới, mô hình chỉ tính phí cho đoạn văn bản mới, bảo vệ triệt để ngân sách $5 của dự án mà vẫn đảm bảo độ sâu của ngữ cảnh lịch sử.

**NOTE FROM HƯNG**: Ghi nhận -  10/05/2026
- 4 mô hình được đề xuất bên trên thực tế đã nằm trong 7 model Mode gốc -> Giữ lại Model Mode cũ và người dùng (HR) vẫn được quyền chọn 1 trong 7 để chat.
- Sẽ nghiên cứu về việc cache để giảm thiểu tiêu thụ token nói riêng và các cơ chế tiết kiệm chi phí khác nói chung.
- **Đặc biệt**: (ghi nhớ) nghiên cứu về việc nâng cấp chức năng phục vụ HR trong một JobApplication. Không chỉ Chat mà còn nghiên cứu nâng cấp chức năng AI lên mức độ Agent bao gồm: 
    - Nghiên cứu xây dựng Agent, dạy bằng Skill để xử lý các tác vụ phục vụ chuyên môn cho HR v.v
    - Cung cấp khả năng để Agent tương tác với các thông tin trong ngữ cảnh ví dụ như tạo interview, viết interview feedback, đưa offer v.v Tất cả phải được HR duyệt/chỉnh sửa/nhận xét và được kiểm soát chặt chẽ.
    - Những chức năng khó như để Agent search web v.v sẽ chỉ được xem xét khi xong những điều trên.

### **Bảng 4: Xếp hạng và Đánh giá (Reranking / Cross-Encoder)**

Để giải quyết vấn đề độ nhiễu ngữ nghĩa sau bước tìm kiếm Sparse/Dense, Reranker đóng vai trò là trọng tài cuối cùng đánh giá mức độ tương thích ngữ nghĩa chéo (Cross-Attention) giữa Câu truy vấn (Query) và Văn bản (Document).

| Model | Provider | Loại (API / Local) | Chi phí ($/1M token hoặc theo truy vấn) | Năng lực Đa ngôn ngữ | Ghi chú |
| :---- | :---- | :---- | :---- | :---- | :---- |
| jina-reranker-v3 | Jina AI | Cả hai | $0.045 / 1M token (Miễn phí 10M token đầu tiên) | Xuất sắc | Cửa sổ ngữ cảnh 131K, khả năng đánh giá sự phù hợp HR tiếng Việt rất ấn tượng, mã nguồn mở.33 |
| voyage-rerank-2.5 | Voyage AI | API | $0.05 / 1M token (Miễn phí 200M token đầu tiên) | Tốt | Tối ưu hóa độ trễ, cung cấp điểm số relevance có độ tin cậy cao.35 |
| cohere-rerank-3.5 | Cohere | API | $2.00 / 1.000 lượt search | Tốt | API tiêu chuẩn ngành công nghiệp nhưng cách tính phí theo lượt search khá đắt đỏ.37 |

**Khuyến nghị cho dự án FANG:** Các mô hình Cross-Encoder (như BGE-Reranker) hoạt động bằng cách đưa cả Query và Document vào cùng một mạng transformer, đòi hỏi một lượng năng lực tính toán bình phương. Thiết bị phần cứng của dự án (RTX 2050 4GB VRAM) hoàn toàn không thể tải các mô hình Reranker cục bộ một cách hiệu quả.38 Giải pháp duy nhất là sử dụng API.

Khuyến nghị FANG tích hợp **jina-reranker-v3** hoặc **voyage-rerank-2.5** vào module NMAIex. Voyage AI mang lại sự an tâm tuyệt đối về ngân sách học thuật nhờ chính sách cấp phát miễn phí lên tới 200 triệu token.35 Sự hiện diện của Reranker sẽ bù đắp hoàn toàn những khiếm khuyết của RRF, đẩy điểm số đánh giá độ phù hợp (relevance score) của ứng viên lên độ chính xác cao nhất.39

**NOTE FROM HƯNG**: đã đọc -  10/05/2026
- Chưa triển khai reranking vội, ưu tiên refactor toàn bộ dự án và sử dụng tạm thời cơ chế RRF + late fusion + scoring hiện tại. Sẽ nghiên cứu về metric + áp dụng reranking trong tương lai

## ---

**Phần B — Phân tích Chuyên đề về Kiến trúc Embedding Model**

Quyết định lựa chọn và thay thế mô hình Embedding là một trong những cột mốc kiến trúc mang tính bất biến (immutable) nhất trong vòng đời của một dự án RAG. Một khi dữ liệu đã được vector hóa và lưu trữ, mọi sự thay đổi mô hình đều kéo theo việc phải xóa trắng cơ sở dữ liệu và tái nhúng (re-embed) toàn bộ hệ thống. Với lợi thế FANG chưa có dữ liệu production thật, đây là thời điểm vàng để đưa ra các quyết định tái định hình không gian vector.

**1\. Vị thế của text-embedding-3-small tính đến tháng 5/2026** Khi ra mắt vào đầu năm 2024, mô hình này đã thống trị thị trường nhờ mức giá rẻ vô địch ($0.02/1M token) và hỗ trợ Matryoshka.26 Tuy nhiên, thị trường năm 2026 đã chứng kiến sự ra đời của các mô hình chuyên biệt hóa mạnh mẽ hơn. Về hiệu năng đa ngôn ngữ, đặc biệt là sự phức tạp trong hình thái học tiếng Việt, text-embedding-3-small bị kìm hãm ở điểm số MTEB khoảng 62.3 \- 64.6.26 Khả năng phân tách các ý niệm kỹ thuật, từ mượn và danh từ ghép trong chuyên ngành HR của mô hình này tỏ ra yếu thế hơn so với các mô hình nhúng mã nguồn mở (như Qwen3-Embedding) hay các mô hình thương mại thế hệ mới. Mặc dù vẫn là một giải pháp an toàn trong hệ sinh thái OpenAI, nó không còn là vị vua tuyệt đối về mặt hiệu năng.

**2\. Đánh giá gemini-embedding-001 (Google) so với text-embedding-3-small** Google đã tiến hành quy hoạch hệ thống danh pháp, trong đó gemini-text-embedding-004 hiện đã trở thành nền tảng chính thức dưới tên gọi **gemini-embedding-001** (hay Gemini Embedding 2).25 Mô hình này đại diện cho bước tiến lớn về công nghệ nhúng:

* **Hiệu năng Tiếng Việt:** Được huấn luyện dựa trên bộ trọng số đa ngôn ngữ gốc của dòng LLM Gemini, nó đạt điểm MTEB đa ngôn ngữ 68.32, bỏ xa đối thủ từ OpenAI.25 Sự vượt trội này mang tính sống còn khi hệ thống phải xử lý các câu mô tả công việc hàm chứa cả tiếng Anh và tiếng Việt đan xen.  
* **Chi phí Kỹ thuật:** Với FANG, yếu tố quan trọng nhất là API này được cung cấp hoàn toàn **miễn phí** qua hệ thống Google AI Studio.23 Điều này giải phóng lập tức khoản ngân sách $5 của OpenAI, cho phép dồn toàn lực tài chính vào các tầng Fallback sinh văn bản đắt đỏ hơn.  
* **Rủi ro môi trường Dev vs. Production:** Việc sử dụng Google Free Tier để sinh dữ liệu trong môi trường phát triển (Dev) là một nước đi xuất sắc. Nếu sau này dự án chuyển sang môi trường Production và buộc phải đổi nhà cung cấp (do Google giới hạn Rate Limit hoặc khóa key), rủi ro lớn nhất là chi phí API để tái nhúng hàng trăm ngàn CV, đồng thời gây ra thời gian ngưng trệ hệ thống (downtime). Tuy nhiên, vì Google vẫn cung cấp Paid Tier với giá $0.15/1M token 25, dự án hoàn toàn có thể nâng cấp thanh toán ngay trên hệ thống của Google mà không cần thay đổi mô hình, triệt tiêu hoàn toàn rủi ro tái nhúng dữ liệu.

**3\. Tiêu chí cốt lõi khi chọn Embedding Model hướng Production**

Để bảo đảm tính bền vững của không gian Vector trong chu kỳ từ 2 đến 3 năm, các tiêu chí sau phải được đặt lên hàng đầu:

* **Độ linh hoạt của số chiều (Native Matryoshka Support):** Hệ thống cơ sở dữ liệu có xu hướng phình to theo cấp số nhân. Mô hình bắt buộc phải hỗ trợ MRL để kỹ sư quản trị có thể tự do giới hạn số chiều lưu trữ (1024 hoặc 512\) nhằm cứu nguy cho tài nguyên RAM mà không làm sụp đổ cấu trúc phân cụm vector.29  
* **Năng lực xử lý ngữ cảnh dài (Long-Context Span):** Với kiến trúc Chunking Small-to-Big của FANG 9, các Parent Node có thể vượt quá giới hạn 512 token. Mô hình nhúng phải có khả năng mã hóa từ 2048 đến 8192 token để không chặt đứt các thông tin cuối cùng của đoạn văn.25  
* **Sức mạnh Đa ngôn ngữ (VN-MTEB Performance):** Ngữ nghĩa tiếng Việt cần được chiếu xạ một cách độc lập và chính xác, không bị phụ thuộc vào các nhãn từ tiếng Anh.

Dựa trên các hệ quy chiếu này, **gemini-embedding-001** của Google, với hỗ trợ MRL bẩm sinh, ngữ cảnh 2048 token và điểm MTEB hàng đầu, là cấu trúc nhúng đáp ứng tốt nhất yêu cầu ổn định lâu dài.

**4\. Tác động vật lý của Matryoshka Embeddings đối với Storage Type** Kỹ thuật Matryoshka Representation Learning (MRL) và kiểu lưu trữ halfvec (Lượng tử hóa vô hướng) có một sự tương tác cộng sinh tuyệt vời ở cấp độ phần cứng.29 MRL tổ chức mạng nơ-ron để các thành phần quan trọng (principal components) của vector tập trung ở những chiều không gian đầu tiên. Khi FANG thiết lập số chiều là 1024 (cắt đi 2048 chiều kém quan trọng từ mảng 3072 gốc của Gemini), hệ thống không làm mất đi các đặc trưng phân loại chính.

Việc áp dụng kiểu halfvec(1024) mang lại ba lợi ích cốt lõi chi phối trực tiếp đến phần cứng hệ thống:

1. **Dấu chân bộ nhớ (Memory Footprint):** Float16 (2 byte) cắt giảm một nửa kích thước của Float32 (4 byte). Một vector 1024 chiều hiện tại chỉ chiếm khoảng 2KB thay vì 4KB.31  
2. **Tối ưu hóa Băng thông I/O:** Cấu trúc phân trang (Paging) của PostgreSQL mặc định là 8KB. Với 2KB mỗi vector cộng thêm siêu dữ liệu, PostgreSQL có thể nhồi nhét hai (thậm chí ba) vector vào một trang vật lý. Điều này đồng nghĩa với việc các phép quét tuần tự (sequential scans) hoặc nạp chỉ mục HNSW sẽ giảm một nửa số lượng lời gọi đọc đĩa (disk reads).9  
3. **Bảo vệ giới hạn phần cứng:** Máy trạm (Laptop) phát triển chỉ có 16GB RAM. Quá trình tính toán khoảng cách cosine trong đồ thị HNSW diễn ra chủ yếu ở bộ nhớ chính. Bằng việc duy trì không gian vector ở giới hạn halfvec(1024), FANG ngăn chặn hiện tượng tràn RAM (OOM) và đảm bảo thuật toán truy vấn không bị gián đoạn.

**NOTE FROM HƯNG**: Xác nhận -  10/05/2026
- Chuyển đổi sang gemini-embedding-001 ok, nhưng cần lưu ý về khả năng hỗ trợ long-context

## ---

**Phần C — Cập nhật Tình trạng Khấu hao (Deprecation) và Quản trị Rủi ro**

Dựa trên việc đối chiếu với nhật ký thay đổi (Changelog) chính thức từ các nhà cung cấp, chiến lược LLM hiện tại trong các tệp cấu hình của FANG đang tiềm ẩn những rủi ro ngắt kết nối nghiêm trọng. Hệ thống quản lý Fallback cần phải được thiết lập lại ngay lập tức để duy trì tính liền mạch.

**1\. Các mô hình đã bị Deprecated hoặc ngừng phục vụ** Các tài liệu vận hành đã phản ánh chính xác tình trạng "lão hóa" của nhiều điểm cuối API 9:

* **Google:** gemini-3-pro-preview đã chính thức bị đóng cửa (shutdown) vào ngày 09/03/2026. Ngoài ra, phiên bản gemini-2.0-flash cũng đã được đưa vào danh sách deprecated.40  
* **OpenAI:** Các mô hình thế hệ cũ bao gồm gpt-4o, gpt-4.1, gpt-4.1-mini đã chính thức nghỉ hưu từ ngày 13/02/2026. Mô hình gpt-5.1 (bao gồm các phiên bản Instant/Thinking/Pro) cũng đã bị tháo gỡ hoàn toàn khỏi hệ thống vào ngày 11/03/2026.41  
* **Anthropic:** Mô hình claude-3.5-sonnet ngừng phục vụ từ ngày 19/02/2026, và claude-3.7-sonnet dự kiến sẽ đóng cửa vào ngày 11/05/2026.43 Đáng lưu ý hơn, do tài khoản cấp quyền của FANG đã bị khóa, toàn bộ mọi nỗ lực định tuyến tới bất kỳ mô hình Claude 4.5/4.6 nào cũng sẽ trả về mã lỗi 403 (Forbidden) hoặc 401 (Unauthorized). Việc tiếp tục bảo lưu claude-4.5-haiku ở Tier 3 sẽ làm tăng độ trễ mạng do hệ thống phải chờ phản hồi lỗi trước khi chuyển sang tầng Fallback tiếp theo.

**2\. Lộ trình Thay thế Chính thức từ Provider**

* Với Google, mọi lưu lượng truy cập tới mô hình 3.0 Pro cần được chuyển dời toàn bộ sang **gemini-3.1-pro-preview**.40 Dòng mô hình 3.1 được Google tái tối ưu cấu trúc giá, trở thành trụ cột dài hạn.  
* Với OpenAI, các văn bản quy phạm kỹ thuật khuyến nghị người dùng di dời khối lượng công việc cấp thấp từ gpt-4o/gpt-5.1 sang **gpt-5.4-mini**, trong khi các tác vụ lý luận phức tạp cần được chuyển giao cho **gpt-5.4** hoặc **gpt-5.5**.3

**3\. Khuyến nghị Tái quy hoạch Danh sách Tier cho Dự án FANG**

Dựa trên những phát kiến công nghệ từ đầu năm 2026, chiến lược 5-Tier Parser và RAG Generation cần được lập trình lại. MODEL\_CANDIDATES trong file rag\_model\_adapters.py phải được tinh chỉnh để loại bỏ Anthropic và khai thác triệt để Google Free Tier nhằm bảo vệ quỹ OpenAI:

* **Tier 1 (Mặc định \- Nhóm Lite):** gemini-3.1-flash-lite-preview. Đây là tấm khiên phòng thủ đầu tiên. Với tốc độ xử lý 363 tokens/giây và không mất chi phí qua AI Studio, nó thừa sức giải quyết 90% các CV thông thường cũng như tổng hợp ngữ cảnh đàm thoại RAG.4  
* **Tier 2 (Dự phòng hạ tầng \- Nhóm Lite):** gpt-5.4-mini. Đóng vai trò là hệ thống chuyển mạch (failover) an toàn nhất. Nếu API của Google gặp lỗi giới hạn tần suất (Rate Limit 429), gpt-5.4-mini với ngân sách $5 sẽ dễ dàng tiếp quản công việc mà không làm sụp đổ hệ thống.3  
* **Tier 3 (Bảo đảm chất lượng \- Nhóm Lite):** gemini-3.1-flash (Bản tiêu chuẩn). Việc loại bỏ Claude tạo ra một khoảng trống về chất lượng. Bản tiêu chuẩn của Flash sẽ đảm nhiệm vai trò kiểm soát lỗi cho các hồ sơ mà bản Lite không xử lý tốt.  
* **Tier 4 (Chốt chặn chuyên môn \- Nhóm Pro):** gemini-3.1-pro-preview. Được điều hướng bởi cơ chế ProTierGate, mô hình này sẽ giải mã các CV chứa cấu trúc bảng biểu nhiễu loạn hoặc các câu hỏi tư vấn tuyển dụng mang tính định hướng chiến lược. Sử dụng Free Key thứ hai để phân tải.17  
* **Tier 5 (Lá chắn cuối cùng \- Nhóm Pro):** gpt-5.4. Khi tất cả các tuyến phòng ngự trước đều thất bại, hệ thống buộc phải dựa vào năng lực lý luận (reasoning) vượt bậc của OpenAI.20 Lệnh gọi đến tầng này cần được giám sát chặt chẽ thông qua bảng AIQUERYLOG để ngăn chặn việc rò rỉ ngân sách quá đà.9

**Tổng kết:** Cấu trúc AI Core của FANG hiện đang sở hữu một triết lý thiết kế (Zero-LLM-Cost Ingestion và 5-Tier ProTierGate) đi trước thời đại. Việc thay thế các cấu kiện nhúng thành gemini-embedding-001, áp dụng chiến lược Full Context Injection thay cho RAG đối với các Job Application đơn lẻ, và cấu hình lại hàng rào Fallback sẽ củng cố tính vững chắc của hệ thống, biến FANG thành một công trình học thuật có khả năng chịu tải tương đương với các giải pháp thương mại thực tiễn.

**NOTE FROM HƯNG**: Đã đọc - 10/05/2026
- Thực ra tạo lại Account Claude platform mới và giữ lại Claude Haiku trong tier và đặt ở tier 4 vẫn có vẻ thích hơn :b -> 6 tier nhé

#### **Nguồn trích dẫn**

1. Is RAG Still Worth It in the Age of Million-Token Context Windows? \- AlphaCorp AI, truy cập vào tháng 5 10, 2026, [https://www.alphacorp.ai/blog/is-rag-still-worth-it-in-the-age-of-million-token-context-windows](https://www.alphacorp.ai/blog/is-rag-still-worth-it-in-the-age-of-million-token-context-windows)  
2. We tested RAG vs. Long-Context Agents in live conversations. Offline benchmarks are lying to us : r/LocalLLaMA \- Reddit, truy cập vào tháng 5 10, 2026, [https://www.reddit.com/r/LocalLLaMA/comments/1r4g7jh/we\_tested\_rag\_vs\_longcontext\_agents\_in\_live/](https://www.reddit.com/r/LocalLLaMA/comments/1r4g7jh/we_tested_rag_vs_longcontext_agents_in_live/)  
3. GPT-5.4 mini Model | OpenAI API, truy cập vào tháng 5 10, 2026, [https://developers.openai.com/api/docs/models/gpt-5.4-mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini)  
4. Gemini 3.1 Flash-Lite Preview \- Google AI for Developers, truy cập vào tháng 5 10, 2026, [https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite-preview](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite-preview)  
5. OpenAI API Pricing 2026: True Cost Guide for Every Model | MetaCTO, truy cập vào tháng 5 10, 2026, [https://www.metacto.com/blogs/unlocking-the-true-cost-of-openai-api-a-deep-dive-into-usage-integration-and-maintenance](https://www.metacto.com/blogs/unlocking-the-true-cost-of-openai-api-a-deep-dive-into-usage-integration-and-maintenance)  
6. Pricing \- Claude API Docs, truy cập vào tháng 5 10, 2026, [https://platform.claude.com/docs/en/about-claude/pricing](https://platform.claude.com/docs/en/about-claude/pricing)  
7. RAG vs Long-Context LLMs: A Comprehensive Comparison | by Rost Glukhov | Medium, truy cập vào tháng 5 10, 2026, [https://medium.com/@rosgluk/rag-vs-long-context-llms-a-comprehensive-comparison-9b30594c445e](https://medium.com/@rosgluk/rag-vs-long-context-llms-a-comprehensive-comparison-9b30594c445e)  
8. RAG vs long context model LLM \- Elasticsearch Labs, truy cập vào tháng 5 10, 2026, [https://www.elastic.co/search-labs/blog/rag-vs-long-context-model-llm](https://www.elastic.co/search-labs/blog/rag-vs-long-context-model-llm)  
9. chunking\_strategy.md  
10. AI Context Window Comparison 2026: 1M to 10M Tokens \- Digital Applied, truy cập vào tháng 5 10, 2026, [https://www.digitalapplied.com/blog/ai-context-window-comparison-2026-1m-to-10m-tokens](https://www.digitalapplied.com/blog/ai-context-window-comparison-2026-1m-to-10m-tokens)  
11. Should You Be Using RAG in 2026? \- DEV Community, truy cập vào tháng 5 10, 2026, [https://dev.to/riddhesh/should-you-be-using-rag-in-2026-28ef](https://dev.to/riddhesh/should-you-be-using-rag-in-2026-28ef)  
12. RAG vs. long-context LLMs: A side-by-side comparison \- Meilisearch, truy cập vào tháng 5 10, 2026, [https://www.meilisearch.com/blog/rag-vs-long-context-llms](https://www.meilisearch.com/blog/rag-vs-long-context-llms)  
13. Google's New Gemini 3.1 Model Creates a Stir at Night: Processes 363 Tokens per Second with 1/4 Price Advantage over Claude \- 36氪, truy cập vào tháng 5 10, 2026, [https://eu.36kr.com/en/p/3707817046045065](https://eu.36kr.com/en/p/3707817046045065)  
14. GPT-5.4 Mini vs Claude Haiku 4.5: Which Is the Better Sub-Agent Model? | MindStudio, truy cập vào tháng 5 10, 2026, [https://www.mindstudio.ai/blog/gpt-54-mini-vs-claude-haiku-sub-agent-comparison](https://www.mindstudio.ai/blog/gpt-54-mini-vs-claude-haiku-sub-agent-comparison)  
15. Claude API Pricing 2026: Full Anthropic Cost Breakdown \- MetaCTO, truy cập vào tháng 5 10, 2026, [https://www.metacto.com/blogs/anthropic-api-pricing-a-full-breakdown-of-costs-and-integration](https://www.metacto.com/blogs/anthropic-api-pricing-a-full-breakdown-of-costs-and-integration)  
16. Introducing Claude Haiku 4.5 \- Anthropic, truy cập vào tháng 5 10, 2026, [https://www.anthropic.com/news/claude-haiku-4-5](https://www.anthropic.com/news/claude-haiku-4-5)  
17. Gemini 3.1 Pro | Generative AI on Vertex AI \- Google Cloud Documentation, truy cập vào tháng 5 10, 2026, [https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-1-pro](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/3-1-pro)  
18. Gemini 3.1 Pro Preview \- Intelligence, Performance & Price Analysis, truy cập vào tháng 5 10, 2026, [https://artificialanalysis.ai/models/gemini-3-1-pro-preview](https://artificialanalysis.ai/models/gemini-3-1-pro-preview)  
19. GPT-5.4 Model | OpenAI API, truy cập vào tháng 5 10, 2026, [https://developers.openai.com/api/docs/models/gpt-5.4](https://developers.openai.com/api/docs/models/gpt-5.4)  
20. API Pricing \- OpenAI, truy cập vào tháng 5 10, 2026, [https://openai.com/api/pricing/](https://openai.com/api/pricing/)  
21. GPT-5.5 Model | OpenAI API, truy cập vào tháng 5 10, 2026, [https://developers.openai.com/api/docs/models/gpt-5.5](https://developers.openai.com/api/docs/models/gpt-5.5)  
22. Gemini 3 Developer Guide \- Interactions API, truy cập vào tháng 5 10, 2026, [https://ai.google.dev/gemini-api/docs/interactions/gemini-3](https://ai.google.dev/gemini-api/docs/interactions/gemini-3)  
23. Gemini Developer API pricing, truy cập vào tháng 5 10, 2026, [https://ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing)  
24. State-of-the-art text embedding via the Gemini API \- Google Developers Blog, truy cập vào tháng 5 10, 2026, [https://developers.googleblog.com/en/gemini-embedding-text-model-now-available-gemini-api/](https://developers.googleblog.com/en/gemini-embedding-text-model-now-available-gemini-api/)  
25. Gemini Embedding now generally available in the Gemini API \- Google Developers Blog, truy cập vào tháng 5 10, 2026, [https://developers.googleblog.com/gemini-embedding-available-gemini-api/](https://developers.googleblog.com/gemini-embedding-available-gemini-api/)  
26. Text Embedding Models Compared 2026: Pricing, Dimensions, and MTEB Scores, truy cập vào tháng 5 10, 2026, [https://pecollective.com/tools/text-embedding-models-compared/](https://pecollective.com/tools/text-embedding-models-compared/)  
27. Best Embedding Models 2026: MTEB Benchmarks \+ Pricing \- PE Collective, truy cập vào tháng 5 10, 2026, [https://pecollective.com/tools/best-embedding-models/](https://pecollective.com/tools/best-embedding-models/)  
28. Best Embedding Models for RAG (2026): Ranked by MTEB Score, Cost, and Self-Hosting, truy cập vào tháng 5 10, 2026, [https://blog.premai.io/best-embedding-models-for-rag-2026-ranked-by-mteb-score-cost-and-self-hosting/](https://blog.premai.io/best-embedding-models-for-rag-2026-ranked-by-mteb-score-cost-and-self-hosting/)  
29. Matryoshka embeddings: How to make vector search 5x faster | by Stéphane Derosiaux | Data Science Collective | Medium, truy cập vào tháng 5 10, 2026, [https://medium.com/data-science-collective/matryoshka-embeddings-how-to-make-vector-search-5x-faster-f9fdc54d5ffd](https://medium.com/data-science-collective/matryoshka-embeddings-how-to-make-vector-search-5x-faster-f9fdc54d5ffd)  
30. Load vector embeddings up to 67x faster with pgvector and Amazon Aurora \- AWS, truy cập vào tháng 5 10, 2026, [https://aws.amazon.com/blogs/database/load-vector-embeddings-up-to-67x-faster-with-pgvector-and-amazon-aurora/](https://aws.amazon.com/blogs/database/load-vector-embeddings-up-to-67x-faster-with-pgvector-and-amazon-aurora/)  
31. Scaling Vector Search: Comparing Quantization and Matryoshka Embeddings for 80% Cost Reduction | Towards Data Science, truy cập vào tháng 5 10, 2026, [https://towardsdatascience.com/649627-2/](https://towardsdatascience.com/649627-2/)  
32. A Guide to Embeddings and pgvector \- DEV Community, truy cập vào tháng 5 10, 2026, [https://dev.to/googleai/a-guide-to-embeddings-and-pgvector-df0](https://dev.to/googleai/a-guide-to-embeddings-and-pgvector-df0)  
33. Reranker API \- Jina AI, truy cập vào tháng 5 10, 2026, [https://jina.ai/reranker/](https://jina.ai/reranker/)  
34. jinaai/jina-reranker-v3 \- Hugging Face, truy cập vào tháng 5 10, 2026, [https://huggingface.co/jinaai/jina-reranker-v3](https://huggingface.co/jinaai/jina-reranker-v3)  
35. Pricing \- Introduction \- Voyage AI, truy cập vào tháng 5 10, 2026, [https://docs.voyageai.com/docs/pricing](https://docs.voyageai.com/docs/pricing)  
36. Rerankers \- Voyage AI by MongoDB, truy cập vào tháng 5 10, 2026, [https://www.mongodb.com/docs/voyageai/models/rerankers/](https://www.mongodb.com/docs/voyageai/models/rerankers/)  
37. Cohere API Pricing 2026: Command R+, Rerank & Embed Costs | MetaCTO, truy cập vào tháng 5 10, 2026, [https://www.metacto.com/blogs/cohere-pricing-explained-a-deep-dive-into-integration-development-costs](https://www.metacto.com/blogs/cohere-pricing-explained-a-deep-dive-into-integration-development-costs)  
38. Open-source alternatives to Cohere Rerank in 2026 \- ZeroEntropy, truy cập vào tháng 5 10, 2026, [https://zeroentropy.dev/articles/open-source-alternatives-to-cohere-rerank/](https://zeroentropy.dev/articles/open-source-alternatives-to-cohere-rerank/)  
39. Top 7 Rerankers for RAG \- Analytics Vidhya, truy cập vào tháng 5 10, 2026, [https://www.analyticsvidhya.com/blog/2025/06/top-rerankers-for-rag/](https://www.analyticsvidhya.com/blog/2025/06/top-rerankers-for-rag/)  
40. Models | Gemini API \- Google AI for Developers, truy cập vào tháng 5 10, 2026, [https://ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models)  
41. Retiring GPT-4o and other ChatGPT models \- OpenAI Help Center, truy cập vào tháng 5 10, 2026, [https://help.openai.com/en/articles/20001051-retiring-gpt-4o-and-other-chatgpt-models](https://help.openai.com/en/articles/20001051-retiring-gpt-4o-and-other-chatgpt-models)  
42. Deprecations | OpenAI API, truy cập vào tháng 5 10, 2026, [https://developers.openai.com/api/docs/deprecations](https://developers.openai.com/api/docs/deprecations)  
43. Model deprecations (MaaS) | Generative AI on Vertex AI \- Google Cloud Documentation, truy cập vào tháng 5 10, 2026, [https://docs.cloud.google.com/vertex-ai/generative-ai/docs/deprecations/partner-models](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/deprecations/partner-models)
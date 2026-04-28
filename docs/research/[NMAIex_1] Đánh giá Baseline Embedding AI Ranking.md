# **Báo cáo Nghiên cứu Kỹ thuật: Thiết kế và Đánh giá Baseline Retrieval/Ranking cho Hệ thống AI Tuyển dụng**

## **1\. Bối cảnh Hệ thống và Phân tích Cấu trúc AI Core (FANG)**

Sự dịch chuyển kiến trúc của hệ thống tuyển dụng từ mô hình phân tán sang kiến trúc tập trung, trong đó miCareer-mini trở thành một thin client và giao phó toàn bộ trọng trách xử lý dữ liệu ngôn ngữ tự nhiên (NLP), nhúng vector (embedding) và tìm kiếm (vector search) cho hệ thống AI Core trung tâm (FANG), đòi hỏi một chiến lược đánh giá và thiết kế lại cơ chế xếp hạng (ranking) vô cùng nghiêm ngặt.1 Hệ thống FANG v2 hiện tại đã xây dựng được một nền tảng hạ tầng khá hoàn thiện, bao gồm quy trình tiếp nhận dữ liệu (ingestion), bộ phân tích cú pháp (parser) 5 tầng phức tạp, chiến lược phân đoạn văn bản nhận thức cấu trúc (structure-aware chunking), và hệ thống lưu trữ vector mạnh mẽ trên PostgreSQL.1

### **1.1. Hiện trạng Hạ tầng Dữ liệu và Vector Search**

Việc đánh giá bất kỳ đường cơ sở (baseline) nào cũng phải bắt đầu từ việc hiểu rõ giới hạn và năng lực của hạ tầng lưu trữ và truy xuất hiện có. Hệ thống FANG đang lưu trữ các biểu diễn vector trong bảng AIDOCUMENTCHUNK của cơ sở dữ liệu PostgreSQL thông qua tiện ích mở rộng pgvector.1

Đặc tả kỹ thuật hiện tại cho thấy việc nhúng dữ liệu được thực hiện bởi mô hình text-embedding-3-small của OpenAI, tạo ra các vector có số chiều là 1024\.1 Một điểm đáng chú ý trong thiết kế là hệ thống đang sử dụng kiểu dữ liệu halfvec(1024) – tức là số thực dấu phẩy động bán độ chính xác (16-bit) – làm cấu hình mặc định cho các môi trường phát triển và kiểm thử nhằm tối ưu hóa dung lượng RAM và kích thước chỉ mục.1 Chỉ mục (index) được xây dựng dựa trên thuật toán HNSW (Hierarchical Navigable Small World) với các tham số siêu liên kết m = 16 và ef_construction = 64, sử dụng lớp toán tử halfvec\_cosine\_ops để thực thi phép đo khoảng cách độ tương đồng Cosine (Cosine Similarity).1

Bên cạnh đó, dữ liệu nghiệp vụ lõi (Web Core) cư trú tại micareer\_lite\_db chứa đựng mạng lưới dữ liệu quan hệ phong phú. Hồ sơ ứng viên (Candidate Profile) được cấu trúc hóa qua các bảng user, CANDIDATE, và CANDIDATESKILL, lưu trữ các thông tin từ văn bản tự do (bio) đến dữ liệu định lượng (expyears, dob) và dữ liệu phân loại (prov, stat).1 Tương tự, tin tuyển dụng (Job Posting) được phân giải qua các bảng JOBPOSTING, JOBREQUIREMENT, và COMPANY, mang theo các siêu dữ liệu then chốt như khoảng lương (minSalary, maxSalary), địa điểm làm việc (workLoc), và hình thức làm việc (workMode).1 Sự tồn tại song song của dữ liệu phi cấu trúc (được vector hóa) và dữ liệu có cấu trúc (truy vấn bằng SQL) định hình trực tiếp con đường xây dựng hệ thống đối khớp (matching) hiệu quả.

### **1.2. Mục tiêu Khảo nghiệm**

Mặc dù FANG v2 hỗ trợ mạnh mẽ các luồng RAG (Retrieval-Augmented Generation) cho việc truy vấn lịch sử ứng viên qua endpoint POST /v2/chat/query, tài liệu hợp đồng API (API contract) hiện hành cho thấy FANG chưa cung cấp sẵn logic đối khớp (ranking) hai chiều giữa danh sách công việc và danh sách ứng viên.1 Các thao tác này hiện vẫn do client tự xử lý thông qua truy vấn cơ sở dữ liệu truyền thống.1 Do đó, trọng tâm của nghiên cứu này là thiết lập một hệ thống đánh giá đường cơ sở (baseline evaluation protocol) nghiêm túc, khoa học để xác định xem liệu việc kết hợp embedding hiện có với các bộ lọc heuristic có đủ khả năng giải quyết bài toán ranking hai chiều hay không, trước khi đề xuất bất kỳ sự thay đổi kiến trúc tốn kém nào.

## **2\. Đặc tả Bài toán Đối khớp Tuyển dụng và Tính Bất đối xứng**

Lĩnh vực tuyển dụng trực tuyến hoạt động dưới một sự mất cân bằng thông tin nghiêm trọng: người tìm việc phải duyệt qua hàng vạn tin tuyển dụng thay đổi liên tục, trong khi nhà tuyển dụng bị quá tải bởi hồ sơ ứng tuyển ồ ạt nhưng có độ phù hợp thấp.2 Việc coi đối khớp tuyển dụng đơn thuần là một bài toán tính điểm tương đồng văn bản (text similarity) sẽ dẫn đến những thất bại trong triển khai thực tế. Sự khác biệt cốt lõi nằm ở tính bất đối xứng giữa hai luồng tìm kiếm.

### **2.1. Tính Bất đối xứng: Candidate-to-Job và Job-to-Candidate**

Hệ thống bắt buộc phải tách biệt baseline cho luồng ứng viên tìm việc (Candidate -> Job) và luồng công việc tìm ứng viên (Job -> Candidate), bởi vì bản chất của quá trình ra quyết định, bộ lọc và loại hình suy luận (reasoning types) ở hai phía là hoàn toàn khác nhau.3

| Đặc điểm | Job → Candidate (Nhà tuyển dụng tìm Ứng viên) | Candidate → Job (Ứng viên tìm Công việc) |
| :---- | :---- | :---- |
| **Bản chất Suy luận** | **Parallel Reasoning (Suy luận Song song):** Hệ thống phải kiểm tra đồng thời nhiều ràng buộc cứng khắt khe.5 | **Serial/Multi-hop Reasoning (Suy luận Chuỗi):** Hệ thống cần suy luận về kỹ năng chuyển đổi (transferable skills) và tiềm năng phát triển.5 |
| **Độ nhạy cảm Ràng buộc** | Rất cao. Một ứng viên có bộ kỹ năng hoàn hảo nhưng thiếu 2 năm kinh nghiệm bắt buộc sẽ bị loại ngay lập tức (Hard Filter). | Thấp hơn. Ứng viên có xu hướng nộp hồ sơ vào các vị trí yêu cầu cao hơn hoặc ở địa điểm lân cận nếu mức lương đủ hấp dẫn (Soft Preference). |
| **Mục tiêu Tối ưu** | **Precision (Độ chuẩn xác):** Quỹ thời gian của nhà tuyển dụng rất giới hạn (chỉ vài giây mỗi CV) 7, do đó kết quả hiển thị trên cùng (Top-K) phải hoàn toàn khớp với JD. | **Recall & Diversity (Độ phủ và Đa dạng):** Đảm bảo ứng viên không bị bỏ lỡ các cơ hội nghề nghiệp mà họ có khả năng đáp ứng thông qua đào tạo ngắn hạn. |
| **Yếu tố Veto (Quyền phủ quyết)** | Trạng thái tài khoản (stat \= INACTIVE), thiếu kỹ năng lõi (skillId), khoảng cách địa lý không phù hợp. | Tin tuyển dụng đã hết hạn (expAt \< NOW), mức lương (maxSalary) thấp hơn kỳ vọng tối thiểu. |

Việc sử dụng chung một công thức Cosine(Vector\_CV, Vector\_JD) cho cả hai luồng sẽ tạo ra hiện tượng sai số hệ thống. Ví dụ, một nhà tuyển dụng tìm "Senior Java Developer với 5 năm kinh nghiệm", vector embedding có thể trả về một "Junior Java Developer với 1 năm kinh nghiệm" ở thứ hạng cao vì nội dung công nghệ (Java, Spring Boot, Microservices) trùng khớp mạnh mẽ.8 Trong khi đó, với luồng Candidate ![][image3] Job, việc gợi ý vị trí Senior cho một Junior lại có thể là một chiến lược khuyến khích ứng viên vươn lên, tùy thuộc vào ngưỡng điểm đánh giá.

### **2.2. Nhãn Dữ liệu và Nguy cơ Rò rỉ (Data Leakage)**

Một thách thức lớn trong việc đánh giá các hệ thống Applicant Tracking System (ATS) là sự thiếu hụt các nhãn đánh giá độ phù hợp thực tế (ground truth labels).9 Hệ thống truyền thống thường sử dụng dữ liệu tương tác như lượt nhấp (click), lượt xem (view), hoặc việc ứng viên chủ động nộp hồ sơ để làm nhãn "Tích cực" (Positive).

Tuy nhiên, việc sử dụng các tương tác bề mặt này dẫn đến **rò rỉ dữ liệu (Data Leakage)** và **thiên vị (Bias)**. Một ứng viên nộp hồ sơ không có nghĩa là họ phù hợp với công việc đó.10 Ngược lại, nếu chỉ dựa vào quyết định mời phỏng vấn của nhà tuyển dụng để làm nhãn, hệ thống AI sẽ vô tình học và khuếch đại những thiên kiến ẩn (unconscious bias) của con người về giới tính, độ tuổi, hoặc trường đại học.4

Giao thức đánh giá cần phải đo lường "Độ phù hợp Năng lực" (Competency Alignment) thực chất thay vì đo lường khả năng trúng tuyển bị nhiễu bởi yếu tố ngoại cảnh.5 Các nhãn sử dụng trong quá trình benchmark phải được định nghĩa rõ ràng: Nhãn dương (Positive) chỉ được cấp khi có đủ bằng chứng trong CV hỗ trợ các yêu cầu trong JD.5

## **3\. Thiết kế Baseline Retrieval và Ranking**

Để có một sự so sánh công bằng và khoa học, baseline phải được xây dựng từ mức độ cơ bản nhất đến các phương pháp tiên tiến, đảm bảo phù hợp với khối lượng dữ liệu thực tế của ATS. Quá trình này không thể chỉ dựa vào một lệnh tìm kiếm ORDER BY embedding \<=\> query\_embedding 1, bởi giới hạn lý thuyết của vector mật độ (Dense Vector) đã được chứng minh: một mô hình vector đơn lẻ không thể phân hoạch không gian hình học để thỏa mãn tính phức tạp tổ hợp của các truy vấn.13

### **3.1. Các Phương án Baseline Đề xuất và Lựa chọn**

Dưới đây là các phương án kiến trúc Baseline được phân tích, xếp hạng theo mức độ phù hợp với hệ thống FANG hiện tại:

1. **Hạng 3 (Kém phù hợp nhất): Cosine Similarity Thuần Túy**  
   * *Kiến trúc:* Chỉ sử dụng toán tử halfvec\_cosine\_ops trên bảng AIDOCUMENTCHUNK.1  
   * *Nhược điểm:* Bỏ qua hoàn toàn các siêu dữ liệu cấu trúc như năm kinh nghiệm, mức lương, và kỹ năng bắt buộc. Thường xuyên trả về các kết quả có độ tương đồng ngữ nghĩa cao nhưng sai lệch nghiêm trọng về cấp độ chuyên môn (Senior vs Intern).  
2. **Hạng 2 (Đạt yêu cầu tối thiểu): Vector Retrieval \+ Heuristic Filter (Hard Filtering)**  
   * *Kiến trúc:* Sử dụng SQL để lọc các ràng buộc cứng trước (ví dụ: WHERE expyears \>= 3 AND workLoc \= 'Hanoi'), sau đó tính Cosine Similarity trên các hồ sơ còn lại.  
   * *Ưu điểm:* Giải quyết ngay lập tức các lỗi sai lệch cấp độ và địa lý. Dễ dàng triển khai bằng SQL kết hợp pgvector.  
   * *Nhược điểm:* Quá cứng nhắc. Việc thiếu một từ khóa chính xác có thể loại bỏ hoàn toàn một ứng viên xuất sắc sở hữu từ khóa đồng nghĩa nhưng chưa được chuẩn hóa.14  
3. **Hạng 1 (Tối ưu nhất cho FANG): Hybrid Search \+ Linear Scoring (Xếp hạng Tuyến tính Lai)**  
   * *Kiến trúc:* Kết hợp điểm số truy xuất ngữ nghĩa (Dense Vector Search) với điểm số truy xuất từ khóa/siêu dữ liệu (Metadata/Sparse Matching), và hợp nhất chúng bằng một hàm tuyến tính có trọng số.15  
   * *Lý do lựa chọn:* Cơ sở dữ liệu micareer\_lite\_db đã có sẵn các bảng quan hệ CANDIDATESKILL và JOBREQUIREMENT.1 Việc tận dụng dữ liệu cấu trúc này kết hợp với khả năng hiểu ngữ cảnh của vector embedding tạo ra một hệ thống đối khớp đa chiều. Linear Scoring cho phép hiệu chỉnh trọng số (calibration) tùy theo tính chất của từng vị trí tuyển dụng.

### **3.2. RRF so với Kết hợp Tuyến tính (Linear Combination)**

Khi hợp nhất hai tập kết quả từ Vector Search và Metadata Search, ngành công nghiệp thường tranh luận giữa Reciprocal Rank Fusion (RRF) và Linear Combination.17

* **Reciprocal Rank Fusion (RRF):** Phương pháp này loại bỏ điểm số thô và chỉ dựa vào thứ hạng (rank). Công thức $$RRF(d) = \sum \frac{1}{k + rank(d)}$$ tạo ra sự ổn định khi kết hợp các hệ thống có thang điểm khác nhau.19 RRF rất dễ triển khai "out-of-the-box".  
* **Linear Combination (Kết hợp Tuyến tính):** Yêu cầu chuẩn hóa điểm số (ví dụ: Min-Max scaling) trước khi nhân với trọng số ![][image5] (alpha) và ![][image6] (beta). $$Score = \alpha \cdot Norm(V_{cosine}) + \beta \cdot Norm(S_{heuristic})$$. Phương pháp này tôn trọng độ lớn của điểm số (magnitude of scores).

**Quyết định Kỹ thuật:** Đối với bài toán tuyển dụng, **Linear Combination là phương án vượt trội hơn**.16 RRF có một điểm yếu chí mạng trong tuyển dụng: nó làm mất đi sự trừng phạt về mặt điểm số đối với các hồ sơ thiếu hụt kỹ năng trầm trọng. Nếu một JD yêu cầu 5 kỹ năng, và ứng viên chỉ có 1 kỹ năng, điểm số heuristic sẽ rất thấp, nhưng RRF có thể vẫn đẩy ứng viên này lên cao nếu vector search vô tình xếp hạng cao do văn phong tương đồng. Linear Scoring cho phép gán một trọng số phủ quyết lớn vào bộ lọc kỹ năng cứng.

### **3.3. Xử lý và Chuẩn hóa Văn bản Trước Nhúng (Pre-embedding Text Normalization)**

Chất lượng của vector embedding phụ thuộc trực tiếp vào văn bản đầu vào. Dữ liệu CV và JD thường chứa rất nhiều nhiễu, mã hóa sai, và định dạng phi cấu trúc.23 Do FANG v2 sử dụng bộ phân tích cú pháp (Parser) 5 tầng mạnh mẽ với các quy tắc Quality Gate xác định 1, hệ thống có lợi thế tuyệt đối trong việc cấu trúc hóa trước khi nhúng.

Baseline cần xử lý các trường dữ liệu theo quy trình sau:

1. **Làm sạch Tiêu chuẩn:** Loại bỏ các thẻ HTML, ký tự phi ASCII, stopwords không mang ý nghĩa, và chuyển đổi chữ thường (lowercase) toàn bộ hệ thống để đảm bảo tính nhất quán.23  
2. **Chuẩn hóa Chức danh (Job Title) và Lĩnh vực (Domain):** Chức danh công việc tại Việt Nam rất đa dạng và có sự pha trộn giữa tiếng Anh và tiếng Việt (VD: "Lập trình viên Frontend", "Frontend Developer", "Nhân viên phát triển giao diện Web"). Cần xây dựng một từ điển đồng nghĩa (Taxonomy/Ontology) để ánh xạ các chức danh này về một ID chung hoặc chuỗi chuẩn trước khi đưa vào embedding.26  
3. **Xử lý Kỹ năng (Skill):** Trích xuất kỹ năng thành một danh sách độc lập và tính toán độ tương đồng Jaccard (Jaccard Similarity) song song với việc lưu trữ nội dung mô tả kỹ năng trong vector.31 Điều này tránh việc vector bị pha loãng bởi các từ khóa không trọng tâm.  
4. **Xử lý Kinh nghiệm (Experience) và Thâm niên (Seniority):** Thông tin định lượng như số năm kinh nghiệm (expyears) 1 không nên đưa vào khối văn bản nhúng. Khả năng hiểu các con số của các mô hình embedding rất kém. Số năm kinh nghiệm cần được chuyển thành một đặc trưng tính toán chênh lệch (Delta Feature): $$\Delta_{exp} = Candidate_{exp} - Job_{min\_exp}$$.  
5. **Xử lý Địa lý (Location):** Tương tự như kỹ năng, địa điểm (prov, ward) cần được chuẩn hóa qua danh mục hành chính 1 để làm bộ lọc hoặc sử dụng hàm suy hao khoảng cách (distance decay) thay vì phân tích ngữ nghĩa.  
6. **Chiến lược Phân đoạn (Chunking):** Việc bảo toàn ngữ cảnh phân đoạn (Section-Pinning) đang có sẵn trong FANG là một phương pháp cực kỳ hiệu quả.1 Cần đảm bảo rằng các đoạn văn mô tả kinh nghiệm (Experience) không bị trộn lẫn với mục tiêu nghề nghiệp (Objective) trong quá trình tính toán khoảng cách vector.

## **4\. Đánh giá Mô hình text-embedding-3-small**

Với việc kho dữ liệu PostgreSQL đã được định dạng cho cột embedding halfvec(1024) chạy thuật toán HNSW cosine 1, việc ra quyết định giữ hay thay đổi mô hình text-embedding-3-small cần có luận cứ kỹ thuật sắc bén.

### **4.1. Năng lực Thực tế và Điều kiện Giữ nguyên**

Theo các bài kiểm tra benchmark độc lập, text-embedding-3-small là một bước nhảy vọt so với thế hệ trước (ada-002). Nó đạt điểm trung bình 62.3% trên bộ MTEB (đối với tiếng Anh) và 44.0% trên bộ MIRACL (truy xuất đa ngôn ngữ), trong khi chi phí cực kỳ rẻ ở mức 0.02 USD/1 triệu token.33

**Điều kiện để giữ nguyên:**

Mô hình này hoàn toàn đủ tốt để đóng vai trò làm **Retriever (Máy truy xuất) ở Giai đoạn 1** của một hệ thống tuyển dụng nếu thỏa mãn các điều kiện:

* Mục tiêu hiện tại là tạo ra một danh sách ứng viên thu gọn (Shortlisting) ưu tiên độ phủ (Recall) cao.  
* Hệ thống không yêu cầu mô hình nhúng phải giải quyết được tính tổ hợp phức tạp (như khả năng tự động hiểu rằng 5 năm kinh nghiệm phải đi kèm với kỹ năng quản lý).13  
* Cơ sở hạ tầng hiện tại (việc sử dụng halfvec(1024)) 1 đang đáp ứng được thời gian trễ (latency) \< 100ms cho các truy vấn RAG.38

Sự kết hợp giữa HNSW và halfvec cung cấp tỷ lệ đánh đổi (trade-off) hoàn hảo giữa độ chính xác và hiệu năng phần cứng trong bài toán Semantic Retrieval (Truy xuất Ngữ nghĩa). Các thử nghiệm thực tế chứng minh rằng việc hạ độ phân giải xuống 16-bit gần như không tác động tiêu cực đến chỉ số NDCG hay Recall trong các bài toán xếp hạng văn bản.

### **4.2. Dấu hiệu Nhận biết "Bottleneck" Thực sự của Embedding**

Mặc dù mạnh mẽ, các mô hình nhúng mục đích chung (General-purpose embeddings) được huấn luyện trên dữ liệu web thường bộc lộ những khiếm khuyết chết người khi áp dụng vào ngôn ngữ chuyên ngành (Domain-specific jargon) của HR. Những dấu hiệu chứng minh embedding hiện tại đã trở thành điểm nghẽn (bottleneck) bao gồm:

1. **Ảo giác Ngữ nghĩa Đặc thù (Semantic Hallucination & Domain Mismatch):** Như "Bài toán Java Developer" đã minh họa.8 Mô hình sẽ đánh giá độ tương đồng Cosine rất cao (ví dụ: \> 0.85) giữa một bản JD tìm kiếm "Java Developer" (ngôn ngữ biên dịch, backend) và một CV của "JavaScript Developer" (ngôn ngữ thông dịch, frontend) chỉ vì hai từ khóa này chia sẻ gốc từ và thường xuất hiện cùng nhau trong không gian vector của các bài báo công nghệ.  
2. **Sự Sụp đổ Không gian Nhúng (Embedding Collapse):** Xảy ra khi các vector có xu hướng quy tụ về một không gian chiều thấp do ảnh hưởng của các văn bản rập khuôn.40 Hàng ngàn CV sử dụng chung các cụm từ sáo rỗng (buzzwords) như "năng động", "chịu được áp lực", "kỹ năng làm việc nhóm" sẽ khiến vector của chúng gần như giống hệt nhau, làm lu mờ các kỹ năng công nghệ cốt lõi, khiến mô hình mất đi tính phân biệt (discriminative power).41  
3. **Thất bại với Truy vấn Tổ hợp (Combinatorial Query Failures):** Khi nhà tuyển dụng tìm kiếm một yêu cầu đa điều kiện phức tạp, vector 1024 chiều không thể biểu diễn một cách hình học tất cả các ràng buộc đó cùng một lúc. Mọi sự nỗ lực ép mô hình vector hiểu các quy tắc cứng sẽ dẫn đến kết quả trả về là sự "trung bình hóa" nội dung (average context) thay vì chính xác thông tin.13

*Quyết định:* **Nên đánh giá embedding theo Semantic Retrieval**, chứ không phải theo Matching Classification hay Ranking cuối cùng.39 Vai trò của Embedding là mang lại Recall cao. Việc tinh chỉnh (fine-tuning) các yếu tố xếp hạng nên dành cho hàm Linear Scoring ở Giai đoạn 2\.

## **5\. Giao thức Đánh giá, So sánh và Đo lường (Evaluation Protocol)**

Trong bối cảnh hệ thống FANG v2, nguyên tắc cao nhất là ưu tiên các đề xuất có thể kiểm chứng bằng **Offline Evaluation (Đánh giá ngoại tuyến)** trước khi đưa ra A/B testing trên môi trường thật. Giao thức đánh giá đề xuất là mô hình PJB (Person-Job Benchmark) nhằm chẩn đoán năng lực hệ thống.5

### **5.1. Định mức và Các Metric Chính**

Việc đo lường hệ thống Candidate Ranking không thể chỉ dựa vào một chỉ số đơn lẻ. Đề xuất sử dụng hệ thống Metric phân tầng 38:

* **Đo lường năng lực của Baseline Retrieval (Giai đoạn 1):** Sử dụng **Recall@K** (ví dụ: Recall@50 hoặc Recall@100).  
  * *Ý nghĩa:* Tỷ lệ phần trăm các ứng viên/công việc phù hợp (Relevant items) xuất hiện trong top K kết quả trả về. Nếu Recall thấp, điều đó có nghĩa là mô hình text-embedding-3-small đã thất bại trong việc nắm bắt không gian ngữ nghĩa cơ bản, và mọi nỗ lực Reranking ở phía sau sẽ vô nghĩa vì các hồ sơ tốt đã bị bỏ lọt.44  
* **Đo lường năng lực của Xếp hạng Tổng thể (Giai đoạn 2):** Sử dụng **NDCG@10** (Normalized Discounted Cumulative Gain tại Top 10).  
  * *Ý nghĩa:* Khác với Precision hay Recall, NDCG có tính nhận thức về thứ hạng (rank-aware) và hỗ trợ nhãn phân cấp (graded relevance) thay vì chỉ nhị phân (có/không).43 Một hồ sơ ứng viên xuất sắc được xếp ở vị trí số 1 sẽ nhận được điểm thưởng (Gain) cao hơn nhiều so với việc xuất hiện ở vị trí số 10\. Đây là metric phù hợp nhất phản ánh trải nghiệm của HR.  
* **Đo lường Phản hồi Đầu tiên:** Sử dụng **MRR** (Mean Reciprocal Rank) để đánh giá tốc độ hệ thống cung cấp kết quả đúng đầu tiên.43

### **5.2. Thiết lập Mốc Đánh giá (Boundaries)**

Để đánh giá công bằng, hệ thống cần thiết lập các cột mốc:

* **Lower Bound (Mốc cơ sở tối thiểu):**  
  Sử dụng kết quả trực tiếp từ phép đo **Cosine Similarity thuần túy** bằng text-embedding-3-small trên nội dung văn bản gốc, không sử dụng bộ lọc SQL, không chuẩn hóa kỹ năng. Đây là mức điểm mà hệ thống FANG bắt buộc phải vượt qua một khoảng cách xa để chứng minh sự tồn tại của hệ thống lai (Hybrid) là hợp lý.  
* **Sanity Upper Reference (Mốc trần tham chiếu tham số hóa):** Việc tạo nhãn thủ công (Human Annotation) trên dữ liệu ATS quy mô lớn là bất khả thi. Để có Ground Truth, FANG cần sử dụng phương pháp **Outcome-Grounded Benchmark** kết hợp **LLM-as-a-Judge**.5  
  * *Nguồn dữ liệu lịch sử:* Các hồ sơ ứng viên trong bảng JOBAPPLICATION có sự kiện tiến sâu vào phỏng vấn (INTERVIEWFEEDBACK) hoặc nhận thư mời làm việc (OFFER) 1 sẽ được tự động gán nhãn Tương quan cao (Relevance \= 2).  
  * *Nguồn dữ liệu đánh giá bằng AI:* Sử dụng mô hình thuộc nhóm Pro Tier (Gemini Pro hoặc GPT-5.4) 1 thông qua kĩ thuật Prompt kỹ lưỡng, được cung cấp toàn bộ JD và CV để chấm điểm mức độ phù hợp từ 0-3 dựa trên rubric khắt khe. Các nhãn sinh ra bởi LLM Pro sẽ làm mốc tham chiếu "Trần" để các mô hình Retrieval nhỏ hơn (như baseline hybrid) cố gắng tiếp cận.

### **5.3. Nghiên cứu Cắt bỏ (Ablation Study)**

Để trả lời câu hỏi: *"Embedding hiện tại đóng góp bao nhiêu % vào độ chính xác?"*, một bài kiểm tra Ablation (Cắt bỏ) là bắt buộc.5

Dưới đây là ma trận Ablation Study được đề xuất vận hành trong hệ thống FANG:

| Kịch bản Test (Runs) | Dense Embedding (text-embedding-3-small) | Metadata Filtering (SQL Lọc Cứng) | Sparse/Skill Matching (Tính điểm Jaccard) | Mục tiêu Quan sát |
| :---- | :---- | :---- | :---- | :---- |
| **Run 0 (Lower Bound)** | Trọng số \= 1.0 | Không áp dụng | Trọng số \= 0.0 | Đo lường năng lực ngữ nghĩa trần trụi. Đánh giá mức độ Semantic Hallucination. |
| **Run 1 (Heuristic Only)** | Trọng số \= 0.0 | Có áp dụng | Trọng số \= 1.0 | Đánh giá năng lực của kiến trúc DB quan hệ cũ (micareer\_lite\_db). |
| **Run 2 (Hybrid Basic)** | Trọng số \= 0.5 | Không áp dụng | Trọng số \= 0.5 | Kiểm tra xem sự kết hợp ngữ nghĩa và từ khóa có cải thiện NDCG không khi bỏ qua ràng buộc cứng. |
| **Run 3 (Hybrid Full \- Đề xuất)** | Trọng số \= ![][image5] | Có áp dụng | Trọng số \= ![][image6] | Tìm ra hệ số calibration tốt nhất. Xác nhận Uplift của toàn bộ hệ thống. |

**Tiêu chí quyết định:** Nếu chênh lệch $\Delta NDCG@10$ giữa **Run 3** và **Run 1** cực kỳ thấp (ví dụ \< 2-3%), điều đó có nghĩa mô hình embedding hiện tại thực sự là Bottleneck và không mang lại khả năng nắm bắt bối cảnh nào hơn việc đếm từ khóa thông thường. Trong trường hợp này, đề xuất nâng cấp mô hình embedding hoặc huấn luyện tinh chỉnh (Fine-tuning) bằng phương pháp Contrastive Learning sẽ được kích hoạt.5

## **6\. Chiến lược Mở rộng Dữ liệu Tổng hợp (Synthetic ATS Data) và Quality Gates**

Để vận hành giao thức đánh giá ngoại tuyến trên một cách hiệu quả, hệ thống gặp phải rào cản về tính bảo mật dữ liệu và sự mất cân bằng nhóm (class imbalance) trong dữ liệu thật. Chiến lược **sinh dữ liệu tổng hợp (Synthetic Data Generation)** ở mức thực tế là chìa khóa giải quyết vấn đề này, đặc biệt để tạo ra các trường hợp "Hard Negatives" (Gần đúng nhưng sai bản chất).39

### **6.1. Phương pháp Sinh CV và JD Quy mô lớn**

Sử dụng năng lực của hệ thống FANG hiện hành (các mô hình LLM thuộc Lite/Pro Tiers) 1 để tự động hóa quá trình sinh dữ liệu:

1. **Hạt giống Dữ liệu (Seed Data):** Lấy mẫu ngẫu nhiên và ẩn danh hóa (de-identify) một tập hợp nhỏ các JD và CV thực tế từ bảng JOBPOSTING và CVPARSED.1  
2. **Sinh mẫu Tích cực (Positive Augmentation):** Dùng LLM viết lại (paraphrase) các CV sao cho chúng thay đổi về mặt từ vựng, cấu trúc trình bày, thứ tự các phần (để mô phỏng các format PDF khác nhau) nhưng vẫn giữ nguyên ý nghĩa chuyên môn (Semantic Fidelity) nhằm khớp hoàn hảo với một JD.39  
3. **Sinh mẫu Đối nghịch Khó (Hard Negative Mining/Generation):** Đây là bước quan trọng nhất để rèn luyện baseline.9 Yêu cầu LLM tạo ra các CV:  
   * Chia sẻ đến 80% từ vựng với JD (ví dụ dùng chung các từ quản lý, lập trình, kiểm thử).  
   * Nhưng thay đổi một công nghệ cốt lõi (Java thành C\#) hoặc hạ thấp số năm kinh nghiệm xuống dưới mức yêu cầu. Các hồ sơ này sẽ được gán nhãn Relevance \= 0, buộc hệ thống Linear Scoring học cách trừ điểm thích đáng.

### **6.2. Cổng Chất lượng Dữ liệu (Data Quality Gates) & Consistency Checks**

Không thể đưa dữ liệu LLM sinh ra trực tiếp vào đánh giá mà không có cơ chế kiểm duyệt. FANG cần tích hợp các quy trình Quality Gates khắt khe 1:

* **Structural Consistency Check (Kiểm tra Tính Nhất quán Cấu trúc):** Mọi CV tổng hợp phải đi qua bộ Parser 5 tầng hiện tại của FANG. Nếu Parser không thể trích xuất được rawText length hoặc các section signals hợp lệ theo rule deterministic, CV tổng hợp đó sẽ bị loại bỏ.1  
* **Temporal Consistency (Kiểm tra Nhất quán Thời gian):** Viết script Python để kiểm tra logic thời gian (Ví dụ: Năm tốt nghiệp đại học trừ đi năm sinh phải hợp lý, số năm làm việc trong CV phải tổng hòa tương đương với CANDIDATE.expyears 1).  
* **Data Leakage/Contamination Check:** Đảm bảo rằng tập dữ liệu dùng để chạy text-embedding-3-small làm tham chiếu đánh giá phải hoàn toàn cô lập với tập dữ liệu (Prompts) đưa vào LLM để sinh dữ liệu. Không dùng chính LLM đánh giá (LLM-as-a-judge) để sinh dữ liệu tổng hợp ở cùng một tham số nhiệt độ (temperature) để tránh thiên vị thuật toán (algorithmic bias).

## **7\. Khuyến nghị và Tổng kết Chiến lược**

Nghiên cứu kết luận rằng cấu trúc lưu trữ và nhúng vector hiện tại của FANG v2 là một bệ phóng vững chắc và **không nên bị thay thế trong giai đoạn này**. Các điểm nghẽn về ngữ nghĩa và tính bất đối xứng trong tìm kiếm có thể được giải quyết thông qua kỹ thuật toán học tại lớp truy xuất.

Dưới đây là bảng xếp hạng ưu tiên các quyết định kỹ thuật cần thực thi ngay, thỏa mãn điều kiện triển khai nhanh và kiểm chứng ngoại tuyến (Offline Evaluation) 5:

1. **Thiết lập Baseline Hệ thống (Ưu tiên Cao nhất):** Triển khai ngay lập tức phương pháp **Hybrid Search kết hợp Linear Scoring**. Điểm số cuối cùng sẽ là sự kết hợp có trọng số giữa  $V_{cosine}$ của halfvec(1024) 1 từ PostgreSQL và điểm Jaccard của CANDIDATESKILL / JOBREQUIREMENT 1, được lọc trước (Hard Filter) bằng SQL thông qua số năm kinh nghiệm và địa lý. Không sử dụng Reciprocal Rank Fusion (RRF) do bản chất dễ che lấp các lỗi sai kỹ năng nghiêm trọng.  
2. **Tách biệt Luồng Đối khớp (Ưu tiên Cao):** Xây dựng hai hàm Linear Scoring riêng biệt:  
   * *Candidate ![][image3] Job:* Nới lỏng các bộ lọc SQL thành điểm trừ (soft penalty) để tăng Recall và tính đa dạng.  
   * *Job ![][image3] Candidate:* Sử dụng các bộ lọc cứng khắt khe bằng SQL trước khi thực hiện Vector Search để tối đa hóa Precision.  
3. **Khởi động Giao thức PJB (Person-Job Benchmark) Nội bộ (Ưu tiên Trung bình):** Thiết lập kịch bản Ablation Study trên một tập dữ liệu 10,000 cặp CV-JD (được trộn giữa dữ liệu thật và dữ liệu tổng hợp có kiểm soát bằng Quality Gate). Sử dụng NDCG@10 và Recall@50 làm bộ đôi chỉ số định hướng.  
4. **Bảo toàn Hạ tầng text-embedding-3-small:** Giữ nguyên quy trình cấu trúc Parser 5 tầng, mô hình nhúng và bảng lưu trữ halfvec(1024). Việc chuyển đổi sang mô hình tinh chỉnh miền đặc thù (Domain-adapted LLMs) hay Cross-Encoders phức tạp chỉ được khởi động nếu và chỉ nếu bài kiểm tra Ablation cho thấy mô hình nhúng hiện tại không mang lại mức tăng trưởng $\Delta NDCG@10 > 2\%$ so với việc chỉ dùng Metadata SQL.

Hướng đi này tối đa hóa các thành phần đã có sẵn tại AI Core FANG, đảm bảo tiết kiệm chi phí tính toán API ($0.02/1M token 34), đồng thời áp đặt một khung quản trị chất lượng cực kỳ nghiêm ngặt đối với hệ thống xếp hạng tuyển dụng. Các khuyến nghị trong báo cáo này hoàn toàn khả thi để thực hiện ngay lập tức, đóng vai trò như một cột mốc cơ sở (gold standard baseline) vững chắc, làm bệ phóng cho các cụm nghiên cứu và tinh chỉnh (tuning) tiếp theo.

#### **Nguồn trích dẫn**

1. schema\_ai\_core.sql  
2. Synapse: Evolving Job-Person Fit with Explainable Two-phase Retrieval and LLM-guided Genetic Resume Optimization \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2604.02539v1](https://arxiv.org/html/2604.02539v1)  
3. Fairness of recommender systems in the recruitment domain: an analysis from technical and legal perspectives \- PMC, truy cập vào tháng 4 23, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC10587596/](https://pmc.ncbi.nlm.nih.gov/articles/PMC10587596/)  
4. Fairness in AI-Driven Recruitment: Challenges, Metrics, Methods, and Future Directions, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2405.19699v3](https://arxiv.org/html/2405.19699v3)  
5. PJB: A Reasoning-Aware Benchmark for Person-Job Retrieval \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2603.17386](https://arxiv.org/html/2603.17386)  
6. PJB: A Reasoning-Aware Benchmark for Person-Job Retrieval \- WisPaper, truy cập vào tháng 4 23, 2026, [https://www.wispaper.ai/en/blog/reasoning-aware-benchmark-person-job-retrieval-20260320/zho](https://www.wispaper.ai/en/blog/reasoning-aware-benchmark-person-job-retrieval-20260320/zho)  
7. How AI Is Replacing Traditional Hiring \-And the Tools Smart Recruiters Are Already Using in 2026 | by Klizo Solutions Pvt. Ltd. \- Medium, truy cập vào tháng 4 23, 2026, [https://medium.com/@klizosolutions/how-ai-is-replacing-traditional-hiring-and-the-tools-smart-recruiters-are-already-using-in-2026-21b36f40454b](https://medium.com/@klizosolutions/how-ai-is-replacing-traditional-hiring-and-the-tools-smart-recruiters-are-already-using-in-2026-21b36f40454b)  
8. Why generic embeddings fail for workforce decisions | Agentic HR Academy \- Gloat, truy cập vào tháng 4 23, 2026, [https://gloat.com/academy/why-generic-embeddings-fail-workforce/](https://gloat.com/academy/why-generic-embeddings-fail-workforce/)  
9. CONFIT V2: Improving Resume-Job Matching using Hypothetical Resume Embedding and Runner-Up Hard-Negative Mining \- ACL Anthology, truy cập vào tháng 4 23, 2026, [https://aclanthology.org/2025.findings-acl.661.pdf](https://aclanthology.org/2025.findings-acl.661.pdf)  
10. ConFit v2: Improving Resume-Job Matching using Hypothetical Resume Embedding and Runner-Up Hard-Negative Mining \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2502.12361v1](https://arxiv.org/html/2502.12361v1)  
11. Algorithms risk perpetuating bias in hiring. How can employers use them to make hiring more inclusive? | Urban Institute, truy cập vào tháng 4 23, 2026, [https://www.urban.org/urban-wire/algorithms-risk-perpetuating-bias-hiring-how-can-employers-use-them-make-hiring-more-inclusive](https://www.urban.org/urban-wire/algorithms-risk-perpetuating-bias-hiring-how-can-employers-use-them-make-hiring-more-inclusive)  
12. AI-assisted recruitment is biased. Here's how to make it more fair | World Economic Forum, truy cập vào tháng 4 23, 2026, [https://www.weforum.org/stories/2019/05/ai-assisted-recruitment-is-biased-heres-how-to-beat-it/](https://www.weforum.org/stories/2019/05/ai-assisted-recruitment-is-biased-heres-how-to-beat-it/)  
13. The Vector Bottleneck: Limitations of Embedding-Based Retrieval \- Shaped.ai, truy cập vào tháng 4 23, 2026, [https://www.shaped.ai/blog/the-vector-bottleneck-limitations-of-embedding-based-retrieval](https://www.shaped.ai/blog/the-vector-bottleneck-limitations-of-embedding-based-retrieval)  
14. Hyper-Relevant Semantic Hiring with Vector Search & RAG \- V2Solutions, truy cập vào tháng 4 23, 2026, [https://www.v2solutions.com/blogs/semantic-hiring-vector-search-rag/](https://www.v2solutions.com/blogs/semantic-hiring-vector-search-rag/)  
15. How does vector search compare to hybrid search approaches? \- Milvus, truy cập vào tháng 4 23, 2026, [https://milvus.io/ai-quick-reference/how-does-vector-search-compare-to-hybrid-search-approaches](https://milvus.io/ai-quick-reference/how-does-vector-search-compare-to-hybrid-search-approaches)  
16. A Comprehensive Hybrid Search Guide | Elastic, truy cập vào tháng 4 23, 2026, [https://www.elastic.co/what-is/hybrid-search](https://www.elastic.co/what-is/hybrid-search)  
17. Hybrid Search Fusion Ranking \- Salesforce Help, truy cập vào tháng 4 23, 2026, [https://help.salesforce.com/s/articleView?id=data.c360\_a\_hybridsearch\_fusion\_ranking.htm\&language=en\_US\&type=5](https://help.salesforce.com/s/articleView?id=data.c360_a_hybridsearch_fusion_ranking.htm&language=en_US&type=5)  
18. Elastic linear retriever for hybrid search: introduction & config \- Elasticsearch Labs, truy cập vào tháng 4 23, 2026, [https://www.elastic.co/search-labs/blog/linear-retriever-hybrid-search](https://www.elastic.co/search-labs/blog/linear-retriever-hybrid-search)  
19. Relevance scoring in hybrid search using Reciprocal Rank Fusion (RRF) \- Microsoft Learn, truy cập vào tháng 4 23, 2026, [https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking)  
20. Understand Hybrid Search \- Oracle Help Center, truy cập vào tháng 4 23, 2026, [https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/understand-hybrid-search.html](https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/understand-hybrid-search.html)  
21. Reciprocal Rank Fusion and Relative Score Fusion: Classic Hybrid Search Techniques | by MongoDB \- Medium, truy cập vào tháng 4 23, 2026, [https://medium.com/mongodb/reciprocal-rank-fusion-and-relative-score-fusion-classic-hybrid-search-techniques-3bf91008b81d](https://medium.com/mongodb/reciprocal-rank-fusion-and-relative-score-fusion-classic-hybrid-search-techniques-3bf91008b81d)  
22. Real-Time Hybrid Search Using RRF \- Spice AI, truy cập vào tháng 4 23, 2026, [https://spice.ai/blog/real-time-hybrid-search-using-rrf](https://spice.ai/blog/real-time-hybrid-search-using-rrf)  
23. Resume2Vec: Transforming Applicant Tracking Systems with Intelligent Resume Embeddings for Precise Candidate Matching \- MDPI, truy cập vào tháng 4 23, 2026, [https://www.mdpi.com/2079-9292/14/4/794](https://www.mdpi.com/2079-9292/14/4/794)  
24. Building a Job Description to Resume Matcher using Natural Language Processing, truy cập vào tháng 4 23, 2026, [https://kartikmadan11.medium.com/building-a-job-description-to-resume-matcher-using-natural-language-processing-5a4f5181cfe4](https://kartikmadan11.medium.com/building-a-job-description-to-resume-matcher-using-natural-language-processing-5a4f5181cfe4)  
25. AI-Driven Resume Analysis and Enhancement Using Semantic Modeling and Large Language Feedback Loops \- ACL Anthology, truy cập vào tháng 4 23, 2026, [https://aclanthology.org/2025.clicit-1.51.pdf](https://aclanthology.org/2025.clicit-1.51.pdf)  
26. Combining Embeddings and Domain Knowledge for Job Posting Duplicate Detection \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2406.06257v1](https://arxiv.org/html/2406.06257v1)  
27. VietJobs: A Vietnamese Job Advertisement Dataset \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2603.05262v1](https://arxiv.org/html/2603.05262v1)  
28. VietJobs: A Vietnamese Job Advertisement Dataset \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/pdf/2603.05262](https://arxiv.org/pdf/2603.05262)  
29. Deep Learning for Categorizing Job Titles \- Textkernel, truy cập vào tháng 4 23, 2026, [https://www.textkernel.com/learn-support/blog/deep-learning-for-categorizing-job-titles/](https://www.textkernel.com/learn-support/blog/deep-learning-for-categorizing-job-titles/)  
30. Extracting position titles from unstructured historical job advertisements \- ACL Anthology, truy cập vào tháng 4 23, 2026, [https://aclanthology.org/2024.nlp4dh-1.8.pdf](https://aclanthology.org/2024.nlp4dh-1.8.pdf)  
31. SAGE: A Realistic Benchmark for Semantic Understanding \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2509.21310v1](https://arxiv.org/html/2509.21310v1)  
32. Hanoi to tap into AI to analyze labor market data \- VnEconomy, truy cập vào tháng 4 23, 2026, [https://en.vneconomy.vn/hanoi-to-tap-into-ai-to-analyze-labor-market-data.htm](https://en.vneconomy.vn/hanoi-to-tap-into-ai-to-analyze-labor-market-data.htm)  
33. Embeddings FAQ \- OpenAI Help Center, truy cập vào tháng 4 23, 2026, [https://help.openai.com/en/articles/6824809-embeddings-faq](https://help.openai.com/en/articles/6824809-embeddings-faq)  
34. text-embedding-3-small Model | OpenAI API, truy cập vào tháng 4 23, 2026, [https://developers.openai.com/api/docs/models/text-embedding-3-small](https://developers.openai.com/api/docs/models/text-embedding-3-small)  
35. text-embedding-3-small: High-Quality Embeddings at Scale \- PromptLayer Blog, truy cập vào tháng 4 23, 2026, [https://blog.promptlayer.com/text-embedding-3-small-high-quality-embeddings-at-scale/](https://blog.promptlayer.com/text-embedding-3-small-high-quality-embeddings-at-scale/)  
36. Analyzing Performance Gains in OpenAI's Text-Embedding-3-Small \- TiDB, truy cập vào tháng 4 23, 2026, [https://www.pingcap.com/article/analyzing-performance-gains-in-openais-text-embedding-3-small/](https://www.pingcap.com/article/analyzing-performance-gains-in-openais-text-embedding-3-small/)  
37. Evaluating OpenAI's new embedding models with Lantern and Parea AI, truy cập vào tháng 4 23, 2026, [https://lantern.dev/blog/evaluating](https://lantern.dev/blog/evaluating)  
38. JobMatchAI An Intelligent Job Matching Platform Using Knowledge Graphs, Semantic Search and Explainable AI Website Installation Package Demo Video \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2603.14558v2](https://arxiv.org/html/2603.14558v2)  
39. Mira-Embeddings-V1: Domain-Adapted Semantic Reranking for Recruitment via LLM-Synthesized Data \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2604.17738v1](https://arxiv.org/html/2604.17738v1)  
40. On the Embedding Collapse When Scaling Up Recommendation Models \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2310.04400v2](https://arxiv.org/html/2310.04400v2)  
41. How do you increase accuracy in CV ↔ Job matching with embeddings? : r/Rag \- Reddit, truy cập vào tháng 4 23, 2026, [https://www.reddit.com/r/Rag/comments/1n3t15r/how\_do\_you\_increase\_accuracy\_in\_cv\_job\_matching/](https://www.reddit.com/r/Rag/comments/1n3t15r/how_do_you_increase_accuracy_in_cv_job_matching/)  
42. The Hidden Problem in Vector Search: You're Measuring Similarity, Not Relevance : r/Rag \- Reddit, truy cập vào tháng 4 23, 2026, [https://www.reddit.com/r/Rag/comments/1pcgrnj/the\_hidden\_problem\_in\_vector\_search\_youre/](https://www.reddit.com/r/Rag/comments/1pcgrnj/the_hidden_problem_in_vector_search_youre/)  
43. Evaluation Metrics for Search and Recommendation Systems \- Weaviate, truy cập vào tháng 4 23, 2026, [https://weaviate.io/blog/retrieval-evaluation-metrics](https://weaviate.io/blog/retrieval-evaluation-metrics)  
44. A Practical Guide to Recall, Precision, and NDCG \- Edge AI and Vision Alliance, truy cập vào tháng 4 23, 2026, [https://www.edge-ai-vision.com/2026/02/a-practical-guide-to-recall-precision-and-ndcg/](https://www.edge-ai-vision.com/2026/02/a-practical-guide-to-recall-precision-and-ndcg/)  
45. Normalized Discounted Cumulative Gain (NDCG) explained \- Evidently AI, truy cập vào tháng 4 23, 2026, [https://www.evidentlyai.com/ranking-metrics/ndcg-metric](https://www.evidentlyai.com/ranking-metrics/ndcg-metric)  
46. 10 metrics to evaluate recommender and ranking systems \- Evidently AI, truy cập vào tháng 4 23, 2026, [https://www.evidentlyai.com/ranking-metrics/evaluating-recommender-systems](https://www.evidentlyai.com/ranking-metrics/evaluating-recommender-systems)  
47. Ranking Evaluation Metrics for Recommender Systems | Towards Data Science, truy cập vào tháng 4 23, 2026, [https://towardsdatascience.com/ranking-evaluation-metrics-for-recommender-systems-263d0a66ef54/](https://towardsdatascience.com/ranking-evaluation-metrics-for-recommender-systems-263d0a66ef54/)  
48. Towards Comparing Recommendation to Multiple-Query Search Sessions for Talent Search \- Aalborg Universitets forskningsportal, truy cập vào tháng 4 23, 2026, [https://vbn.aau.dk/files/517887376/Open\_Access\_Article.pdf](https://vbn.aau.dk/files/517887376/Open_Access_Article.pdf)  
49. A Theoretical Analysis of NDCG Type Ranking Measures | Request PDF \- ResearchGate, truy cập vào tháng 4 23, 2026, [https://www.researchgate.net/publication/236274361\_A\_Theoretical\_Analysis\_of\_NDCG\_Type\_Ranking\_Measures](https://www.researchgate.net/publication/236274361_A_Theoretical_Analysis_of_NDCG_Type_Ranking_Measures)  
50. Evaluating recommendation systems (mAP, MMR, NDCG) \- Shaped.ai, truy cập vào tháng 4 23, 2026, [https://www.shaped.ai/blog/evaluating-recommendation-systems-map-mmr-ndcg](https://www.shaped.ai/blog/evaluating-recommendation-systems-map-mmr-ndcg)  
51. Ranking Evaluation Metrics for Recommender Systems | by Benjamin Wang \- Medium, truy cập vào tháng 4 23, 2026, [https://medium.com/data-science/ranking-evaluation-metrics-for-recommender-systems-263d0a66ef54](https://medium.com/data-science/ranking-evaluation-metrics-for-recommender-systems-263d0a66ef54)  
52. VN-MTEB: Vietnamese Massive Text Embedding ... \- ACL Anthology, truy cập vào tháng 4 23, 2026, [https://aclanthology.org/2026.findings-eacl.86.pdf](https://aclanthology.org/2026.findings-eacl.86.pdf)  
53. RecruitBench: An Outcome-Grounded Benchmark for Evaluating AI Recruiting Systems \- Stanford University, truy cập vào tháng 4 23, 2026, [https://cs191w.stanford.edu/projects/Winter2026/\_Aditya\_\_\_Sood\_.pdf](https://cs191w.stanford.edu/projects/Winter2026/_Aditya___Sood_.pdf)  
54. Concept Embedding Models: Beyond the Accuracy-Explainability Trade-Off, truy cập vào tháng 4 23, 2026, [https://proceedings.neurips.cc/paper\_files/paper/2022/file/867c06823281e506e8059f5c13a57f75-Paper-Conference.pdf](https://proceedings.neurips.cc/paper_files/paper/2022/file/867c06823281e506e8059f5c13a57f75-Paper-Conference.pdf)  
55. Innovative Recommendation Applications Using Two Tower Embeddings at Uber, truy cập vào tháng 4 23, 2026, [https://www.uber.com/us/en/blog/innovative-recommendation-applications-using-two-tower-embeddings/](https://www.uber.com/us/en/blog/innovative-recommendation-applications-using-two-tower-embeddings/)  
56. Inferring Complementary and Substitutable Products Based on Knowledge Graph Reasoning \- MDPI, truy cập vào tháng 4 23, 2026, [https://www.mdpi.com/2227-7390/11/22/4709](https://www.mdpi.com/2227-7390/11/22/4709)  
57. Lessons learned on information retrieval in electronic health records: a comparison of embedding models and pooling strategies \- PMC, truy cập vào tháng 4 23, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC11756698/](https://pmc.ncbi.nlm.nih.gov/articles/PMC11756698/)  
58. Predictive modeling of clinical trial terminations using feature engineering and embedding learning \- PMC, truy cập vào tháng 4 23, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC7876037/](https://pmc.ncbi.nlm.nih.gov/articles/PMC7876037/)  
59. VN-MTEB: Vietnamese Massive Text Embedding Benchmark \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2507.21500v1](https://arxiv.org/html/2507.21500v1)  
60. AgentIR: Reasoning-Aware Retrival for Deep Research Agents \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2603.04384v1](https://arxiv.org/html/2603.04384v1)  
61. LLMs are Also Effective Embedding Models: An In-depth Overview \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2412.12591v1](https://arxiv.org/html/2412.12591v1)  
62. Best Embedding Models 2026: Benchmarks, Pricing ($0.02-$0.18/1M) \- PE Collective, truy cập vào tháng 4 23, 2026, [https://pecollective.com/tools/best-embedding-models/](https://pecollective.com/tools/best-embedding-models/)

[image1]: images/NMAIex_1/image1.png

[image2]: images/NMAIex_1/image2.png

[image3]: images/NMAIex_1/image3.png

[image4]: images/NMAIex_1/image4.png

[image5]: images/NMAIex_1/image5.png

[image6]: images/NMAIex_1/image6.png

[image7]: images/NMAIex_1/image7.png

[image8]: images/NMAIex_1/image8.png

[image9]: images/NMAIex_1/image9.png

[image10]: images/NMAIex_1/image10.png

[image11]: images/NMAIex_1/image11.png

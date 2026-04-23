# **Báo cáo Kỹ thuật: Triển khai Kiến trúc Hybrid Ranking, Feature Engineering và Calibration cho Hệ thống Tuyển dụng FANG**

## **1\. Tổng quan Kiến trúc FANG Hiện tại và Định nghĩa Bài toán**

Trong khuôn khổ chuyển đổi kiến trúc hệ thống, FANG đang được thiết lập để trở thành AI Core trung tâm đảm nhiệm toàn bộ khối lượng công việc phức tạp liên quan đến trí tuệ nhân tạo, bao gồm trích xuất dữ liệu, phân tích cú pháp (parsing), nhúng (embedding), và truy xuất dựa trên thế hệ tăng cường (Retrieval-Augmented Generation \- RAG).1 Với việc giao diện miCareer-mini được tái cấu trúc thành một thin client 1, mọi logic cốt lõi về xử lý tìm kiếm vector và điều phối mô hình ngôn ngữ lớn (LLM) thông qua hệ thống fallback 5 cấp độ đều được quy về FANG.1

Hiện tại, kiến trúc truy xuất (retrieval) của hệ thống FANG chủ yếu dựa trên kỹ thuật tìm kiếm ngữ nghĩa (semantic search). Cụ thể, các đoạn tài liệu sơ yếu lý lịch (CV) được mã hóa thành các vector và lưu trữ tại bảng AIDOCUMENTCHUNK dưới định dạng halfvec(1024).1 Hệ thống sử dụng chỉ mục Hierarchical Navigable Small World (HNSW) kết hợp với khoảng cách Cosine (halfvec\_cosine\_ops) để tính toán mức độ tương đồng giữa câu truy vấn của nhà tuyển dụng và nội dung tài liệu.1 Mặc dù phương pháp nhúng vector hiện tại thể hiện sự xuất sắc trong việc nắm bắt ý nghĩa tiềm ẩn của văn bản, nó bộc lộ những hạn chế đáng kể khi xử lý các truy vấn chứa định danh chính xác (exact identifiers) như mã lỗi, tên công cụ đặc thù, chứng chỉ chuyên ngành, hoặc các ràng buộc cứng mang tính nghiệp vụ tuyển dụng.2

Nghiên cứu này đi sâu vào giải quyết Cụm 4 của lộ trình triển khai: đánh giá và thiết kế hệ thống xếp hạng hỗn hợp (Hybrid Ranking) và hiệu chuẩn trọng số (Weight Calibration). Trọng tâm của hệ thống không dừng lại ở việc truy xuất tài liệu thuần túy, mà là giải quyết bài toán ghép nối hai chiều (Bidirectional Matching) trong hệ sinh thái tuyển dụng.4 Bài toán này được chia thành hai luồng độc lập nhưng có tính tương hỗ:

1. Xếp hạng danh sách công việc cho một ứng viên cụ thể (Candidate ![][image1] Job).  
2. Xếp hạng danh sách ứng viên cho một vị trí công việc cụ thể (Job ![][image1] Candidate).

Mục tiêu cốt lõi của nghiên cứu là đề xuất một lộ trình triển khai thực tiễn, kết hợp kỹ thuật tinh chỉnh đặc trưng (Feature Engineering) với cơ sở hạ tầng Embedding hiện có của FANG. Báo cáo sẽ phân tích chi tiết các đánh đổi kỹ thuật (trade-offs), đảm bảo tính minh bạch của mô hình (Explainability), tối ưu hóa chi phí tính toán, và kiểm soát rủi ro học vẹt (Overfitting) trên các tập dữ liệu Applicant Tracking System (ATS) có quy mô hạn chế. Các đề xuất tuân thủ nghiêm ngặt nguyên tắc tận dụng tối đa tài nguyên có sẵn, tái sử dụng các module hiệu quả và chỉ bổ sung các thành phần mới khi có bằng chứng toán học hoặc thực tiễn đủ mạnh.

## **2\. Phân định Tín hiệu và Nhiễu trong Kỹ thuật Đặc trưng (Feature Engineering)**

Sự thành bại của một hệ thống tuyển dụng AI không chỉ nằm ở kiến trúc mạng nơ-ron mà phần lớn được quyết định bởi chất lượng của các tín hiệu (signals) đầu vào.6 Trong lý thuyết thông tin ứng dụng vào tuyển dụng, việc phân định rõ ràng giữa tín hiệu có giá trị dự đoán thực tiễn và nhiễu (noise) là bước tối quan trọng để xây dựng một lớp Hybrid Ranking chống chịu lỗi tốt.7 Dữ liệu tuyển dụng truyền thống chứa một lượng nhiễu khổng lồ do sự bất đồng nhất trong cách ứng viên viết CV và cách nhà tuyển dụng mô tả công việc (JD).7

### **2.1. Phân tích Cấu trúc Các Đặc trưng Bổ sung**

Việc chỉ sử dụng độ tương đồng vector (Embedding Similarity) dẫn đến hiện tượng đánh đồng các kỹ năng có ngữ nghĩa gần giống nhau nhưng khác biệt hoàn toàn về mặt ứng dụng thực tiễn.9 Dưới đây là phân tích chuyên sâu về các đặc trưng bổ sung, phân loại chúng thành tín hiệu mạnh hoặc nhiễu tiềm năng.

Nhóm đặc trưng liên quan đến năng lực và kinh nghiệm đóng vai trò là trụ cột của hệ thống. Đặc trưng về sự chồng chéo kỹ năng (Skill Overlap) cung cấp một tín hiệu cực kỳ mạnh mẽ. Tuy nhiên, thay vì chỉ đếm số lượng từ khóa trùng khớp—một phương pháp dễ bị thao túng bởi kỹ thuật nhồi nhét từ khóa (Keyword Stuffing)—hệ thống cần đánh giá kỹ năng thông qua lăng kính của độ "tươi" (Recency).10 Một ứng viên sử dụng ReactJS liên tục trong 6 tháng qua mang lại giá trị dự đoán cao hơn nhiều so với một người đã dùng nó cách đây 5 năm.10 Khoảng cách kinh nghiệm (Experience/Seniority Gap) cũng là một tín hiệu định lượng xuất sắc, dễ dàng tính toán thông qua cột expyears trong bảng CANDIDATE của FANG.1 Sự chênh lệch quá lớn giữa yêu cầu của công việc và thâm niên của ứng viên thường dẫn đến việc ứng viên bị loại vì lý do vượt quá năng lực (over-qualified) hoặc thiếu hụt năng lực (under-qualified).11

Ngược lại, nhóm đặc trưng định danh chức danh (Title Match) và miền hoạt động (Domain Match) lại là nguồn tạo nhiễu cực lớn. Chức danh công việc trên thị trường hiện nay thiếu sự chuẩn hóa trầm trọng.9 Ví dụ, một "VP of Engineering" tại một công ty khởi nghiệp 5 người có thể thực hiện các tác vụ lập trình hàng ngày tương tự như một "Senior Software Engineer" tại một tập đoàn công nghệ lớn.9 Việc so khớp chuỗi thuần túy dựa trên chức danh sẽ loại bỏ những ứng viên có năng lực phù hợp nhưng khác biệt về cách gọi tên vị trí. Tương tự, đặc trưng về học vấn (Education) ngày càng trở nên kém quan trọng trong các lĩnh vực kỹ thuật so với các bài kiểm tra năng lực thực tế hoặc danh mục dự án cá nhân, biến nó thành một đặc trưng có độ nhiễu cao hoặc thậm chí mang mầm mống của sự thiên kiến (Bias).12

Nhóm đặc trưng về ràng buộc định lượng (Hard Constraints) bao gồm mức lương (Salary Match), địa điểm (Location Match), và hình thức làm việc (Employment Type). Đây là các tín hiệu mạnh và mang tính tuyệt đối. Dữ liệu từ FANG hiện đang lưu trữ các trường minSalary, maxSalary, workLoc, và workMode trong bảng JOBPOSTING.1 Sự bất đồng thuận về các yếu tố này thường là điểm kết thúc (deal-breaker) cho bất kỳ quá trình đàm phán nào, bất kể ứng viên có xuất sắc đến đâu. Việc chuyển đổi các yếu tố này thành các đặc trưng phạt (Penalty Features) thông qua hàm suy hao tuyến tính là phương pháp hiệu quả để tinh chỉnh kết quả xếp hạng.

Lịch sử ứng tuyển (Application History) trích xuất từ bảng APPSTATUSHISTORY là một con dao hai lưỡi.1 Ở khía cạnh tích cực, nó cung cấp các tín hiệu ẩn (implicit signals) về sở thích của ứng viên đối với các công ty cụ thể hoặc tỷ lệ chấp nhận lời mời làm việc (offer acceptance rate). Tuy nhiên, nếu không được kiểm soát chặt chẽ, việc sử dụng dữ liệu trạng thái phỏng vấn trong quá khứ có thể gây ra hiện tượng rò rỉ dữ liệu (Target Leakage), trong đó mô hình vô tình học thuộc kết quả thay vì học cách dự đoán năng lực.13

### **2.2. Tính Phi đối xứng trong Xếp hạng Hai chiều**

Một sai lầm hệ thống phổ biến trong việc thiết kế công cụ ghép nối tuyển dụng là sử dụng chung một bộ trọng số (Shared Feature Weights) cho cả hai hướng.15 Bài toán tuyển dụng có bản chất phi đối xứng; hàm mục tiêu tối ưu hóa của nhà tuyển dụng hoàn toàn khác biệt so với ứng viên.17

Dữ liệu hệ thống FANG hỗ trợ việc thiết kế hai bộ đặc trưng tách biệt để phản ánh đúng thực tế này. Bảng dưới đây tóm tắt sự phân rã của các nhóm đặc trưng và trọng số kỳ vọng cho từng hướng xếp hạng.

| Nhóm Đặc trưng (Features) | Hướng Candidate → Job (Xếp hạng Việc làm) | Hướng Job → Candidate (Xếp hạng Ứng viên) | Đánh giá Giá trị Phân tích |
| :---- | :---- | :---- | :---- |
| **Salary Match** (Ngân sách & Lương) | **Trọng số Rất Cao:** Thường là yếu tố quyết định cao nhất đối với người tìm việc.19 | **Trọng số Cao:** Cần thiết để lọc bỏ các ứng viên vượt quá ngân sách quỹ lương. | **Tín hiệu Tuyệt đối**. Áp dụng hàm phạt phi tuyến tính nếu chênh lệch vượt ngưỡng 20%. |
| **Location & Work Mode** | **Trọng số Rất Cao:** Xu hướng làm việc Remote/Hybrid quyết định mạnh mẽ sự lựa chọn.20 | **Trọng số Rất Cao:** Ràng buộc về mặt pháp lý và khả năng hiện diện vật lý tại văn phòng.21 | **Tín hiệu Tuyệt đối**. Có thể triển khai dưới dạng bộ lọc cứng (Hard filter) trước khi xếp hạng. |
| **Skill Overlap** (Giao thoa kỹ năng) | **Trọng số Trung bình:** Ứng viên có xu hướng nộp hồ sơ ngay cả khi chỉ đáp ứng 60-70% bộ kỹ năng. | **Trọng số Rất Cao:** NTD đánh giá độ rủi ro của việc tuyển dụng dựa trên sự khớp nối kỹ năng cốt lõi.6 | **Tín hiệu Mạnh**. Đòi hỏi kỹ thuật ánh xạ ngữ nghĩa (semantic mapping) để xử lý từ đồng nghĩa. |
| **Seniority / Exp Gap** | **Trọng số Trung bình:** Ứng viên thường nhắm đến các công việc vượt cấp (reach jobs) để thăng tiến. | **Trọng số Rất Cao:** Tránh hiện tượng ứng viên thiếu năng lực trầm trọng hoặc quá mức trình độ (Over-qualified).11 | **Tín hiệu Định lượng**. Tính toán thông qua chênh lệch năm kinh nghiệm so với yêu cầu JD.1 |
| **Title / Domain Match** | **Trọng số Cao:** Giúp ứng viên nhận diện quỹ đạo sự nghiệp quen thuộc và an toàn.10 | **Trọng số Trung bình:** Chức danh dễ gây nhiễu, NTD ngày càng tập trung vào đánh giá kỹ năng thực tiễn hơn.9 | **Nhiễu Tiềm năng**. Cần cẩn trọng khi sử dụng để tránh loại bỏ ứng viên chuyển đổi ngành nghề. |

Quyết định kỹ thuật: Kiến trúc hệ thống bắt buộc phải duy trì hai tập hợp không gian đặc trưng (feature spaces) độc lập cho hai chức năng API riêng biệt. Việc chia tách này đảm bảo rằng mỗi bảng xếp hạng được tối ưu hóa chính xác cho người dùng cuối tương ứng, tránh hiện tượng trung bình hóa làm giảm chất lượng dự đoán.

## **3\. Đề xuất Kiến trúc Mô hình Hybrid Ranking**

Kiến trúc truy xuất của FANG hiện tại là một hệ thống RAG hai giai đoạn cơ bản, phụ thuộc hoàn toàn vào tìm kiếm vector trên AIDOCUMENTCHUNK.1 Để đáp ứng bài toán xếp hạng ứng viên ở quy mô lớn, việc chỉ dựa vào không gian ngữ nghĩa (Semantic Space) là chưa đủ. Dưới đây là phân tích các phương án thiết kế kiến trúc Hybrid, được xem xét dựa trên các tiêu chí về độ phức tạp, khả năng tích hợp với cơ sở dữ liệu PostgreSQL hiện có, và chi phí vận hành.

### **3.1. Phân tích Các Biến thể Thiết kế Mô hình**

**Mô hình Reranking Layer (Neural Reranking bằng Cross-Encoder):** Phương pháp này đưa toàn bộ kết quả từ bước truy xuất vào một mô hình học sâu (ví dụ: BERT-based cross-encoders) để đánh giá mức độ tương quan thông qua cơ chế self-attention toàn cục giữa truy vấn và tài liệu.22 Mặc dù phương pháp này thường đạt độ chính xác trạng thái kỹ thuật (SOTA), nó vô cùng tốn kém về mặt tính toán (FLOPs cao) và tạo ra độ trễ (Latency) không thể chấp nhận được đối với các hệ thống thời gian thực.23 Đối với kiến trúc FANG đang ở Phase 1-2, tập trung vào mô hình fallback 1, việc chèn thêm một lớp Cross-encoder dày đặc sẽ gây nghẽn cổ chai nghiêm trọng. Phương pháp này chỉ nên được coi là tầm nhìn dài hạn.

**Mô hình Learning-to-Rank (LTR):** Việc ứng dụng các thuật toán dạng cây như Gradient Boosted Decision Trees (GBDT), cụ thể là XGBoost, LightGBM hoặc LambdaMART, cho phép hệ thống học được các tương tác phi tuyến tính phức tạp giữa các đặc trưng.24 LTR chuyển đổi bài toán xếp hạng thành việc tối ưu hóa các cặp (pairwise) hoặc danh sách (listwise).26 Mặc dù cực kỳ mạnh mẽ đối với dữ liệu dạng bảng (tabular data), LTR đòi hỏi một lượng khổng lồ dữ liệu tương tác có nhãn chất lượng cao.26 Do tập dữ liệu ATS lịch sử của FANG có thể còn hạn chế hoặc chứa nhiều thiên kiến, việc đào tạo một mô hình LTR ngay lập tức mang lại nguy cơ overfit rất lớn.25 LTR được khuyến nghị là giai đoạn tiến hóa tiếp theo (Phase 3\) của hệ thống.

### **3.2. Khuyến nghị MVP: Post-Retrieval Rule-based kết hợp RRF và Weighted Linear Scoring**

Dựa trên nguyên tắc không tự động thay đổi kiến trúc nếu không có tính ưu việt rõ rệt về chi phí và rủi ro, chiến lược triển khai kết hợp **Reciprocal Rank Fusion (RRF)** và **Weighted Linear Scoring** được đề xuất làm Giải pháp Khả thi Tối thiểu (MVP). Phương án này khai thác tối đa hạ tầng PostgreSQL đang vận hành tại FANG mà không yêu cầu triển khai thêm các cluster GPU cho mô hình học sâu mới.2

1. **Truy vấn Song song (Parallel Query) tại tầng Database:** FANG sẽ mở rộng bảng AIDOCUMENTCHUNK để hỗ trợ chỉ mục tìm kiếm văn bản đầy đủ (Full-Text Search) thông qua cột tsvector.2 Khi có truy vấn, PostgreSQL sẽ thực thi đồng thời hai luồng tìm kiếm:  
   * *Semantic Search:* Sử dụng pgvector với toán tử \<=\> trên không gian nhúng halfvec(1024) hiện tại.1  
   * *Lexical Search (BM25):* Sử dụng toán tử @@ và hàm ts\_rank\_cd để truy xuất các từ khóa chính xác.31  
2. **Dung hợp Kết quả bằng Reciprocal Rank Fusion (RRF):** RRF là một thuật toán cực kỳ hiệu quả để kết hợp các danh sách xếp hạng có thang điểm khác nhau mà không cần chuẩn hóa phức tạp.32 RRF sẽ được thực thi trực tiếp bằng Common Table Expressions (CTE) trong SQL. Công thức toán học cốt lõi như sau:  
   ![][image2]  
   Trong đó, ![][image3] là một hằng số làm mượt (smoothing constant), thường được đặt bằng 60 để tránh việc các tài liệu ở top 1 chi phối hoàn toàn điểm số, đảm bảo sự phân phối hợp lý ở các hạng đầu.29  
3. **Lớp Xếp hạng Tuyển tính (Weighted Linear Scoring):** Sau khi cơ sở dữ liệu trả về tập hợp ứng viên hoặc công việc tiềm năng thông qua RRF, module FANG backend (viết bằng Python) sẽ áp dụng một lớp tuyến tính muộn (Late Fusion) để kết hợp các điểm số RRF với các đặc trưng cấu trúc (Structured Features) đã được phân tích ở Phần 2\.2 Cấu trúc của hàm đánh giá được thiết kế như sau:  
   ![][image4]  
   Trong đó, ![][image5] là một hàm phi tuyến tính phạt nặng các kết quả vi phạm ngân sách hoặc khoảng cách địa lý vượt quá ngưỡng quy định.3

Sự kết hợp này đảm bảo hệ thống có thể xử lý các truy vấn trừu tượng thông qua vector, đồng thời không bao giờ bỏ sót các yêu cầu từ khóa tuyệt đối nhờ BM25.2 Nó minh bạch, chi phí điện toán thấp, và dễ dàng tinh chỉnh thủ công trong quá trình thử nghiệm.

### **3.3. Ranh giới Áp dụng: Baseline Embedding thuần túy vs. Lớp Hybrid**

Để tối ưu hóa tài nguyên tính toán, FANG cần có cơ chế định tuyến (Routing) linh hoạt giữa các phương pháp truy xuất:

* **Sử dụng Baseline Embedding thuần túy:** Phù hợp cho các tác vụ phân tích định tính nội bộ hoặc các truy vấn dạng khám phá không có ranh giới rõ ràng. Ví dụ: khi HR yêu cầu AI tóm tắt "đánh giá về văn hóa công ty dựa trên nhận xét phỏng vấn", hệ thống chỉ cần dùng Vector Search để truy xuất dữ liệu từ AICHATMESSAGE hoặc các ghi chú phỏng vấn.1  
* **Bắt buộc sử dụng Hybrid Layer (RRF \+ Linear):** Phải được kích hoạt đối với mọi điểm cuối API (API endpoints) phục vụ việc hiển thị danh sách xếp hạng trực tiếp trên giao diện miCareer-mini cho người dùng cuối. Việc dựa hoàn toàn vào Semantic Search trong các danh sách này sẽ gây ra trải nghiệm người dùng kém do sự mất mát thông tin đối với các từ khóa kỹ thuật cốt lõi.2

## **4\. Chiến lược Hiệu chuẩn Trọng số (Weight Calibration) và Ngăn ngừa Overfitting**

Điểm số thô được tạo ra từ hàm khoảng cách Cosine hoặc mô hình XGBoost không đại diện cho xác suất thống kê thực sự.35 Trong môi trường tuyển dụng, việc thiết lập các ngưỡng tự động (Score-thresholding) để quyết định có nên loại một ứng viên hay không đòi hỏi hệ thống phải chuyển đổi các điểm số này thành xác suất đã được hiệu chuẩn (ví dụ: mô hình dự đoán 80% xác suất ứng viên sẽ vượt qua vòng phỏng vấn, và trong thực tế tỷ lệ này dao động gần mức 80%).37

### **4.1. Lựa chọn Phương pháp: Platt Scaling vs. Isotonic Regression**

Quá trình hiệu chuẩn đóng vai trò trung gian giữa đầu ra của mô hình và quyết định nghiệp vụ.39 Hai kỹ thuật phổ biến nhất hiện nay là Platt Scaling (Hiệu chuẩn Logistic) và Isotonic Regression.

Do đặc thù của dữ liệu ATS (APPSTATUSHISTORY) là tỷ lệ chuyển đổi cực thấp (thường dưới 5% ứng viên nộp hồ sơ được tuyển dụng), tập dữ liệu có tính trạng mất cân bằng cực đoan (Highly Imbalanced).36

* **Isotonic Regression:** Là một phương pháp hồi quy phi tham số (non-parametric), nó khớp một hàm bậc thang đơn điệu (monotonic step function) với dữ liệu. Mặc dù linh hoạt, phương pháp này vô cùng nhạy cảm với hiện tượng quá khớp (overfitting) khi làm việc với các tập dữ liệu nhỏ hoặc thiếu tính đại diện.38  
* **Platt Scaling (Logistic Calibration):** Sử dụng một hàm Sigmoid (hồi quy logistic) có tham số để ánh xạ điểm số thô. Mặc dù nó mang tính giả định mạnh mẽ về hình dạng của đường cong hiệu chuẩn, chính sự đơn giản của phương trình logistic lại đóng vai trò như một bộ điều chuẩn (Regularizer) tự nhiên mạnh mẽ.38

**Quyết định Kỹ thuật:** Đối với kiến trúc FANG hiện tại, **Platt Scaling** được chọn làm phương pháp tiêu chuẩn để hiệu chuẩn trọng số. Kỹ thuật này sẽ ngăn chặn việc hệ thống học thuộc các nhiễu cục bộ trong tập dữ liệu ATS lịch sử có kích thước nhỏ.28

### **4.2. Khởi tạo Trọng số và Chuyển đổi sang Supervised Learning**

Hệ thống sẽ được triển khai theo chiến lược hai giai đoạn để đảm bảo tính ổn định:

1. **Giai đoạn Khởi động Lạnh (Cold Start) \- Heuristic Calibration:** Các trọng số tuyến tính ban đầu (![][image6]) sẽ được đặt thủ công thông qua sự đồng thuận của các chuyên gia nhân sự, dựa trên các nghiên cứu thống kê trên thị trường. Ví dụ, thiết lập trọng số ưu tiên 40% cho Skill Overlap, 25% cho kinh nghiệm, và thiết lập mức phạt nghiêm khắc đối với rào cản về ngân sách.33  
2. **Giai đoạn Warm Start \- Supervised Weight Learning:** Khi FANG đã thu thập đủ dữ liệu phản hồi ngầm (Implicit feedback: thời gian xem hồ sơ, nhấp chuột) và phản hồi rõ ràng (Explicit feedback: kết quả phỏng vấn, lời mời làm việc), hệ thống sẽ chuyển sang cơ chế học có giám sát.36 Hàm mục tiêu (Objective Function) sẽ là tối thiểu hóa hàm suy hao Log-Loss. Để kiểm soát overfitting trong quá trình học trọng số, kỹ thuật **L2 Regularization (Weight Decay)** sẽ được tích hợp vào hàm chi phí, ép buộc mô hình phải phân bổ trọng số đồng đều thay vì quá phụ thuộc vào một tín hiệu duy nhất.14

## **5\. Chiến lược Sinh Dữ liệu Tổng hợp (Synthetic Data) Quy mô Lớn**

Sự thiếu hụt về dữ liệu ATS có nhãn chất lượng cao là rào cản lớn nhất cho việc phát triển các mô hình học máy thứ cấp trong hệ thống FANG.45 Để giải quyết tình trạng này, một chiến lược mở rộng dữ liệu thông qua AI tạo sinh (Generative AI) được đề xuất, tận dụng hạ tầng các mô hình Pro (như GPT-5.4 hoặc Gemini-3.1-Pro) đã được tích hợp trong kế hoạch triển khai FANG.1

### **5.1. Pipeline Sinh Sơ yếu Lý lịch (CV Generation) Dựa trên LLM**

Quá trình sinh dữ liệu không thể được thực hiện một cách ngẫu nhiên mà cần có sự điều khiển chặt chẽ (Controlled Generation).

1. **Seed Selection (Chọn Hạt giống):** Thu thập các bản mô tả công việc (JD) ẩn danh từ cơ sở dữ liệu JOBPOSTING.1  
2. **Prompt Engineering:** Xây dựng các siêu câu lệnh (System Prompts) chi tiết, hướng dẫn LLM Pro Tier sinh ra các hồ sơ ứng viên với các mức độ phù hợp khác nhau (ví dụ: hồ sơ xuất sắc, hồ sơ có kỹ năng tốt nhưng thiếu kinh nghiệm, hồ sơ trái ngành hoàn toàn).17 Việc phân chia độ phân giải này đảm bảo mô hình hiệu chuẩn (Calibration Model) sau này học được biên giới quyết định (decision boundaries) một cách chính xác.  
3. **Pseudo-labeling:** Hệ thống tự động gán nhãn mức độ phù hợp tương ứng cho các hồ sơ vừa được sinh ra để tạo thành các cặp \`\`.

### **5.2. Cổng Kiểm soát Chất lượng Dữ liệu (Data Quality Gates)**

Để ngăn chặn việc mô hình xếp hạng bị overfit—nghĩa là nó chỉ học cách nhận diện các cấu trúc văn bản hoàn hảo do LLM tạo ra thay vì năng lực thực sự—các cơ chế kiểm soát chất lượng phải được triển khai như các bộ lọc độc lập trước khi lưu vào cơ sở dữ liệu 48:

* **Bơm Nhiễu (Noise Injection):** Cố ý chèn các lỗi định dạng, từ lóng, sự mâu thuẫn nhẹ về ngữ pháp, hoặc kỹ thuật nhồi nhét từ khóa (Keyword Stuffing) vào khoảng 30% lượng CV tổng hợp.48 Điều này buộc các thuật toán nhúng vector phải học cách tìm kiếm ý nghĩa cốt lõi thay vì phụ thuộc vào cấu trúc bề mặt.  
* **Kiểm tra Tính Nhất quán (Consistency Check):** Áp dụng các quy tắc logic (Rule-based scripts) để kiểm định tính hợp lý của dữ liệu. Ví dụ, một ứng viên tốt nghiệp đại học năm 2024 không thể sở hữu 10 năm kinh nghiệm quản lý dự án, hoặc không thể có ứng viên có 5 năm kinh nghiệm làm việc với một framework công nghệ mới ra mắt được 2 năm. Các hồ sơ vi phạm các định lý logic thời gian này sẽ bị loại bỏ ngay lập tức.50  
* **Chiến lược Sampling:** Không tạo ra dữ liệu tổng hợp một cách vô tội vạ. Chỉ sinh thêm mẫu cho các phân phối thiếu hụt trong tập dữ liệu thực (ví dụ: các vị trí công nghệ ngách mới nổi) để cân bằng không gian học.50

## **6\. Khả năng Giải thích (Explainability \- XAI) trong Quyết định Tuyển dụng**

Việc ứng dụng AI trong quy trình tuyển dụng đang thu hút sự giám sát khắt khe từ các khuôn khổ pháp lý toàn cầu (như Đạo luật AI của Châu Âu hay luật địa phương của Hoa Kỳ) về tính công bằng, chống thiên kiến, và tính minh bạch của thuật toán.10 Trong hệ thống FANG, Khả năng Giải thích (XAI) không chỉ là một yêu cầu kỹ thuật mà là yếu tố quyết định để xây dựng sự tin tưởng từ người dùng.53

### **6.1. Ưu tiên Đặc trưng Giải thích được (Interpretable Features)**

Nguyên tắc cốt lõi trong việc thiết kế kiến trúc là: **Phải ưu tiên các đặc trưng có khả năng giải thích trực tiếp (Rule-based hoặc Linear) hơn các đặc trưng mạng nơ-ron sâu phức tạp nếu hiệu năng của chúng xấp xỉ nhau**.55

Lý do cơ bản là sự đánh đổi giữa độ chính xác vi mô và tính khả tín vĩ mô. Một mô hình mạng nơ-ron sâu như Cross-encoder có thể cải thiện tỷ lệ dự đoán chính xác thêm 2%, nhưng lại hoàn toàn bất lực trong việc trả lời câu hỏi cốt lõi của nhà tuyển dụng: "Tại sao ứng viên này lại được đánh giá cao hơn ứng viên kia?".53 Hệ thống Linear Scoring (Phương án MVP) với các trọng số minh bạch cho phép hệ thống bóc tách điểm số và cung cấp các báo cáo giải thích trực quan.2

Giao diện người dùng (miCareer-mini) có thể tận dụng kiến trúc này để hiển thị kết quả dưới dạng Thẻ điểm (Scorecards). Thay vì đưa ra một con số vô hồn "Độ phù hợp AI: 85%", hệ thống có thể cung cấp các Highlight chi tiết: "Đạt 8/10 kỹ năng yêu cầu (Thiếu kinh nghiệm AWS); Khoảng cách thâm niên: Phù hợp; Mức lương: Nằm trong ngân sách".54 Trải nghiệm người dùng này sẽ thúc đẩy tỷ lệ áp dụng (adoption rate) cao hơn nhiều so với các hộp đen thuật toán.53

### **6.2. Phân tách Công cụ XAI: SHAP cho Backend và Rule-based cho Frontend**

Khi hệ thống FANG tiến hóa lên sử dụng mô hình Learning-to-Rank phức tạp (GBDT) trong giai đoạn tiếp theo, các thuật toán hộp đen sẽ xuất hiện.24 Lúc này, phương pháp **SHAP (SHapley Additive exPlanations)** trở thành công cụ tiêu chuẩn để phân tích tầm quan trọng của các đặc trưng.60 SHAP sử dụng lý thuyết trò chơi hợp tác để phân bổ công bằng sự đóng góp của từng đặc trưng vào điểm số dự đoán cuối cùng (ví dụ: Việc ứng viên có chứng chỉ PMP đóng góp \+0.8 điểm, trong khi việc thiếu hụt 2 năm kinh nghiệm làm giảm 1.5 điểm).63

Tuy nhiên, việc tính toán SHAP theo thời gian thực tốn nhiều tài nguyên, và các biểu đồ phân phối của SHAP thường quá phức tạp đối với người dùng không có chuyên môn về khoa học dữ liệu.47 Do đó, kiến trúc XAI của FANG cần được phân tách thành hai luồng:

1. **Giao diện Người dùng (Frontend \- miCareer-mini):** Chỉ sử dụng các giải thích dựa trên quy tắc (Rule-based Highlights) hoặc các trích xuất thành phần từ phương trình tuyến tính để đảm bảo độ trễ thấp và tính trực quan.47  
2. **Kiểm toán Hệ thống (Backend \- FANG AI Core):** Dữ liệu SHAP sẽ được tính toán định kỳ thông qua các batch jobs và lưu trữ vào các bảng log như AIQUERYLOG. Đội ngũ kỹ sư sẽ sử dụng SHAP như một công cụ kiểm toán chống thiên kiến (Bias Auditing).1 Nếu phân tích SHAP phát hiện ra rằng các biến số nhạy cảm về mặt nhân khẩu học hoặc các đặc trưng gây nhiễu đang có đóng góp bất thường vào quyết định của mô hình, hệ thống sẽ kích hoạt cảnh báo để tinh chỉnh các bộ lọc chặn đứng (Responsible AI Pipeline).10

## **7\. Giao thức Đánh giá Ngoại tuyến (Offline Evaluation Protocol)**

Để tuân thủ nguyên tắc không can thiệp vào hệ thống nếu không có bằng chứng khoa học rõ ràng, một Giao thức Đánh giá Ngoại tuyến chặt chẽ phải được thiết lập để so sánh các phiên bản mô hình.65

### **7.1. Định nghĩa Nhãn Mức độ Phù hợp (Relevance Labels)**

Trong bài toán xếp hạng tìm kiếm, nhãn đánh giá không tồn tại dưới dạng nhị phân (Đúng/Sai) mà là các giá trị thứ bậc (Ordinal labels). FANG có lợi thế lớn khi sở hữu bảng APPSTATUSHISTORY, cho phép tự động nội suy các nhãn độ tương quan từ lịch sử tương tác của người dùng 1:

* **Nhãn 0 (Không phù hợp):** CV bị hệ thống hoặc con người tự động loại (Rejected).  
* **Nhãn 1 (Quan tâm nhẹ):** Ứng viên lọt vào danh sách rút gọn (Shortlisted) hoặc nhận được email liên hệ ban đầu.1  
* **Nhãn 2 (Quan tâm cao):** Ứng viên vượt qua vòng sơ loại và tham gia phỏng vấn (Interviewing).1  
* **Nhãn 3 (Đích đến hoàn hảo):** Ứng viên nhận được đề nghị làm việc (Offered) hoặc được tuyển dụng thành công (Hired).1

*Cảnh báo Target Leakage:* Trong quá trình đánh giá ngoại tuyến, hệ thống cần phải che dấu (masking) cẩn thận thời gian (timestamps) trong cơ sở dữ liệu. Dữ liệu từ tương lai (ví dụ: ngày ứng viên ký hợp đồng) tuyệt đối không được rò rỉ vào không gian đặc trưng của mô hình đang dự đoán kết quả của thời điểm quá khứ.1

### **7.2. Đơn vị Đo lường Đề xuất (Evaluation Metrics)**

Chất lượng của quá trình xếp hạng sẽ được lượng hóa bằng hai chỉ số học thuật tiêu chuẩn 67:

1. **NDCG@K (Normalized Discounted Cumulative Gain):** Đây là thước đo toàn diện nhất cho các bài toán có nhãn đa cấp độ. Thuật toán này không chỉ thưởng cho mô hình khi nó tìm thấy ứng viên phù hợp, mà còn sử dụng hệ số chiết khấu logarit (logarithmic discount) để phạt nặng nếu ứng viên chất lượng cao (Nhãn 3\) bị đẩy xuống các vị trí thấp (ví dụ: nằm ngoài Top 10).68 Đây sẽ là metric quyết định (North Star Metric) cho hệ thống xếp hạng của FANG.  
2. **MRR (Mean Reciprocal Rank):** Chỉ số này đặc biệt quan trọng đối với trải nghiệm tìm kiếm nhanh. MRR đo lường thứ hạng nghịch đảo của ứng viên có độ phù hợp cao đầu tiên xuất hiện trong danh sách.68 Một chỉ số MRR cao đồng nghĩa với việc người dùng (nhà tuyển dụng hoặc ứng viên) hầu như ngay lập tức nhìn thấy kết quả thỏa mãn ở vị trí số 1 hoặc 2, giảm thiểu thời gian cuộn trang.

### **7.3. Thiết lập Tiêu chuẩn Đối chiếu (Benchmark Setup)**

Quá trình kiểm chứng cần thiết lập một môi trường so sánh công bằng giữa ba cấu hình hệ thống:

* **Cấu hình Baseline (A):** Luồng truy vấn Vector Search thuần túy đang vận hành trên AIDOCUMENTCHUNK hiện tại bằng toán tử \<=\> của PostgreSQL.1  
* **Cấu hình MVP (B):** Áp dụng kiến trúc Hybrid Search (kết hợp Vector Embeddings và BM25 thông qua RRF) nhưng chưa có lớp Calibration.2  
* **Cấu hình Tối ưu (C):** Áp dụng kiến trúc Hybrid đầy đủ, bao gồm RRF và Weighted Linear Scoring đã được hiệu chuẩn bằng Platt Scaling (Calibrated Hybrid).71

Quy tắc quyết định: Nếu cấu hình C không thể hiện sự cải thiện ý nghĩa thống kê (statistically significant) ít nhất từ 3% đến 5% trên thang điểm NDCG@10 so với cấu hình B, đội ngũ kỹ thuật nên tạm hoãn việc tích hợp lớp hiệu chuẩn để tránh làm phức tạp hóa hệ thống một cách không cần thiết, và duy trì cấu trúc ở trạng thái cấu hình B.37 Đồng thời, các số liệu về Expected Calibration Error (ECE) phải được theo dõi liên tục để đảm bảo rằng các xác suất phân bổ từ Platt Scaling đang phản ánh sát với tỷ lệ phân phối thực tế trong thế giới thực.28 Tóm lại, bất kỳ sự thay đổi kiến trúc nào cũng phải dựa trên bằng chứng dữ liệu cứng thay vì các giả định lý thuyết đơn thuần.

#### **Nguồn trích dẫn**

1. rag\_query\_strategy.md  
2. Building Hybrid Search for RAG: Combining pgvector and Full-Text Search with Reciprocal Rank Fusion \- DEV Community, truy cập vào tháng 4 23, 2026, [https://dev.to/lpossamai/building-hybrid-search-for-rag-combining-pgvector-and-full-text-search-with-reciprocal-rank-fusion-6nk](https://dev.to/lpossamai/building-hybrid-search-for-rag-combining-pgvector-and-full-text-search-with-reciprocal-rank-fusion-6nk)  
3. I implemented Hybrid Search (BM25 \+ pgvector) in Postgres to fix RAG retrieval for exact keywords. Here is the logic. \- Reddit, truy cập vào tháng 4 23, 2026, [https://www.reddit.com/r/Rag/comments/1pcvtan/i\_implemented\_hybrid\_search\_bm25\_pgvector\_in/](https://www.reddit.com/r/Rag/comments/1pcvtan/i_implemented_hybrid_search_bm25_pgvector_in/)  
4. Improved Candidate-Career Matching Using Comparative Semantic Re \- astesj, truy cập vào tháng 4 23, 2026, [https://www.astesj.com/publications/ASTESJ\_090103.pdf](https://www.astesj.com/publications/ASTESJ_090103.pdf)  
5. Bidirectional job matching through unsupervised feature learning \- Uni Siegen, truy cập vào tháng 4 23, 2026, [https://dspace.ub.uni-siegen.de/entities/publication/eb8b06ea-eb6f-49ff-8e0c-572ba846fe47](https://dspace.ub.uni-siegen.de/entities/publication/eb8b06ea-eb6f-49ff-8e0c-572ba846fe47)  
6. Signal vs. Noise: What Actually Gets You Rejected in ML Interviews, truy cập vào tháng 4 23, 2026, [https://interviewnode.com/post/signal-vs-noise-what-actually-gets-you-rejected-in-ml-interviews](https://interviewnode.com/post/signal-vs-noise-what-actually-gets-you-rejected-in-ml-interviews)  
7. Signal vs Noise in Hiring: How to Identify High-Output Talent Faster \- Bizwork, truy cập vào tháng 4 23, 2026, [https://www.bizworkhq.com/blog/identify-high-output-talent-signal-vs-noise/](https://www.bizworkhq.com/blog/identify-high-output-talent-signal-vs-noise/)  
8. Signal vs Noise in Tech Recruiting and How to Fix Your Funnel, truy cập vào tháng 4 23, 2026, [https://recruiter.daily.dev/resources/signal-vs-noise-tech-recruiting-fix-funnel/](https://recruiter.daily.dev/resources/signal-vs-noise-tech-recruiting-fix-funnel/)  
9. I Built a Job-Matching Algorithm. Now I Understand Why LinkedIn Struggles. | by Tom Ron, truy cập vào tháng 4 23, 2026, [https://pub.towardsai.net/i-built-a-job-matching-algorithm-now-i-understand-why-linkedin-struggles-dd2adb068a63](https://pub.towardsai.net/i-built-a-job-matching-algorithm-now-i-understand-why-linkedin-struggles-dd2adb068a63)  
10. AI-powered talent matching: The tech behind smarter and fairer hiring \- Eightfold AI, truy cập vào tháng 4 23, 2026, [https://eightfold.ai/engineering-blog/ai-powered-talent-matching-the-tech-behind-smarter-and-fairer-hiring/](https://eightfold.ai/engineering-blog/ai-powered-talent-matching-the-tech-behind-smarter-and-fairer-hiring/)  
11. Can AI and AI-Hybrids Detect Persuasion Skills? Salesforce Hiring with Conversational Video Interviews | Marketing Science \- PubsOnLine, truy cập vào tháng 4 23, 2026, [https://pubsonline.informs.org/doi/10.1287/mksc.2023.0149](https://pubsonline.informs.org/doi/10.1287/mksc.2023.0149)  
12. The future of hiring: Advantages of a skill-based, AI-powered, hybrid approach | Brookings, truy cập vào tháng 4 23, 2026, [https://www.brookings.edu/articles/the-future-of-hiring-advantages-of-a-skill-based-ai-powered-hybrid-approach/](https://www.brookings.edu/articles/the-future-of-hiring-advantages-of-a-skill-based-ai-powered-hybrid-approach/)  
13. Prevent overfitting and imbalanced data with Automated ML \- Azure Machine Learning, truy cập vào tháng 4 23, 2026, [https://learn.microsoft.com/en-us/azure/machine-learning/concept-manage-ml-pitfalls?view=azureml-api-2](https://learn.microsoft.com/en-us/azure/machine-learning/concept-manage-ml-pitfalls?view=azureml-api-2)  
14. Overfitting and Regularization \- cs.Princeton, truy cập vào tháng 4 23, 2026, [https://www.cs.princeton.edu/courses/archive/spring19/cos324/files/regularization.pdf](https://www.cs.princeton.edu/courses/archive/spring19/cos324/files/regularization.pdf)  
15. A Framework for Enriching Job Vacancies and Job Descriptions Through Bidirectional Matching | Request PDF \- ResearchGate, truy cập vào tháng 4 23, 2026, [https://www.researchgate.net/publication/301698487\_A\_Framework\_for\_Enriching\_Job\_Vacancies\_and\_Job\_Descriptions\_Through\_Bidirectional\_Matching](https://www.researchgate.net/publication/301698487_A_Framework_for_Enriching_Job_Vacancies_and_Job_Descriptions_Through_Bidirectional_Matching)  
16. AI Candidate Matching: A Complete Guide \- Recruiterflow Blog, truy cập vào tháng 4 23, 2026, [https://recruiterflow.com/blog/candidate-matching/](https://recruiterflow.com/blog/candidate-matching/)  
17. De-conflating Preference and Qualification: Constrained Dual-Perspective Reasoning for Job Recommendation with Large Language Models \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2602.03097v1](https://arxiv.org/html/2602.03097v1)  
18. Learning to Retrieve for Job Matching \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/pdf/2402.13435](https://arxiv.org/pdf/2402.13435)  
19. Your 2026 IT and Technology Salary Guide: Tech Trends Driving the Year's Highest-Paying Jobs | Splunk, truy cập vào tháng 4 23, 2026, [https://www.splunk.com/en\_us/blog/learn/it-salaries.html](https://www.splunk.com/en_us/blog/learn/it-salaries.html)  
20. Hybrid working outpaces pay as the top strategy companies use to compete in the race for tech talent | Onrec, truy cập vào tháng 4 23, 2026, [https://www.onrec.com/news/news-archive/hybrid-working-outpaces-pay-as-the-top-strategy-companies-use-to-compete-in-the](https://www.onrec.com/news/news-archive/hybrid-working-outpaces-pay-as-the-top-strategy-companies-use-to-compete-in-the)  
21. Comparative Evaluation of Sequential Neural Network (GRU, LSTM, Transformer) Within Siamese Networks for Enhanced Job–Candidate Matching in Applied Recruitment Systems \- MDPI, truy cập vào tháng 4 23, 2026, [https://www.mdpi.com/2076-3417/15/11/5988](https://www.mdpi.com/2076-3417/15/11/5988)  
22. We built a hybrid retrieval system combining keyword \+ semantic \+ neural reranking — here's what we learned : r/Rag \- Reddit, truy cập vào tháng 4 23, 2026, [https://www.reddit.com/r/Rag/comments/1r99uaf/we\_built\_a\_hybrid\_retrieval\_system\_combining/](https://www.reddit.com/r/Rag/comments/1r99uaf/we_built_a_hybrid_retrieval_system_combining/)  
23. Matryoshka Re-Ranker: A Flexible Re-Ranking Architecture With Configurable Depth and Width \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2501.16302v1](https://arxiv.org/html/2501.16302v1)  
24. Learning to (Retrieve and) Rank — Intuitive Overview — part III, truy cập vào tháng 4 23, 2026, [https://www.khoury.northeastern.edu/home/vip/teach/IRcourse/6\_ML/other\_notes/Learning%20to%20(Retrieve%20and)%20Rank%20%E2%80%94%20Intuitive%20Overview%20%E2%80%94%20part%20III.pdf](https://www.khoury.northeastern.edu/home/vip/teach/IRcourse/6_ML/other_notes/Learning%20to%20\(Retrieve%20and\)%20Rank%20%E2%80%94%20Intuitive%20Overview%20%E2%80%94%20part%20III.pdf)  
25. Master's Thesis, Extended Research Project Applying Learning-to-Rank to Human Resourcing's Job-Candidate Matching Problem: A, truy cập vào tháng 4 23, 2026, [https://theses.ubn.ru.nl/server/api/core/bitstreams/11ac0404-a328-4fcc-93f9-6618ae540ee6/content](https://theses.ubn.ru.nl/server/api/core/bitstreams/11ac0404-a328-4fcc-93f9-6618ae540ee6/content)  
26. Learning to rank \- Wikipedia, truy cập vào tháng 4 23, 2026, [https://en.wikipedia.org/wiki/Learning\_to\_rank](https://en.wikipedia.org/wiki/Learning_to_rank)  
27. Learning to Retrieve for Job Matching \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2402.13435v1](https://arxiv.org/html/2402.13435v1)  
28. Calibration Under Extreme Imbalance: A Multi-Cluster Benchmark for Operational Queue Delay Prediction \- TechRxiv, truy cập vào tháng 4 23, 2026, [https://www.techrxiv.org/doi/pdf/10.36227/techrxiv.177041829.96464119](https://www.techrxiv.org/doi/pdf/10.36227/techrxiv.177041829.96464119)  
29. Enhancing Search Capabilities in SQL Server and Azure SQL with Hybrid Search and RRF Re-Ranking \- Microsoft Developer Blogs, truy cập vào tháng 4 23, 2026, [https://devblogs.microsoft.com/azure-sql/enhancing-search-capabilities-in-sql-server-and-azure-sql-with-hybrid-search-and-rrf-re-ranking/](https://devblogs.microsoft.com/azure-sql/enhancing-search-capabilities-in-sql-server-and-azure-sql-with-hybrid-search-and-rrf-re-ranking/)  
30. How to Build an AI Candidate Matching Agent? \- Coresignal, truy cập vào tháng 4 23, 2026, [https://coresignal.com/blog/candidate-matching/](https://coresignal.com/blog/candidate-matching/)  
31. Hybrid search on Postgres with pgvector using vecs \- Stack Overflow, truy cập vào tháng 4 23, 2026, [https://stackoverflow.com/questions/79795559/hybrid-search-on-postgres-with-pgvector-using-vecs](https://stackoverflow.com/questions/79795559/hybrid-search-on-postgres-with-pgvector-using-vecs)  
32. What is Reciprocal Rank Fusion? \- ParadeDB, truy cập vào tháng 4 23, 2026, [https://www.paradedb.com/learn/search-concepts/reciprocal-rank-fusion](https://www.paradedb.com/learn/search-concepts/reciprocal-rank-fusion)  
33. JobMatchAI An Intelligent Job Matching Platform Using Knowledge Graphs, Semantic Search and Explainable AI Website Installation Package Demo Video \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2603.14558v2](https://arxiv.org/html/2603.14558v2)  
34. AI Job Search Optimization 2025: The Hybrid Candidate Strategy \- Stemgenic, truy cập vào tháng 4 23, 2026, [https://stemgenicglobal.com/ai-job-search-optimization-2025/](https://stemgenicglobal.com/ai-job-search-optimization-2025/)  
35. Obtaining Calibrated Probabilities with Personalized Ranking Models \- AAAI, truy cập vào tháng 4 23, 2026, [https://cdn.aaai.org/ojs/20326/20326-13-24339-1-2-20220628.pdf](https://cdn.aaai.org/ojs/20326/20326-13-24339-1-2-20220628.pdf)  
36. Mitigating Algorithmic Bias Through Probability Calibration: A Case Study on Lead Generation Data \- MDPI, truy cập vào tháng 4 23, 2026, [https://www.mdpi.com/2227-7390/13/13/2183](https://www.mdpi.com/2227-7390/13/13/2183)  
37. Indeed Engineering Blog, truy cập vào tháng 4 23, 2026, [https://engineering.indeedblog.com/blog/](https://engineering.indeedblog.com/blog/)  
38. When Your Probabilities Lie — A Hands-On Guide to Probability Calibration \- Medium, truy cập vào tháng 4 23, 2026, [https://medium.com/@iamban/why-your-probabilities-lie-a-hands-on-guide-to-probability-calibration-5bc05e4cdb9e](https://medium.com/@iamban/why-your-probabilities-lie-a-hands-on-guide-to-probability-calibration-5bc05e4cdb9e)  
39. Probability Calibration in Machine Learning: Enhancing Model Usability, truy cập vào tháng 4 23, 2026, [https://www.blog.trainindata.com/probability-calibration-in-machine-learning/](https://www.blog.trainindata.com/probability-calibration-in-machine-learning/)  
40. Imbalance: Resampling, Weighting, Calibration VS No Intervention Strategy \- Medium, truy cập vào tháng 4 23, 2026, [https://medium.com/@axegggl/imbalance-resampling-weighting-calibration-vs-no-intervention-strategy-75b4ccb4b5ef](https://medium.com/@axegggl/imbalance-resampling-weighting-calibration-vs-no-intervention-strategy-75b4ccb4b5ef)  
41. (PDF) A Hybrid Approach for Job Recommendation Systems, truy cập vào tháng 4 23, 2026, [https://www.researchgate.net/publication/385535884\_A\_Hybrid\_Approach\_for\_Job\_Recommendation\_Systems](https://www.researchgate.net/publication/385535884_A_Hybrid_Approach_for_Job_Recommendation_Systems)  
42. Traditional supervised weighting method vs. Logistic regression \- MEACSE, truy cập vào tháng 4 23, 2026, [https://meacse.org/ijcar/archives/140.pdf](https://meacse.org/ijcar/archives/140.pdf)  
43. Understanding Overfitting: Strategies and Solutions \- Lyzr, truy cập vào tháng 4 23, 2026, [https://www.lyzr.ai/glossaries/overfitting/](https://www.lyzr.ai/glossaries/overfitting/)  
44. Reduce Overfitting by calibrating machine learning models | by Carlo C. | AI monks.io, truy cập vào tháng 4 23, 2026, [https://medium.com/aimonks/reduce-overfitting-by-calibrating-machine-learning-models-bd5b655f8b87](https://medium.com/aimonks/reduce-overfitting-by-calibrating-machine-learning-models-bd5b655f8b87)  
45. \[2511.16204\] Causal Synthetic Data Generation in Recruitment \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/abs/2511.16204](https://arxiv.org/abs/2511.16204)  
46. RecruitBench: An Outcome-Grounded Benchmark for Evaluating AI Recruiting Systems \- Stanford University, truy cập vào tháng 4 23, 2026, [https://cs191w.stanford.edu/projects/Winter2026/\_Aditya\_\_\_Sood\_.pdf](https://cs191w.stanford.edu/projects/Winter2026/_Aditya___Sood_.pdf)  
47. Integrating Explainable AI (XAI) and NCA-Validated Clustering for an Interpretable Multi-Layered Recruitment Model \- MDPI, truy cập vào tháng 4 23, 2026, [https://www.mdpi.com/2673-2688/7/2/53](https://www.mdpi.com/2673-2688/7/2/53)  
48. A Hybrid Machine Learning Approach for Synthetic Data Generation with Post Hoc Calibration for Clinical Tabular Datasets \- ResearchGate, truy cập vào tháng 4 23, 2026, [https://www.researchgate.net/publication/396458382\_A\_Hybrid\_Machine\_Learning\_Approach\_for\_Synthetic\_Data\_Generation\_with\_Post\_Hoc\_Calibration\_for\_Clinical\_Tabular\_Datasets](https://www.researchgate.net/publication/396458382_A_Hybrid_Machine_Learning_Approach_for_Synthetic_Data_Generation_with_Post_Hoc_Calibration_for_Clinical_Tabular_Datasets)  
49. 8 Misconceptions About AI in Hiring That Are Costing You Talent \- iqigai, truy cập vào tháng 4 23, 2026, [https://iqigai.ai/blogs/ai-hiring-misconceptions-costing-you-talent](https://iqigai.ai/blogs/ai-hiring-misconceptions-costing-you-talent)  
50. I don't understand why people talk about synthetic data. Aren't you just looping your model's assumptions? : r/learnmachinelearning \- Reddit, truy cập vào tháng 4 23, 2026, [https://www.reddit.com/r/learnmachinelearning/comments/1k2foyt/i\_dont\_understand\_why\_people\_talk\_about\_synthetic/](https://www.reddit.com/r/learnmachinelearning/comments/1k2foyt/i_dont_understand_why_people_talk_about_synthetic/)  
51. Candidate Scoring Without the AI Gamble: Best Rule-Based Matching \- Jobful, truy cập vào tháng 4 23, 2026, [https://jobful.io/resources/post/candidate-scoring-without-the-ai-gamble](https://jobful.io/resources/post/candidate-scoring-without-the-ai-gamble)  
52. Explainable AI in Hiring: Why Transparency Matters \- ZYTHR, truy cập vào tháng 4 23, 2026, [https://zythr.com/resources/explainable-ai-in-hiring-why-transparency-matters](https://zythr.com/resources/explainable-ai-in-hiring-why-transparency-matters)  
53. Explainable AI and Human Collaboration: Enhancing Recruitment Decisions with Augmented Intelligence, truy cập vào tháng 4 23, 2026, [https://recruitmentsmart.com/blogs/explainable-ai-and-human-collaboration-enhancing-recruitment-decisions-with-augmented-intelligence](https://recruitmentsmart.com/blogs/explainable-ai-and-human-collaboration-enhancing-recruitment-decisions-with-augmented-intelligence)  
54. Explainable AI in Recruiting: Why It Matters Now \- aurio, truy cập vào tháng 4 23, 2026, [https://www.aurio.ai/articles/explainable-ai-in-recruiting-why-it-matters-now](https://www.aurio.ai/articles/explainable-ai-in-recruiting-why-it-matters-now)  
55. Learning to Rank with Linear Models \- Josh's Notes, truy cập vào tháng 4 23, 2026, [https://joshfleming.com/Machine-Learning/Learning-to-Rank-with-Linear-Models](https://joshfleming.com/Machine-Learning/Learning-to-Rank-with-Linear-Models)  
56. Explainable AI Methods: SHAP, LIME, Trees, Counterfactuals | Medium, truy cập vào tháng 4 23, 2026, [https://medium.com/@stevefab2002\_90152/not-all-explanations-are-equal-4-explainable-ai-methods-and-the-tradeoffs-researchers-keep-1ab982fb2a50](https://medium.com/@stevefab2002_90152/not-all-explanations-are-equal-4-explainable-ai-methods-and-the-tradeoffs-researchers-keep-1ab982fb2a50)  
57. A Comprehensive Guide to Explainable AI: From Classical Models to LLMs \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2412.00800v2](https://arxiv.org/html/2412.00800v2)  
58. Smart-Hiring: An Explainable end-to-end Pipeline for CV Information Extraction and Job Matching \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2511.02537v1](https://arxiv.org/html/2511.02537v1)  
59. Job Match Score | Huntr Help Center, truy cập vào tháng 4 23, 2026, [https://help.huntr.co/en/articles/12241684-job-match-score](https://help.huntr.co/en/articles/12241684-job-match-score)  
60. ShaRP: Explaining Rankings and Preferences with Shapley Values \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2401.16744v4](https://arxiv.org/html/2401.16744v4)  
61. Day6 Lecture \- Explainable AI with SHAP – Demystifying Model Predictions \- YouTube, truy cập vào tháng 4 23, 2026, [https://www.youtube.com/watch?v=cGKXwLybrGg](https://www.youtube.com/watch?v=cGKXwLybrGg)  
62. Mitigating Bias in AI Model Using eXplainable AI in Terms of Hiring Process in the Industry \- IEEE Xplore, truy cập vào tháng 4 23, 2026, [https://ieeexplore.ieee.org/iel8/6287639/10820123/11129014.pdf](https://ieeexplore.ieee.org/iel8/6287639/10820123/11129014.pdf)  
63. An introduction to explainable AI with Shapley values — SHAP latest documentation, truy cập vào tháng 4 23, 2026, [https://shap.readthedocs.io/en/latest/example\_notebooks/overviews/An%20introduction%20to%20explainable%20AI%20with%20Shapley%20values.html](https://shap.readthedocs.io/en/latest/example_notebooks/overviews/An%20introduction%20to%20explainable%20AI%20with%20Shapley%20values.html)  
64. Why SHAP Values Are Useful in Recruitment Analytics \- Resumly.ai, truy cập vào tháng 4 23, 2026, [https://www.resumly.ai/blog/why-shap-values-are-useful-in-recruitment-analytics](https://www.resumly.ai/blog/why-shap-values-are-useful-in-recruitment-analytics)  
65. Calibrated Recommendations: Survey and Future Directions \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2507.02643v1](https://arxiv.org/html/2507.02643v1)  
66. Evaluating AI Recruitment Sourcing Tools by Human Preference \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2504.02463v1](https://arxiv.org/html/2504.02463v1)  
67. Best Practices for Offline Evaluation for Top-N Recommendation: Candidate Set Sampling and Statistical Inference \- ScholarWorks, truy cập vào tháng 4 23, 2026, [https://scholarworks.boisestate.edu/cgi/viewcontent.cgi?article=3375\&context=td](https://scholarworks.boisestate.edu/cgi/viewcontent.cgi?article=3375&context=td)  
68. 10 metrics to evaluate recommender and ranking systems \- Evidently AI, truy cập vào tháng 4 23, 2026, [https://www.evidentlyai.com/ranking-metrics/evaluating-recommender-systems](https://www.evidentlyai.com/ranking-metrics/evaluating-recommender-systems)  
69. Evaluating recommendation systems (mAP, MMR, NDCG) \- Shaped.ai, truy cập vào tháng 4 23, 2026, [https://www.shaped.ai/blog/evaluating-recommendation-systems-map-mmr-ndcg](https://www.shaped.ai/blog/evaluating-recommendation-systems-map-mmr-ndcg)  
70. Mastering Mean Reciprocal Rank Metric for AI Evaluation | Galileo, truy cập vào tháng 4 23, 2026, [https://galileo.ai/blog/mrr-metric-ai-evaluation](https://galileo.ai/blog/mrr-metric-ai-evaluation)  
71. MLPlatt: Simple Calibration Framework for Ranking Models \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2601.08345v1](https://arxiv.org/html/2601.08345v1)  
72. Hybrid search with PostgreSQL and pgvector \- Jonathan Katz, truy cập vào tháng 4 23, 2026, [https://jkatz05.com/post/postgres/hybrid-search-postgres-pgvector/](https://jkatz05.com/post/postgres/hybrid-search-postgres-pgvector/)

[image1]: images/NMAIex_4/image1.png

[image2]: images/NMAIex_4/image2.png

[image3]: images/NMAIex_4/image3.png

[image4]: images/NMAIex_4/image4.png

[image5]: images/NMAIex_4/image5.png

[image6]: images/NMAIex_4/image6.png

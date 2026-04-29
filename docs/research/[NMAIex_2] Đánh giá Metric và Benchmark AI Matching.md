# **Báo cáo Nghiên cứu Kỹ thuật: Khung Đánh giá, Metric và Benchmark cho Hệ thống AI Ranking Hai Chiều trong Tuyển dụng**

Việc chuyển dịch kiến trúc hệ thống tuyển dụng sang mô hình tập trung, trong đó hạt nhân FANG đảm nhiệm toàn bộ vai trò AI Core, đánh dấu một bước ngoặt về chiến lược thiết kế nền tảng. Khi ứng dụng client (miCareer-mini) được cấu trúc lại thành một thin client và hoàn toàn nhường lại các luồng xử lý ngôn ngữ lớn (LLM), embedding, và vector search cho FANG, trọng tâm kỹ thuật của toàn bộ hệ thống lúc này phụ thuộc tuyệt đối vào chất lượng của quy trình truy xuất và xếp hạng (retrieval/ranking). Khảo sát hiện trạng cho thấy FANG đã sở hữu một nền tảng cơ sở hạ tầng vững chắc bao gồm các cơ chế ingestion (thu thập dữ liệu), parsing (phân tích cú pháp), chunking (phân mảnh văn bản), embedding (mã hóa vector), RAG query (truy vấn tăng cường sinh văn bản), quản lý chat history, model fallback và một API contract tiêu chuẩn hóa, cùng với hệ lưu trữ PostgreSQL mạnh mẽ.

Tuy nhiên, bài toán tuyển dụng không đơn thuần là một tác vụ tìm kiếm thông tin một chiều (information retrieval) như các hệ thống tìm kiếm tài liệu thông thường. Đây là một hệ thống gợi ý tương hỗ (reciprocal recommendation system), hay còn gọi là xếp hạng hai chiều (bipartite ranking), nơi mức độ phù hợp và sự hài lòng phải được đáp ứng từ cả hai phía: ứng viên tìm việc và nhà tuyển dụng tìm người.1 Việc chỉ đánh giá chất lượng dựa trên độ tương đồng ngữ nghĩa (semantic similarity) của văn bản thông qua khoảng cách vector là không đủ để phản ánh giá trị vận hành thực tế, và thường dẫn đến những sai lệch nghiêm trọng giữa kết quả thử nghiệm và mức độ hài lòng của người dùng cuối.4

Nghiên cứu này được thực hiện nhằm xác định rõ bài toán, thiết lập các nhãn (labels) chuẩn xác, phân tích nguy cơ rò rỉ dữ liệu (leakage), và đề xuất một giao thức đánh giá (evaluation protocol) toàn diện cho hai luồng ưu tiên: (1) danh sách công việc được sắp xếp theo ứng viên và (2) danh sách ứng viên được sắp xếp theo công việc. Bằng việc đi sâu vào các độ đo (metrics), khung tham chiếu (benchmarks), chiến lược mở rộng dữ liệu tổng hợp (synthetic data) và các kỹ thuật hiệu chuẩn (calibration), báo cáo cung cấp một nền tảng lý luận vững chắc để quyết định việc duy trì, tinh chỉnh hay thay đổi kiến trúc của FANG.

## **Đặc thù của Bài toán Xếp hạng Hai chiều (Bipartite Ranking) trong Tuyển dụng**

Trong các hệ thống thương mại điện tử hoặc giải trí số, quá trình gợi ý thường chỉ mang tính một chiều: người dùng chọn sản phẩm hoặc nội dung, và sản phẩm không có quyền "từ chối" người dùng.6 Ngược lại, nền tảng tuyển dụng là một hệ sinh thái hai bờ (two-sided marketplace) với các động lực, hành vi và quy tắc ra quyết định hoàn toàn khác biệt ở mỗi bên. Sự thành công của hệ thống không chỉ nằm ở việc gợi ý một ứng viên cho một vị trí, mà phụ thuộc vào "tỷ lệ khớp đôi" (mutual match rate) – tức là ứng viên đồng ý nộp đơn và nhà tuyển dụng cũng quyết định phỏng vấn hoặc tuyển dụng.3

Sự khác biệt về hành vi tiêu thụ kết quả này dẫn đến việc không thể áp dụng chung một bộ metric đơn lẻ để đo lường chất lượng cho cả hai chiều. Việc chuẩn hóa các độ đo phải được thiết kế riêng biệt để phản ánh đúng kỳ vọng của từng nhóm người dùng, đồng thời phải có cơ chế tổng hợp để đánh giá mức độ tương thích toàn cục của nền tảng.6

### **Phân rã Luồng 1: Candidate-to-Job (Gợi ý Công việc cho Ứng viên)**

Tại luồng này, hệ thống đóng vai trò như một tư vấn viên nghề nghiệp cá nhân, phân tích hồ sơ (CV) của ứng viên và gợi ý các cơ hội phù hợp nhất.8 Hành vi của ứng viên mang tính khám phá (exploratory). Một ứng viên thường sẵn sàng xem xét nhiều lựa chọn, cân nhắc các yếu tố đa chiều như mức lương, địa điểm, văn hóa công ty, và lộ trình thăng tiến trước khi đưa ra quyết định nộp đơn.

Mức độ phù hợp trong luồng này không mang tính nhị phân (chỉ có "có" hoặc "không") mà mang tính phân cấp (graded relevance).10 Một công việc có thể cực kỳ phù hợp (điểm 3), tương đối phù hợp (điểm 2), phù hợp một phần (điểm 1), hoặc hoàn toàn không phù hợp (điểm 0). Hơn nữa, danh sách trả về cần có sự đa dạng nhất định để ứng viên có thể so sánh. Nếu hệ thống trả về 10 công việc hoàn toàn giống hệt nhau từ cùng một công ty, trải nghiệm người dùng sẽ bị suy giảm nghiêm trọng dù độ tương đồng văn bản là rất cao.

### **Phân rã Luồng 2: Job-to-Candidate (Gợi ý Ứng viên cho Nhà Tuyển dụng)**

Ở luồng ngược lại, đối tượng phục vụ là các chuyên viên tuyển dụng (recruiter) hoặc giám đốc nhân sự (hiring manager). Khác với ứng viên, nhà tuyển dụng có một mục tiêu vô cùng cụ thể: tối ưu hóa thời gian sàng lọc hàng nghìn hồ sơ đổ về cho một vị trí cụ thể.12 Áp lực về thời gian (time-to-fill) và sự chú ý có giới hạn (attention span) của nhà tuyển dụng đòi hỏi hệ thống ATS phải hoạt động với độ chính xác tuyệt đối ngay tại những vị trí hiển thị đầu tiên.4

Nhà tuyển dụng không có nhu cầu "khám phá" các ứng viên "tương đối phù hợp" ở trang thứ hai hoặc thứ ba của danh sách kết quả. Họ kỳ vọng hệ thống sẽ đưa ra các ứng viên xuất sắc nhất, thỏa mãn mọi tiêu chí khắt khe (hard constraints) về kỹ năng, kinh nghiệm, và sự sẵn sàng, ngay lập tức.11 Bất kỳ một kết quả sai lệch nào xuất hiện ở top đầu đều gây ra sự thất vọng lớn và làm giảm niềm tin vào hệ thống AI, khiến họ quay trở lại với phương pháp tìm kiếm từ khóa Boolean truyền thống.15 Do đó, luồng này đòi hỏi một cơ chế trừng phạt mạnh mẽ đối với các kết quả sai (false positives) ở các vị trí xếp hạng cao.

## **Đề xuất Hệ thống Metric Đánh giá Ranking**

Dựa trên cơ sở hạ tầng embedding-based retrieval hiện tại của FANG lưu trữ trên PostgreSQL (có thể đang sử dụng pgvector hoặc một extension tương tự), chất lượng ranking ban đầu được quyết định bởi điểm tương đồng cosine (cosine similarity) hoặc tích vô hướng (dot product) giữa vector của ứng viên và vector của công việc.17 Tuy nhiên, để đánh giá hiệu suất của mô hình xếp hạng, các độ đo (metrics) cần vượt ra ngoài khoảng cách vector đơn thuần để xét đến thứ tự hiển thị (rank order), mức độ suy giảm vị trí, và độ bao phủ của kết quả.18 Việc lựa chọn sai metric sẽ dẫn đến việc tối ưu hóa một mục tiêu không mang lại giá trị kinh doanh.

### **Độ đo Chuyên biệt cho Chiều Candidate-to-Job**

Đối với luồng gợi ý công việc cho ứng viên, mục tiêu là cung cấp một danh sách đa dạng và có độ liên quan theo nhiều cấp độ.

**Độ đo Primary: Normalized Discounted Cumulative Gain (nDCG@K)** Độ đo nDCG là lựa chọn hoàn hảo và bắt buộc phải có cho chiều Candidate-to-Job. Nó giải quyết xuất sắc hai vấn đề nền tảng trong hệ thống gợi ý: nó hỗ trợ chấm điểm mức độ liên quan theo nhiều cấp độ (graded relevance) và nó áp dụng hình phạt suy giảm (discounting factor) dựa trên vị trí hiển thị.11

Nguyên lý của nDCG là các kết quả có độ liên quan cao nhất phải xuất hiện ở các vị trí đầu tiên, và giá trị của một kết quả tốt sẽ giảm dần theo hàm logarit nếu nó bị đẩy xuống dưới danh sách.21 Công thức của Discounted Cumulative Gain (DCG) tại vị trí K được biểu diễn như sau:

$$DCG@K = \sum_{i=1}^{K} \frac{2^{rel_i} - 1}{\log_2(i + 1)}$$  
Trong đó $rel_i$ là điểm đánh giá mức độ phù hợp của công việc tại vị trí i. Ví dụ, một công việc "Perfect Match" có thể được gán $rel = 3$, "Good Match" là $rel = 2$, "Fair Match" là $rel = 1$. Giá trị DCG này sau đó được chuẩn hóa bằng cách chia cho Ideal DCG (IDCG) \- là giá trị DCG đạt được nếu danh sách được sắp xếp hoàn hảo nhất có thể.22 Việc chuẩn hóa này tạo ra nDCG dao động trong khoảng từ 0 đến 1, cho phép so sánh chéo hiệu suất giữa các ứng viên có số lượng công việc phù hợp lý tưởng khác nhau trong cơ sở dữ liệu.22

**Độ đo Secondary: HitRate@K và MAP (Mean Average Precision)** HitRate@K đóng vai trò đo lường tỷ lệ những người dùng nhận được *ít nhất một* gợi ý công việc thực sự chất lượng trong top K.11 HitRate là một thước đo mang tính trực quan cao để đội ngũ phát triển sản phẩm biết được hệ thống có đang giải quyết triệt để vấn đề "khởi động lạnh" (cold start) hay không.11

Trong khi đó, MAP (Mean Average Precision) đo lường diện tích dưới đường cong Precision-Recall.10 Dù MAP là một độ đo kinh điển trong Information Retrieval, nó bị hạn chế ở chỗ chỉ xử lý được nhãn nhị phân (binary relevance) \- nghĩa là một công việc chỉ có thể được dán nhãn "phù hợp" hoặc "không phù hợp".19 Do đó, MAP chỉ nên được sử dụng như một metric phụ trợ để đánh giá năng lực bao phủ toàn bộ các công việc có thể nộp đơn, thay vì làm metric chính.

### **Độ đo Chuyên biệt cho Chiều Job-to-Candidate**

Ngược lại với ứng viên, nhà tuyển dụng có quỹ thời gian hạn hẹp. Sự khắc nghiệt của công việc sàng lọc hồ sơ đòi hỏi một bộ metric tập trung mạnh vào "phát bắn đầu tiên" (first hit).

**Độ đo Primary: Mean Reciprocal Rank (MRR)** MRR là thước đo lý tưởng nhất cho luồng Job-to-Candidate vì nó đặc biệt nhạy cảm với vị trí của kết quả đúng đầu tiên trong danh sách trả về.20 MRR không quan tâm đến việc có bao nhiêu ứng viên phù hợp trong danh sách, mà chỉ quan tâm đến việc nhà tuyển dụng phải cuộn chuột bao xa để tìm thấy ứng viên tốt đầu tiên.11

Nếu ứng viên xuất sắc nhất xuất hiện ở vị trí đầu tiên, Reciprocal Rank là 1\. Nếu xuất hiện ở vị trí thứ hai, điểm giảm mạnh xuống còn 0.5. Nếu ở vị trí thứ ba, điểm là 0.33. Quá trình này được trung bình hóa trên toàn bộ tập truy vấn công việc theo công thức:

$$MRR = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{rank_i}$$ 
Sự suy giảm tuyến tính cực gắt của MRR phản ánh đúng tâm lý thiếu kiên nhẫn của nhà tuyển dụng đối với các hệ thống ATS hiện đại.11 Nếu thuật toán embedding của FANG đẩy các ứng viên không liên quan lên top đầu, điểm MRR sẽ rớt thảm hại, phát ra tín hiệu báo động ngay lập tức cho đội ngũ kỹ sư.

**Độ đo Secondary: Precision@K và AUC (Area Under the ROC Curve)** Hỗ trợ cho MRR, Precision@K (với K nhỏ, thường là K=5 hoặc K=10) sẽ đánh giá tỷ lệ hồ sơ thực sự chất lượng trong cụm kết quả đầu tiên.10 Khác với nDCG đo lường thứ tự một cách chi tiết, Precision@K cung cấp góc nhìn nhị phân về tính hợp lệ của danh sách top đầu, giúp định lượng được tỷ lệ "tín hiệu trên nhiễu" (signal-to-noise ratio).27 AUC có thể được sử dụng để đánh giá năng lực phân loại toàn cục của mô hình (pairwise accuracy) giữa một ứng viên được nhận và một ứng viên bị loại bỏ, tuy nhiên AUC thiếu độ nhạy về mặt thứ hạng vị trí (position bias) nên không thể thay thế nDCG hay MRR.28

### **Tổng hợp Độ đo Hai chiều và Lựa chọn Tham số Top-K**

Một hệ thống tuyển dụng xuất sắc không chỉ phục vụ tốt một bên. Khái niệm Gợi ý Tương hỗ (Reciprocal Recommendation) đòi hỏi việc tổng hợp mức độ thành công của các tương tác.1 Việc lựa chọn giá trị $K$ (top-K cutoff) đóng vai trò quyết định trong việc định hình kết quả đánh giá.11 Dữ liệu và nghiên cứu cho thấy sự chú ý của con người suy giảm nghiêm trọng sau một số lượng kết quả nhất định.11

| Tham số Top-K | Ý nghĩa trong Luồng Candidate-to-Job | Ý nghĩa trong Luồng Job-to-Candidate | Đề xuất cho hệ thống FANG |
| :---- | :---- | :---- | :---- |
| **K \= 5** | Phản ánh chất lượng của các gợi ý "hàng đầu", thường xuất hiện trên trang chủ ứng dụng hoặc thông báo đẩy email. Giai đoạn gây ấn tượng mạnh nhất với ứng viên. | Mang tính sống còn. Nhà tuyển dụng kỳ vọng tìm thấy ứng viên xuất sắc ngay lập tức để tiến hành mời phỏng vấn nhanh, giảm thiểu Time-to-Hire. | Sử dụng làm ngưỡng cutoff tuyệt đối cho các metric khắt khe như Precision@5 và HitRate@5. Giúp giảm tải context đưa vào LLM nếu cần thực hiện reasoning. |
| **K \= 10** | Mức độ phổ quát cho một trang hiển thị tiêu chuẩn (pagination). Đủ không gian để ứng viên so sánh các đặc tính công việc. | Giới hạn kiên nhẫn thông thường của quy trình sàng lọc tự động (screening). Vượt quá K=10, nhà tuyển dụng có xu hướng bỏ cuộc hoặc thay đổi từ khóa. | Đặt làm tham số cốt lõi cho nDCG@10. Phản ánh đúng hành vi người dùng lướt qua màn hình đầu tiên của ứng dụng Web/Mobile. |
| **K \= 20** | Phù hợp để đánh giá độ bao phủ (Recall@20). Ứng viên đang trong giai đoạn tìm kiếm mở rộng và sẵn sàng lướt qua nhiều trang danh sách. | Thường chỉ có ý nghĩa đối với các chiến dịch tìm kiếm nguồn lực thụ động (passive sourcing) quy mô lớn hoặc khi thị trường lao động cực kỳ khan hiếm. | Chỉ dùng cho các báo cáo phân tích sâu (deep analytics) nội bộ để theo dõi độ chênh lệch của retrieval engine, không dùng làm KPI chính. |

### **Chiến lược Trung bình hóa (Averaging Strategy): Macro vs Micro**

Trong bài toán tuyển dụng, sự phân bổ dữ liệu luôn tồn tại hiện tượng mất cân bằng nghiêm trọng (extreme class imbalance).32 Có những công việc phổ thông (head entities) như "Nhân viên Bán hàng" thu hút hàng nghìn lượt ứng tuyển, trong khi các vị trí ngách chuyên sâu (tail entities) như "Kỹ sư Blockchain" chỉ có vài hồ sơ.32 Tương tự, có những ứng viên sở hữu kỹ năng đại trà và những ứng viên có bộ kỹ năng cực kỳ đặc thù. Khi tổng hợp điểm số metric cho toàn bộ hệ thống FANG, quyết định sử dụng Macro-averaging hay Micro-averaging sẽ định hình cách hệ thống được tối ưu hóa.34

**Micro-averaging** gộp tất cả các phiên bản (instances) lại với nhau và tính toán điểm số chung dựa trên tổng số True Positives, False Positives.34 Cách tiếp cận này bị chi phối mạnh mẽ bởi các đối tượng có tần suất xuất hiện cao. Nếu hệ thống FANG ưu tiên Micro-averaging, kết quả báo cáo sẽ dễ dàng trở nên "đẹp trên giấy" nhờ vào hiệu suất tốt trên tập dữ liệu khổng lồ của các công việc phổ thông. Tuy nhiên, nó sẽ hoàn toàn che đậy sự yếu kém cốt lõi của AI trong việc xếp hạng và nhận diện các vị trí cấp cao, khan hiếm hoặc các ứng viên đặc thù.34

**Macro-averaging** giải quyết triệt để vấn đề này bằng cách tính toán hiệu suất (ví dụ nDCG hoặc MRR) cho từng cá thể riêng biệt (từng công việc hoặc từng ứng viên), sau đó lấy trung bình cộng không trọng số (unweighted mean) của tất cả các điểm số này.34 Bằng cách này, một công việc ngách với 10 ứng viên có trọng số đánh giá ngang bằng hoàn toàn với một công việc đại trà có 1000 ứng viên.36

Đối với hệ thống xếp hạng tuyển dụng FANG, **Macro-averaging là phương pháp bắt buộc phải áp dụng làm tiêu chuẩn đánh giá chính thức**. Việc sử dụng Macro-averaging đảm bảo rằng mô hình embedding và retrieval không bị thiên lệch, đồng thời buộc hệ thống phải duy trì chất lượng dịch vụ (QoS) đồng đều trên toàn bộ hệ sinh thái của nền tảng, tôn trọng cả head entities và tail entities.36

## **Khung Benchmark Thực tế cho Hệ thống ATS**

Dù các chỉ số toán học có hoàn hảo đến đâu, nếu dữ liệu nền tảng (ground truth) không phản ánh đúng thực tiễn kinh doanh, hệ thống AI sẽ chỉ đang tối ưu hóa một bài toán sai lệch, hay còn gọi là hiện tượng "tối ưu hóa cục bộ" (local optima). Việc xây dựng benchmark nội bộ cho hệ thống ATS không chỉ dừng lại ở việc so khớp văn bản mà phải bao hàm được tính logic của quá trình tuyển dụng.4

### **Đánh giá và Khả năng Tái sử dụng Các Tập Dữ liệu Công khai**

Trong nghiên cứu AI tuyển dụng, việc sử dụng các bộ dữ liệu công khai mang lại lợi thế khởi động nhanh cho việc kiểm thử mô hình (bootstrap testing). Các tập dữ liệu như Kaggle Resume Dataset cung cấp dữ liệu văn bản thuần túy của hàng nghìn hồ sơ kèm theo nhãn ngành nghề, trong khi bộ dữ liệu Glassdoor Data Science cung cấp chi tiết về mô tả công việc của các vị trí yêu cầu kỹ năng cao.38

Tuy nhiên, việc phụ thuộc hoàn toàn vào các tập dữ liệu công khai cho hệ thống FANG ẩn chứa rủi ro kiến trúc nghiêm trọng. Hầu hết các bộ benchmark cộng đồng này được xây dựng dựa trên mức độ trùng khớp từ vựng (lexical overlap) hoặc độ tương đồng ngữ nghĩa nông (shallow semantic similarity) thay vì lịch sử ra quyết định thực tế của con người.4 Chúng tồn tại những giới hạn cốt lõi sau:

1. **Thiếu hụt Tín hiệu Ẩn (Implicit Signals):** Các tập dữ liệu công khai hiếm khi chứa thông tin về những yếu tố quyết định như: khoảng trống thời gian làm việc (gap years), mức độ thăng tiến liên tục, mức lương kỳ vọng, tính sẵn sàng làm việc (availability), và sự phù hợp về văn hóa.5  
2. **Thiên lệch Miền (Domain Shift):** Dữ liệu công khai thường lỗi thời so với sự thay đổi danh pháp của thị trường công nghệ. Ví dụ, một kỹ năng như "AngularJS" trong tập dữ liệu 2018 không mang cùng trọng số như "React" hay "Next.js" ở thời điểm hiện tại.16  
3. **Hạn chế Đánh giá Tương hỗ:** Các tập dữ liệu này chỉ phản ánh một chiều (thường là từ góc độ ứng viên nộp CV vào vị trí), bỏ qua hoàn toàn phản hồi từ phía nhà tuyển dụng (như quyết định phỏng vấn hay loại bỏ).40

Do đó, nếu FANG chỉ được benchmark trên các tập dữ liệu này, hệ thống sẽ trở thành một công cụ "so khớp từ khóa cao cấp" (glorified keyword matcher) thay vì một AI đánh giá nhân sự thực thụ.4 **Khuyến nghị kỹ thuật:** Tập dữ liệu công khai chỉ nên được sử dụng ở pha tiền huấn luyện (pre-training) của các mô hình ngôn ngữ hoặc để đánh giá sức mạnh thô của bộ nhúng (embedding capability) trong việc nhận diện khái niệm chéo (cross-domain semantics). Tuyệt đối không dùng chúng làm thước đo quyết định cho chất lượng ranking cuối cùng của sản phẩm.5

### **Chiến lược Xây dựng Dữ liệu ATS Tổng hợp (Synthetic Data) Quy mô Lớn**

Để vượt qua rào cản về tính bảo mật thông tin cá nhân (PII), các quy định pháp lý khắt khe, và sự khan hiếm của dữ liệu nhãn nội bộ chất lượng cao, việc sinh dữ liệu tổng hợp (synthetic data generation) ở quy mô lớn là hướng đi bắt buộc, hiện đại và bền vững nhất để xây dựng benchmark.42 Chiến lược này có thể tận dụng triệt để chính năng lực LLM và hạ tầng RAG query hiện có trong FANG, biến hệ thống thành một mô hình tự sản xuất, tự đánh giá và tự cải thiện (generate and annotate paradigm).45

Quá trình này yêu cầu một kiến trúc đường ống (pipeline architecture) tinh vi để đảm bảo dữ liệu sinh ra không phải là những đoạn văn bản ngẫu nhiên, mà phản ánh đúng sự phức tạp, các góc khuất và các biến thể của thị trường lao động.46

**Bước 1: Khởi tạo Dữ liệu Mầm (Seed Data Initialization)** Một tập dữ liệu mầm (seed dataset) nhỏ (khoảng 500 \- 1000 hồ sơ) nhưng đại diện cho các trường hợp thực tế và đã được ẩn danh hóa nghiêm ngặt (de-identified) sẽ được sử dụng làm cơ sở học tập (few-shot prompting).48

**Bước 2: Augmentation thông qua LLM** Từ tập dữ liệu mầm, phương pháp Proportional Augmentation và Templatic Augmentation sẽ được áp dụng thông qua LLM.49 FANG sẽ điều phối các pipeline tự động để tạo ra các hồ sơ ứng viên mang các kịch bản nghề nghiệp phức tạp.50 Ví dụ:

* Kịch bản 1: Ứng viên có kỹ năng cao nhưng chuyển đổi ngành nghề (Career switcher).  
* Kịch bản 2: Ứng viên có kinh nghiệm quản lý nhưng kỹ năng kỹ thuật đã cũ.  
* Kịch bản 3: Ứng viên thăng tiến cực nhanh trong thời gian ngắn (High-performer). Bằng cách tinh chỉnh các tham số temperature và top\_p của LLM, hệ thống có thể kiểm soát được mức độ đa dạng và sáng tạo của dữ liệu sinh ra, đảm bảo độ phủ rộng khắp các tình huống tuyển dụng.47

**Bước 3: Thiết lập Cổng Kiểm soát Chất lượng (Data Quality Gates)** Để dữ liệu tổng hợp đạt đủ tiêu chuẩn làm ground truth cho benchmark, sự hiện diện của các cổng kiểm soát chất lượng tự động và các cơ chế kiểm tra tính nhất quán (consistency checks) là yếu tố sống còn.51 Nếu không có các cổng này, mô hình sẽ học từ những dữ liệu "ảo giác" (hallucinated data) và dẫn đến sự sụp đổ hiệu suất (performance collapse).54

1. **Kiểm tra Nhất quán Thời gian (Temporal Consistency):** LLM thường có xu hướng tạo ra các mốc thời gian không hợp lý trong hồ sơ tổng hợp.56 Hệ thống kiểm soát cần quét toàn bộ các mốc thời gian làm việc, thời gian tốt nghiệp và các dự án để đảm bảo sự logic tuyến tính. Ví dụ: không thể có tình trạng tổng số năm kinh nghiệm ở các vị trí cộng dồn lại lớn hơn độ tuổi thực tế từ ngày tốt nghiệp, hoặc các khoảng thời gian học đại học và làm giám đốc cấp cao chồng chéo một cách phi lý.57 Việc áp dụng Temporal Consistency thông qua các quy tắc biểu thức chính quy (Regex script) và logic toán học chuỗi thời gian kết hợp với sự phản biện vòng lặp của LLM (self-reflection/debate) sẽ đảm bảo tính chân thực tuyệt đối của dữ liệu thời gian.56  
2. **Kiểm tra Tính Đồng nhất Kỹ năng \- Kinh nghiệm (Skill-Experience Alignment):** Một lỗi phổ biến của việc sinh CV giả là ứng viên liệt kê một danh sách dài các công nghệ tân tiến (hard skills) ở phần kỹ năng, nhưng trong phần mô tả kinh nghiệm làm việc lại hoàn toàn không có bối cảnh áp dụng các kỹ năng đó.58 Các bộ xác thực tự động (automated validators) được tích hợp trong pipeline phải thực hiện trích xuất thực thể (NER) và phân tích phụ thuộc ngữ pháp (dependency parsing) để đảm bảo rằng các kỹ năng cốt lõi luôn xuất hiện kèm theo các động từ hành động mạnh (action verbs) mang tính định lượng trong bối cảnh công việc cụ thể.58 Hệ thống sẽ tự động hạ điểm hoặc loại bỏ các hồ sơ vi phạm quy luật đối xứng này, đảm bảo benchmark chỉ chứa các hồ sơ có chất lượng cấu trúc cao.53  
3. **Cổng Bảo mật và Chống Rò rỉ Dữ liệu (Privacy & Leakage Gates):** Trước khi đưa vào làm ground truth cho benchmark nội bộ, toàn bộ tập dữ liệu tổng hợp phải đi qua hệ thống đánh giá nguy cơ rò rỉ thông tin cá nhân (leakage risk assessments).61 FANG cần thực hiện các bài test tương đồng (similarity checks) giữa dòng dữ liệu vừa sinh ra và cơ sở dữ liệu thật ban đầu để đảm bảo không có bản ghi nào sao chép quá đà định dạng hoặc nội dung của bản ghi gốc. Điều này ngăn chặn hoàn toàn nguy cơ tái định danh (membership inference risk) và đảm bảo hệ thống tuân thủ các tiêu chuẩn bảo mật dữ liệu doanh nghiệp.61

## **Hiệu chuẩn Điểm số (Score Calibration) và Hybrid Feature Engineering**

Sau khi đã có bộ metric vững chắc và framework benchmark chuẩn xác, nhiệm vụ tiếp theo là đánh giá baseline truy xuất hiện tại của FANG. Hiện nay, FANG đang sử dụng embedding-based retrieval kết hợp lưu trữ PostgreSQL. Điều này đồng nghĩa với việc điểm số xếp hạng thô (raw score) chủ yếu dựa trên khoảng cách vector, điển hình là Cosine Similarity hay Inner Product.5

Điểm số Cosine Similarity có bản chất toán học nằm trong khoảng từ \-1 đến 1 (hoặc 0 đến 1 nếu dùng vector không âm). Dù cực kỳ hữu ích trong việc phân loại thứ tự ưu tiên (người có điểm 0.9 thì liên quan hơn người có điểm 0.7), điểm số này lại **hoàn toàn vô nghĩa dưới góc độ diễn giải xác suất thực tế**.63 Ví dụ, một mức điểm Cosine Similarity là 0.85 không đồng nghĩa với việc ứng viên có 85% cơ hội trúng tuyển hay độ tự tin của mô hình là 85%. Việc sử dụng điểm cosine trực tiếp làm ngưỡng cắt (thresholding) hoặc đẩy thẳng ra API contract cho client xử lý sẽ gây ra sự thiếu ổn định nghiêm trọng, bởi vì phân phối điểm số của các vị trí công việc khác nhau là hoàn toàn khác biệt.63

### **Giải pháp Lớp Hiệu chuẩn Điểm số (Calibration Layer)**

Để biến kết quả xếp hạng từ một danh sách điểm số vô tri thành một tín hiệu định lượng có ý nghĩa vận hành (ví dụ: "hệ thống tự tin 90% rằng ứng viên này sẽ vượt qua vòng lọc hồ sơ"), việc tích hợp một lớp hiệu chuẩn điểm số (Calibration layer) vào ngay sau quy trình retrieval của FANG là thao tác kỹ thuật có giá trị ROI (Return on Investment) cực cao và chi phí vận hành thấp.64

Lớp hiệu chuẩn có nhiệm vụ biến đổi (transform) không tuyến tính điểm số Cosine thô thành một phân phối xác suất mang tính dự báo thực tế, tiệm cận với xác suất trúng tuyển  ($P(Hire|CV, Job)$). Hai kỹ thuật toán học hàng đầu được xem xét trong báo cáo này là Platt Scaling và Isotonic Regression.66

| Tiêu chí | Platt Scaling | Isotonic Regression | Phân tích Mức độ Phù hợp với FANG |
| :---- | :---- | :---- | :---- |
| **Bản chất Toán học** | Huấn luyện một mô hình Hồi quy Logistic trên điểm số thô, biến đổi kết quả theo hàm Sigmoid chuẩn.68 Công thức: $P = \frac{1}{1 + \exp(A \cdot f + B)}$ | Hồi quy phi tham số (non-parametric), thiết lập một hàm bậc thang để sửa chữa bất kỳ biến dạng đơn điệu nào (monotonic distortion).67 | Cả hai đều biến đổi điểm số về dải $$ chuẩn xác suất. |
| **Yêu cầu Khối lượng Dữ liệu** | Hoạt động cực kỳ ổn định ngay cả khi dữ liệu huấn luyện (cross-validation) nhỏ gọn.66 | Đòi hỏi một lượng lớn dữ liệu phân phối đều để xác định các điểm ngắt của hàm bậc thang một cách chính xác.66 | FANG hiện đang ở giai đoạn mở rộng dữ liệu, số lượng ground truth chưa thể đạt mức khổng lồ ngay lập tức. |
| **Nguy cơ Quá khớp (Overfitting)** | Rất thấp, cấu trúc hàm tham số có tính tổng quát hóa (generalization) cao đối với các điểm dữ liệu mới.67 | Rất cao nếu dữ liệu có nhiều nhiễu, phân phối lệch, hoặc đối với các truy vấn hiếm (tail queries).66 | Isotonic Regression có nguy cơ phá vỡ hệ thống nếu áp dụng cho các tin tuyển dụng ngách có ít ứng viên. |

**Quyết định Kỹ thuật:** Dựa trên bối cảnh hiện tại của FANG, **Platt Scaling** là kỹ thuật được đề xuất ưu tiên áp dụng ngay lập tức. Tính ổn định, khả năng kháng nhiễu và khả năng tính toán gọn nhẹ của hàm Sigmoid cho phép nó được tích hợp thẳng vào luồng xử lý PostgreSQL/API contract hiện có mà gần như không làm tăng thêm độ trễ (latency) của hệ thống. Khi quy mô dữ liệu lịch sử phản hồi tương tác (click, reject, hire) đạt đến ngưỡng đủ lớn trong tương lai, các phương pháp như Isotonic Regression hoặc SoftmaxCorr 69 có thể được nghiên cứu thử nghiệm trên các cụm dữ liệu phân tách (A/B split) để tối ưu hóa thêm.67

### **Hybrid Feature Engineering: Kết hợp Tín hiệu Cứng và Mềm**

Embeddings và Cosine Similarity rất xuất sắc trong việc nắm bắt "tín hiệu mềm" (soft signals) – tức là ý nghĩa ngữ nghĩa, sự tương đồng về bối cảnh kinh nghiệm.41 Tuy nhiên, trong môi trường tuyển dụng thực tế, quyết định thuê người phụ thuộc rất nhiều vào các "tín hiệu cứng" (hard constraints) – là những yếu tố định dạng bảng (tabular data) không thể hiện qua ngữ nghĩa.16

Ví dụ, một ứng viên có độ tương đồng ngữ nghĩa cực cao (Cosine score \= 0.95) nhưng đòi hỏi mức lương vượt quá 50% ngân sách của công ty, hoặc vị trí địa lý cách nơi làm việc bắt buộc 2000 km mà không chấp nhận làm việc từ xa, thì giá trị thực tế của ứng viên đó đối với nhà tuyển dụng là bằng 0\.5 Nếu hệ thống chỉ xếp hạng dựa trên AI embedding, nó sẽ liên tục đưa những ứng viên này lên đầu, gây ức chế cho người dùng.

Do đó, FANG cần triển khai kiến trúc **Hybrid Feature Engineering**. Quá trình này diễn ra như sau:

1. **Giai đoạn Truy xuất (Retrieval):** Sử dụng PostgreSQL pgvector để thực hiện truy vấn khoảng cách gần nhất (KNN/ANN search) nhằm lấy ra Top 100 ứng viên có điểm tương đồng ngữ nghĩa cao nhất.  
2. **Giai đoạn Tính điểm Tabular:** Tính toán các khoảng cách tuyến tính dựa trên dữ liệu cấu trúc: độ chênh lệch mức lương (Salary delta), khoảng cách địa lý (Location geofencing), số năm kinh nghiệm tối thiểu (Experience constraints), và tính khả dụng (Availability/Notice period).5  
3. **Giai đoạn Reranking (Xếp hạng lại):** Sử dụng một mô hình trọng số hỗn hợp (Linear Weighted Model hoặc XGBoost hạng nhẹ) để kết hợp điểm Cosine đã được hiệu chuẩn (Calibrated Score) với các điểm số Tabular kể trên để tính ra thứ hạng cuối cùng.63

Sự kết hợp này là điểm cốt lõi để thu hẹp khoảng cách giữa sự hoàn hảo về "chuẩn học thuật" (Academic accuracy) của thuật toán vector và tính "phù hợp sản phẩm" (Product market fit) của bài toán kinh doanh.19

## **Proxy Fairness Metrics (Chỉ số Công bằng AI)**

Tuyển dụng là một quy trình chịu sự giám sát pháp lý và đạo đức mạnh mẽ nhất trong ứng dụng trí tuệ nhân tạo. Việc sử dụng AI ranking tiềm ẩn rủi ro rất lớn trong việc khuếch đại các thiên kiến (biases) có sẵn trong tập dữ liệu lịch sử.70 Việc chỉ tối ưu hóa một cách mù quáng các độ đo hiệu suất như nDCG hay MRR có thể vô tình dẫn đến hiện tượng ưu tiên các nhóm đa số (majority groups) và loại bỏ hoàn toàn các nhóm thiểu số có năng lực nhưng sở hữu lối hành văn CV khác biệt.33

Để ngăn chặn hệ thống bị đánh giá là "thiếu công bằng" hoặc vi phạm các tiêu chuẩn đạo đức AI (như Đạo luật AI của EU) 40, các Proxy Fairness Metrics cần được tính toán song song với bộ metric chất lượng.33

1. **Demographic Parity (Đồng nhất Nhân khẩu học / Statistical Parity):** Độ đo này đánh giá độc lập mô hình đối với các thuộc tính nhạy cảm (như giới tính, sắc tộc, hoặc độ tuổi ẩn).74 Nó yêu cầu tỷ lệ ứng viên được chọn vào danh sách xếp hạng cao (Top-K) phải tỷ lệ thuận với sự hiện diện của họ trong quần thể.76 Nếu tập hồ sơ nộp vào có 40% là nữ giới, thì trong danh sách Top 10 trả về ở nhiều đợt tìm kiếm tổng hợp, tỷ lệ hồ sơ đại diện cho nữ giới cũng nên dao động xấp xỉ mức 40%. Sự suy giảm mạnh mẽ của chỉ số này là một cờ đỏ (red flag) cho thấy mô hình embedding đang "học" cách thiên vị một cấu trúc từ vựng cụ thể nào đó mang định kiến giới.76  
2. **Equal Opportunity (Bình đẳng Cơ hội):** Độ đo này tinh tế và sát thực tế hơn Demographic Parity ở chỗ nó chỉ xét trên nhóm ứng viên *thực sự đủ tiêu chuẩn chuyên môn* cho vị trí.74 Equal Opportunity đo lường và so sánh tỷ lệ True Positive Rate giữa các nhóm nhân khẩu học khác nhau.33 Việc giám sát độ đo này giúp đảm bảo rằng FANG không đánh rớt một nhân tài xuất sắc chỉ vì mô hình không quen thuộc với định dạng hồ sơ của một nền giáo dục phi truyền thống.  
3. **Predictive Rate Parity:** Đảm bảo rằng độ chính xác của các dự đoán trúng tuyển do hệ thống đưa ra là đồng đều cho mọi nhóm người dùng.71 Nếu điểm số hiệu chuẩn (calibrated score) là 0.8 cho ứng viên nam và ứng viên nữ, thì xác suất họ được gọi phỏng vấn trên thực tế phải tương đương nhau.75

**Đề xuất tích hợp:** Các fairness metric này không nhất thiết phải tham gia trực tiếp vào việc tính toán Loss Function trong giai đoạn huấn luyện ban đầu để tránh sự phức tạp hóa kiến trúc quá mức.77 Tuy nhiên, chúng **bắt buộc** phải được thiết lập như một lớp giám sát ngoại tuyến (offline monitoring dashboard). Trước khi tung ra bất kỳ bản cập nhật trọng số embedding nào cho FANG, hệ thống phải chạy qua cổng kiểm định Fairness để tạo ra cơ sở bằng chứng về sự minh bạch, giảm thiểu rủi ro pháp lý và trách nhiệm giải trình của hệ thống ATS.60

## **Đánh giá Ngoại tuyến (Offline Evaluation) và Tính Thực tế Kinh doanh**

Khả năng đánh giá chính xác chất lượng mô hình mà không cần trực tiếp can thiệp vào môi trường sản xuất (online A/B testing) là một năng lực mang tính sống còn đối với một lõi AI trung tâm như FANG. Phương pháp Đánh giá Ngoại tuyến (Offline Evaluation) cho phép đội ngũ kỹ sư kiểm thử hàng ngàn kịch bản, thay đổi tham số thuật toán, và kiểm định các trọng số hybrid một cách nhanh chóng, an toàn và hoàn toàn tự động.79

Tuy nhiên, giới hạn nguy hiểm nhất của Offline Evaluation truyền thống là nó phụ thuộc vào các log tương tác lịch sử bị thiên lệch (logged bandit feedback).80 Lịch sử tuyển dụng chỉ ghi nhận những tương tác của nhà tuyển dụng (như nhấp chuột, từ chối, mời phỏng vấn) trên những ứng viên mà hệ thống cũ *đã* đề xuất. Điều này dẫn đến một điểm mù khổng lồ đối với những ứng viên xuất sắc nhưng chưa từng được hệ thống cũ đưa lên màn hình hiển thị. Đánh giá một mô hình mới dựa trên dữ liệu bị che khuất này sẽ tạo ra ảo giác về hiệu suất.

### **Giao thức Đánh giá Off-Policy Evaluation (OPE)**

Để giải quyết triệt để vấn đề thiên lệch dữ liệu lịch sử, quy trình đánh giá offline của FANG cần ứng dụng khuôn khổ Off-Policy Evaluation (OPE).80 OPE tiếp cận bài toán xếp hạng dưới góc nhìn của học tăng cường (reinforcement learning) và lý thuyết Multi-armed Bandit.80

Thay vì chỉ so sánh nhãn trực tiếp, OPE sử dụng các phương pháp hiệu chỉnh tỷ trọng xác suất nghịch đảo (Inverse Probability Weighting \- IPW). Nó tính toán xác suất hiển thị của một hồ sơ theo "chính sách cũ" (logging policy) và so sánh với xác suất được hiển thị theo "chính sách mới" (target policy \- mô hình FANG đang thử nghiệm).80 Bằng cách gán trọng số bù trừ cho các trường hợp hiếm gặp, OPE cho phép dự đoán chính xác sự thay đổi về hành vi của người dùng và hiệu suất của thuật toán ranking mới từ các bản log ngoại tuyến.81 Khung đánh giá này thu hẹp đáng kể khoảng cách giữa kết quả đo lường trong phòng thí nghiệm (offline benchmark) và kết quả thực chiến (online A/B testing), giúp đội ngũ tiết kiệm hàng tháng trời thử nghiệm sai lầm.80

### **Tương quan với Giá trị Kinh doanh (Business Metrics)**

Cuối cùng, mọi thay đổi tinh xảo về kỹ thuật, các chỉ số điểm nDCG, MRR, hay các hàm hiệu chuẩn phức tạp đều trở nên vô nghĩa nếu chúng không tạo ra sự cộng hưởng với các giá trị cốt lõi của bài toán vận hành nhân sự (Business/HR Metrics). Một hệ thống AI có nDCG cao nhưng lại cung cấp những ứng viên ảo, ứng viên không có nhu cầu tìm việc, hoặc những ứng viên từ chối lời mời phỏng vấn sẽ phá hủy hoàn toàn trải nghiệm người dùng.82

Do đó, các metric kỹ thuật trung gian phải được theo dõi sự tương quan biến thiên với các chỉ số kinh doanh cốt lõi sau:

* **Time to Fill (Thời gian Lấp đầy) & Time to Hire (Thời gian Tuyển dụng):** Đây là thước đo sống còn về mặt tốc độ. Nó đo lường số ngày từ lúc vị trí được mở đến lúc ứng viên ký hợp đồng.14 Nếu MRR của hệ thống tăng (ứng viên tốt nằm ở top đầu) nhưng Time to Hire không suy giảm, hệ thống có thể đang gặp lỗi nghiêm trọng về "độ tươi" (freshness) của dữ liệu 85 – tức là gợi ý những người có kỹ năng tốt nhưng đã có việc làm ổn định và không muốn nhảy việc.  
* **Quality of Hire (Chất lượng Tuyển dụng) & First-year Attrition (Tỷ lệ Nghỉ việc Năm đầu):** Đây là metric mang tính chiến lược dài hạn, phản ánh giá trị thực sự của ứng viên đối với tổ chức sau khi họ nhận việc.14 Dữ liệu hiệu suất làm việc của nhân viên (Performance appraisals) phải được phản hồi ngược lại về FANG theo cơ chế vòng lặp đóng (closed-loop feedback).88 Dữ liệu này sẽ là nguồn ground truth chất lượng cao nhất để tinh chỉnh các trọng số hybrid của thuật toán ranking.  
* **Hiring Manager Satisfaction (Độ hài lòng của Quản lý Tuyển dụng):** Các chỉ số đo lường định tính này thường có tương quan mạnh mẽ nhất với tính minh bạch, độ trơn tru và logic của quá trình cung cấp chứng cứ quyết định (explainable AI).84 Nhà tuyển dụng sẽ hài lòng hơn khi hệ thống không chỉ đưa ra một con số xác suất, mà còn bôi đậm các kỹ năng tương khớp và giải thích lý do (rationale) tại sao ứng viên này được xếp hạng cao.13 Việc FANG kết hợp module lý luận (reasoning module) trong lộ trình tương lai với kết quả ranking đã hiệu chuẩn sẽ là đòn bẩy thúc đẩy chỉ số này lên mức tối đa.

## **Quyết định Kiến trúc và Khuyến nghị Triển khai Kỹ thuật**

Nghiên cứu chi tiết về các độ đo, khung đánh giá, và dữ liệu cho hệ thống AI Ranking FANG trong bài toán tuyển dụng đã cung cấp các cơ sở dữ liệu vững chắc để đưa ra các quyết định kiến trúc. Dựa trên bộ nguyên tắc đã đề ra ban đầu, lộ trình ưu tiên được phân định rõ ràng nhằm tối đa hóa hiệu quả đầu tư và tận dụng nền tảng kỹ thuật hiện tại.

**Nguyên tắc tối thượng:** Tuyệt đối **không** cần phải vội vã thay thế kiến trúc mã hóa vector (embedding) và truy xuất (retrieval) hiện tại của FANG. Sự kết hợp giữa hạ tầng vector search trên PostgreSQL cùng với các pipeline chunking và parsing hiện hành hoàn toàn đủ sức chứa để cung cấp các tín hiệu văn bản chất lượng cao. Việc thay đổi sang các mô hình nhúng mới khổng lồ hơn sẽ làm tăng vọt chi phí inference mà lợi ích mang lại chưa được chứng minh là vượt bậc so với việc xây dựng một hệ thống đánh giá và tinh chỉnh đúng đắn.

**Phân định các Thành phần Kiến trúc:**

1. **Thứ đã có sẵn trong FANG (Duy trì và Tối ưu hóa):**  
   * Hệ thống thu thập (Ingestion), phân tích cú pháp (Parsing), và phân mảnh (Chunking).  
   * Mô hình nhúng hiện tại (Current Embedding Model) cung cấp điểm số Cosine Similarity cơ bản.  
   * Hệ lưu trữ cơ sở dữ liệu và tìm kiếm vector trên PostgreSQL.  
   * API Contract tiêu chuẩn giao tiếp với miCareer-mini.  
2. **Thứ có thể Tái sử dụng (Chuyển đổi Mục đích):**  
   * Khung hạ tầng truy vấn RAG (RAG query infrastructure): Thay vì chỉ phục vụ luồng Chatbot, năng lực xử lý LLM mạnh mẽ này sẽ được điều hướng để vận hành các đường ống sinh dữ liệu tổng hợp (Synthetic Data Generation) quy mô lớn ở chế độ batch processing. Sử dụng chính mô hình ngôn ngữ nội bộ để xây dựng bộ benchmark giả lập là giải pháp kinh tế và bảo mật nhất.43  
3. **Thứ cần Bổ sung mới (Xếp theo thứ tự ưu tiên bắt buộc):**  
   * **Ưu tiên 1: Lõi Đo lường Metric (Core Metric Engine).** Xây dựng ngay hệ thống giám sát và báo cáo trực tiếp tích hợp độ đo **nDCG@10** và **HitRate@5** làm tiêu chuẩn vàng cho luồng đánh giá phía Ứng viên (Candidate-to-Job). Song song đó, thiết lập đo lường **MRR** và **Precision@5** cho sự khắt khe của luồng Nhà tuyển dụng (Job-to-Candidate). Quan trọng nhất, toàn bộ hệ thống tính toán trung bình phải được chuyển đổi sang chế độ **Macro-averaging** để đảm bảo sự công bằng cho các vị trí công việc ngách và các ứng viên có kỹ năng đặc thù.  
   * **Ưu tiên 2: Lớp Hiệu chuẩn và Hybrid Feature Engineering.** Không đẩy trực tiếp điểm Cosine ra API. Bổ sung ngay một module trung gian sử dụng thuật toán **Platt Scaling** (Hồi quy Logistic) ngay sau khâu vector search trên PostgreSQL. Thao tác này dịch mã điểm số khoảng cách trừu tượng thành xác suất phần trăm ($P \\in $). Sau đó, kết hợp điểm xác suất này với các biến số Tabular cứng (Khoảng cách địa lý, Ngân sách lương, Số năm kinh nghiệm) để tạo ra bảng xếp hạng cuối cùng (Reranking).  
   * **Ưu tiên 3: Hàng rào Cổng Chất lượng cho Dữ liệu Tổng hợp (Synthetic Data Quality Gates).** Để việc sinh dữ liệu bằng LLM có ý nghĩa, phải lập trình các kịch bản kiểm tra (Consistency Checks) gắt gao. Xây dựng các module kiểm chứng logic tuyến tính về mặt thời gian (Temporal Consistency) tránh ảo giác năm kinh nghiệm, và module phân tích phụ thuộc ngữ pháp để đối chiếu tính đồng nhất giữa danh sách kỹ năng khai báo và phần mô tả thực thi (Skill-Experience Alignment).  
   * **Ưu tiên 4: Khung Đánh giá OPE và Proxy Fairness.** Trước khi bước vào giai đoạn thử nghiệm A/B trên tập khách hàng thật, FANG phải sở hữu năng lực kiểm thử mô phỏng Off-Policy Evaluation (OPE) kết hợp với các phép hiệu chỉnh xu hướng (Inverse Probability Weighting). Ngoài ra, các chỉ số Proxy Fairness Metrics như Demographic Parity phải được thiết lập thành một dashboard bắt buộc thông qua các buổi họp duyệt mô hình (model governance) để đảm bảo không có rủi ro thiên vị diện rộng trên nền tảng.

Bằng việc bám sát lộ trình và triển khai một cách có hệ thống các khung đo lường, hiệu chuẩn, và đánh giá ngoại tuyến nêu trên, hệ thống FANG sẽ không chỉ giải quyết triệt để bài toán khó nhất của việc xếp hạng tương hỗ trong tuyển dụng, mà còn tạo ra một cơ chế tự học, tự cải thiện an toàn, minh bạch. Đây là nền tảng tối thượng để biến FANG từ một công cụ tìm kiếm văn bản đơn thuần trở thành một AI Core nhân sự thực thụ, đáp ứng trọn vẹn cả tiêu chuẩn khắt khe về học thuật và giá trị thực tiễn khổng lồ của sản phẩm thương mại.

#### **Nguồn trích dẫn**

1. Reciprocal Recommendation for Job Matching with Bidirectional Feedback | Request PDF, truy cập vào tháng 4 23, 2026, [https://www.researchgate.net/publication/261434696\_Reciprocal\_Recommendation\_for\_Job\_Matching\_with\_Bidirectional\_Feedback](https://www.researchgate.net/publication/261434696_Reciprocal_Recommendation_for_Job_Matching_with_Bidirectional_Feedback)  
2. A Study of Reciprocal Job Recommendation for College Graduates Integrating Semantic Keyword Matching and Social Networking \- MDPI, truy cập vào tháng 4 23, 2026, [https://www.mdpi.com/2076-3417/13/22/12305](https://www.mdpi.com/2076-3417/13/22/12305)  
3. Revisiting Reciprocal Recommender Systems: Metrics, Formulation, and Method \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2408.09748v1](https://arxiv.org/html/2408.09748v1)  
4. An AI based talent acquisition and benchmarking for job \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/pdf/2009.09088](https://arxiv.org/pdf/2009.09088)  
5. AI-driven semantic similarity-based job matching framework for ..., truy cập vào tháng 4 23, 2026, [https://bura.brunel.ac.uk/bitstream/2438/32657/1/FullText.pdf](https://bura.brunel.ac.uk/bitstream/2438/32657/1/FullText.pdf)  
6. Revisiting Reciprocal Recommender Systems: Metrics, Formulation, and Method, truy cập vào tháng 4 23, 2026, [http://ai.ruc.edu.cn/uploads/20240924/be36f10fce04e3f88152637c591430b0.pdf](http://ai.ruc.edu.cn/uploads/20240924/be36f10fce04e3f88152637c591430b0.pdf)  
7. \[2312.16015\] A Comprehensive Survey of Evaluation Techniques for Recommendation Systems \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/abs/2312.16015](https://arxiv.org/abs/2312.16015)  
8. AutoScreen-FW: An LLM-based Framework for Resume Screening \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2603.18390](https://arxiv.org/html/2603.18390)  
9. ConFit: Improving Resume-Job Matching using Data Augmentation and Contrastive Learning \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2401.16349v1](https://arxiv.org/html/2401.16349v1)  
10. Introduction to \- Information Retrieval \- Stanford University, truy cập vào tháng 4 23, 2026, [https://web.stanford.edu/class/cs276/handouts/EvaluationNew-handout-1-per.pdf](https://web.stanford.edu/class/cs276/handouts/EvaluationNew-handout-1-per.pdf)  
11. 10 metrics to evaluate recommender and ranking systems \- Evidently AI, truy cập vào tháng 4 23, 2026, [https://www.evidentlyai.com/ranking-metrics/evaluating-recommender-systems](https://www.evidentlyai.com/ranking-metrics/evaluating-recommender-systems)  
12. LangGraph Agentic AI: Automating Resume Skill Matching and Screening \- Medium, truy cập vào tháng 4 23, 2026, [https://medium.com/@jhahimanshu3636/langgraph-agentic-ai-automating-resume-skill-matching-and-screening-f9878fa99865](https://medium.com/@jhahimanshu3636/langgraph-agentic-ai-automating-resume-skill-matching-and-screening-f9878fa99865)  
13. AI-Driven Decision-Making System for Hiring Process \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2512.20652v1](https://arxiv.org/html/2512.20652v1)  
14. Recruiting benchmarks: 14 metrics every talent team should track | Metaview Blog, truy cập vào tháng 4 23, 2026, [https://www.metaview.ai/resources/blog/recruiting-benchmarks](https://www.metaview.ai/resources/blog/recruiting-benchmarks)  
15. Candidate Matching: Step-by-Step Guide (2026) \- Juicebox, truy cập vào tháng 4 23, 2026, [https://juicebox.ai/blog/candidate-matching](https://juicebox.ai/blog/candidate-matching)  
16. Getting The Most From AI Fit Scores, Candidate Discovery & More \- Phenom, truy cập vào tháng 4 23, 2026, [https://www.phenom.com/blog/how-to-get-the-most-from-ai-fit-scores-candidate-discovery](https://www.phenom.com/blog/how-to-get-the-most-from-ai-fit-scores-candidate-discovery)  
17. Zero-Shot Recommendation AI Models for Efficient Job–Candidate Matching in Recruitment Process \- MDPI, truy cập vào tháng 4 23, 2026, [https://www.mdpi.com/2076-3417/14/6/2601](https://www.mdpi.com/2076-3417/14/6/2601)  
18. Ranking Evaluation Metrics for Recommender Systems | by Benjamin Wang \- Medium, truy cập vào tháng 4 23, 2026, [https://medium.com/data-science/ranking-evaluation-metrics-for-recommender-systems-263d0a66ef54](https://medium.com/data-science/ranking-evaluation-metrics-for-recommender-systems-263d0a66ef54)  
19. Comprehensive Guide to Ranking Evaluation Metrics | Towards Data Science, truy cập vào tháng 4 23, 2026, [https://towardsdatascience.com/comprehensive-guide-to-ranking-evaluation-metrics-7d10382c1025/](https://towardsdatascience.com/comprehensive-guide-to-ranking-evaluation-metrics-7d10382c1025/)  
20. Normalized Discounted Cumulative Gain (NDCG) explained \- Evidently AI, truy cập vào tháng 4 23, 2026, [https://www.evidentlyai.com/ranking-metrics/ndcg-metric](https://www.evidentlyai.com/ranking-metrics/ndcg-metric)  
21. Understanding NDCG as a Metric for your Recommendation System | by Sumant Hegde, truy cập vào tháng 4 23, 2026, [https://medium.com/@readsumant/understanding-ndcg-as-a-metric-for-your-recomendation-system-5cd012fb3397](https://medium.com/@readsumant/understanding-ndcg-as-a-metric-for-your-recomendation-system-5cd012fb3397)  
22. Evaluating recommendation systems (mAP, MMR, NDCG) \- Shaped.ai, truy cập vào tháng 4 23, 2026, [https://www.shaped.ai/blog/evaluating-recommendation-systems-map-mmr-ndcg](https://www.shaped.ai/blog/evaluating-recommendation-systems-map-mmr-ndcg)  
23. Recommendations system advice: candidate generation vs ranking : r/MLQuestions \- Reddit, truy cập vào tháng 4 23, 2026, [https://www.reddit.com/r/MLQuestions/comments/1mu4eic/recommendations\_system\_advice\_candidate/](https://www.reddit.com/r/MLQuestions/comments/1mu4eic/recommendations_system_advice_candidate/)  
24. Mean Reciprocal Rank (MRR) explained \- Evidently AI, truy cập vào tháng 4 23, 2026, [https://www.evidentlyai.com/ranking-metrics/mean-reciprocal-rank-mrr](https://www.evidentlyai.com/ranking-metrics/mean-reciprocal-rank-mrr)  
25. Mean reciprocal rank \- Wikipedia, truy cập vào tháng 4 23, 2026, [https://en.wikipedia.org/wiki/Mean\_reciprocal\_rank](https://en.wikipedia.org/wiki/Mean_reciprocal_rank)  
26. Matching, Re-ranking and Scoring: Learning Textual Similarity by Incorporating Dependency Graph Alignment and Coverage Features \- Universität Hamburg, truy cập vào tháng 4 23, 2026, [https://www.inf.uni-hamburg.de/en/inst/ab/lt/publications/2017-kohail-biemann-cicling.pdf](https://www.inf.uni-hamburg.de/en/inst/ab/lt/publications/2017-kohail-biemann-cicling.pdf)  
27. A Comprehensive Survey of Evaluation Techniques for Recommendation Systems \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2312.16015v2](https://arxiv.org/html/2312.16015v2)  
28. Temporal Flattening in LLM-Generated Text: Comparing Human and LLM Writing Trajectories \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2604.12097v1](https://arxiv.org/html/2604.12097v1)  
29. Reciprocal recommendation for job matching with bidirectional feedback \- Kyushu University, truy cập vào tháng 4 23, 2026, [https://kyushu-u.elsevierpure.com/en/publications/reciprocal-recommendation-for-job-matching-with-bidirectional-fee](https://kyushu-u.elsevierpure.com/en/publications/reciprocal-recommendation-for-job-matching-with-bidirectional-fee)  
30. \[2508.05673\] Breaking the Top-$K$ Barrier: Advancing Top-$K$ Ranking Metrics Optimization in Recommender Systems \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/abs/2508.05673](https://arxiv.org/abs/2508.05673)  
31. Towards Optimizing Top-$K$ Ranking Metrics in Recommender Systems \- OpenReview, truy cập vào tháng 4 23, 2026, [https://openreview.net/forum?id=bHNVmLDtFo](https://openreview.net/forum?id=bHNVmLDtFo)  
32. What is micro and macro averaging? \- Kaggle, truy cập vào tháng 4 23, 2026, [https://www.kaggle.com/discussions/questions-and-answers/478940](https://www.kaggle.com/discussions/questions-and-answers/478940)  
33. Towards AI-Based Matching Processes Mitigating Human Biases in Candidate Selection \- DiVA portal, truy cập vào tháng 4 23, 2026, [https://www.diva-portal.org/smash/get/diva2:2006805/FULLTEXT01.pdf](https://www.diva-portal.org/smash/get/diva2:2006805/FULLTEXT01.pdf)  
34. Accuracy, precision, and recall in multi-class classification \- Evidently AI, truy cập vào tháng 4 23, 2026, [https://www.evidentlyai.com/classification-metrics/multi-class-metrics](https://www.evidentlyai.com/classification-metrics/multi-class-metrics)  
35. Micro Average vs Macro average Performance in a Multiclass classification setting, truy cập vào tháng 4 23, 2026, [https://datascience.stackexchange.com/questions/15989/micro-average-vs-macro-average-performance-in-a-multiclass-classification-settin](https://datascience.stackexchange.com/questions/15989/micro-average-vs-macro-average-performance-in-a-multiclass-classification-settin)  
36. Macro vs micro-averaging switched up in user guide · Issue \#28585 \- GitHub, truy cập vào tháng 4 23, 2026, [https://github.com/scikit-learn/scikit-learn/issues/28585](https://github.com/scikit-learn/scikit-learn/issues/28585)  
37. Micro, Macro & Weighted Averages of F1 Score, Clearly Explained | Towards Data Science, truy cập vào tháng 4 23, 2026, [https://towardsdatascience.com/micro-macro-weighted-averages-of-f1-score-clearly-explained-b603420b292f/](https://towardsdatascience.com/micro-macro-weighted-averages-of-f1-score-clearly-explained-b603420b292f/)  
38. recruitment dataset \- Kaggle, truy cập vào tháng 4 23, 2026, [https://www.kaggle.com/datasets/surendra365/recruitement-dataset](https://www.kaggle.com/datasets/surendra365/recruitement-dataset)  
39. Job matching: Development and evaluation of a web-based instrument to assess degree of match among employment preferences, truy cập vào tháng 4 23, 2026, [http://www.worksupport.com/documents/jvr\_job\_matching.pdf](http://www.worksupport.com/documents/jvr_job_matching.pdf)  
40. Does fair ranking lead to fair recruitment outcomes? A study of interventions, interfaces, and interactions \- ResearchGate, truy cập vào tháng 4 23, 2026, [https://www.researchgate.net/publication/403348742\_Does\_fair\_ranking\_lead\_to\_fair\_recruitment\_outcomes\_A\_study\_of\_interventions\_interfaces\_and\_interactions](https://www.researchgate.net/publication/403348742_Does_fair_ranking_lead_to_fair_recruitment_outcomes_A_study_of_interventions_interfaces_and_interactions)  
41. Resume2Vec: Transforming Applicant Tracking Systems with Intelligent Resume Embeddings for Precise Candidate Matching \- MDPI, truy cập vào tháng 4 23, 2026, [https://www.mdpi.com/2079-9292/14/4/794](https://www.mdpi.com/2079-9292/14/4/794)  
42. Causal Synthetic Data Generation in Recruitment \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2511.16204v1](https://arxiv.org/html/2511.16204v1)  
43. Candidate Profile Summarization: A RAG Approach with Synthetic Data Generation for Tech Jobs \- ACL Anthology, truy cập vào tháng 4 23, 2026, [https://aclanthology.org/2025.ranlp-1.3.pdf](https://aclanthology.org/2025.ranlp-1.3.pdf)  
44. A Systematic Review of Synthetic Data Generation Techniques Using Generative AI \- MDPI, truy cập vào tháng 4 23, 2026, [https://www.mdpi.com/2079-9292/13/17/3509](https://www.mdpi.com/2079-9292/13/17/3509)  
45. An LLM-based Scalable Synthetic Data Generation Pipeline for Low-Resource Languages \- \- MURAL \- Maynooth University Research Archive Library, truy cập vào tháng 4 23, 2026, [https://mural.maynoothuniversity.ie/id/eprint/21336/1/SP\_synth.pdf](https://mural.maynoothuniversity.ie/id/eprint/21336/1/SP_synth.pdf)  
46. How to Build License-Compliant Synthetic Data Pipelines for AI Model Distillation, truy cập vào tháng 4 23, 2026, [https://developer.nvidia.com/blog/how-to-build-license-compliant-synthetic-data-pipelines-for-ai-model-distillation/](https://developer.nvidia.com/blog/how-to-build-license-compliant-synthetic-data-pipelines-for-ai-model-distillation/)  
47. Building a High‑Quality Synthetic Data Pipeline for Supervised Fine‑Tuning \- Fireworks AI, truy cập vào tháng 4 23, 2026, [https://fireworks.ai/blog/synthetic-data-pipeline](https://fireworks.ai/blog/synthetic-data-pipeline)  
48. Impact of Synthetic Data on Recruitment Models – Insights \- Resumly.ai, truy cập vào tháng 4 23, 2026, [https://www.resumly.ai/blog/impact-of-synthetic-data-on-recruitment-models-insights](https://www.resumly.ai/blog/impact-of-synthetic-data-on-recruitment-models-insights)  
49. Synthetic Task Generation \- John Snow Labs NLP libraries, truy cập vào tháng 4 23, 2026, [https://nlp.johnsnowlabs.com/docs/en/alab/synthetic\_task](https://nlp.johnsnowlabs.com/docs/en/alab/synthetic_task)  
50. Layout-Aware Parsing Meets Efficient LLMs: A Unified, Scalable Framework for Resume Information Extraction and Evaluation \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2510.09722v1](https://arxiv.org/html/2510.09722v1)  
51. Synthetic data generation: methods and tools \- Innovatiana, truy cập vào tháng 4 23, 2026, [https://www.innovatiana.com/en/post/data-generator-our-best-tips](https://www.innovatiana.com/en/post/data-generator-our-best-tips)  
52. Using LLMs for Synthetic Data Generation: The Definitive Guide \- Confident AI, truy cập vào tháng 4 23, 2026, [https://www.confident-ai.com/blog/the-definitive-guide-to-synthetic-data-generation-using-llms](https://www.confident-ai.com/blog/the-definitive-guide-to-synthetic-data-generation-using-llms)  
53. AI candidate screening: How to automate top-of-funnel screens | Metaview Blog, truy cập vào tháng 4 23, 2026, [https://www.metaview.ai/resources/blog/ai-candidate-screening](https://www.metaview.ai/resources/blog/ai-candidate-screening)  
54. Measuring Validity in LLM-based Resume Screening \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2602.18550v1](https://arxiv.org/html/2602.18550v1)  
55. How to evaluate synthetic data quality \- Syntheticus, truy cập vào tháng 4 23, 2026, [https://syntheticus.ai/blog/how-to-evaluate-synthetic-data-quality](https://syntheticus.ai/blog/how-to-evaluate-synthetic-data-quality)  
56. Temporal Consistency for LLM Reasoning Process Error Identification \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2503.14495v1](https://arxiv.org/html/2503.14495v1)  
57. Parsing Resumes with LLMs: A Guide to Structuring CVs for HR Automation \- Datumo, truy cập vào tháng 4 23, 2026, [https://www.datumo.io/blog/parsing-resumes-with-llms-a-guide-to-structuring-cvs-for-hr-automation](https://www.datumo.io/blog/parsing-resumes-with-llms-a-guide-to-structuring-cvs-for-hr-automation)  
58. The 5-Minute ATS Resume Checklist to Avoid Costly Parsing Errors and Boost Relevance Scores \- AscendurePro, truy cập vào tháng 4 23, 2026, [https://ascendurepro.com/ats-resume-checklist/](https://ascendurepro.com/ats-resume-checklist/)  
59. Mastering Automated Resume Screening Software | Red Brick Labs Blog, truy cập vào tháng 4 23, 2026, [https://www.redbricklabs.io/blog/automated-resume-screening-software](https://www.redbricklabs.io/blog/automated-resume-screening-software)  
60. Applying Artificial Intelligence to Automate Resume Screening in The Technology Sector \- The USA Journals, truy cập vào tháng 4 23, 2026, [https://www.theamericanjournals.com/index.php/tajas/article/download/7149/6536/10207](https://www.theamericanjournals.com/index.php/tajas/article/download/7149/6536/10207)  
61. What is Synthetic Data Generation? A Practical Guide \- K2view, truy cập vào tháng 4 23, 2026, [https://www.k2view.com/what-is-synthetic-data-generation/](https://www.k2view.com/what-is-synthetic-data-generation/)  
62. How to evaluate the quality of the synthetic data – measuring from the perspective of fidelity, utility, and privacy | Artificial Intelligence \- AWS, truy cập vào tháng 4 23, 2026, [https://aws.amazon.com/blogs/machine-learning/how-to-evaluate-the-quality-of-the-synthetic-data-measuring-from-the-perspective-of-fidelity-utility-and-privacy/](https://aws.amazon.com/blogs/machine-learning/how-to-evaluate-the-quality-of-the-synthetic-data-measuring-from-the-perspective-of-fidelity-utility-and-privacy/)  
63. Cosine Re-weighting Guide 2025 | ShadeCoder, truy cập vào tháng 4 23, 2026, [https://www.shadecoder.com/topics/cosine-re-weighting-a-comprehensive-guide-for-2025](https://www.shadecoder.com/topics/cosine-re-weighting-a-comprehensive-guide-for-2025)  
64. An introduction to calibration (part II): Platt scaling, isotonic regression, and beta calibration., truy cập vào tháng 4 23, 2026, [https://www.abzu.ai/data-science/calibration-introduction-part-2/](https://www.abzu.ai/data-science/calibration-introduction-part-2/)  
65. 1.16. Probability calibration — scikit-learn 1.8.0 documentation, truy cập vào tháng 4 23, 2026, [https://scikit-learn.org/stable/modules/calibration.html](https://scikit-learn.org/stable/modules/calibration.html)  
66. i-vector Score Calibration \- MATLAB & Simulink \- MathWorks, truy cập vào tháng 4 23, 2026, [https://www.mathworks.com/help/audio/ug/i-vector-score-calibration.html](https://www.mathworks.com/help/audio/ug/i-vector-score-calibration.html)  
67. Calibration Techniques and it's importance in Machine Learning \- Subham Sarkar \- Medium, truy cập vào tháng 4 23, 2026, [https://kingsubham27.medium.com/calibration-techniques-and-its-importance-in-machine-learning-71bec997b661](https://kingsubham27.medium.com/calibration-techniques-and-its-importance-in-machine-learning-71bec997b661)  
68. The Complete Guide to Platt Scaling \- Train in Data's Blog, truy cập vào tháng 4 23, 2026, [https://www.blog.trainindata.com/complete-guide-to-platt-scaling/](https://www.blog.trainindata.com/complete-guide-to-platt-scaling/)  
69. What Does Softmax Probability Tell Us about Classifiers Ranking Across Diverse Test Conditions? \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2406.09908v1](https://arxiv.org/html/2406.09908v1)  
70. AI tools show biases in ranking job applicants' names according to perceived race and gender – UW News, truy cập vào tháng 4 23, 2026, [https://www.washington.edu/news/2024/10/31/ai-bias-resume-screening-race-gender/](https://www.washington.edu/news/2024/10/31/ai-bias-resume-screening-race-gender/)  
71. Fairness in AI-Driven Recruitment: Challenges, Metrics, Methods, and Future Directions, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2405.19699v2](https://arxiv.org/html/2405.19699v2)  
72. Fairness in AI-Driven Recruitment: Challenges, Metrics, Methods, and Future Directions, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2405.19699v3](https://arxiv.org/html/2405.19699v3)  
73. Bipartite Ranking Fairness Through a Model Agnostic Ordering Adjustment \- IEEE Computer Society, truy cập vào tháng 4 23, 2026, [https://www.computer.org/csdl/journal/tp/2023/11/10169084/1Op7GHI8LSg](https://www.computer.org/csdl/journal/tp/2023/11/10169084/1Op7GHI8LSg)  
74. Fairness of recommender systems in the recruitment domain: an analysis from technical and legal perspectives \- PMC, truy cập vào tháng 4 23, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC10587596/](https://pmc.ncbi.nlm.nih.gov/articles/PMC10587596/)  
75. AI Fairness Testing: Metrics and Methods Guide, truy cập vào tháng 4 23, 2026, [https://www.warden-ai.com/resources/ai-fairness-testing-metrics-methods](https://www.warden-ai.com/resources/ai-fairness-testing-metrics-methods)  
76. Common fairness metrics — Fairlearn 0.14.0.dev0 documentation, truy cập vào tháng 4 23, 2026, [https://fairlearn.org/main/user\_guide/assessment/common\_fairness\_metrics.html](https://fairlearn.org/main/user_guide/assessment/common_fairness_metrics.html)  
77. \[2307.14668\] Bipartite Ranking Fairness through a Model Agnostic Ordering Adjustment \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/abs/2307.14668](https://arxiv.org/abs/2307.14668)  
78. How to Implement Fair and Compliant AI Candidate Ranking in Recruiting \- EverWorker, truy cập vào tháng 4 23, 2026, [https://everworker.ai/blog/ai\_candidate\_ranking\_recruiting\_checklist](https://everworker.ai/blog/ai_candidate_ranking_recruiting_checklist)  
79. Data split and candidate set in offline evaluation \- ResearchGate, truy cập vào tháng 4 23, 2026, [https://www.researchgate.net/figure/Data-split-and-candidate-set-in-offline-evaluation\_fig4\_361369087](https://www.researchgate.net/figure/Data-split-and-candidate-set-in-offline-evaluation_fig4_361369087)  
80. Off-policy evaluation of candidate generators in two-stage ..., truy cập vào tháng 4 23, 2026, [https://www.amazon.science/publications/off-policy-evaluation-of-candidate-generators-in-two-stage-recommender-systems](https://www.amazon.science/publications/off-policy-evaluation-of-candidate-generators-in-two-stage-recommender-systems)  
81. Off-Policy Evaluation and Learning for Matching Markets \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2507.13608v1](https://arxiv.org/html/2507.13608v1)  
82. The Ultimate List of Recruiting Benchmarks \- Crosschq, truy cập vào tháng 4 23, 2026, [https://www.crosschq.com/blog/ultimate-list-recruiting-benchmarks](https://www.crosschq.com/blog/ultimate-list-recruiting-benchmarks)  
83. HR Organizations Under-use HR Metrics \- The Hackett Group, truy cập vào tháng 4 23, 2026, [https://www.thehackettgroup.com/hr-metrics-hackett/](https://www.thehackettgroup.com/hr-metrics-hackett/)  
84. 23 Recruiting Metrics You Should Know \- AIHR, truy cập vào tháng 4 23, 2026, [https://www.aihr.com/blog/recruiting-metrics/](https://www.aihr.com/blog/recruiting-metrics/)  
85. AI-powered talent matching: The tech behind smarter and fairer hiring \- Eightfold AI, truy cập vào tháng 4 23, 2026, [https://eightfold.ai/engineering-blog/ai-powered-talent-matching-the-tech-behind-smarter-and-fairer-hiring/](https://eightfold.ai/engineering-blog/ai-powered-talent-matching-the-tech-behind-smarter-and-fairer-hiring/)  
86. Transformational HR: key metrics being tracked by strategic HR departments \- Eightfold AI, truy cập vào tháng 4 23, 2026, [https://eightfold.ai/blog/hr-transformation-metrics/](https://eightfold.ai/blog/hr-transformation-metrics/)  
87. Quality of hire: The KPI you need to measure in 2026 | Jobylon, truy cập vào tháng 4 23, 2026, [https://www.jobylon.com/blog/quality-of-hire](https://www.jobylon.com/blog/quality-of-hire)  
88. 25 Recruitment Metrics for Data-Driven Human Capital Management \- NetSuite, truy cập vào tháng 4 23, 2026, [https://www.netsuite.com/portal/resource/articles/human-resources/recruitment-metrics.shtml](https://www.netsuite.com/portal/resource/articles/human-resources/recruitment-metrics.shtml)  
89. 2026 Hiring Benchmarks Data Deep Dive \- Starred, truy cập vào tháng 4 23, 2026, [https://www.starred.com/benchmarks-reports-download/2026-hiring-benchmarks-data-deep-dive](https://www.starred.com/benchmarks-reports-download/2026-hiring-benchmarks-data-deep-dive)

[image1]: images/NMAIex_2/image1.png

[image2]: images/NMAIex_2/image2.png

[image3]: images/NMAIex_2/image3.png

[image4]: images/NMAIex_2/image4.png

[image5]: images/NMAIex_2/image5.png

[image6]: images/NMAIex_2/image6.png

[image7]: images/NMAIex_2/image7.png

[image8]: images/NMAIex_2/image8.png

[image9]: images/NMAIex_2/image9.png

[image10]: images/NMAIex_2/image10.png

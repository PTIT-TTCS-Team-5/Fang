# **Báo cáo Kiến trúc: Tối ưu hóa Hệ thống Xếp hạng Hai chiều NMAI trên Nền tảng FANG AI Core**

## **Tóm tắt Điều hành**

Báo cáo kiến trúc này xác lập các quyết định kỹ thuật cốt lõi nhằm triển khai lớp mở rộng (extension) NMAI trên nền tảng FANG AI Core, phục vụ hệ thống tuyển dụng hai chiều cho thin client miCareer-mini. Giải pháp đề xuất sử dụng phương pháp tìm kiếm lai (Hybrid Search) kết hợp thuật toán Reciprocal Rank Fusion (RRF) có trọng số, cho phép cân bằng tín hiệu từ khóa, tín hiệu ngữ nghĩa vector và siêu dữ liệu mà không can thiệp sâu vào lõi FANG. Quá trình hiệu chuẩn xác suất (Calibration) được khuyến nghị lùi sang Phase 1.5 để ưu tiên thu thập đủ lượng dữ liệu tương tác thực tế, tránh rủi ro quá khớp (overfitting) hệ thống sớm. Một hệ thống nhãn phân cấp (Graded Relevance) 5 mức độ được định nghĩa chặt chẽ, ánh xạ trực tiếp từ trạng thái ATS nhằm phục vụ đo lường thông qua chỉ số Macro NDCG@10 và NDCG@20. Báo cáo cũng phác thảo thiết kế thử nghiệm A/B/C, quy định ngưỡng chuyển đổi an toàn sang mô hình học xếp hạng có giám sát (Supervised Reranker), nhận diện rủi ro vận hành, và cung cấp lộ trình triển khai 4 tuần đảm bảo khả năng tích hợp tức thời, đáp ứng nghiêm ngặt các giới hạn về độ trễ và tài nguyên tính toán.

## **Bối cảnh Kiến trúc và Động lực học Hệ thống Tương hỗ**

Kiến trúc hiện tại đặt FANG AI Core ở vị trí trung tâm, chịu trách nhiệm xử lý các tác vụ học máy nặng như nội suy vector, quản lý cơ sở dữ liệu nhúng (embedding) và thực thi các truy vấn không gian nhiều chiều. Hệ thống miCareer-mini đóng vai trò là một thin client, yêu cầu các phản hồi API có độ trễ cực thấp để duy trì trải nghiệm người dùng liền mạch. Việc hệ thống phân tích cú pháp (Parser) đã được trang bị cơ chế dự phòng 5 cấp độ (5-tier fallback) đảm bảo rằng thông tin từ CV và mô tả công việc (Job Description \- JD) luôn được trích xuất tối đa, cung cấp một nguồn dữ liệu văn bản phong phú và liên tục cho các thuật toán đối sánh từ khóa.1 Bên cạnh đó, hệ thống Retrieval-Augmented Generation (RAG) hiện có 7 chế độ mô hình (modelMode), cung cấp khả năng truy xuất thông tin linh hoạt, tạo tiền đề vững chắc cho việc tạo ra các vector nhúng giàu ngữ cảnh.2 Tuy nhiên, do chưa ưu tiên việc giải thích bằng mô hình ngôn ngữ lớn (explain-by-LLM) theo từng JobPosting ở giai đoạn này, hệ thống xếp hạng NMAI extension phải tự chứng minh được độ tin cậy thông qua độ chính xác của kết quả sắp xếp (ranking) thay vì dựa vào các đoạn văn bản giải thích sinh tự động.3

Bài toán tuyển dụng hai chiều bản chất là một Hệ thống Khuyến nghị Tương hỗ (Reciprocal Recommender Systems \- RRS). Khác biệt hoàn toàn với các hệ thống khuyến nghị thương mại điện tử nơi chỉ có một phía người dùng đưa ra quyết định mua hàng, RRS đòi hỏi sự đồng thuận từ cả hai phía: Ứng viên phải tìm thấy sự phù hợp về mức lương, văn hóa và lộ trình thăng tiến, trong khi Nhà tuyển dụng phải đánh giá cao bộ kỹ năng và kinh nghiệm của ứng viên.4 Sự phức tạp này dẫn đến hiện tượng "lệch pha kỳ vọng", nơi một danh sách xếp hạng có thể xuất sắc dưới góc nhìn của nhà tuyển dụng nhưng lại chứa toàn bộ các công việc mà ứng viên sẽ từ chối. Do đó, NMAI extension không thể sử dụng một thuật toán nguyên khối chung cho cả hai chiều. Nó đòi hỏi một kiến trúc tính toán điểm số đối xứng nhưng sở hữu trọng số bất đối xứng, đảm bảo tối ưu hóa sự hài lòng cho cả hai nhóm người dùng trên cùng một nền tảng dữ liệu.5

## **Bảng Quyết định Công thức Điểm Đầu cuối (End-to-End Scoring)**

Việc kết hợp nhiều nguồn truy xuất (retrieval pipelines) đặt ra một thách thức lớn về sự đồng nhất thang đo. Điểm số từ truy vấn vector (thường là Cosine Similarity hoặc Euclidean Distance) mang bản chất phân phối hoàn toàn khác biệt so với điểm số từ truy vấn từ khóa (như thuật toán BM25 dựa trên tần suất nghịch đảo tài liệu). Việc áp dụng cộng tuyến tính trực tiếp các điểm số này (Relative Score Fusion \- RSF) đòi hỏi các kỹ thuật chuẩn hóa (normalization) phức tạp như Z-score hoặc Min-Max, vốn rất nhạy cảm với các điểm dị biệt (outliers) trong từng truy vấn cụ thể.7

Thay vào đó, thuật toán Reciprocal Rank Fusion (RRF) cung cấp một cơ chế kết hợp mạnh mẽ, thanh lịch và không cần tinh chỉnh (zero-tuning). RRF bỏ qua hoàn toàn điểm số thô và chỉ quan tâm đến thứ hạng tương đối của tài liệu trong từng danh sách trả về.9 Bằng cách tính tổng nghịch đảo của thứ hạng cộng với một hằng số làm mượt, RRF trừng phạt mạnh mẽ các tài liệu xếp hạng thấp và thưởng cho các tài liệu xuất hiện ở vị trí cao trên nhiều danh sách truy xuất khác nhau.10 Tuy nhiên, RRF truyền thống đối xử bình đẳng với mọi thuật toán truy xuất. Để giải quyết đặc thù của RRS, hệ thống NMAI sẽ triển khai RRF có trọng số (Weighted RRF), cho phép cấp quyền chi phối lớn hơn cho vector hoặc từ khóa tùy thuộc vào chiều xếp hạng đang được thực thi.9

Bảng dưới đây quy định chi tiết công thức và cơ chế vận hành cho hai chiều xếp hạng, tuân thủ nghiêm ngặt giới hạn thay đổi tối thiểu lên FANG Core.

**Bảng 1: Quyết định Kiến trúc Công thức Điểm Đầu cuối cho Hệ thống Hai chiều**

| Thuộc tính Kiến trúc | Chiều 1: Danh sách Ứng viên (Candidate) xếp theo Công việc (Job) | Chiều 2: Danh sách Công việc (Job) xếp theo Ứng viên (Candidate) | Đánh giá Đánh đổi (Trade-offs: Accuracy, Latency, Complexity) |
| :---- | :---- | :---- | :---- |
| **Công thức Toán học Cốt lõi** | CT_1 | CT_2 | **Trễ:** Phép tính phân tán in-memory trên mảng có độ trễ <10ms. **Chính xác:** RRF bảo toàn thứ hạng xuất sắc. **Phức tạp:** Yêu cầu chạy 2 retriever song song. |
| **Cơ chế Tính toán RRF** | CT_3 | CT_3 | Sử dụng hằng số k = 60 theo tiêu chuẩn công nghiệp nhằm cân bằng trọng số giữa các tài liệu top đầu và phần đuôi (long-tail).11 |
| **Thành phần Vector (V)** | Khoảng cách Cosine giữa Vector mô tả Công việc và Vector hồ sơ Ứng viên. | Khoảng cách Cosine giữa Vector hồ sơ Ứng viên và Vector mô tả Công việc. | Giải quyết vấn đề từ đồng nghĩa và kỹ năng chuyển đổi (transferable skills). Đánh đổi: Tiêu tốn băng thông bộ nhớ của FANG Core.12 |
| **Thành phần Từ khóa (K)** | Tính điểm BM25 dựa trên các từ khóa kỹ năng cứng, chứng chỉ bắt buộc từ JD. | Tính điểm BM25 dựa trên chức danh và mô tả kinh nghiệm làm việc trong CV. | Đảm bảo tính chính xác tuyệt đối (Precision) cho các tiêu chí không thể thương lượng. Đánh đổi: Yêu cầu Parser 5-tier phải hoạt động hoàn hảo.13 |
| **Thành phần Siêu dữ liệu (M)** | Hàm $M\_{score} \\in $ đánh giá độ mới của CV, mức độ hoạt động và sự ổn định. | Hàm $M\_{score} \\in $ đánh giá khoảng cách địa lý, chênh lệch mức lương, độ uy tín của công ty. | Yếu tố phá vỡ thế hòa (Tie-breaker). Hoạt động độc lập với RRF, được cộng vào giai đoạn cuối để định hình lại bảng xếp hạng dựa trên logic nghiệp vụ.14 |

CT_1 = $$S_{C|J} = w_v \cdot RRF(V) + w_k \cdot RRF(K) + w_m \cdot M_{score}$$

CT_2 = $$S_{J|C} = w_v \cdot RRF(V) + w_k \cdot RRF(K) + w_m \cdot M_{score}$$

CT_3 = $$RRF(X) = \sum \frac{1}{60 + rank_{X}(d)}$$

## **Chiến lược Khởi tạo Bộ Trọng số cho Phase 1**


Triển khai một công thức điểm lai (hybrid scoring) đòi hỏi sự tinh chỉnh cẩn thận về trọng số (**$w_v, w_k, w_m$**) để phản ánh đúng động lực tâm lý của người dùng. Việc gán trọng số đồng đều cho tất cả các thành phần sẽ dẫn đến một trải nghiệm trung bình, không phục vụ tốt cho bất kỳ ai. Dựa trên phân tích hành vi tuyển dụng, bộ trọng số được đề xuất theo nguyên tắc bất đối xứng, điều khiển thông qua cấu hình môi trường của NMAI extension nhằm duy trì tính linh hoạt.

Đối với chiều sắp xếp danh sách Ứng viên theo Công việc (phục vụ Nhà tuyển dụng), mức độ dung sai đối với các kỹ năng không phù hợp là cực kỳ thấp. Các chuyên gia nhân sự và hệ thống quản lý ứng viên thường loại bỏ hồ sơ ngay lập tức nếu thiếu vắng các từ khóa cốt lõi (như ngôn ngữ lập trình cụ thể, hoặc chứng chỉ hành nghề).15 Do đó, tín hiệu từ khóa (Keyword/BM25) phải đóng vai trò chi phối. Đề xuất khởi tạo trọng số ![][image7] để đảm bảo các ứng viên khớp từ khóa cứng được đẩy lên top đầu. Tín hiệu ngữ nghĩa vector được gán ![][image8] nhằm đóng vai trò mở rộng tập tìm kiếm (Recall expansion), giúp nhà tuyển dụng phát hiện các ứng viên sử dụng từ ngữ thay thế nhưng có nền tảng tư duy tương đương.2 Cuối cùng, siêu dữ liệu được gán ![][image9] để ưu tiên những CV được cập nhật gần đây, giảm thiểu rủi ro nhà tuyển dụng liên hệ với các ứng viên đã ngừng tìm việc.

Ngược lại, ở chiều sắp xếp danh sách Công việc theo Ứng viên (phục vụ Người tìm việc), hành vi đánh giá mang tính chiến lược và dài hạn hơn. Một ứng viên hiếm khi chấp nhận một công việc khớp 100% về từ khóa kỹ năng nhưng lại yêu cầu giảm 50% mức lương hiện tại hoặc yêu cầu chuyển chỗ ở sang một quốc gia khác mà không hỗ trợ thị thực. Ở luồng này, siêu dữ liệu đóng vai trò của bộ lọc sinh tử. Đề xuất gán trọng số siêu dữ liệu ![][image10] để sự chênh lệch lương, khoảng cách địa lý, và cấp độ thâm niên (seniority level) chi phối mạnh mẽ kết quả. Tín hiệu vector duy trì ở mức ![][image8] để giúp ứng viên khám phá các cơ hội chuyển đổi nghề nghiệp (cross-functional roles) dựa trên bản chất năng lực tổng thể. Tín hiệu từ khóa bị hạ xuống ![][image11] vì các mô tả công việc (JD) thường chứa rất nhiều văn bản mẫu (boilerplate) hoặc các yêu cầu kỹ năng phi thực tế, gây nhiễu nặng nề cho thuật toán BM25 và làm suy giảm chất lượng khuyến nghị nếu được gán trọng số quá cao.

Việc duy trì bộ trọng số bất đối xứng này tạo ra một rào cản vận hành nhất định, buộc đội ngũ kỹ thuật phải thiết kế các kịch bản kiểm thử (test cases) riêng biệt cho từng luồng. Tuy nhiên, sự hi sinh về độ phức tạp bảo trì này đổi lấy việc tăng cường đáng kể tỷ lệ nhấp chuột (Click-Through Rate) và tỷ lệ chuyển đổi sâu (Conversion Rate) trên nền tảng miCareer-mini, giải quyết triệt để bài toán cá nhân hóa trong hệ thống tuyển dụng tương hỗ.

## **Chiến lược Hiệu chuẩn Xác suất (Probability Calibration)**

Xếp hạng lại các tài liệu dựa trên điểm số RRF giải quyết tốt bài toán thứ tự tương đối, nhưng nó không cung cấp một ý nghĩa xác suất tuyệt đối. Một điểm RRF là 0.08 không có nghĩa là ứng viên có 8% cơ hội trúng tuyển. Tuy nhiên, trong tương lai, hệ thống UI của miCareer-mini có thể yêu cầu hiển thị "Chỉ số Phù hợp" (Match Score) dưới dạng phần trăm (ví dụ: 85% Match), hoặc hệ thống định tuyến tự động cần một ngưỡng xác suất thực tế để kích hoạt các kịch bản gửi email tự động.16 Đây là lúc các kỹ thuật hiệu chuẩn xác suất (Calibration) như Platt Scaling hoặc Isotonic Regression trở nên cần thiết. Platt Scaling sử dụng hồi quy logistic để ép điểm số thô vào một đường cong Sigmoid, trong khi Isotonic Regression xây dựng một hàm bậc thang đơn điệu không tham số, bảo toàn thứ tự nhưng tinh chỉnh độ lớn của điểm số.17

Mặc dù hiệu chuẩn mang lại giá trị lớn, quyết định kiến trúc cho NMAI extension là **chưa kích hoạt Calibration trong Phase 1** và bảo lưu tính năng này cho Phase 1.5. Việc hoãn lại dựa trên các đánh giá kỹ thuật và quản trị rủi ro nghiêm ngặt.

Thứ nhất, các mô hình hiệu chuẩn, đặc biệt là Isotonic Regression, cực kỳ khát dữ liệu. Để xây dựng một hàm ánh xạ xác suất đáng tin cậy, hệ thống cần hàng chục ngàn mẫu dữ liệu lịch sử phản ánh đúng phân phối tương tác của người dùng.19 Trong Phase 1, NMAI extension chưa tích lũy đủ các điểm dữ liệu tương tác thực tế (phản hồi hai chiều, lịch sử phỏng vấn) trên thiết kế mới. Việc ép buộc hiệu chuẩn trên một tập dữ liệu nhỏ bé (hoặc dữ liệu tổng hợp synthetic) sẽ dẫn đến rủi ro quá khớp (overfitting) nghiêm trọng, làm biến dạng hoàn toàn bảng xếp hạng và tạo ra các cụm điểm số ảo (tied probabilities) khiến hệ thống mất khả năng phân loại các ứng viên xuất sắc.20 Thứ hai, việc bổ sung một lớp biến đổi hàm số (transformation layer) sau quá trình dung hợp RRF sẽ tạo thêm một nút thắt cổ chai về độ trễ (latency bottleneck), đi ngược lại yêu cầu tối ưu hóa tốc độ cho thin client miCareer-mini ở giai đoạn ra mắt.

Hệ thống sẽ chỉ được phép kích hoạt Calibration cho Phase 1.5 khi và chỉ khi đáp ứng đủ các điều kiện tiên quyết sau:

1. Nền tảng đã thu thập và xử lý làm sạch tối thiểu 10,000 cặp tương tác ứng viên-công việc với nhãn kết quả rõ ràng (Interview, Rejected, Hired) từ hệ thống ATS.  
2. Các phân tích dữ liệu cho thấy sự phân phối điểm RRF bị nén chặt (Score Skewness), khiến các thuật toán hạ nguồn không thể thiết lập ngưỡng cắt (cut-off threshold) tự động một cách an toàn.  
3. Khi kích hoạt, hệ thống phải áp dụng Platt Scaling trước tiên do tính chất ổn định và ít rủi ro quá khớp trên tập dữ liệu trung bình. Isotonic Regression chỉ được kích hoạt khi quy mô dữ liệu vượt qua ngưỡng kiểm định chéo (cross-validation) an toàn và phân phối điểm số được chứng minh là đa phương thức (multi-modal) không tuân theo hàm Sigmoid.20

## **Chuẩn nhãn Phân cấp (Graded Relevance) và Ánh xạ Trạng thái ATS**

Để đánh giá chính xác một hệ thống xếp hạng tương hỗ, việc sử dụng các thước đo nhị phân (Đạt/Trượt) là hoàn toàn sai lầm. Tuyển dụng là một hệ sinh thái có độ phân giải cao; một ứng viên lọt vào vòng phỏng vấn cuối cùng mang lại giá trị thông tin cho thuật toán lớn hơn hàng ngàn lần so với một ứng viên chỉ mới nộp đơn.22 Do đó, hệ thống cần một thang đo mức độ liên quan phân cấp (Graded Relevance) để áp dụng cho các công thức đo lường hạng nặng như Normalized Discounted Cumulative Gain (NDCG). Hệ thống ATS hiện tại theo dõi toàn bộ vòng đời của ứng viên, cung cấp một nguồn dữ liệu phong phú để ánh xạ thành các nhãn phân cấp.

**Bảng 2: Chuẩn nhãn Graded Relevance ánh xạ với Trạng thái ATS**

| Điểm Liên quan (Relevance Score) | Mức độ Phù hợp (Relevance Level) | Phân tích Ánh xạ Trạng thái ATS (ATS Status Mapping & Logic) | Giá trị Hưởng lợi (Gain Value \= 2rel−1) |
| :---- | :---- | :---- | :---- |
| **0** | **Nhiễu / Loại bỏ (Irrelevant)** | Bao gồm các trạng thái Auto-Rejected (bởi bộ lọc knockout), Manual Reject, Ghosted (ứng viên biến mất). Đại diện cho sự lãng phí tài nguyên của hệ thống, thuật toán không nhận được điểm thưởng khi xếp hạng các mục này.24 | ![][image12] |
| **1** | **Chạm ngưỡng (Barely Relevant)** | Trạng thái Applied, Parsed. Ứng viên vượt qua hệ thống phân tích cú pháp (5-tier fallback) và lọt vào danh sách chờ. Chưa có sự xác nhận chuyên môn từ nhà tuyển dụng.25 | ![][image13] |
| **2** | **Có tiềm năng (Moderately Relevant)** | Bao gồm Screened, Shortlisted, Phone Screen. Hồ sơ đã được mở, xem xét bởi con người và được lưu lại. Thể hiện thuật toán đã thành công trong việc thu hút sự chú ý của nhà tuyển dụng. | ![][image14] |
| **3** | **Tương thích cao (Highly Relevant)** | Các vòng Technical Interview, Assessment, Cultural Fit. Ứng viên đang trực tiếp cạnh tranh cho vị trí. Thuật toán đã kết nối thành công năng lực lõi và yêu cầu công việc. | ![][image15] |
| **4** | **Mục tiêu tối thượng (Perfect Match)** | Trạng thái Offered, Hired, Placed. Khớp nối hai chiều thành công. Phần thưởng cho cấp độ này tăng theo cấp số nhân nhằm ép buộc thuật toán học cách ưu tiên các đặc trưng của những người chiến thắng.25 | ![][image16] |

Việc ánh xạ hàm mũ (Exponential Gain) đảm bảo rằng việc đẩy một ứng viên trúng tuyển (Score 4\) từ vị trí thứ 10 lên vị trí thứ 1 sẽ làm tăng đột biến điểm số NDCG của toàn hệ thống, tạo áp lực tối ưu hóa chính xác vào những hồ sơ thực sự tạo ra doanh thu và giá trị cho nền tảng.

## **Thiết kế Thử nghiệm A/B/C (Benchmark Design)**

Để xác thực tính đúng đắn của cấu trúc điểm số và quản lý rủi ro trước khi triển khai diện rộng, hệ thống NMAI extension sẽ vận hành một cơ sở thử nghiệm A/B/C nghiêm ngặt. Traffic từ miCareer-mini sẽ được định tuyến thông qua một API Gateway dựa trên hàm băm (hashing) của User ID nhằm đảm bảo tính nhất quán của phiên làm việc (session consistency). Các cấu hình thử nghiệm được thiết kế để đánh giá từng bước chuyển đổi của kiến trúc.

**Bảng 3: Khung Thiết kế Thử nghiệm A/B/C Benchmark**

| Biến thể (Variant) | Cấu trúc Kiến trúc (Architecture Setup) | Giả thuyết và Mục tiêu Kiểm định (Hypothesis & Objectives) |
| :---- | :---- | :---- |
| **Variant A** | **Chỉ dùng Vector (Semantic Baseline):** Sử dụng các embedding từ 7 modelMode của FANG Core. Không có tín hiệu từ khóa. Sắp xếp thuần túy bằng Cosine Similarity.26 | Khảo sát giới hạn của khả năng hiểu ngữ nghĩa thuần túy. Biến thể này dự kiến sẽ có độ phủ (Recall) xuất sắc nhưng độ chính xác (Precision) kém khi đối mặt với các truy vấn chứa từ khóa đặc thù (ví dụ: mã sản phẩm, chứng chỉ công nghệ hẹp). Đóng vai trò mốc cơ sở (Baseline). |
| **Variant B** | **Hệ thống Lai RRF (Kiến trúc Mục tiêu):** Truy vấn song song Vector và BM25. Áp dụng công thức Weighted RRF (như định nghĩa tại Bảng 1). Không bật tính năng Calibration.13 | Kiểm chứng giả thuyết rằng việc kết hợp đa tín hiệu thông qua RRF sẽ giải quyết được điểm mù của Variant A. Biến thể này được kỳ vọng sẽ tối ưu hóa điểm NDCG@10 với mức tăng độ trễ (latency) chấp nhận được, trở thành giải pháp chính cho Phase 1\. |
| **Variant C** | **Hệ thống Lai RSF có Hiệu chuẩn (Tương lai):** Sử dụng Relative Score Fusion (RSF), áp dụng Platt Scaling lên từng danh sách điểm số trước khi kết hợp tuyến tính.7 | Thử nghiệm áp lực (Stress-test) quy trình hiệu chuẩn trong môi trường thực tế (Shadow mode). Đánh giá sự gia tăng độ trễ tính toán và hiện tượng biến dạng phân phối điểm (score skewness). Dữ liệu từ Variant C sẽ cung cấp minh chứng cho việc kích hoạt Phase 1.5. |

## **Bộ Chỉ số Đo lường và Cơ chế Macro-Averaging**

Đo lường sai lầm là con đường nhanh nhất dẫn đến sự suy thoái của một hệ thống học máy. Trong môi trường tuyển dụng, nếu áp dụng phương pháp Micro-averaging (tính trung bình trên toàn bộ các lượt xem CV mà không phân biệt công việc), hệ thống sẽ bị thiên lệch hoàn toàn (Popularity Bias) bởi các vị trí tuyển dụng đại trà (ví dụ: nhân viên bán hàng, trực tổng đài) với hàng ngàn lượt ứng tuyển. Các vị trí chuyên môn cao (như Kỹ sư AI, Giám đốc Tài chính) với số lượng hồ sơ ít ỏi sẽ trở thành các "nhiễu thống kê" và bị thuật toán phớt lờ.27 Do đó, việc đánh giá bắt buộc phải sử dụng Macro-averaging: Tính toán điểm số độc lập cho từng Công việc (hoặc từng Ứng viên), sau đó mới lấy trung bình cộng của tất cả các điểm số đó.

Ở chiều **Danh sách Ứng viên xếp theo Công việc (Phục vụ Nhà tuyển dụng)**, chỉ số chính (Primary Metric) là **Macro NDCG@10**. Các chuyên gia tuyển dụng hoạt động dưới áp lực thời gian cực lớn và hiếm khi lật qua trang thứ hai của kết quả tìm kiếm.28 NDCG@10 đánh giá sự hoàn hảo của trang đầu tiên, sử dụng nhãn Graded Relevance (0-4) để đảm bảo các ứng viên tiềm năng nhất nằm ở các vị trí có khả năng được click cao nhất. Chỉ số phụ (Secondary Metric) là **MRR (Mean Reciprocal Rank)**. MRR đo lường vị trí xuất hiện của ứng viên phù hợp *đầu tiên*.29 Một MRR cao (tiệm cận 1.0) đảm bảo rằng nhà tuyển dụng không cảm thấy thất vọng ngay từ những hồ sơ đầu tiên, duy trì sự gắn kết của họ với hệ thống miCareer-mini.

Ở chiều **Danh sách Công việc xếp theo Ứng viên (Phục vụ Người tìm việc)**, hành vi duyệt web thay đổi đáng kể. Ứng viên có xu hướng kiên nhẫn hơn, sẵn sàng cuộn qua nhiều trang để tìm kiếm cơ hội đổi đời.28 Do đó, chỉ số chính sẽ được nới lỏng thành **Macro NDCG@20**. Thước đo này đánh giá chất lượng của toàn bộ hệ sinh thái gợi ý việc làm trong một phiên làm việc dài. Chỉ số phụ ở chiều này là **Macro Hit Rate@10 (HR@10)**. HR@10 kiểm tra xem liệu trong 10 gợi ý đầu tiên, ứng viên có tìm thấy ít nhất một công việc mà họ thực sự nhấn nút "Ứng tuyển" (Apply \- Relevance ![][image17] 1\) hay không. Chỉ số này mang tính sống còn đối với các nền tảng thin client vì nó ảnh hưởng trực tiếp đến tỷ lệ giữ chân người dùng (Retention Rate).30

## **Ngưỡng Chuyển đổi sang Supervised Reranker (Học Xếp hạng \- LTR)**

Phương pháp tìm kiếm lai (Hybrid RRF) trong Phase 1 về cơ bản vẫn là một kiến trúc heuristic (dựa trên quy tắc và kinh nghiệm tĩnh). Mặc dù hoạt động nhanh và ổn định, kiến trúc này sẽ dần bão hòa khi nền tảng miCareer-mini mở rộng. Bước tiến hóa tiếp theo là áp dụng mô hình Học Xếp hạng có giám sát (Learning to Rank \- LTR) như RankNet, LambdaMART hoặc các cấu trúc Neural Cross-Encoder mạnh mẽ, cho phép hệ thống tự động học các tương tác phi tuyến tính giữa các đặc trưng của ứng viên và công việc.8 Tuy nhiên, việc vận hành LTR đòi hỏi tài nguyên GPU khổng lồ và làm tăng độ phức tạp vận hành lên nhiều lần.33

Do đó, việc chuyển đổi từ Heuristic sang Supervised Reranker LTR trên NMAI extension bị khóa cứng và chỉ được phê duyệt khi đáp ứng đồng thời 4 ngưỡng an toàn sau:

1. **Ngưỡng Bão hòa Thuật toán (Algorithmic Plateau):** Dữ liệu A/B Testing chỉ ra rằng việc liên tục tinh chỉnh các trọng số ![][image6] trong RRF không còn mang lại sự gia tăng đáng kể. Cụ thể, sự chênh lệch ![][image18] Macro NDCG@10 giữa hai cấu hình trọng số tốt nhất duy trì ở mức dưới ![][image19] trong 4 tuần liên tiếp.  
2. **Ngưỡng Dữ liệu Mật độ cao (Data Density Threshold):** Hệ thống LTR thuộc nhóm mô hình Listwise hoặc Pairwise yêu cầu lượng dữ liệu khổng lồ để tránh thiên lệch.34 NMAI extension chỉ kích hoạt dự án LTR khi Data Lake đã thu thập và làm sạch tối thiểu 25,000 phiên truy vấn (Query Sessions), trong đó mỗi phiên chứa ít nhất 3 nhãn phân cấp hợp lệ từ Bảng 2\.  
3. **Ngưỡng Khả thi Lợi nhuận (ROI Evaluation):** Trong quá trình huấn luyện ngoại tuyến (Offline Training), mô hình LTR phải chứng minh khả năng vượt qua đường cơ sở (baseline) của Hybrid RRF với mức tăng tối thiểu ![][image20] Macro NDCG@10. Nếu độ tăng ích thấp hơn mức này, chi phí hạ tầng để duy trì máy chủ suy luận (inference servers) cho LTR là một khoản đầu tư lỗ.  
4. **Ngưỡng Ràng buộc Độ trễ (Latency Ceiling):** LTR chỉ được triển khai như một bước Re-ranking áp dụng trên tập Top 100 tài liệu đã được thu hẹp (Truncated List). Tổng thời gian thực thi end-to-end, tính từ lúc miCareer-mini gửi yêu cầu đến khi nhận lại danh sách đã rerank, phải đảm bảo ![][image21] Latency ![][image22].35 Nếu vượt quá, trải nghiệm người dùng sẽ bị phá vỡ.

## **Quản trị Rủi ro Kiến trúc và Hậu quả Kỹ thuật**

Triển khai một kiến trúc mới dựa trên các module tách rời mang lại sự linh hoạt nhưng cũng tiềm ẩn rủi ro phát sinh từ các điểm mù (blind spots) của hệ thống. Bảng dưới đây phân định các rủi ro hệ trọng nhất, tác động trực tiếp của chúng đối với hạ tầng và chiến lược ứng phó.

**Bảng 4: Phân tích Rủi ro và Chiến lược Giảm thiểu Kỹ thuật**

| Mã (ID) | Rủi ro Quyết định Kiến trúc (Architectural Risks) | Hậu quả Kỹ thuật và Vận hành (Technical Consequences) | Chiến lược Giảm thiểu và Khắc phục (Mitigation Strategy) |
| :---- | :---- | :---- | :---- |
| **R01** | Bật ép buộc tính năng Calibration bằng Isotonic Regression quá sớm khi thiếu dữ liệu mẫu. | Thuật toán xây dựng các hàm bậc thang lớn (large step functions) do quá khớp (overfitting). Dẫn đến tình trạng hàng chục ứng viên bị gán cùng một mức điểm xác suất giả tạo, triệt tiêu hoàn toàn khả năng phân định thứ hạng ở top đầu của hệ thống.20 | Thiết lập khóa kỹ thuật (feature gate) chặt chẽ. Buộc tuân thủ lộ trình Phase 1.5, khởi động bằng Platt Scaling trước khi tích lũy đủ \>10,000 nhãn để chạy Isotonic. |
| **R02** | Khai báo trọng số từ khóa (Keyword/BM25) quá cao (ví dụ: ![][image23]) trong công thức RRF lai. | NMAI extension bị thoái hóa về cấp độ của các ATS đời cũ. Khuyến khích hành vi "nhồi nhét từ khóa" (keyword stuffing) của ứng viên. Vector ngữ nghĩa mất tiếng nói, làm giảm thê thảm tỷ lệ tìm thấy ứng viên chuyển đổi ngành (Recall drop).15 | Mã hóa cứng (Hardcode) ngưỡng giới hạn an toàn cho biến môi trường: ![][image24]. Áp dụng thuật toán trừng phạt (penalty) tần suất từ khóa lặp lại bất thường. |
| **R03** | Thiết kế NMAI Extension như một khối nguyên khối (Monolithic coupling) gắn chặt vào FANG Core. | Bất kỳ lỗi tràn bộ nhớ (Memory Leak) hoặc treo luồng (Thread deadlock) trong quá trình tính toán RRF sẽ đánh sập FANG Core, làm gián đoạn toàn bộ hệ thống Parser 5-tier và RAG 7 modelMode.36 | Tuân thủ tuyệt đối nguyên tắc Middleware. NMAI extension phải được deploy như một vi dịch vụ (Microservice) hoặc Serverless function độc lập. Giao tiếp qua API không trạng thái (Stateless). |
| **R04** | Trình phân tích cú pháp (Parser) 5-tier gặp lỗi định dạng dị biệt, trả về chuỗi rỗng cho module BM25. | Giá trị ![][image25] trở nên vô cực, điểm RRF từ khóa sụp đổ về 0\. Ứng viên xuất sắc bị đẩy xuống đáy bảng xếp hạng chỉ vì dùng một template PDF phức tạp.1 | Tích hợp cơ chế Fallback Score in-memory. Nếu Sparse Vector báo rỗng, thuật toán NMAI tự động dồn toàn bộ trọng số (Weight transfer) ![][image26] sang ![][image27] để bù đắp bằng nhận thức ngữ nghĩa.7 |

## **Kế hoạch Triển khai (Sprint Roadmap 4 Tuần)**

Lộ trình dưới đây được thiết kế với phương pháp tiếp cận linh hoạt (Agile), phân chia thành 4 Sprint ngắn hạn nhằm đảm bảo khả năng cung cấp giá trị liên tục cho nền tảng miCareer-mini mà không gây gián đoạn cho FANG AI Core.

* **Sprint 1 (Tuần 1): Thiết lập Nền tảng NMAI và API Truy xuất (Variant A Baseline)**  
  * *Mục tiêu giao nghiệm (Deliverable):* Khởi tạo NMAI Extension dưới dạng Microservice. Xây dựng các API endpoints kết nối với FANG Core để truy xuất song song Top-200 Vector và Top-200 Keyword. Hoàn thành Variant A (Chỉ sử dụng Semantic Vector).  
  * *Tiêu chí hoàn thành (Pass Criteria):* Hệ thống định tuyến thành công các yêu cầu từ miCareer-mini. P95 Latency của toàn bộ quá trình giao tiếp (round-trip) duy trì ở mức ![][image28]. Không có lỗi sập kết nối (timeout).  
* **Sprint 2 (Tuần 2): Tích hợp Hybrid RRF và Động cơ Trọng số (Variant B Deployment)**  
  * *Mục tiêu giao nghiệm:* Cài đặt thuật toán Weighted RRF trực tiếp trên bộ nhớ (in-memory) của NMAI. Tích hợp module tính toán Siêu dữ liệu (![][image29]). Thiết lập hệ thống biến môi trường để hỗ trợ thao tác bật/tắt (feature flags) bộ trọng số bất đối xứng (J2C và C2J).  
  * *Tiêu chí hoàn thành:* Bảng xếp hạng từ Variant B thể hiện sự khác biệt thống kê (thông qua Jaccard similarity) so với Variant A. Việc điều chỉnh trọng số thông qua cấu hình có hiệu lực ngay lập tức (Zero-downtime reconfiguration).  
* **Sprint 3 (Tuần 3): Thu thập Hệ thống Nhãn và Khởi chạy A/B Testing (Evaluation Phase)**  
  * *Mục tiêu giao nghiệm:* Tích hợp luồng ghi log (logging pipeline) đồng bộ với cơ sở dữ liệu ATS để cập nhật nhãn Graded Relevance (0-4) theo thời gian thực. Khởi động A/B Testing, điều hướng 15% traffic thực tế vào Variant B. Xây dựng Dashboard tính toán Macro NDCG@10.  
  * *Tiêu chí hoàn thành:* Dữ liệu log không bị thất thoát Session ID. Bảng điều khiển (Dashboard) hiển thị tự động và chính xác chỉ số Macro NDCG cho cả hai chiều. Variant B chứng minh được ![][image18] NDCG dương (tăng trưởng) so với Variant A.  
* **Sprint 4 (Tuần 4): Chuẩn bị Hạ tầng Calibration & Củng cố Rủi ro (Shadow Mode & Stability)**  
  * *Mục tiêu giao nghiệm:* Viết mã cho các module Platt Scaling và Isotonic Regression, nhưng chỉ triển khai dưới dạng chạy ngầm (Shadow mode \- Variant C) để hấp thụ log và mô phỏng hiệu chuẩn. Hoàn thiện hệ thống Fallback Score đối phó với lỗi Parser.  
  * *Tiêu chí hoàn thành:* Các module Calibration chạy ngầm không tiêu thụ quá 5% tài nguyên CPU của NMAI extension. Báo cáo đánh giá mức độ lệch phân phối điểm số (Score Skewness) được trích xuất thành công, chuẩn bị hồ sơ kỹ thuật đầy đủ để kích hoạt Phase 1.5 trong tương lai.

## **Danh sách Quyết định Cuối cùng (Dành cho Issue Tracker)**

Phần này tóm lược các quyết định kiến trúc cốt lõi dưới dạng các thẻ hành động (actionable items) sẵn sàng để sao chép trực tiếp vào hệ thống quản lý công việc (Jira/Trello).

1. **\[Architecture\]** Khởi tạo NMAI Extension như một Middleware (Microservice) hoàn toàn độc lập, tách biệt vòng đời triển khai khỏi FANG AI Core. Tính toán dung hợp (Fusion) diễn ra in-memory.  
2. **\[Algorithm\]** Kích hoạt Weighted Reciprocal Rank Fusion (Weighted RRF) là thuật toán lõi. Thiết lập hằng số làm mượt mặc định ![][image5].  
3. \*\*\*\* Áp dụng bộ trọng số bất đối xứng. Chiều Candidate-to-Job (Ứng viên tìm việc): ![][image30]. Chiều Job-to-Candidate (Tuyển dụng tìm CV): ![][image31]. Mọi thay đổi thao tác qua Feature Flags.  
4. **\[Calibration\]** Chặn (Block) kích hoạt hiệu chuẩn điểm (Platt/Isotonic) ở Phase 1\. Chỉ đưa vào Shadow Mode để thu thập dữ liệu. Thiết lập trigger kích hoạt Phase 1.5 khi đạt ![][image32] nhãn ATS.  
5. **\[Metrics\]** Khởi tạo pipeline tính toán Macro NDCG@10 (cho Recruiter) và Macro NDCG@20 (cho Candidate). Hệ thống sử dụng thang điểm Graded Relevance 5 mức (0: Reject, 1: Applied, 2: Screened, 3: Interview, 4: Offered).  
6. \*\*\*\* Điều hướng traffic qua API Gateway để chạy song song: Variant A (Vector Baseline) và Variant B (Hybrid RRF).  
7. **\[Fallback\]** Mã hóa quy tắc chuyển trọng số (Weight Transfer Rule): Nếu API Sparse Vector trả về lỗi hoặc tập rỗng do Parser sập, tự động chuyển toàn bộ giá trị ![][image26] sang ![][image27] để duy trì xếp hạng.  
8. \*\*\*\* Cấu hình khóa nâng cấp kiến trúc Neural Reranker (LTR) cho đến khi Heuristic RRF đạt trạng thái bão hòa (Độ tăng NDCG ![][image33] qua 2 Sprint liên tiếp) và P95 Latency của LTR được chứng minh giới hạn dưới ![][image34].

#### **Nguồn trích dẫn**

1. The 5-Minute ATS Resume Checklist to Avoid Costly Parsing Errors and Boost Relevance Scores \- AscendurePro, truy cập vào tháng 4 23, 2026, [https://ascendurepro.com/ats-resume-checklist/](https://ascendurepro.com/ats-resume-checklist/)  
2. A Comprehensive Hybrid Search Guide | Elastic, truy cập vào tháng 4 23, 2026, [https://www.elastic.co/what-is/hybrid-search](https://www.elastic.co/what-is/hybrid-search)  
3. Replacing Re-ranking with Selection in RAG for Sensitive Domains \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2505.16014v3](https://arxiv.org/html/2505.16014v3)  
4. Revisiting Reciprocal Recommender Systems: Metrics, Formulation, and Method \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/pdf/2408.09748](https://arxiv.org/pdf/2408.09748)  
5. (PDF) A Study of Reciprocal Job Recommendation for College Graduates Integrating Semantic Keyword Matching and Social Networking \- ResearchGate, truy cập vào tháng 4 23, 2026, [https://www.researchgate.net/publication/375650973\_A\_Study\_of\_Reciprocal\_Job\_Recommendation\_for\_College\_Graduates\_Integrating\_Semantic\_Keyword\_Matching\_and\_Social\_Networking](https://www.researchgate.net/publication/375650973_A_Study_of_Reciprocal_Job_Recommendation_for_College_Graduates_Integrating_Semantic_Keyword_Matching_and_Social_Networking)  
6. Revisiting Reciprocal Recommender Systems: Metrics, Formulation, and Method \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2408.09748v1](https://arxiv.org/html/2408.09748v1)  
7. Understand Hybrid Search \- Oracle Help Center, truy cập vào tháng 4 23, 2026, [https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/understand-hybrid-search.html](https://docs.oracle.com/en/database/oracle/oracle-database/23/vecse/understand-hybrid-search.html)  
8. Reciprocal Rank Fusion and Relative Score Fusion: Classic Hybrid Search Techniques | by MongoDB \- Medium, truy cập vào tháng 4 23, 2026, [https://medium.com/mongodb/reciprocal-rank-fusion-and-relative-score-fusion-classic-hybrid-search-techniques-3bf91008b81d](https://medium.com/mongodb/reciprocal-rank-fusion-and-relative-score-fusion-classic-hybrid-search-techniques-3bf91008b81d)  
9. Weighted reciprocal rank fusion(RRF) in Elasticsearch, truy cập vào tháng 4 23, 2026, [https://www.elastic.co/search-labs/blog/weighted-reciprocal-rank-fusion-rrf](https://www.elastic.co/search-labs/blog/weighted-reciprocal-rank-fusion-rrf)  
10. Relevance scoring in hybrid search using Reciprocal Rank Fusion (RRF) \- Microsoft Learn, truy cập vào tháng 4 23, 2026, [https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking](https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking)  
11. What is Reciprocal Rank Fusion? \- ParadeDB, truy cập vào tháng 4 23, 2026, [https://www.paradedb.com/learn/search-concepts/reciprocal-rank-fusion](https://www.paradedb.com/learn/search-concepts/reciprocal-rank-fusion)  
12. Hybrid AI Search: Vector \+ Keyword Matching for Smarter Results | by Thinking Loop, truy cập vào tháng 4 23, 2026, [https://medium.com/@ThinkingLoop/hybrid-ai-search-vector-keyword-matching-for-smarter-results-bc4b6239eb91](https://medium.com/@ThinkingLoop/hybrid-ai-search-vector-keyword-matching-for-smarter-results-bc4b6239eb91)  
13. Hybrid Search Explained | Weaviate, truy cập vào tháng 4 23, 2026, [https://weaviate.io/blog/hybrid-search-explained](https://weaviate.io/blog/hybrid-search-explained)  
14. Hybrid Search Fusion Ranking \- Salesforce Help, truy cập vào tháng 4 23, 2026, [https://help.salesforce.com/s/articleView?id=data.c360\_a\_hybridsearch\_fusion\_ranking.htm\&language=en\_US\&type=5](https://help.salesforce.com/s/articleView?id=data.c360_a_hybridsearch_fusion_ranking.htm&language=en_US&type=5)  
15. The Complete Guide to Hybrid Search: The Perfect Blend of Full-Text and Vector Search, truy cập vào tháng 4 23, 2026, [https://www.alibabacloud.com/blog/the-complete-guide-to-hybrid-search-the-perfect-blend-of-full-text-and-vector-search\_602921](https://www.alibabacloud.com/blog/the-complete-guide-to-hybrid-search-the-perfect-blend-of-full-text-and-vector-search_602921)  
16. Aman's AI Journal • Recommendation Systems • Calibration, truy cập vào tháng 4 23, 2026, [https://aman.ai/recsys/callibration/](https://aman.ai/recsys/callibration/)  
17. Classifier calibration with Platt's scaling and isotonic regression \- FastML, truy cập vào tháng 4 23, 2026, [https://fastml.com/classifier-calibration-with-platts-scaling-and-isotonic-regression/](https://fastml.com/classifier-calibration-with-platts-scaling-and-isotonic-regression/)  
18. Smooth Isotonic Regression: A New Method to Calibrate Predictive Models \- PMC, truy cập vào tháng 4 23, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC3248752/](https://pmc.ncbi.nlm.nih.gov/articles/PMC3248752/)  
19. When Your Probabilities Lie — A Hands-On Guide to Probability Calibration \- Medium, truy cập vào tháng 4 23, 2026, [https://medium.com/@iamban/why-your-probabilities-lie-a-hands-on-guide-to-probability-calibration-5bc05e4cdb9e](https://medium.com/@iamban/why-your-probabilities-lie-a-hands-on-guide-to-probability-calibration-5bc05e4cdb9e)  
20. Postprint \- Diva-portal.org, truy cập vào tháng 4 23, 2026, [https://www.diva-portal.org/smash/get/diva2:1791506/FULLTEXT01.pdf](https://www.diva-portal.org/smash/get/diva2:1791506/FULLTEXT01.pdf)  
21. Calibration Techniques and it's importance in Machine Learning \- Subham Sarkar \- Medium, truy cập vào tháng 4 23, 2026, [https://kingsubham27.medium.com/calibration-techniques-and-its-importance-in-machine-learning-71bec997b661](https://kingsubham27.medium.com/calibration-techniques-and-its-importance-in-machine-learning-71bec997b661)  
22. Normalized Discounted Cumulative Gain (NDCG) \- The Ultimate Ranking Metric, truy cập vào tháng 4 23, 2026, [https://towardsdatascience.com/normalized-discounted-cumulative-gain-ndcg-the-ultimate-ranking-metric-437b03529f75/](https://towardsdatascience.com/normalized-discounted-cumulative-gain-ndcg-the-ultimate-ranking-metric-437b03529f75/)  
23. Measuring Search Relevance, Part 2: nDCG Deep Dive \- Reddit, truy cập vào tháng 4 23, 2026, [https://www.reddit.com/r/RedditEng/comments/y6idrl/measuring\_search\_relevance\_part\_2\_ndcg\_deep\_dive/](https://www.reddit.com/r/RedditEng/comments/y6idrl/measuring_search_relevance_part_2_ndcg_deep_dive/)  
24. How Applicant Tracking Systems Actually Work in 2026 | Huntr Blog, truy cập vào tháng 4 23, 2026, [https://huntr.co/blog/how-applicant-tracking-systems-work](https://huntr.co/blog/how-applicant-tracking-systems-work)  
25. Evaluating information retrieval with NDCG@K & Redis, truy cập vào tháng 4 23, 2026, [https://redis.io/blog/evaluating-information-retrieval-with-ndcgk-redis/](https://redis.io/blog/evaluating-information-retrieval-with-ndcgk-redis/)  
26. Understanding hybrid search RAG for better AI answers \- Meilisearch, truy cập vào tháng 4 23, 2026, [https://www.meilisearch.com/blog/hybrid-search-rag](https://www.meilisearch.com/blog/hybrid-search-rag)  
27. PJB: A Reasoning-Aware Benchmark for Person-Job Retrieval \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2603.17386](https://arxiv.org/html/2603.17386)  
28. Evaluating recommendation systems (mAP, MMR, NDCG) \- Shaped.ai, truy cập vào tháng 4 23, 2026, [https://www.shaped.ai/blog/evaluating-recommendation-systems-map-mmr-ndcg](https://www.shaped.ai/blog/evaluating-recommendation-systems-map-mmr-ndcg)  
29. Understanding Semantic Search — (Part 5: Ranking Metrics for Evaluating Question Answering Systems) \- Kaushik Shakkari, truy cập vào tháng 4 23, 2026, [https://kaushikshakkari.medium.com/understanding-semantic-search-part-5-ranking-metrics-for-evaluating-question-answering-systems-f3150872d986](https://kaushikshakkari.medium.com/understanding-semantic-search-part-5-ranking-metrics-for-evaluating-question-answering-systems-f3150872d986)  
30. Ranking Evaluation Metrics for Recommender Systems | by Benjamin Wang \- Medium, truy cập vào tháng 4 23, 2026, [https://medium.com/data-science/ranking-evaluation-metrics-for-recommender-systems-263d0a66ef54](https://medium.com/data-science/ranking-evaluation-metrics-for-recommender-systems-263d0a66ef54)  
31. Ranking Evaluation Metrics for Recommender Systems | Towards Data Science, truy cập vào tháng 4 23, 2026, [https://towardsdatascience.com/ranking-evaluation-metrics-for-recommender-systems-263d0a66ef54/](https://towardsdatascience.com/ranking-evaluation-metrics-for-recommender-systems-263d0a66ef54/)  
32. Learning to Rank: A Complete Guide to Ranking using Machine Learning | by Francesco Casalegno | TDS Archive | Medium, truy cập vào tháng 4 23, 2026, [https://medium.com/data-science/learning-to-rank-a-complete-guide-to-ranking-using-machine-learning-4c9688d370d4](https://medium.com/data-science/learning-to-rank-a-complete-guide-to-ranking-using-machine-learning-4c9688d370d4)  
33. Exploring depth in a 'retrieve-and-rerank' pipeline \- Elastic, truy cập vào tháng 4 23, 2026, [https://www.elastic.co/search-labs/blog/elastic-semantic-reranker-part-3](https://www.elastic.co/search-labs/blog/elastic-semantic-reranker-part-3)  
34. Learning to Rank with Top-K Fairness \- arXiv, truy cập vào tháng 4 23, 2026, [https://arxiv.org/html/2509.18067v1](https://arxiv.org/html/2509.18067v1)  
35. Calibrating reranker thresholds in production RAG (What worked for us) \- Reddit, truy cập vào tháng 4 23, 2026, [https://www.reddit.com/r/Rag/comments/1ojkisg/calibrating\_reranker\_thresholds\_in\_production\_rag/](https://www.reddit.com/r/Rag/comments/1ojkisg/calibrating_reranker_thresholds_in_production_rag/)  
36. Master Advanced Search: Ranking, Fusion, and Reranking Explained \- Progress Software, truy cập vào tháng 4 23, 2026, [https://www.progress.com/blogs/master-advanced-search-ranking-fusion-and-reranking-explained](https://www.progress.com/blogs/master-advanced-search-ranking-fusion-and-reranking-explained)

[image1]: images/NMAIex_th_4/image1.png

[image2]: images/NMAIex_th_4/image2.png

[image3]: images/NMAIex_th_4/image3.png

[image4]: images/NMAIex_th_4/image4.png

[image5]: images/NMAIex_th_4/image5.png

[image6]: images/NMAIex_th_4/image6.png

[image7]: images/NMAIex_th_4/image7.png

[image8]: images/NMAIex_th_4/image8.png

[image9]: images/NMAIex_th_4/image9.png

[image10]: images/NMAIex_th_4/image10.png

[image11]: images/NMAIex_th_4/image11.png

[image12]: images/NMAIex_th_4/image12.png

[image13]: images/NMAIex_th_4/image13.png

[image14]: images/NMAIex_th_4/image14.png

[image15]: images/NMAIex_th_4/image15.png

[image16]: images/NMAIex_th_4/image16.png

[image17]: images/NMAIex_th_4/image17.png

[image18]: images/NMAIex_th_4/image18.png

[image19]: images/NMAIex_th_4/image19.png

[image20]: images/NMAIex_th_4/image20.png

[image21]: images/NMAIex_th_4/image21.png

[image22]: images/NMAIex_th_4/image22.png

[image23]: images/NMAIex_th_4/image23.png

[image24]: images/NMAIex_th_4/image24.png

[image25]: images/NMAIex_th_4/image25.png

[image26]: images/NMAIex_th_4/image26.png

[image27]: images/NMAIex_th_4/image27.png

[image28]: images/NMAIex_th_4/image28.png

[image29]: images/NMAIex_th_4/image29.png

[image30]: images/NMAIex_th_4/image30.png

[image31]: images/NMAIex_th_4/image31.png

[image32]: images/NMAIex_th_4/image32.png

[image33]: images/NMAIex_th_4/image33.png

[image34]: images/NMAIex_th_4/image34.png

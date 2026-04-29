# **Báo Cáo Quyết Định Kiến Trúc: Phân Hệ Xếp Hạng Hai Chiều NMAI Extension Trên Nền Tảng FANG Core**

## **Tóm Tắt Điều Hành**

Báo cáo phân tích kiến trúc này cung cấp bản thiết kế kỹ thuật toàn diện nhằm triển khai phân hệ NMAI (NMAI extension) phục vụ bài toán xếp hạng hai chiều trên nền tảng FANG AI Core hiện hữu. Mục tiêu cốt lõi là thiết lập cơ chế tự động phân loại và sắp xếp danh sách công việc theo ứng viên, cũng như danh sách ứng viên theo công việc, trong bối cảnh tính năng giải thích bằng mô hình ngôn ngữ lớn (explain-by-LLM) chưa được kích hoạt. Phân tích chỉ ra rằng việc chỉ sử dụng truy xuất vector thuần túy gây ra sai lệch nghiêm trọng về đánh giá cấp độ chuyên môn. Do đó, kiến trúc được đề xuất sử dụng chiến lược Hợp nhất Muộn (Late Fusion), kết hợp thuật toán Reciprocal Rank Fusion (RRF) cho dữ liệu văn bản và các Hàm Phạt Tuyến tính (Linear Penalty Functions) cho dữ liệu định lượng. Quyết định kỹ thuật nhấn mạnh việc duy trì hệ trọng số phi đối xứng giữa hai luồng truy vấn, đồng thời khuyến nghị dời thời điểm kích hoạt cơ chế hiệu chuẩn tự động (Calibration) sang Giai đoạn 1.5, sau khi hệ thống tổng hợp dữ liệu ATS mô phỏng đạt đủ quy mô. Mọi sự thay đổi được thiết kế dưới dạng cấu hình cờ tính năng (Feature Toggle) để tuân thủ ràng buộc can thiệp tối thiểu vào FANG core, đảm bảo khả năng giám sát qua các độ đo nDCG@10 và MRR, thiết lập tiền đề vững chắc trước khi chuyển đổi sang mô hình tái xếp hạng có giám sát (Supervised Reranker).

## **Bối Cảnh Hệ Sinh Thái và Triết Lý Phân Hệ Khuyến Nghị Tương Hỗ**

Việc thiết kế một hệ thống trí tuệ nhân tạo trong không gian tuyển dụng đòi hỏi một sự dịch chuyển hệ hình từ các mô hình truy xuất thông tin truyền thống sang mô hình Hệ thống Khuyến nghị Tương hỗ (Reciprocal Recommender System \- RRS).1 Trong một bài toán tìm kiếm tài liệu thông thường, tài liệu là các thực thể thụ động. Ngược lại, thị trường tuyển dụng là một nền kinh tế ghép nối hai mặt (two-sided matching market), nơi cả ứng viên và nhà tuyển dụng đều hoạt động như những tác nhân có quyền tự quyết, mang theo những kỳ vọng độc lập và các rào cản tương tác riêng biệt.1 Một lượt ghép nối chỉ được định nghĩa là thành công khi có sự đồng thuận song phương, được biểu diễn qua xác suất hợp tính $P(Match | C, J)$, là tích số của xác suất ứng viên nộp hồ sơ $P(C \rightarrow J)$ và xác suất nhà tuyển dụng chấp thuận phỏng vấn $P(J \rightarrow C)$.1

Kiến trúc hiện tại của hệ sinh thái miCareer được phân tách rõ ràng giữa máy khách mỏng (thin client) miCareer-mini và hệ thống trung tâm FANG v2.0 AI Core.1 FANG v2.0 hoạt động như một máy chủ REST API độc lập dựa trên FastAPI, chịu trách nhiệm quản lý toàn bộ vòng đời phân tích từ việc tiếp nhận tài liệu (Ingestion Pipeline) đến quá trình xử lý truy vấn thế hệ tăng cường truy xuất (RAG Chat Pipeline).1 Nền tảng cốt lõi này đã được trang bị một hệ thống phân tích sơ yếu lý lịch (CV Parser) có cơ chế dự phòng 5 cấp độ (5-tier fallback), sử dụng một loạt các mô hình ngôn ngữ từ nhóm Lite (như Gemini Flash, GPT-5.4 mini) đến nhóm Pro (như GPT-5.4).1 Cơ sở hạ tầng này đảm bảo rằng các thuộc tính siêu dữ liệu quan trọng như số năm kinh nghiệm, kỹ năng và học vấn được trích xuất với độ tin cậy cao nhất có thể trước khi dữ liệu bị phân mảnh và nhúng vào không gian vector.1 Hơn nữa, hệ thống FANG quản lý ngân sách ngữ cảnh thông qua 7 chế độ modelMode (từ auto-lite đến gpt-full), cho phép linh hoạt trong việc đánh đổi giữa tốc độ phản hồi và khả năng lập luận của AI.1

Trong bối cảnh tính năng giải thích kết quả qua LLM (explain-by-LLM) chưa được ưu tiên, gánh nặng về độ tin cậy được đặt hoàn toàn lên vai thuật toán xếp hạng. Module NMAI extension phải được thiết kế như một lớp trung gian (middleware/extension layer) hoạt động độc lập ngay phía trên lớp cơ sở dữ liệu PostgreSQL (pgvector), tái sử dụng toàn bộ đường ống đã được xây dựng mà không làm gián đoạn luồng thực thi của 7 chế độ modelMode hiện có.1 Dữ liệu hiện tại được biểu diễn dưới dạng halfvec(1024)—một kiểu dữ liệu số thực dấu phẩy động 16-bit được tạo ra bởi mô hình text-embedding-3-small.1 Mặc dù kiểu dữ liệu này tối ưu hóa dung lượng RAM cho thuật toán tìm kiếm lân cận xấp xỉ HNSW, việc chỉ dựa vào phép đo tương đồng Cosine (Cosine Similarity) trên tập vector này đã bộc lộ những khiếm khuyết cơ bản.1 Các mô hình nhúng ngôn ngữ lớn gặp khó khăn nghiêm trọng trong việc thấu hiểu dữ liệu định lượng, dẫn đến tình trạng "đồng nhất hóa không gian ngữ nghĩa", nơi một ứng viên sơ cấp nhưng sử dụng chung bộ từ vựng công nghệ có thể được hệ thống đánh giá ngang hàng với một chuyên gia dày dạn kinh nghiệm.1 Do đó, NMAI extension bắt buộc phải áp dụng một phương pháp luận kết hợp, tận dụng sức mạnh truy xuất của vector song song với việc áp đặt các rào cản quy tắc kinh doanh chặt chẽ thông qua siêu dữ liệu.

## **Thiết Kế Công Thức Hợp Nhất Hệ Số Điểm Hỗn Hợp (Hybrid Scoring)**

Sự phân cực giữa khả năng nắm bắt ngữ nghĩa trừu tượng của mô hình vector và sự cần thiết của các rào cản logic cứng nhắc đã định hình quyết định loại bỏ mô hình Vector-only thuần túy.1 Quyết định kiến trúc cho NMAI extension là triển khai chiến lược Xếp hạng Tuyến tính Lai (Hybrid Search \+ Linear Scoring).1 Chiến lược này không chỉ giải quyết được giới hạn về địa lý hay sự đồng nghĩa của từ khóa mà còn cho phép hiệu chỉnh trọng số động dựa trên đặc thù của từng vai trò tìm kiếm.1 Mặc dù phương pháp Reciprocal Rank Fusion (RRF) có lợi thế vượt trội về tính dễ dàng khi triển khai—đặc biệt là khả năng kết hợp hai danh sách xếp hạng có thang đo hoàn toàn khác biệt (vector similarity và BM25 text score) mà không cần chuẩn hóa thống kê—việc sử dụng RRF như công cụ duy nhất lại mang đến rủi ro nghiêm trọng trong bài toán tuyển dụng.1 RRF thiếu đi năng lực "trừng phạt" (veto power), nghĩa là một hồ sơ có thể thiếu hụt trầm trọng một kỹ năng cốt lõi nhưng vẫn có thể nổi lên đầu danh sách chỉ nhờ văn phong trình bày hoặc các kỹ năng thứ cấp tương đồng.1

Để khắc phục rào cản này, công thức điểm cuối cùng được cấu trúc dưới dạng một ma trận hàm Hợp nhất Muộn (Late Fusion), nơi điểm số cơ sở của RRF được điều chỉnh bởi một chuỗi các hàm phạt phi tuyến và hệ số tuyến tính được xác định thông qua siêu dữ liệu có cấu trúc. Công thức tổng quát áp dụng cho module NMAI như sau:

| Thành phần Thuật toán | Cấu trúc Toán học Triển khai | Phân tích Ràng buộc và Vai trò Nghiệp vụ |
| :---- | :---- | :---- |
| **Reciprocal Rank Fusion (RRF)** | CT_1 | Thiết lập điểm số ngữ nghĩa nền tảng.1 Hằng số điều hòa $k = 60$ được lựa chọn để chống lại hiện tượng chi phối tuyệt đối của kết quả top 1 ở một trong hai cơ chế tìm kiếm, đảm bảo sự phân phối mượt mà trên dải phổ Top 100 kết quả.1 |
| **Điểm Cơ Sở Hợp Nhất (Base Score)** | CT_2 | Tích hợp lớp tín hiệu mạnh (Strong Signals).1 Tại đây, độ đo $Skill\_Overlap$ được điều chỉnh bởi hệ số "độ tươi" (Recency), đánh giá cao các kỹ năng được thực hành liên tục trong 6 tháng gần nhất, vượt trội hơn các kỹ năng đã không sử dụng trong 5 năm.1 |
| **Hàm Phạt Biến Trở (Penalty Decay)** | CT_3 | Cấu phần quan trọng nhất tạo nên tính thực tiễn. Áp dụng các trọng số phủ quyết trực tiếp nhằm giảm trừ điểm số khi hệ thống phát hiện sự bất cân xứng định lượng vượt quá năng lực hoặc kỳ vọng (ví dụ: Seniority Gap hoặc Salary Gap).1 |

Việc quyết định công thức này tạo ra một tác động sâu rộng đối với hệ thống lõi. Thay vì để mô hình text-embedding-3-small tự giải quyết toàn bộ bài toán phân loại, chúng ta giải phóng mô hình này khỏi nhiệm vụ phân tích logic, giới hạn vai trò của nó ở việc cung cấp ứng viên có độ tương đồng bề mặt, sau đó áp dụng logic nghiệp vụ như một bộ lọc màng lưới khắt khe. Điều này đáp ứng chính xác yêu cầu triển khai nhanh ngay trên extension layer mà không yêu cầu huấn luyện lại hoặc thay đổi bản chất của FANG AI Core.

CT_1 = $$RRF\_Score(d) = \frac{1}{60 + rank_{vec}(d)} + \frac{1}{60 + rank_{text}(d)}$$

CT_2 = $$Score_{base} = (w_{rrf} \cdot RRF\_Score) + (w_{skill} \cdot Skill\_Overlap) + \dots$$

CT_3 = $$Final\_Score = Score_{base} - \sum (Penalty_{j} \cdot Gap(Req, Cand))$$

## **Chiến Lược Phân Bổ Trọng Số Khởi Tạo Cho Giai Đoạn 1**

Việc phân bổ bộ trọng số khởi tạo (Initial Weights) không thể tuân theo một cấu hình đối xứng đơn giản. Bản chất của bài toán ghép nối hai mặt quy định rằng nhà tuyển dụng và ứng viên sử dụng hệ thống với mục tiêu và sự khoan dung hoàn toàn trái ngược nhau. Mọi hệ số được đề xuất dưới đây đi kèm với đánh giá chi tiết về sự đánh đổi (Trade-off) giữa Độ chính xác (Accuracy), Độ trễ (Latency) và Độ phức tạp vận hành (Operational Complexity). Mọi hệ số đều có khả năng bật tắt qua tệp tin cấu hình môi trường .env hoặc cơ sở dữ liệu để đáp ứng ràng buộc của nền tảng FANG.1

### **Luồng 1: Danh sách Ứng viên Xếp hạng theo Công việc (Job $\rightarrow$ Candidate)**

Trong không gian tìm kiếm này, nhà tuyển dụng là những người sử dụng có quỹ thời gian hạn hẹp, thường xuyên lướt qua hồ sơ trong thời gian ngắn.1 Họ không có độ khoan dung cho các ứng viên thiếu năng lực cốt lõi. Nhiệm vụ chính của luồng này là tối ưu hóa độ chuẩn xác (Precision) và ưu tiên hiển thị các ứng viên có khả năng tham gia vào dự án ngay lập tức với chi phí đào tạo tối thiểu.1

| Trọng số Khởi tạo & Tên Đặc trưng | Đề xuất Trọng số (w) | Trade-off: Độ chính xác / Độ trễ / Vận hành | Lý do Nghiệp vụ (Business Rationale) và Suy luận Cơ chế |
| :---- | :---- | :---- | :---- |
| **Điểm Hỗn hợp Ngữ nghĩa $w_{rrf}$** | 0.30 | **Độ trễ:** Tăng trưởng thời gian truy vấn khoảng 15-20ms do yêu cầu thực thi song song thuật toán tìm kiếm láng giềng gần nhất (k-NN) trong pgvector và truy xuất full-text BM25. | Trọng số được cấu hình ở mức thấp nhằm hạn chế sự thiên kiến văn phong.1 Hệ thống không được phép xếp hạng cao một ứng viên chỉ vì người đó vô tình sử dụng cùng một cấu trúc câu với bản mô tả công việc (Job Description) mà thiếu bằng chứng thực tế về kỹ năng. |
| **Giao thoa Kỹ năng ($w_{skill}$)** | 0.40 | **Vận hành:** Tăng chi phí bảo trì hệ thống. Yêu cầu bộ phận dữ liệu liên tục cập nhật và duy trì một Taxonomy (Hệ thống phân loại) và Ontology các từ đồng nghĩa kỹ thuật để tính toán.1 | Yếu tố cốt lõi và trực diện nhất định hình năng lực công việc.1 Khả năng kết nối các kỹ năng thông qua phân tích cú pháp 5-tier từ sơ yếu lý lịch đóng vai trò quyết định, đặc biệt là khi kết hợp với yếu tố độ tươi (Recency) của kỹ năng trong quá khứ gần.1 |
| **Hàm Phạt Thâm niên ($Penalty_{sen}$)** | Hàm phi tuyến | **Chính xác:** Cực đại hóa chất lượng top K. Ngăn chặn triệt để âm tính giả và dương tính giả ở cấp độ vị trí. | Đây là đặc trưng phủ quyết.1 Cơ chế này sử dụng chênh lệch (Delta Feature) giữa expyears trong cơ sở dữ liệu.1 Sự chênh lệch thâm niên quá lớn (ví dụ: Junior ứng tuyển vị trí Senior) sẽ tự động kích hoạt suy hao điểm số hàm mũ, đánh bật ứng viên ra khỏi danh sách hiển thị ưu tiên bất chấp điểm RRF có cao đến đâu.1 |
| **Nhiễu Học vấn ($w_{edu}$)** | 0.00 | **Vận hành:** Giảm tải tính toán. Không cần xử lý các chuỗi văn bản danh xưng học thuật phức tạp từ bộ phân tích (Parser).1 | Trong bối cảnh tuyển dụng lĩnh vực công nghệ hiện đại, học vấn thuần túy thường mang lại nhiễu và thiên kiến (Bias) lớn hơn là giá trị dự đoán năng lực thực tế so với các dự án mã nguồn mở hoặc kinh nghiệm thương mại.1 |

### **Luồng 2: Danh sách Công việc Xếp hạng theo Ứng viên (Candidate $\rightarrow$ Job)**

Ứng viên hoạt động theo cơ chế khám phá sự nghiệp. Họ sẵn sàng tiếp nhận các cơ hội chéo (Career Pivot) và học hỏi kỹ năng mới, do đó hệ thống cần ưu tiên độ phủ và sự đa dạng (Recall & Diversity) bằng các chiến lược suy luận đa bước.1 Tuy nhiên, các rào cản cứng về quyền lợi cá nhân không cho phép sự nhân nhượng.

| Trọng số Khởi tạo & Tên Đặc trưng | Đề xuất Trọng số (w) | Trade-off: Độ chính xác / Độ trễ / Vận hành | Lý do Nghiệp vụ (Business Rationale) và Suy luận Cơ chế |
| :---- | :---- | :---- | :---- |
| **Điểm Hỗn hợp Ngữ nghĩa $w_{rrf}$** | 0.35 | **Độ chính xác:** Có thể dẫn đến một số gợi ý công việc bề ngoài không liên quan trực tiếp, nhưng giúp tăng cường khả năng phát hiện tiềm năng chéo (Serendipity). | Trọng số cao hơn luồng ngược lại. Mục tiêu là cho phép ứng viên khám phá những quỹ đạo sự nghiệp tiềm năng dựa trên các năng lực tương đồng, ví dụ: chuyển đổi từ Data Analyst sang Machine Learning Engineer nếu họ sở hữu nền tảng thống kê và kỹ năng lập trình cơ bản vững chắc.1 |
| **Hàm Phạt Khoảng cách Lương ($Penalty_{sal}$)** | Phạt tuyến tính | **Chính xác:** Thu hẹp phổ lựa chọn, nhưng bảo vệ tỷ lệ "Mutual Match Rate" (Đồng thuận song phương). | Mức lương (dữ liệu từ minSalary, maxSalary) là rào cản sinh tồn.1 Một công việc dẫu phù hợp 100% về kỹ năng nhưng đề xuất mức thù lao thấp hơn 20% so với kỳ vọng của ứng viên sẽ bị áp dụng hàm suy hao tuyến tính, vì xác suất ứng viên chấp nhận phỏng vấn là gần như bằng không.1 |
| **Ràng buộc Không gian/Thời gian ($w_{loc/mode}$)** | Bộ lọc Tiền xử lý (Hard Filter) | **Độ trễ:** Giảm thiểu độ trễ truy vấn một cách cực đoan (Ultra-low latency) nhờ khả năng loại bỏ hàng chục ngàn bản ghi không phù hợp khỏi không gian tìm kiếm vector ngay từ lớp SQL.1 | Địa điểm làm việc (workLoc) và hình thức làm việc (workMode \- Remote/Hybrid) là những yếu tố định tuyến cứng.1 Nếu ứng viên ở Hà Nội chỉ nhận làm việc từ xa, không có lý do gì để tính toán Cosine Similarity cho các vị trí yêu cầu làm việc tại văn phòng ở TP.HCM.1 |
| **Nhiễu Chức danh ($w_{title}$)** | 0.15 | **Chính xác:** Sự nhập nhằng trong cấu trúc danh xưng công nghiệp có thể vô tình tạo ra kết quả nhiễu nếu không có taxonomy chuẩn xác. | Việc khớp chính xác chức danh (Title Match) đóng vai trò giúp ứng viên có cảm giác an toàn và quen thuộc. Tuy nhiên, trọng số bị giới hạn ở 0.15 vì sự thiếu nhất quán (ví dụ: VP Engineering tại startup chỉ tương đương Senior Engineer tại tập đoàn lớn).1 |

## **Lộ Trình Hiệu Chuẩn Hệ Số Tự Động (Calibration Roadmap)**

Một trong những quyết định kỹ thuật then chốt là xác định thời điểm tích hợp cơ chế tự động hiệu chuẩn (Dynamic Calibration). Chức năng này—bao gồm Hiệu chuẩn Trọng số theo Hướng (Directional Weight Calibration) và Hiệu chuẩn Hàm Phạt (Penalty Calibration)—về mặt lý thuyết là cực kỳ hiệu quả để đối phó với sự bất cân xứng của bài toán RRS.1 Tuy nhiên, từ quan điểm của một Principal AI Architect, khuyến nghị bắt buộc là **giữ nguyên trọng số tĩnh ở Giai đoạn 1 và chỉ kích hoạt Calibration tại Giai đoạn 1.5**, đi kèm với các điều kiện giới hạn chặt chẽ.

Quyết định trì hoãn này xuất phát từ bản chất dữ liệu hiện tại của hệ sinh thái miCareer. Ở thời điểm hiện tại, phân hệ máy khách mỏng miCareer-mini chưa thể tạo ra đủ lưu lượng tương tác thực tế từ người dùng để làm điểm tựa tinh chỉnh các đường cong suy hao. Nếu chúng ta tiến hành hiệu chuẩn sớm dựa trên dữ liệu khan hiếm, mô hình sẽ lâm vào tình trạng quá khớp (overfitting) hoặc học phải những thiên kiến lịch sử sai lệch, dẫn đến rủi ro từ chối sai (False Negatives) trầm trọng. Hệ thống NMAI extension sẽ vô tình loại bỏ các ứng viên cực kỳ tài năng chỉ vì mức lương kỳ vọng của họ chênh lệch 5% so với ngân sách của công ty.

Để giải phóng tính năng Calibration tại Phase 1.5, kiến trúc lõi FANG phải thỏa mãn ba **điều kiện kích hoạt** tiên quyết về dữ liệu tổng hợp (Synthetic Data Strategy):

1. **Mở Rộng Dữ Liệu Hình Phễu 180:1:** Hệ thống sinh dữ liệu ATS (Applicant Tracking System) giả lập phải hoàn thành việc tạo lập bộ dữ liệu tổng hợp theo nguyên tắc tỷ lệ chuyển đổi phi tuyến tính. Hệ thống phải sản sinh trung bình 180 hồ sơ nộp vào (nhóm nhiễu) cho mỗi 1 hồ sơ được tuyển dụng thành công.1 Tập dữ liệu khổng lồ này, đóng vai trò như các "mẫu âm tính" (negative samples), là môi trường thử nghiệm chịu tải (stress test) bắt buộc để rèn luyện độ bền của thuật toán xếp hạng trước các nỗ lực thao túng như nhồi nhét từ khóa (keyword stuffing).1  
2. **Thiết Lập Ma Trận Phụ Thuộc Cholesky (Dependency Matrices):** Dữ liệu phải được giới hạn bởi các hàm tương quan logic thực tế thông qua các ma trận phụ thuộc.1 Ví dụ: Dữ liệu mô phỏng phải thể hiện rõ quy luật thị trường, chẳng hạn như dải lương công nghệ tại Hà Nội thường thấp hơn 10-15% so với TP.HCM, hoặc chứng chỉ kiến trúc sư đám mây AWS sẽ cộng thêm 20-40% phí bảo hiểm kỹ năng.1 Không có các ma trận này, mô hình hiệu chuẩn sẽ học trên những hồ sơ phi logic (ví dụ: sinh viên mới ra trường yêu cầu mức lương của giám đốc).  
3. **Khởi Tạo Bằng Kiến Trúc Lai Ghép (Hybrid Generation):** Để tạo ra sự phong phú trong ngôn ngữ, dữ liệu CV quy mô lớn phải được sinh ra qua chiến lược Hybrid Generation—kết hợp khung xương logic từ Đồ thị Kỹ năng (Skill Graph) và quyền năng tạo sinh ngữ nghĩa tự nhiên từ các LLM tier 1 & 2 (Gemini Flash Lite, GPT-5.4 mini).1 Phương pháp này ngăn chặn việc hệ thống vector ghi nhớ (memorize) cấu trúc tài liệu tĩnh dạng mẫu (Template-based Design) gây rò rỉ dữ liệu (Data Leakage).1 Thêm vào đó, việc tiêm nhiễu đa dạng thông qua giả lập khoảng trống sự nghiệp (Career Gaps) hoặc chuyển dịch ngành nghề (Career Pivots) qua mô hình Markov Ẩn (Hidden Markov Models) là điều kiện cần thiết để kiểm thử tính kiên cường của parser 5 cấp độ.1

## **Hệ Thống Chuẩn Nhãn Phân Cấp và Ánh Xạ Trạng Thái Quản Trị Tuyển Dụng**

Để xây dựng một cơ chế đánh giá Benchmark nội bộ đáng tin cậy, việc sử dụng các nhãn dữ liệu bề mặt như lượt nhấp chuột (clicks) hay hành vi nộp hồ sơ thụ động bị nghiêm cấm. Cách tiếp cận này tạo ra hiện tượng "Rò rỉ Mục tiêu" (Target Leakage), khiến thuật toán xếp hạng khuếch đại các thiên kiến bề ngoài (như tiêu đề clickbait, mức lương ảo) thay vì phản ánh "Độ Phù Hợp Năng Lực" (Competency Alignment) thực chất.1 Dữ liệu thực sự (Ground Truth) trong tuyển dụng nằm ở điểm cuối của phễu tương tác.

Hệ thống FANG v2 sẽ tuân thủ nghiêm ngặt **Chuẩn Nhãn Mức Độ Phù Hợp Phân Cấp (Graded Relevance Labels)**, được quy đổi trực tiếp từ các trạng thái hành vi thực tế trên Applicant Tracking System (ATS) thông qua chiến lược chuyển đổi học tương phản (Contrastive Learning).1

| Trọng Số Nhãn (Label Score) | Phân Loại Cấp Độ Phù Hợp (Graded Relevance) | Ánh Xạ Trạng Thái Nội Bộ của ATS | Bản Chất Tín Hiệu Xếp Hạng & Tỷ Lệ Chuyển Đổi |
| :---- | :---- | :---- | :---- |
| **3** | Khớp Hoàn Hảo (Perfect Match) | **Offer to Hire / Offer Accepted** (Tuyển dụng thành công) | **Ground Truth (Chân Lý Tuyệt Đối).** Ứng viên vượt qua mọi rào cản kỹ thuật, đồng thuận song phương về văn hóa và thu nhập. Tỷ lệ đóng phễu cao nhất, đạt 55.6% \- 82.0% từ giai đoạn offer.1 |
| **2** | Khớp Tốt (Good Match) | **Interview to Offer** (Vượt qua đánh giá kỹ thuật) | **Strong Positive (Tín hiệu dương mạnh).** Hồ sơ thể hiện sự tương hợp sâu sắc về chuyên môn, có thể thiếu sót một số kỹ năng nhánh phân phối đuôi dài (Long-tail skills). Tỷ lệ chuyển đổi từ 27.0% \- 36.2%.1 |
| **1** | Khớp Một Phần (Fair Match) | **Application to Interview** (Vượt qua sàng lọc CV vòng 1\) | **Positive (Tín hiệu dương sơ bộ).** Ứng viên đạt ngưỡng nền tảng về Cosine Similarity và điểm RRF nhưng xuất hiện các khoảng cách thâm niên nhẹ. Tỷ lệ chuyển đổi khắc nghiệt ở mức 3.0% \- 8.4%.1 |
| **0** | Không Phù Hợp (Unfit) | **Rejected / No Action** (Nằm trong hồ bơi hàng ngàn đơn đăng ký không được hồi đáp) | **Baseline/Negative (Tín hiệu nhiễu/Âm).** Chiếm đại đa số dữ liệu theo tỷ lệ 180:1. Bị loại vì không thỏa mãn các rào cản cứng hoặc là hệ quả của hành vi nhồi nhét từ khóa.1 |

Việc chuẩn hóa nhãn thành phổ phân cấp từ 0 đến 3 không chỉ dập tắt các tín hiệu nhiễu mà còn là điều kiện nền tảng để áp dụng các công thức tính toán đánh giá hệ thống hạng nặng như nDCG.

## **Chiến Lược Đo Lường Nội Bộ và Khung Đánh Giá A/B/C Đa Biến**

Với một hệ thống đã trang bị chuẩn nhãn phân cấp, FANG sẽ thực thi đánh giá hiệu năng thuật toán qua một thiết kế thử nghiệm A/B/C Test đa biến. Mục đích của thiết kế này là cô lập các thành phần hệ thống để định lượng được sức mạnh đóng góp của từng lớp thuật toán (Vector, Lexical, Feature Penalty) trước khi đẩy mô hình ra giao diện người dùng.1

* **Nhóm A (Nhóm Đối Chứng Bất Lợi): Vector-only (Chỉ sử dụng Vector Retrieval).**  
  * **Kiến trúc thử nghiệm:** Hệ thống loại bỏ hoàn toàn mã logic bằng SQL, chỉ gửi câu lệnh truy vấn đa hướng trực tiếp đến toán tử halfvec\_cosine\_ops dựa trên khoảng cách Cosine trên các điểm dữ liệu 1024 chiều trong bảng AIDOCUMENTCHUNK.1  
  * **Chức năng đánh giá:** Đo lường sức mạnh biểu diễn ngữ nghĩa thuần túy của OpenAI text-embedding-3-small.1 Nhóm này được dự báo sẽ thất bại nghiêm trọng trong việc phân tách cấp độ Junior/Senior và dự kiến sẽ đóng vai trò cột mốc thấp nhất (baseline) để chứng minh sự phụ thuộc bắt buộc vào siêu dữ liệu.1  
* **Nhóm B (Nhóm Triển Khai MVP): Hybrid tĩnh, Không Calibration.**  
  * **Kiến trúc thử nghiệm:** Khởi chạy kiến trúc Late Fusion tuyến tính với các thuật toán bộ lọc thô. Kích hoạt $k = 60$ cho RRF kết hợp điểm số BM25 và Vector. Áp dụng các trọng số cứng (như $w_{skill}=0.4$) và các phép lọc tiền xử lý SQL loại bỏ thẳng tay hồ sơ sai khác vị trí địa lý.1  
  * **Chức năng đánh giá:** Đây là kiến trúc được chọn để vận hành chính thức trong Phase 1\. Benchmark nội bộ sẽ tập trung kiểm tra xem thuật toán bù trừ RRF có khả năng khắc phục được những ứng viên thiếu năng lực hiển ngôn mà mô hình nhúng bỏ sót hay không.  
* **Nhóm C (Nhóm Thách Thức Phase 1.5): Hybrid có Calibration tự động.**  
  * **Kiến trúc thử nghiệm:** Tích hợp bộ máy học Contrastive Learning trên nền dữ liệu 10,000 lượt phản hồi phân cấp.1 Kích hoạt toàn bộ hàm suy hao hàm mũ trên các đặc trưng liên quan đến mức lương và thâm niên.1 Hệ thống NMAI liên tục cập nhật ma trận trọng số (Directional Weights) dựa trên dòng dữ liệu tương tác theo chu kỳ.  
  * **Chức năng đánh giá:** Đo lường đỉnh cao lý thuyết của các thuật toán Heuristic. Kết quả của Nhóm C sẽ quyết định việc hệ thống có cần thiết phải nhảy vọt lên cấu trúc Reranker dùng mạng nơ-ron hay không.

## **Ma Trận Độ Đo Hiệu Suất và Kỹ Thuật Trung Bình Hóa**

Hệ thống đánh giá hiệu suất của bài toán hai chiều sở hữu một đặc thù khó khăn: nó yêu cầu hai bộ độ đo (Metrics) trực giao để đại diện cho sự hài lòng của hai loại người dùng, đi kèm với các kỹ thuật gộp dữ liệu (Averaging) tinh vi nhằm tránh bị thiên lệch bởi quy mô cộng đồng.1 Việc phân bổ kỹ năng theo quy luật luật lũy thừa (Zipf's Law) trong dữ liệu tổng hợp (nơi mà một vài kỹ năng phổ thông như Java chiếm sóng, trong khi các kỹ năng ngách như Quantum Computing hay Edge AI rải rác ở đuôi dài) đòi hỏi một chiến lược trung bình hóa cẩn trọng.1

Báo cáo khuyến nghị sử dụng phương pháp **Macro-averaging** (tính toán trung bình độc lập cho từng danh mục công việc/ứng viên trước khi cộng gộp trung bình tổng).1 Nếu áp dụng Micro-averaging, báo cáo hiệu năng của toàn hệ thống sẽ bị thao túng bởi kết quả từ hàng ngàn công việc phổ thông, trong khi che lấp sự yếu kém của cỗ máy tìm kiếm trong việc ghép nối các hồ sơ lãnh đạo cấp cao hoặc chuyên gia ngách.1

### **Phân Tích Độ Đo Luồng Gợi Ý Công Việc Cho Ứng Viên (Candidate $\rightarrow$ Job)**

Ứng viên mang tâm lý của một nhà thám hiểm. Bảng điều khiển giao diện thường hiển thị danh sách dài để ứng viên tự do đối chiếu văn hóa, địa điểm và phúc lợi.1

1. **Độ Đo Chính Thức Trọng Tâm: nDCG@10 (Normalized Discounted Cumulative Gain).**  
   * **Bản chất Toán học:** Công thức $DCG@K = \sum_{i=1}^{K} \frac{2^{rel_i} - 1}{\log_2(i + 1)}$ (chuẩn hóa bằng IDCG) được lựa chọn vì nó là độ đo duy nhất trong hệ thống tích hợp trực tiếp Chuẩn Nhãn Phân Cấp ($rel_i$) ở các mức 0, 1, 2, 3\.1  
   * **Ý nghĩa Thực tiễn:** Cơ chế chiết khấu theo hàm logarit đại diện hoàn hảo cho sự suy giảm kiên nhẫn của người dùng khi cuộn trang (scrolling) màn hình đầu tiên (K=10) trên ứng dụng Web/Mobile.1 Nếu hệ thống NMAI đẩy một vị trí "Perfect Match" (Điểm 3\) xuống hạng 5, và đưa một vị trí "Fair Match" (Điểm 1\) lên hạng 1, nDCG@10 sẽ lập tức suy giảm cực mạnh, trừng phạt hệ thống vì sắp xếp sai thứ tự tương đối.1 Năng lực tính toán giá trị chuẩn hóa từ 0 đến 1 cho phép so sánh chéo khả năng cá nhân hóa giữa các ứng viên khác biệt.1  
2. **Độ Đo Phụ Trợ (Secondary Metrics): HitRate@5 và MAP.**  
   * **HitRate@5:** Đo lường tỷ lệ các phiên tìm kiếm mà NMAI trả về ít nhất một kết quả chất lượng cao ngay trong Top 5\. Độ đo này là "chìa khóa" giải quyết vấn đề Khởi động Lạnh (Cold Start) cho những người dùng mới tạo hồ sơ.1  
   * **MAP (Mean Average Precision):** Cung cấp bức tranh toàn cảnh về diện tích dưới đường cong của toàn hệ thống (Recall Coverage). MAP phục vụ mục đích phân tích sâu thay vì làm chỉ số đánh giá kinh doanh cốt lõi do nó giới hạn ở phân loại nhị phân.1

### **Phân Tích Độ Đo Luồng Gợi Ý Ứng Viên Cho Nhà Tuyển Dụng (Job $\rightarrow$ Candidate)**

Ngược lại với ứng viên, nhà tuyển dụng có giới hạn chú ý cực ngắn.1 Họ yêu cầu kết quả chính xác tuyệt đối trên cùng và không có thời gian đào sâu xuống dưới lớp kết quả nhiễu.

1. **Độ Đo Chính Thức Trọng Tâm: MRR (Mean Reciprocal Rank).**  
   * **Bản chất Toán học:** Thuật toán MRR tính toán điểm số dựa trên nghịch đảo vị trí của kết quả chính xác đầu tiên. Nếu hồ sơ xuất sắc đứng số 1, điểm là 1\. Nếu rơi xuống vị trí 2, điểm chỉ còn 0.5; xuống vị trí 3 còn 0.33.1  
   * **Ý nghĩa Thực tiễn:** Sự nhạy cảm vị trí này phản chiếu chính xác áp lực công việc của quản lý nhân sự.1 Sự sụt giảm MRR là hồi chuông báo động kỹ thuật nghiêm trọng nhất, vì nó hàm ý bộ mã nhúng (Embedding Algorithm) và các lớp RRF đang đánh mất khả năng phát hiện tài năng kiệt xuất, trực tiếp kéo dài Thời gian Tuyển dụng (Time-to-Hire).1  
2. **Độ Đo Phụ Trợ (Secondary Metrics): Precision@5 và AUC.**  
   * **Precision@5:** Sử dụng làm ngưỡng cắt tuyệt đối (absolute cutoff) để định lượng tỷ lệ "tín hiệu trên nhiễu".1 Nó trả lời câu hỏi: Trong 5 ứng viên đầu tiên gửi cho quản lý kỹ thuật phỏng vấn, có bao nhiêu người thực sự vượt qua vòng duyệt CV?  
   * **AUC (Area Under the ROC Curve):** Đánh giá năng lực tổng quát của các biến hàm phạt trong việc chia rẽ hai tập hợp dữ liệu lớn: Nhóm trúng tuyển và Nhóm bị từ chối.1 Dù thiếu tính nhạy cảm trật tự, AUC khẳng định sức mạnh phân loại toàn cục của thuật toán tuyến tính.

(Ghi chú kỹ thuật: Các tham số K cao như K=20 chỉ được bảo lưu nội bộ cho các bộ phận khoa học dữ liệu nhằm theo dõi độ chênh lệch của Retrieval Engine, không áp dụng cho quản lý cấp cao 1).

## **Ngưỡng Dịch Chuyển Trạng Thái: Từ Heuristic Sang Supervised Reranker**

Mô hình Xếp hạng Lai (Hybrid Reranker) hiện tại, được cấu thành từ RRF và các phương trình tuyến tính, bản chất là một kiến trúc Heuristic tinh vi. Tuy nhiên, kiến trúc này được định vị là Giai đoạn 1 của giải pháp dài hạn.1 Kiến trúc Two-Tower (song tháp) tiêu chuẩn giúp mở rộng năng lực tìm kiếm thô trong hàng triệu hồ sơ với chi phí thấp (Retrieval Stage), nhưng nó vĩnh viễn "mù lòa" trước các đặc trưng chéo phức tạp (Cross-features).1 Việc kết hợp thủ công hai không gian đặc trưng bằng các trọng số $w$ không thể mô phỏng được những quy luật ngầm định của thị trường. Việc dịch chuyển sang một mô hình Tái xếp hạng Có Giám sát (Supervised Reranker) mạnh mẽ hơn—chẳng hạn như Cross-Encoder hoặc mô hình Listwise LTR (Learning to Rank)—là mục tiêu tất yếu.1 Tuy nhiên, thay đổi kiến trúc khổng lồ này đòi hỏi tài nguyên tính toán LLM và chi phí GPU rất lớn, nên nó chỉ được cấp phép khi NMAI vượt qua các **Ngưỡng Thành Công Tối Thiểu (Plateau Thresholds)** sau:

1. **Trạng Thái Bão Hòa Độ Đo (Metric Plateau):** Các chỉ số đo lường trung tâm không còn khả năng tăng trưởng tự nhiên. Cụ thể, khi  $nDCG@10$ liên tục duy trì ở mức $> 0.68$ và $MRR$ ổn định ở mức $> 0.65$ trong suốt 3 chu kỳ đánh giá (sprint) liên tiếp trên bộ dữ liệu thực tế (thay vì dữ liệu giả lập ATS). Điều này là minh chứng toán học tuyệt đối khẳng định sức mạnh của các phương trình tuyến tính đã cạn kiệt không gian tối ưu. Việc nâng điểm nDCG từ 0.68 lên 0.75 sẽ bắt buộc phải dùng đến Listwise LTR, vì nó tối ưu hóa trực tiếp trên toàn bộ danh sách hiển thị.1  
2. **Giới Hạn Tải Trọng Vận Hành (OpEx Tipping Point):** Nỗ lực kỹ thuật để duy trì các luật lệ (rules) lớn hơn chi phí huấn luyện AI. Khi việc bảo trì liên tục Hệ thống Từ điển Taxonomy và tái cấu trúc thuật toán "Độ tươi Kỹ năng" (Recency) tốn quá nhiều giờ làm việc của kỹ sư, tạo ra rào cản ngăn cản hệ thống tiếp nhận các ngành nghề ngoài IT.  
3. **Hội Đủ Khối Lượng Dữ Liệu Tương Tác (Data Tolerance):** Mô hình Listwise LTR nổi tiếng với độ "đói" dữ liệu và rất dễ rơi vào bẫy Overfitting.1 NMAI chỉ được phép nâng cấp khi kho dữ liệu tương tác bề mặt (Interaction Layer) đã thu thập thành công 500,000 cặp tương tác ứng viên-công việc thực tế từ miCareer-mini, với tỷ lệ phân bổ phân cấp tuân thủ nghiêm quy luật phân phối ngách.1

## **Phân Tích Rủi Ro Kiến Trúc và Các Kịch Bản Đổ Vỡ Kỹ Thuật**

Là một kiến trúc mở rộng hoạt động tích hợp trên FANG core, NMAI chịu rủi ro rò rỉ và khuếch đại lỗi từ các hệ thống phía dưới (như CV Parser hay pgvector).1 Bảng dưới đây phác thảo các quyết định sai lầm tiềm ẩn, chuỗi phản ứng kỹ thuật và chiến lược phòng thủ.

| Mã Rủi Ro & Quyết Định Sai Lầm Khởi Thủy | Hậu Quả Kỹ Thuật / Nghiệp Vụ Phát Sinh | Giải Pháp Phòng Thủ (Mitigation Strategy) |
| :---- | :---- | :---- |
| **Cấu hình Trọng số RRF quá cao (\>0.5)** cho luồng tìm kiếm nhà tuyển dụng.1 | **Âm tính Giả Cấp độ (Level False Negatives):** Mô hình rơi vào trạng thái Đồng nhất hóa Không gian Ngữ nghĩa (Homogenization). Một sinh viên viết CV mô tả dự án học thuật bằng cùng một khuôn mẫu ngôn ngữ với bản JD của vị trí Giám đốc. Nếu vector score chiếm ưu thế, sinh viên này sẽ xếp trên một Giám đốc thật sự.1 Phá hủy niềm tin của bộ phận nhân sự. | Triển khai triệt để cơ chế Linear Penalty (Hàm phạt tuyến tính) với tư cách là các rào cản phủ quyết (Veto Weights). Đảm bảo điểm RRF chỉ được đánh giá đóng góp sau khi các rào cản tiền đề về kinh nghiệm đã vượt qua.1 |
| **Vô hiệu hóa Hệ thống Phân loại Chức danh (Taxonomy Mapping)** trước khi đưa dữ liệu vào vector nhúng.1 | **Rò rỉ Nhiễu Ngữ nghĩa (Semantic Noise Leakage):** Hiện tượng bất đồng nhất ngôn ngữ trong ngành. Hệ thống so khớp chuỗi BM25 thất bại trong việc nhận diện "Lập trình viên giao diện" và "Frontend Engineer" là một, dẫn đến điểm $rank_{text}$ tụt thảm hại, đánh rơi nhân tài.1 | Áp dụng mạng lưới Đồ thị Kỹ năng (Skill Graph).1 Ánh xạ toàn bộ chức danh về một hệ ID Ontology chung duy nhất trước khi gọi API text-embedding-3-small.1 |
| **Sử dụng Dữ liệu Nhãn Click bề mặt** cho quá trình đánh giá hoặc cấu hình hệ số phạt.1 | **Rò rỉ Mục tiêu (Target Leakage):** Thuật toán tự động học cách xếp hạng cao những bản mô tả công việc mang tính chất "Clickbait" (tiêu đề thổi phồng, quảng cáo phúc lợi ảo). Mô hình trở thành một cỗ máy tối ưu lượt nhấp chuột thay vì tối ưu hóa "Độ Phù Hợp Năng Lực" (Competency) thực tiễn.1 | Cương quyết sử dụng hệ thống Graded Relevance Labels (0 đến 3). Chỉ ghi nhận các tiến trình chuyển đổi qua phễu ATS (Interview, Offer) làm cơ sở tham chiếu chân lý.1 |
| **Phụ thuộc độc tôn vào một mô hình đơn (ví dụ: gemini-flash tier 1\)** để trích xuất metadata CV.1 | **Sụp đổ Tuyến Tính Cục bộ (Pipeline Collapse):** Khi Tier 1 đối mặt với CV đa cột phức tạp, bộ sinh JSON bị lỗi. Khối lượng siêu dữ liệu biến mất. Các biến số expyears, skills trở về Null. Hàm Linear Scoring không thể hoạt động, bắt buộc kiến trúc thoái lui về trạng thái Vector-only yếu kém ban đầu.1 | Bảo toàn nghiêm ngặt cơ chế Fallback 5 cấp độ và cổng kiểm soát ProTierGate trên FANG. Quá trình kiểm định chất lượng nội tại (Quality Gate) dựa trên độ dài văn bản (rawText) và các tín hiệu định danh cốt lõi phải được thực thi không khoan nhượng trước khi chốt luồng xử lý RAG hoặc Ranking.1 |

## **Kế Hoạch Triển Khai Kỹ Thuật Chuyên Sâu Qua Hai Chu Kỳ Khởi Tạo (Sprint/Weekly Roadmap)**

Lộ trình triển khai NMAI extension được cô đọng trong hai chu kỳ phát triển (Sprint), tương đương 4 tuần thực thi. Thiết kế đảm bảo sự thay đổi diễn ra âm thầm, có khả năng kích hoạt/tắt bỏ (toggle) và hoàn toàn không làm suy giảm hiệu suất của phân hệ truy vấn đàm thoại RAG 7-mode (/v2/chat) hay tiến trình tổng hợp ngữ cảnh đàm thoại hiện tại.1

### **Tuần 1-2 (Sprint 1): Nền Tảng Hỗn Hợp Tĩnh và Chiến Lược Dữ Liệu Synthetic**

**Mục tiêu cốt lõi:** Thiết lập mở rộng mã nguồn trên nền FastAPI, bảo đảm truy xuất RRF thông qua cơ sở dữ liệu pgvector, và hoàn thiện quá trình giả lập phễu ATS nhằm cung cấp đạn dược cho việc đo lường.

* **Công việc (Deliverables):**  
  * *Kỹ thuật Hệ thống:* Khởi tạo định tuyến (router) mới /v2/ranking song song với kiến trúc RAG hiện hành.1 Lập trình tích hợp khối tính toán Reciprocal Rank Fusion (RRF) vào các lệnh SQL truy vấn trực tiếp trên cấu trúc bảng AIDOCUMENTCHUNK và Job Posting thông qua plugin pgvector.1  
  * *Bộ Lọc Cứng (Hard Filters):* Mở rộng mã logic kiểm duyệt tiền xử lý (Heuristic Filter) nhằm loại trừ thẳng tay các thực thể không tương thích về biến số vị trí địa lý hay loại hình làm việc ngay trong tập lệnh SQL, giới hạn lại bán kính của thuật toán tìm kiếm lân cận HNSW.1  
  * *Kiến trúc Dữ liệu:* Hoàn thiện chiến lược sinh dữ liệu CV khối lượng lớn. Vận hành công cụ LLM-assisted kết hợp Skill Graph (Kiến trúc Lai \- Hybrid Generation) nhằm thiết lập cấu hình tỷ lệ 180:1 và tuân thủ định luật Zipf cho danh mục kỹ năng, tiêm nhiễu đa dạng để thử nghiệm parser.1  
* **Tiêu chí Vượt qua (Pass Criteria):**  
  * Độ trễ toàn vẹn cho điểm cuối /v2/ranking ở cấu hình $K = 10$ không được phép vượt qua giới hạn 250ms cho mỗi yêu cầu phản hồi (Request).  
  * Nhóm đối chứng Vector-only (A) và nhóm triển khai MVP Hybrid Tĩnh (B) phải có thể chuyển đổi mượt mà thông qua bộ cấu hình biến môi trường .env.1  
  * Chỉ số Khởi động lạnh HitRate@5 của Nhóm B phải ghi nhận sự vượt trội tối thiểu 15% so với sự yếu kém của Nhóm A, xác nhận vai trò của các bộ lọc thô.

### **Tuần 3-4 (Sprint 2): Tích Hợp Cơ Chế Suy Hao Tuyến Tính và Hệ Thống Dashboard Đo Lường Đa Chiều**

**Mục tiêu cốt lõi:** Kích hoạt toàn bộ lớp mã dịch vụ (Service Layer) phụ trách trọng số tuyến tính và hàm phạt phi tuyến. Thiết lập trung tâm giám sát Macro-averaging cho hai độ đo cốt lõi.

* **Công việc (Deliverables):**  
  * *Tính toán Định lượng:* Lập trình và triển khai các hàm $Penalty$ đối với Khoảng cách Thâm niên (Seniority Gap), sử dụng cột dữ liệu expyears từ các bản ghi CANDIDATE làm đầu vào tính toán.1  
  * *Tối ưu hóa Quyền lợi:* Tích hợp thuật toán suy hao hàm tuyến tính đặc tả cho Khoảng cách Tiền lương, tính toán trên các cực trị minSalary và maxSalary trong luồng tìm kiếm Candidate $\rightarrow$ Job.1 Đưa các hệ số đã quyết định vào tệp cấu hình trung tâm tĩnh.  
  * *Dashboard Theo dõi:* Xây dựng giao diện báo cáo chuyên biệt (Dashboard) vận hành chức năng tính toán tổng hợp Macro-averaging dựa trên hệ thống nhãn đánh giá phân cấp (Graded Feedback). Mục tiêu hướng đến việc theo dõi sự thay đổi của nDCG@10 và MRR nội bộ.1  
* **Tiêu chí Vượt qua (Pass Criteria):**  
  * Chỉ số MRR trong luồng truy vấn Job $\rightarrow$ Candidate phải đạt ngưỡng lý thuyết $> 0.50$, phản ánh thực trạng rằng ứng viên tối ưu nhất về kỹ năng luôn nằm ở ít nhất vị trí hiển thị số 1 hoặc 2\.1  
  * Độ tin cậy của thuật toán Phạt Thâm niên: Việc truy vấn thử nghiệm một công việc cấp độ Senior (yêu cầu tối thiểu 5 năm kinh nghiệm) phải tự động "hất văng" mọi ứng viên sơ cấp cấp độ Junior (dưới 1 năm kinh nghiệm) khỏi Top 20 ưu tiên, hoàn toàn bất chấp hệ số tương đồng Cosine của các vector.1  
  * Ràng buộc kiến trúc: Mọi cải tiến này tuyệt đối không được phép phá vỡ hay gây ảnh hưởng tiêu cực lên hạn mức ngân sách token đa tầng của RAG 7-mode hoặc can thiệp vào cơ chế Summarization Context (Tóm tắt ngữ cảnh đàm thoại) tại đường ống /v2/chat.1

## **Danh Mục Quyết Định Quản Trị Kỹ Thuật Cốt Lõi (Issue Tracker Ready)**

Phần tổng kết sau đây chứa các khối quyết định kỹ thuật chuyên sâu đã được phê duyệt, được định dạng theo tiêu chuẩn sẵn sàng tích hợp (copy-paste) vào các hệ thống quản trị quy trình dự án như Jira hoặc Trello, đảm bảo tính liên kết xuyên suốt với đội ngũ kỹ thuật.

1. **Chốt triển khai cấu trúc thiết kế Hybrid Two-stage Pipeline.** Quy trình hoạt động: Sàng lọc giảm kích thước dữ liệu (Retrieval Stage) thông qua Hard Filter $\rightarrow$ Tái Xếp hạng Heuristic qua RRF và Linear Penalty (Reranking). Phủ quyết hoàn toàn việc sử dụng mô hình Vector-only (chỉ dùng Cosine Similarity) do yếu điểm trầm trọng trước dữ liệu định lượng và rủi ro đồng nhất hóa không gian.1  
2. **Quyết định sử dụng phương pháp luận Hợp nhất Muộn (Late Fusion).** Dựa trên Cấu trúc Xếp hạng Tuyến tính (Weighted Linear Combination) làm lõi sức mạnh. Lựa chọn này lấp đầy khiếm khuyết của riêng RRF—thuật toán vốn thiếu sức mạnh "trừng phạt" (Veto Power) đối với những hồ sơ vi phạm các kỹ năng bắt buộc.1  
3. **Cấu hình cố định một hệ ma trận trọng số phi đối xứng.** Trong luồng ứng viên tìm việc (C $\rightarrow$ J), ưu tiên cấu hình ràng buộc cứng lên hệ số tiền lương (Salary Match) và thiết lập lọc cứng vị trí địa lý/hình thức làm việc (Location/Work mode).1 Ngược lại, luồng nhà tuyển dụng săn người (J $\rightarrow$ C) sẽ áp đặt trọng số cực đại cho sự giao thoa về kỹ năng (Skill Overlap) và hàm phạt nghiêm khắc lên khoảng cách tuổi nghề (Seniority Gap). Đặc trưng về học vấn (Education) bị đóng băng ở mức trọng số 0 ở Giai đoạn 1 do rủi ro gây nhiễu.1  
4. **Quyết định trì hoãn và đóng băng tính năng hiệu chuẩn tự động (Dynamic Penalty Calibration).** Giải pháp này được bảo lưu sang Giai đoạn 1.5. Chìa khóa để mở khóa tính năng này là việc hoàn tất khối lượng dữ liệu khổng lồ từ hệ thống sinh CV tổng hợp dựa trên phễu ATS tỷ lệ 180:1.1  
5. **Phê chuẩn hệ thống Nhãn phân cấp chuẩn (Graded Relevance Labels) gồm 4 phân tầng giá trị $(0, 1, 2, 3)$.** Các giá trị này được cấu hình để đối chiếu và quy đổi tỷ lệ trực tiếp từ 4 giai đoạn tiến trình sinh tử trên hệ thống quản trị ATS thực tế (Lần lượt từ: Từ chối $\rightarrow$ Nộp đơn $\rightarrow$ Phỏng vấn $\rightarrow$ Chấp nhận Đề nghị), tái thiết lập Chân lý Dữ Liệu (Ground Truth).1  
6. **\[Evaluation Mechanism\]** Chốt hệ thống giám sát hiệu năng với cấu trúc Macro-averaging: Chọn nDCG@10 làm ngọn hải đăng soi đường cho luồng đánh giá Trải nghiệm Ứng viên (C $\rightarrow$ J) và MRR làm quy chuẩn sống còn đo lường độ sắc bén của luồng Nhà Tuyển dụng (J $\rightarrow$ C).1  
7. **Phê duyệt chiến lược Kiến trúc Lai Ghép (Hybrid Generation Architecture).** Sử dụng logic khung xương từ mạng Đồ thị Kỹ năng (Skill Graph) kết hợp trí thông minh ngôn ngữ tự nhiên từ LLM nhằm sản xuất quy mô lớn các tập dữ liệu CV/JD giả lập (Synthetic ATS Data), làm nền tảng kiểm thử chịu tải (Stress-testing) độ chống chịu của bộ mã Ranking Engine.1  
8. **\[Infrastructure Integrity\]** Ban lệnh đảm bảo mọi thuật toán phân tích khoảng cách vector tiếp tục vận hành kiên định trên định dạng số thực halfvec(1024) của pgvector. Song song đó, bảo vệ nghiêm ngặt sự toàn vẹn của cổng đánh giá ProTierGate và đường ống Fallback 5 cấp độ (từ Lite-to-Lite đến Lite-to-Pro) của bộ phân tích CV, đây là tấm khiên duy nhất đảm bảo sự giàu có của metadata (dữ liệu siêu dẫn) được bơm vào thuật toán xếp hạng tuyến tính.1

#### **Nguồn trích dẫn**

1. README.md

[image1]: images/NMAIex_th_3/image1.png

[image2]: images/NMAIex_th_3/image2.png

[image3]: images/NMAIex_th_3/image3.png

[image4]: images/NMAIex_th_3/image4.png

[image5]: images/NMAIex_th_3/image5.png

[image6]: images/NMAIex_th_3/image6.png

[image7]: images/NMAIex_th_3/image7.png

[image8]: images/NMAIex_th_3/image8.png

[image9]: images/NMAIex_th_3/image9.png

[image10]: images/NMAIex_th_3/image10.png

[image11]: images/NMAIex_th_3/image11.png

[image12]: images/NMAIex_th_3/image12.png

[image13]: images/NMAIex_th_3/image13.png

[image14]: images/NMAIex_th_3/image14.png

[image15]: images/NMAIex_th_3/image15.png

[image16]: images/NMAIex_th_3/image16.png

[image17]: images/NMAIex_th_3/image17.png

[image18]: images/NMAIex_th_3/image18.png

[image19]: images/NMAIex_th_3/image19.png

[image20]: images/NMAIex_th_3/image20.png

[image21]: images/NMAIex_th_3/image21.png

[image22]: images/NMAIex_th_3/image22.png

[image23]: images/NMAIex_th_3/image23.png

[image24]: images/NMAIex_th_3/image24.png

[image25]: images/NMAIex_th_3/image25.png

[image26]: images/NMAIex_th_3/image26.png

[image27]: images/NMAIex_th_3/image27.png

[image28]: images/NMAIex_th_3/image28.png

[image29]: images/NMAIex_th_3/image29.png

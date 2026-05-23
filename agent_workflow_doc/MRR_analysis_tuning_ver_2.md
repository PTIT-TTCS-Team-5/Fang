# Phân Tích Toán Học Sâu & Lộ Trình Tối Ưu Hóa Ranking NMAIex - Phiên Bản 2

Tài liệu này trình bày phân tích toán học chuyên sâu, phân tích cấu trúc dữ liệu và phương án tối ưu hóa hệ thống xếp hạng NMAIex nhằm vượt qua các giới hạn xếp hạng hiện tại và bứt phá chỉ số MRR (Mean Reciprocal Rank).

---

## I. 🧮 Phân Tích Seniority Penalty & Giới Hạn Tuyến Tính

Trong các phiên bản trước, Seniority Penalty thường bị coi là một hình phạt cố định. Tuy nhiên, hệ thống thực tế cho phép Optuna tinh chỉnh hai tham số động cực kỳ quan trọng:
*   `NMAIEX_JC_PENALTY_SENIORITY_COEF` (Hệ số phạt cơ bản - $jc\_sen\_coef$): Phạm vi tinh chỉnh $[0.05, 0.60]$.
*   `NMAIEX_SENIORITY_OVERQUALIFIED_PENALTY_RATIO` (Tỷ lệ phạt khi thừa kinh nghiệm - $sen\_overq\_ratio$): Phạm vi tinh chỉnh $[0.05, 0.50]$.

### 1.1 Cơ chế toán học động
Hàm phạt kinh nghiệm được định nghĩa động theo cấu trúc:

$$\text{Seniority Penalty} = \begin{cases} 
jc\_sen\_coef \times (Job_{min} - Exp) & \text{nếu } Exp < Job_{min} \\
jc\_sen\_coef \times sen\_overq\_ratio \times (Exp - Job_{max}) & \text{nếu } Exp > Job_{max} \\
0 & \text{nếu } Job_{min} \le Exp \le Job_{max}
\end{cases}$$

> [!NOTE]
> **Tác động của Hyperparameter Tuning:** Optuna có khả năng co giãn độ dốc của hàm phạt này. Nếu tập dữ liệu Ground Truth chỉ ra rằng những ứng viên lệch kinh nghiệm nhưng có kỹ năng xuất sắc vẫn được đánh giá cao, Optuna sẽ tự động ép $jc\_sen\_coef$ về cận dưới ($0.05$) để giảm thiểu tối đa hình phạt, nhường quyền quyết định cho điểm Skill và RRF.

### 1.2 Nguyên nhân tồn tại "Trần cứng" (Ceiling) tại một số Jobs
Dù Optuna có thể triệt tiêu hình phạt bằng cách giảm $jc\_sen\_coef$ về sát $0$, hệ thống vẫn gặp trần cứng tại một số công việc (Relevant candidate không thể lên Top 1) do các giới hạn sau:
1.  **Dấu của Gap là cố định:** Hệ thống chỉ có thể phạt ($P \ge 0$), không thể chuyển thành thưởng ($P < 0$) cho ứng viên lệch kinh nghiệm nhưng có năng lực xuất sắc vượt trội.
2.  **Sự đồng thuận của các tín hiệu thành phần khác:** Đối với các ứng viên phù hợp (Relevant) nhưng bị xếp dưới, điểm tương đồng vector (RRF) hoặc số lượng kỹ năng khớp chuẩn (exact skill overlap) của họ vẫn thấp hơn các ứng viên không phù hợp (Non-relevant) trong cùng pool. Khi mọi tín hiệu cấu trúc và ngữ nghĩa đều xếp ứng viên Non-relevant cao hơn, không một tổ hợp trọng số tuyến tính nào có thể đảo ngược thứ tự để đưa Relevant candidate lên đầu.

---

## II. 🔍 Khắc Phục Lỗi CANDIDATE_SKILL_RAW = 0 & Chiến Lược Kiểm Soát Skill Ngoài Catalog

### 2.1 Phát hiện nguyên nhân gốc trong Pipeline mẫu
Qua rà soát mã nguồn hệ thống tạo dữ liệu giả lập (`synthetic_data`), chúng tôi phát hiện 2 điểm nghẽn chính:
1.  **Lỗi Ingestion trong `db_writer.py`:** Hàm `write_candidate_cv` chỉ tập trung ghi thông tin Candidate, JobApplication, ParsedCV, chunking và embedding mà hoàn toàn bỏ quên bước phân loại và lưu trữ kỹ năng ứng viên vào bảng `CANDIDATESKILL` (exact) và `CANDIDATE_SKILL_RAW` (unmatched).
2.  **Dữ liệu CV sinh ra quá "sạch":** Khi dùng script `backfill_candidate_skills.py` để vá lỗi, toàn bộ kỹ năng do LLM sinh ra trong CV ứng viên đều trùng khớp 100% với danh mục kỹ năng chuẩn trong hệ thống (`SKILL` catalog). Do đó, 100% kỹ năng được đưa vào bảng exact, khiến bảng `CANDIDATE_SKILL_RAW` hoàn toàn trống trơn ($0$ bản ghi).

> [!IMPORTANT]
> **Hậu quả:** Điểm `fuzzy_overlap` luôn bằng $0.0$ do không có dữ liệu thô để so khớp vector cosine. Tín hiệu Skill Score thực chất bị thoái hóa thành so khớp chính xác (`exact_overlap`), triệt tiêu hoàn toàn sức mạnh của **Thuật toán So Khớp Kỹ Năng 2 Tầng (Tiered Skill Scoring)**.

### 2.2 Chiến lược kiểm soát chặt chẽ tỷ lệ Skill ngoài Catalog (5-10%)
Để giải quyết triệt để và tự nhiên nhất mà không làm "bịa" kỹ năng bừa bãi, chúng ta triển khai giải pháp kiểm soát chặt chẽ:
1.  **Truyền trực tiếp danh mục kỹ năng hệ thống (Exact Catalog):** Trích xuất danh sách tất cả các kỹ năng hiện có trong `SKILL_CATALOG` từ [personas.py](file:///c:/Users/os/Desktop/cur_prj/Fang/synthetic_data/personas.py) và tiêm trực tiếp vào `CV_SYSTEM_PROMPT` trong [prompts.py](file:///c:/Users/os/Desktop/cur_prj/Fang/synthetic_data/prompts.py). LLM sẽ biết chính xác hệ thống đang có những kỹ năng gì.
2.  **Khống chế tỷ lệ CV có skill ngoài catalog ở mức 5-10%:**
    *   Chúng ta áp dụng quy tắc deterministic dựa trên chỉ số của CV: **Chỉ cho phép sinh skill ngoài catalog nếu `cv_index % 15 == 0`** (tương đương **~6.6%** tổng số CV, nằm chính xác trong dải 5-10% yêu cầu).
    *   Trong các trường hợp được phép này (`cv_index % 15 == 0`), chúng ta bổ sung chỉ thị cụ thể trong prompt: *LLM được phép sinh từ 1 đến vài kỹ năng thô, chuyên sâu nằm ngoài catalog nhưng PHẢI hoàn toàn hợp lý với bối cảnh kinh nghiệm và phần tự giới thiệu (bio) của ứng viên* (ví dụ: thay vì ghi "ReactJS" trong catalog thì ghi "React compound components pattern", "asynchronous state management with Redux", hoặc thay vì "Git" thì ghi "Git Gitflow Workflow").
    *   Đối với 93.4% số CV còn lại, prompt sẽ ép cứng LLM chỉ được sử dụng các kỹ năng nằm chính xác trong danh sách `skill_pool` chuẩn được cấp.

Giải pháp này vừa kích hoạt hoàn hảo thuật toán `fuzzy_overlap` 2 tầng, vừa đảm bảo tính chân thực và chất lượng cực cao của tập dữ liệu CV mà không bị loãng.

---

## III. 💰 Loại Bỏ `base_weight` Khỏi Hàm Salary Adjustment

Trong hàm `compute_salary_adjustment` hiện tại, hệ thống đang nhân với một hệ số cứng `base_weight = 0.20`. Việc này gây ra sự chồng chéo và làm lu mờ không gian tìm kiếm của Optuna khi ở tầng Late Fusion bên ngoài đã có trọng số `cj_w_salary` (hoặc `nmaiex_cj_weight_salary`).

### 3.1 Bảng so sánh các phương án toán học

| Phương án | Cơ chế toán học | Ưu điểm | Nhược điểm & Hạn chế |
| :--- | :--- | :--- | :--- |
| **Phương án cũ: Giữ `base_weight = 0.20` trong lõi** | Điểm hiệu chỉnh thực tế: $\Delta_{salary} = 0.20 \times \text{SalaryAdjustmentRatio}$. Sau đó Fusion nhân thêm: $\text{Score} += W_{salary} \times \Delta_{salary}$ | API độc lập không bị lỗi tỉ lệ nếu không truyền trọng số cấu hình. | Optuna tinh chỉnh trọng số $W_{salary}$ nhưng hiệu ứng thực tế bị thu nhỏ $5$ lần ($W_{salary} \times 0.20$). Gây nhiễu khi đánh giá tầm quan trọng của thuộc tính (Feature Importance). |
| **Phương án mới: Loại bỏ `base_weight` khỏi lõi, đưa lên tầng Fusion (Khuyến nghị)** | Hàm trả về raw ratio cực đại trong khoảng $[-1.0, +0.2]$. Điểm cộng cuối cùng: $\text{Score} += \text{NMAIEX\_CJ\_WEIGHT\_SALARY} \times \text{SalaryAdjustmentRatio}$ | **Toán học sạch sẽ 100%**. Tách biệt hoàn toàn phần trích xuất đặc trưng (Feature Extraction) và phần kết hợp trọng số (Late Fusion). Optuna tinh chỉnh trực tiếp trọng số thực tế trong không gian $[0.0, 0.50]$. | Cần gán giá trị mặc định cho biến cấu hình hệ thống là $0.20$ để đảm bảo tính tương thích ngược khi không chạy tuning. |

> [!TIP]
> **Quyết định triển khai:** Chúng ta loại bỏ hoàn toàn dòng gán cứng `base_weight = 0.20` trong `compute_salary_adjustment`. Tương tự, ta sẽ tách biệt tham số `NMAIEX_SKILL_ALPHA` thành hai tham số riêng biệt cho hai chiều: `NMAIEX_SKILL_ALPHA_JC` và `NMAIEX_SKILL_ALPHA_CJ` nhằm tối ưu hóa sâu cho từng luồng tìm kiếm độc lập.

---

## IV. 📊 Đánh Giá Ngân Sách LLM Khi Mở Rộng Bộ Ground Truth lên 3000 Cặp

### 4.1 Thống kê tài nguyên quota từ Pool 13 Google Keys (9Router)
Mỗi API Key miễn phí của Google có hạn mức:
*   `gemini-3.5-flash`: **5 RPM** | **20 RPD** (Requests Per Day)
*   `gemini-3.1-flash-lite`: **15 RPM** | **500 RPD**

Với pool tích hợp **13 keys** qua 9Router, tổng công suất là:
*   **Gemini 3.5 Flash:** **65 RPM** | **260 RPD**
*   **Gemini 3.1 Flash Lite:** **195 RPM** | **6500 RPD**

### 4.2 Tính toán ngân sách cho bộ Ground Truth mới (3000 cặp)
Chúng ta sẽ bổ sung thêm **150 ứng viên niche** thuộc các lĩnh vực mới (Mobile, QA, DevOps/IT Infra, SAP/ERP) vào bộ 500 candidates hiện có, nâng tổng số lên **~650 candidates**.

Quy mô xây dựng Ground Truth mới:
*   **Số lượng Jobs:** 20 Jobs.
*   **Candidates per Job:** Tăng từ 100 lên **150** (để phủ hết các ứng viên thuộc các nhóm chuyên môn mới thêm).
*   **Tổng số cặp cần đánh giá:** $20 \text{ jobs} \times 150 \text{ candidates} = 3000 \text{ pairs}$.

#### Phép toán chi phí và thời gian gọi LLM-as-Judge:
Hệ thống sử dụng cơ chế **Batching** với `BATCH_SIZE = 10` (Đánh giá 10 ứng viên trong 1 request).
*   **Số requests LLM thực tế cần gọi:** $3000 \text{ pairs} / 10 = 300 \text{ requests}$.

Nếu sử dụng **Gemini 3.1 Flash Lite** làm Judge:
*   **Hạn mức tiêu thụ:** 300 requests chỉ chiếm **4.6%** tổng quota ngày ($6500 \text{ RPD}$).
*   **Thời gian thực thi:** Với tốc độ $195 \text{ RPM}$, quá trình rebuild chỉ mất:
    $$\text{Thời gian} = \frac{300}{195} \approx 1.54 \text{ phút!}$$
*   **Chi phí:** **$0** (Hoàn toàn miễn phí trên Free Tier).

Do đó, việc mở rộng Ground Truth lên 3000 cặp hoặc thậm chí lớn hơn nữa hoàn toàn nằm trong khả năng chịu tải và không tốn bất kỳ chi phí nào!

---

## V. 🎯 Tóm Tắt Lộ Trình Triển Khai Không Gây Gián Đoạn

Hệ thống Optuna Tuning trên terminal của người dùng tải dữ liệu Ground Truth vào RAM một lần duy nhất lúc khởi động, sau đó chạy lặp in-memory. Do đó, chúng ta hoàn toàn có thể triển khai song song việc chuẩn bị dữ liệu mới (sửa code generator, personas, prompts, bổ sung ứng viên niche và cập nhật DB) mà **không gây ảnh hưởng hay xung đột gì** tới tiến trình Phase 2 đang chạy. 

Khi Phase 2 tuning hiện tại kết thúc, người dùng có thể ngay lập tức kích hoạt bộ tham số mới, rebuild Ground Truth lên 3000 cặp chất lượng cao và khởi chạy đợt tuning bứt phá tiếp theo.

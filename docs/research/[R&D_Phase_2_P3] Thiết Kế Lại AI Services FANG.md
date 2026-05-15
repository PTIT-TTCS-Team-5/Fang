# **Technical Design Document: Chiến Lược Tái Cấu Trúc Toàn Diện AI Services Cho Hệ Thống FANG FastAPI V2**

## **1\. Bối Cảnh Lịch Sử Và Động Lực Nâng Cấp Hệ Thống Kiến Trúc FANG**

Hệ thống FANG phiên bản 2 (v2) hiện đang hoạt động với tư cách là một lõi trí tuệ nhân tạo trung tâm (AI Core) độc lập, cung cấp giao diện lập trình ứng dụng (API) cho toàn bộ các ứng dụng ngoại vi (Thin Client) điển hình như miCareer-mini thông qua tập lệnh fang\_client.py và giao diện người dùng Streamlit.1 Sự phân tách này tuân thủ nguyên tắc thiết kế "Thick Core \- Thin Client", trong đó toàn bộ gánh nặng về xử lý nghiệp vụ, tích hợp mô hình ngôn ngữ lớn (LLM), lưu trữ vector và điều phối RAG (Retrieval-Augmented Generation) được dồn hoàn toàn vào máy chủ FastAPI.1 Các điểm cuối (endpoints) của hệ thống được cô lập dưới tiền tố định tuyến /v2/, với khả năng bảo vệ nguyên tắc chia sẻ tài nguyên nguồn gốc chéo (CORS) thông qua cấu hình CORS\_ALLOWED\_ORIGINS linh hoạt.1

Mặc dù kiến trúc v2 đã chứng minh được tính hiệu quả trong việc hỗ trợ các luồng xử lý phức tạp, điển hình là bộ phân giải tài liệu 5 lớp (5-Tier Parser) và truy vấn đa nguồn, cơ chế tích hợp AI Services hiện tại đang dựa trên nền tảng của các bộ chuyển đổi tự viết (Custom Adapters).1 Tệp tin app/services/rag\_model\_adapters.py đảm nhận vai trò kết nối với 5 loại mô hình từ ba nhà cung cấp lớn là Gemini (Google), OpenAI và Anthropic.1 Cách tiếp cận này yêu cầu hệ thống phải trực tiếp nhập (import) và duy trì các bộ công cụ phát triển phần mềm (SDK) riêng lẻ, dẫn đến một khối lượng mã nguồn tương thích (boilerplate code) khổng lồ, đi kèm với logic xử lý ngoại lệ (try-catch) phân mảnh và khó kiểm thử tự động. Sự cứng nhắc này biểu hiện rõ nhất qua biến MODEL\_CANDIDATES, nơi các cấu hình, giới hạn ngữ cảnh và ngân sách từ vựng bị mã hóa cứng (hardcoded) vào logic ứng dụng.1

Động lực chính thúc đẩy sự ra đời của thiết kế này bắt nguồn trực tiếp từ các quyết định mang tính chiến lược được phê duyệt sau giai đoạn nghiên cứu (R\&D Phase 2, P1 & P2). Dựa trên các chỉ thị và xác nhận định hướng kỹ thuật từ người chịu trách nhiệm hệ thống (được ghi nhận là "Hưng"), ba giới hạn cốt lõi của kiến trúc hiện hành cần được tái thiết kế triệt để bao gồm:

Thứ nhất, đối với lớp nhúng dữ liệu không gian (Embedding Layer), hệ thống hiện đang lưu trữ vector với số chiều cố định 1024-dim dưới định dạng halfvec(1024) của công cụ pgvector trên cơ sở dữ liệu PostgreSQL.1 Định dạng này tối ưu hóa việc sử dụng RAM và tăng tốc độ thuật toán HNSW cosine.1 Việc thay đổi các mô hình nhúng (Embedding Models) trong tương lai có thể trả về các vector có kích thước không tương thích (ví dụ: 1536 chiều của mô hình nguyên bản text-embedding-3-small hoặc 768 chiều từ các mô hình mã nguồn mở).1 Quyết định kỹ thuật tối cao được đưa ra là: Tuyệt đối tránh việc sửa đổi lược đồ cơ sở dữ liệu (Database Schema Migration) sau khi hệ thống đã đi vào vận hành.1 Chiến lược chuẩn hóa tại lớp ứng dụng thông qua kỹ thuật "Zero-Padding" (đệm không) và "Truncation" (cắt cụt) được chốt như một phương án phòng thủ vững chắc nhất.1 Giải pháp này đóng vai trò như một cơ chế đệm, giữ cho hệ thống không bị phá vỡ cấu trúc và tạo tiền đề an toàn cho các chiến dịch nhúng lại toàn bộ dữ liệu (re-embed) trong tương lai khi hạ tầng cho phép.1

Thứ hai, để đạt được trạng thái "model-agnostic" (bất khả tri về mô hình), hệ thống cần một cơ chế chuẩn hóa giao tiếp đầu ra/đầu vào. Việc sử dụng các Cổng Trí tuệ Nhân tạo độc lập (AI Gateway như Kong hoặc Portkey) đã bị loại bỏ hoàn toàn khỏi tầm nhìn kiến trúc.1 Nguyên nhân cốt lõi là do hạn chế về tài nguyên hệ thống của một dự án phát triển cá nhân/độc lập (Indie Developer); việc phải duy trì thêm các thùng chứa (containers) trung gian sẽ tạo ra gánh nặng vận hành quá mức (DevOps overhead) và tăng độ trễ mạng lưới nội bộ.1 Thay vào đó, quyết định được thống nhất là nhúng trực tiếp bộ thư viện LiteLLM Python SDK vào trong lõi của FastAPI.1 Thư viện này sẽ hoạt động như một lớp proxy cục bộ, tiêu chuẩn hóa mọi lệnh gọi API theo định dạng chung của OpenAI, biến mọi mô hình từ các nhà cung cấp khác nhau trở thành một giao diện đồng nhất.1

Thứ ba, sự dịch chuyển từ cấu hình tĩnh sang Cấu hình Động Tập trung (Centralized Dynamic Registry).1 Logic dự phòng mô hình (Fallback Delegation) và kiểm soát định tuyến hiện đang nằm rải rác ở rag\_orchestrator.py và rag\_model\_adapters.py sẽ bị triệt tiêu hoàn toàn.1 Toàn bộ quyền quyết định mô hình nào được gọi, với ngân sách bao nhiêu, chi phí ra sao và chuỗi dự phòng là gì sẽ được nhường lại cho một tệp tin cấu hình duy nhất: models\_registry.yaml.1 Tệp tin này đóng vai trò là "Nguồn chân lý duy nhất" (Single Source of Truth), tách biệt hoàn toàn mã nguồn nghiệp vụ khỏi dữ liệu cấu hình môi trường.1

Báo cáo thiết kế kỹ thuật này sẽ phác thảo chi tiết cách thức mã nguồn Python, kiến trúc thư mục, hệ thống luồng RAG và luồng nạp dữ liệu (Ingestion Pipeline) được định hình lại để phản ánh chính xác các quyết định chiến lược đã nêu trên.

## **2\. Phân Tích So Sánh Trạng Thái Hệ Thống: As-Is So Với To-Be**

Để làm rõ lộ trình chuyển đổi và giá trị mang lại từ đợt tái cấu trúc, việc đối chiếu giữa kiến trúc hiện hành và kiến trúc đích là bước thiết yếu. Bảng dưới đây cung cấp một cái nhìn toàn diện về sự dịch chuyển trong các thành phần cốt lõi của lõi AI FANG.

| Tiêu Chí So Sánh | Trạng Thái Hiện Tại (As-Is \- FANG v2 Core) | Trạng Thái Đích Đề Xuất (To-Be \- FANG AI Services Refactored) |
| :---- | :---- | :---- |
| **Quản Lý Giao Tiếp Mô Hình** | Phụ thuộc vào app/services/rag\_model\_adapters.py chứa nhiều logic kiểm tra cấu trúc SDK độc quyền (Google google-generativeai, OpenAI, Anthropic). | Xóa bỏ hoàn toàn lớp bộ chuyển đổi tự viết. Sử dụng litellm.completion() chuẩn hóa mọi tương tác ngay trong mã nguồn FastAPI. |
| **Kiểm Soát Cấu Hình** | Khai báo biến hằng số MODEL\_CANDIDATES ngay trong tệp Python, khó khăn trong việc thiết lập A/B testing hoặc đổi model khi đang chạy (hot-swap). | "Nguồn chân lý duy nhất" thông qua tệp app/core/models\_registry.yaml, hỗ trợ phân tầng chi phí và giới hạn ngân sách ngữ cảnh độc lập. |
| **Cơ Chế Phục Hồi Lỗi (Fallback)** | Mã nguồn vòng lặp try...except lồng ghép thủ công trong rag\_orchestrator.py để leo thang từ mô hình này sang mô hình khác. | Sử dụng tính năng Ủy quyền Dự phòng tự động của LiteLLM. Ứng dụng chỉ truyền tham số fallbacks=\["model\_a", "model\_b"\] vào hàm. |
| **Quản Lý Xử Lý Ngoại Lệ (Exceptions)** | Mỗi SDK sinh ra một loại lỗi riêng (ví dụ: Google API Error khác với OpenAI Rate Limit). Hệ thống phải bắt (catch) và ánh xạ từng loại lỗi. | LiteLLM chuẩn hóa thành các lớp ngoại lệ thống nhất (litellm.exceptions.RateLimitError, APIError). Lớp dịch vụ xử lý đồng nhất và tinh gọn. |
| **Bảo Vệ Kiến Trúc Lưu Trữ Vector** | Schema cố định halfvec(1024). Nếu text-embedding-3-small hoặc model thay thế trả về chiều dài khác, app/services/persistence.py sẽ gặp lỗi tràn cơ sở dữ liệu. | Tích hợp lớp chuẩn hóa (Zero-Padding / Truncation) sử dụng Numpy trong bộ nhớ ứng dụng. Vector luôn được đúc về đúng 1024 chiều trước khi vào Postgres. |
| **Kiểm Soát Chất Lượng Phân Giải (Parser)** | Cổng chất lượng (ProTierGate) lồng ghép chung với cơ chế thử lại của mạng, làm mờ ranh giới giữa lỗi kỹ thuật và lỗi nghiệp vụ. | Tách bạch hoàn toàn: LiteLLM quản lý lỗi mạng lưới hạ tầng. ProTierGate chỉ tập trung phân tích văn bản AI (heuristic) xem chất lượng có đạt yêu cầu JSON không. |
| **Cơ Chế Theo Dõi Ngân Sách Hội Thoại** | Trích xuất bộ đếm token rườm rà. Hệ thống phải đếm thủ công dựa trên thư viện tiktoken hoặc ước lượng không chuẩn xác trên các mô hình Anthropic/Gemini. | LiteLLM hỗ trợ stream\_options={"include\_usage": True}. Phân giải tự động prompt\_tokens cho mọi dòng dữ liệu (stream), kích hoạt cảnh báo 80% độ chính xác tuyệt đối. |

Sự chuyển dịch này không chỉ giải quyết bài toán giảm thiểu nợ kỹ thuật (technical debt) mà còn gia tăng đáng kể khả năng đáp ứng của hệ thống trước sự biến thiên khó lường của thị trường cung cấp dịch vụ AI đám mây, tuân thủ đúng nguyên lý Đóng-Mở (Open-Closed Principle) trong kỹ nghệ phần mềm.

**NOTE FROM HƯNG**: Ghi chú -  10/05/2026
- Cơ chế fallback khi dùng LiteLLM cần được chỉ ra tường minh, xem xét quyền cấu hình ví dụ như thời gian, lần thử v.v
- ProtierGate cũ sử dụng cơ chế đoán cứng (<50 token là coi là hỏng). Cần nghiên cứu cải thiện ví dụ như: dùng model siêu nhẹ để kiểm tra về định dạng, tính toàn vẹn,  lỗi cú pháp v.v

## **3\. Kiến Trúc Cấu Hình Động Tập Trung (Centralized Dynamic Registry)**

Trọng tâm của bản thiết kế nằm ở khả năng tách rời siêu dữ liệu của mô hình ra khỏi hệ thống thực thi. Sự ra đời của tệp tin models\_registry.yaml là bước tiến then chốt, tạo ra một kho lưu trữ thông tin tập trung, mô tả không chỉ danh tính của các mô hình khả dụng mà còn là quy tắc định tuyến, ngân sách, chuỗi dự phòng và tham số nhúng.1

### **3.1. Thiết Kế Lược Đồ Tệp models\_registry.yaml**

Cấu trúc YAML được thiết kế để phản ánh hệ sinh thái 5 lớp hiện hành của mạng lưới FANG.1 Nhóm mô hình được chia thành hai phân vùng rõ rệt: Nhóm Lite (Tiers 1-3) đóng vai trò tiền tuyến với chi phí siêu rẻ và tốc độ phản hồi tính bằng mili-giây, phục vụ các truy vấn sàng lọc đơn giản và phân giải tài liệu 1; và Nhóm Pro (Tiers 4-5) đóng vai trò vũ khí chiến lược, giải quyết các nhiệm vụ đòi hỏi khả năng tư duy logic và lập luận sâu (complex reasoning), dù chi phí có thể cao gấp 5 đến 20 lần.1

Bên cạnh đó, nó quy định rõ ràng lược đồ nhúng không gian. Do cấu hình cục bộ nhắm đến môi trường phát triển (DEV) với số chiều mặc định là 1024 và tối ưu hóa tài nguyên phần cứng, các đặc tả kỹ thuật này phải được ghi nhận rõ ràng.1 Dưới đây là kiến trúc tệp models\_registry.yaml chi tiết:

```yaml
\# Đường dẫn hệ thống: app/core/models\_registry.yaml  
\# Phiên bản định dạng: 1.0.0  
\# Ngày phê duyệt cập nhật: 10/05/2026  
\# Mục đích: Single Source of Truth điều phối toàn bộ AI Services

metadata:  
  description: "Centralized Dynamic Registry for FANG FastAPI AI Layer."  
  maintainer: "NHÁP"

\# \=====================================================================  
\# 1\. CẤU HÌNH LỚP NHÚNG KHÔNG GIAN (EMBEDDING LAYER CONFIGURATION)  
\# \=====================================================================  
embedding\_models:  
  default\_provider: "google"  
  target\_dimension: 1024 \# đúc vector về 1024 chiều
  models:  
    gemini-embedding-001:  
      litellm\_path: "google/gemini-embedding-001"  
      native\_dimension: 3072 \# Kích thước nguyên bản từ nhà cung cấp (Gemini 2)  
      cost\_per\_1m\_tokens: 0.15  
      description: "Default embedding model for DEV environment. MTEB score 68.32 (best for Vietnamese), native Matryoshka support (MRL), free tier via Google AI Studio. Requires truncation down to 1024-dim."  

\# \=====================================================================  
\# 2\. ĐỊNH NGHĨA MÔ HÌNH SINH VĂN BẢN (GENERATION MODELS)  
\# \=====================================================================  
generation\_models:  
  \# LITE TIERS: Tối ưu cho tốc độ và giá thành. Được ưu tiên chạy trước.  
  \# Đặc biệt: Tối ưu hóa cho CV Parsing và tác vụ suy luận phân tích ngách.  
  
  gemini-3.1-flash-lite-preview:  
    tier: 1  
    litellm\_path: "gemini/gemini-3.1-flash-lite-preview"  
    context\_window: 1048576  
    cost\_per\_1m\_input: 0.25  
    cost\_per\_1m\_output: 1.50  
    description: "Tier 1 (Default Lite): Ra mắt tháng 3/2026, miễn phí qua Google AI Studio, tốc độ 363 tokens/giây, MTEB: 68.32 (tốt cho tiếng Việt). Primary engine cho CV parsing pipeline."

  gpt-5.4-mini:  
    tier: 2  
    litellm\_path: "openai/gpt-5.4-mini"  
    context\_window: 400000  
    cost\_per\_1m\_input: 0.75  
    cost\_per\_1m\_output: 4.50  
    description: "Tier 2 (Lite Fallback): Tối ưu hóa suy luận, vượt trội về mã hóa JSON. Hỗ trợ Prompt Caching ($0.075 input). Fallback an toàn khi Google API gặp Rate Limit."

  gemini-3.1-flash:  
    tier: 3  
    litellm\_path: "gemini/gemini-3.1-flash"  
    context\_window: 1000000  
    cost\_per\_1m\_input: 0.75  
    cost\_per\_1m\_output: 3.00  
    description: "Tier 3 (Lite Alternative): Phiên bản mạnh hơn bản Lite. Hỗ trợ miễn phí từ Google Free Tier"

  claude-4.5-haiku:  
    tier: 4  
    litellm\_path: "anthropic/claude-4.5-haiku"  
    context\_window: 200000  
    cost\_per\_1m\_input: 1.00  
    cost\_per\_1m\_output: 5.00  
    description: "Tier 4 : Mô hình nhanh nhất của Anthropic, lý tưởng cho dữ liệu phi cấu trúc"

  \# PRO TIERS: Tối ưu cho lập luận phức tạp. Chỉ gọi khi vượt qua ProTierGate.  
  \# Đặc biệt: Xử lý các CV không đạt Quality Gate, dữ liệu dị biệt cao.  

  gemini-3.1-pro-preview:  
    tier: 5  
    litellm\_path: "gemini/gemini-3.1-pro-preview"  
    context\_window: 1000000  
    cost\_per\_1m\_input: 2.00  
    cost\_per\_1m\_output: 12.00  
    description: "Tier 5 (ProTierGate Primary): Khả năng suy luận mạnh mẽ ngang ngửa GPT-5.4. Hỗ trợ miễn phí từ Google Free Tier. Entry point cho suy luận phức tạp CV."

  gpt-5.4:  
    tier: 6  
    litellm\_path: "openai/gpt-5.4"  
    context\_window: 272000  
    cost\_per\_1m\_input: 2.50  
    cost\_per\_1m\_output: 15.00  
    description: "Tier 6: Giải pháp cuối cùng cho CV mang tính dị biệt cao. Chi phí đắt đỏ, chỉ kích hoạt khi tất cả Tier 5 thất bại."

\# \=====================================================================  
\# 3\. CHÍNH SÁCH ĐỊNH TUYẾN VÀ CHUỖI DỰ PHÒNG (ROUTING MODES & FALLBACKS)  
\# \=====================================================================  
routing\_modes:  
  \# Các chiến lược dự phòng tự động nhiều cấp  
  auto-lite:  
    primary: "gemini-3.1-flash-lite-preview"  
    fallbacks: \["gpt-5.4-mini", "gemini-3.1-flash", "claude-4.5-haiku"\]  
    description: "Standard mode for CV parsing and basic RAG. Cascades through tiers 1, 2, 3 and 4. Leverages Google Free Tier + OpenAI + Anthropic, Prompt Caching for cost optimization."  
      
  auto-pro:  
    primary: "gemini-3.1-pro-preview"  
    fallbacks: \["gpt-5.4"\]  
    description: "Escalation mode activated via ProTierGate. Cascades through tiers 5 and 6. For complex reasoning and quality gate rescue operations."

  \# Các chiến lược chỉ định trực tiếp (Không có Fallbacks để tránh tiêu hao tài nguyên ngoài ý muốn)  
  direct-gemini-3.1-flash-lite-preview:  
    primary: "gemini-3.1-flash-lite-preview"  
    fallbacks:  
    description: "Strictly calls Gemini 3.1 Flash Lite Preview. Cost-optimized direct mode for basic CV parsing."  
      
  direct-gpt-5.4-mini:  
    primary: "gpt-5.4-mini"  
    fallbacks:  
    description: "Strictly calls GPT-5.4-mini. Used when HR user explicitly needs OpenAI inference."  

  direct-gemini-3.1-flash:  
    primary: "gemini-3.1-flash"  
    fallbacks:  
    description: "Strictly calls Gemini 3.1 Flash. Direct mode for enhanced Lite-tier reasoning."

  direct-gemini-3.1-pro-preview:  
    primary: "gemini-3.1-pro-preview"  
    fallbacks:  
    description: "Strictly calls Gemini 3.1 Pro Preview. Direct mode for complex reasoning via Google's Pro tier."

  direct-claude-4.5-haiku:  
    primary: "claude-4.5-haiku"  
    fallbacks:  
    description: "Strictly calls Claude 4.5 Haiku. Direct mode for Anthropic-based inference on unstructured data."

  direct-gpt-5.4:  
    primary: "gpt-5.4"  
    fallbacks:  
    description: "Strictly calls GPT-5.4. Ultimate direct mode for highest-tier OpenAI inference. Maximum cost, maximum capability."
```
### **3.2. Cơ Sở Lập Luận Thiết Kế Khai Báo (Declarative Rationale)**

1. **Tiền Tố Định Tuyến Chuẩn Hóa (litellm\_path)**: Thuộc tính này là chìa khóa để khai thác LiteLLM. Bằng cách nối tên nhà cung cấp với tên mô hình (ví dụ: anthropic/claude-4.5-haiku hoặc gemini/gemini-3-flash) 1, cấu hình này cung cấp cho litellm.completion() điểm kết nối đích chính xác mà không yêu cầu hệ thống phải biên dịch lại logic nội bộ.1 Bất kỳ thay đổi phiên bản mô hình nào trong tương lai (như việc nâng cấp từ claude-4.5-haiku lên một phiên bản tiềm năng claude-5) chỉ yêu cầu sửa đổi văn bản YAML.  
2. **Đại lượng context\_window (Giới hạn Ngân sách Từ vựng)**: Tham số này được sử dụng làm mẫu số cho phép tính toán cảnh báo ngữ cảnh tại bước thứ 8 trong luồng 12 bước của hệ thống truy vấn đàm thoại RAG.1 Do chiến lược v2 đã loại bỏ cơ chế "Trượt Khung Ngữ Cảnh" (Sliding Window) nhằm bảo tồn thông tin, hệ thống phải liên tục kiểm tra tổng số lượng token đã tiêu hao so với giới hạn của mô hình.1 Cấu hình tĩnh này cho phép FastAPI lấy context\_window (ví dụ: 800,000 cho Gemini Flash) nhân với ngưỡng CONTEXT\_BUDGET\_WARNING\_THRESHOLD (thường là 80%) để đưa ra cảnh báo contextWarning khi phiên làm việc phình to.1  
3. **Khóa routing\_modes với Mảng fallbacks**: Cấu trúc này ánh xạ tỷ lệ 1:1 với khái niệm 7 chế độ modelMode từ hệ thống phiên bản trước.1 Đặc biệt, nó loại bỏ khối mã if-else khổng lồ. Nếu tham số fallbacks trống, ứng dụng sẽ hiểu rằng người dùng nhân sự (HR) đã chọn đích danh một mô hình duy nhất và từ chối kích hoạt chuyển đổi chuỗi dự phòng âm thầm, đáp ứng chính xác yêu cầu về tính minh bạch đã định nghĩa trong tài liệu quy trình truy vấn hệ thống.1

### **3.3. Giải Pháp Mã Nguồn Nạp Cấu Hình Động Trình Quản Lý Dữ Liệu (Registry Manager)**

Để hiện thực hóa tệp YAML vào bộ nhớ ứng dụng FastAPI, lớp RegistryManager được xây dựng dựa trên mẫu thiết kế Singleton kết hợp với thư viện Pydantic. Việc sử dụng Pydantic đảm bảo tính toàn vẹn và an toàn kiểu dữ liệu (type safety), một nguyên tắc bắt buộc trong các hệ thống phần mềm doanh nghiệp cấp sản xuất (production-grade software).

```python
\# app/core/models/registry\_schema.py  
import yaml  
import logging  
from typing import Dict, List, Optional  
from pydantic import BaseModel, Field, field\_validator

logger \= logging.getLogger(\_\_name\_\_)

\# \--- Định nghĩa Schema Pydantic Xác thực Siêu Dữ Liệu \---

class GenerationModelConfig(BaseModel):  
    tier: int \= Field(ge=1, le=6, description="Cấp độ từ 1 (Flask-Lite) đến 6 (Pro)")  
    litellm\_path: str \= Field(..., description="Đường dẫn gọi LiteLLM")  
    context\_window: int \= Field(gt=0, description="Giới hạn số token tối đa cho hội thoại")  
    cost\_per\_1m\_input: float  
    cost\_per\_1m\_output: float  
    description: Optional\[str\] \= None

class RoutingModeConfig(BaseModel):  
    primary: str \= Field(..., description="Tên mô hình chính (phải ánh xạ với generation\_models)")  
    fallbacks: List\[str\] \= Field(default\_factory=list, description="Danh sách tuần tự các mô hình dự phòng")  
    description: Optional\[str\] \= None

class EmbeddingModelConfig(BaseModel):  
    litellm\_path: str \= Field(..., description="Đường dẫn gọi LiteLLM cho embedding (ví dụ: google/gemini-embedding-001)")  
    native\_dimension: int \= Field(gt=0, description="Kích thước chiều nguyên bản trả về từ nhà cung cấp (ví dụ: 3072 cho Gemini)")  
    cost\_per\_1m\_tokens: float \= Field(gt=0, description="Chi phí theo ngàn token")  
    description: Optional\[str\] \= None

class EmbeddingRegistry(BaseModel):  
    default\_provider: str \= Field(..., description="Nhà cung cấp embedding mặc định (ví dụ: 'google')")  
    target\_dimension: int \= Field(ge=1024, le=1024, description="Chiều chuẩn hóa cố định cho lược đồ pgvector (1024)")  
    models: Dict\[str, EmbeddingModelConfig\] \= Field(..., description="Danh sách các mô hình embedding khả dụng")

class ModelRegistrySchema(BaseModel):  
    metadata: Dict\[str, str\]  
    embedding\_models: EmbeddingRegistry  
    generation\_models: Dict\[str, GenerationModelConfig\]  
    routing\_modes: Dict

\# \--- Tóm Tắt Cấu Trúc Pydantic Schema Cho AI Registry \---  
\# Tất cả 5 lớp schema trên đảm bảo tính toàn vẹn dữ liệu (Type Safety):  
\# 1\. GenerationModelConfig: Định nghĩa từng mô hình sinh văn bản (tier, litellm\_path, context\_window, cost)  
\# 2\. RoutingModeConfig: Định nghĩa chiến lược định tuyến (primary model + fallback chain)  
\# 3\. EmbeddingModelConfig: Định nghĩa từng mô hình embedding (litellm\_path, native\_dimension, cost)  
\# 4\. EmbeddingRegistry: Quản lý lớp embedding (default\_provider, target\_dimension=1024 cố định, models dict)  
\# 5\. ModelRegistrySchema: Root schema chứa toàn bộ thông tin cấu hình (metadata, embedding\_models, generation\_models, routing\_modes)

\# \--- Lớp Trình Quản Lý Mẫu Độc Bản (Singleton Manager) \---

class RegistryManager:  
    """  
    Trình quản lý cấu hình AI nội bộ cung cấp giao diện truy xuất Nguồn Chân Lý Duy Nhất.  
    Chịu trách nhiệm nạp, xác thực (validation) tệp YAML và cung cấp giao diện truy vấn (Query Interface) để các dịch vụ  
    truy xuất siêu dữ liệu mô hình một cách an toàn. Xác thực bao gồm:  
    - Generation Models: Tất cả GenerationModelConfig phải khớp với litellm\_path hợp lệ  
    - Embedding Models: EmbeddingRegistry đảm bảo target\_dimension = 1024 và models dict không rỗng  
    - Routing Modes: Primary model phải tồn tại trong generation\_models; fallbacks phải là danh sách hợp lệ  
    """  
    \_instance \= None  
    \_config: Optional \= None

    def \_\_new\_\_(cls, filepath: str \= "app/core/models\_registry.yaml"):  
        if cls.\_instance is None:  
            cls.\_instance \= super(RegistryManager, cls).\_\_new\_\_(cls)  
            cls.\_instance.\_load\_and\_validate(filepath)  
        return cls.\_instance

    def \_load\_and\_validate(self, filepath: str) \-\> None:  
        try:  
            with open(filepath, 'r', encoding='utf-8') as file:  
                raw\_yaml \= yaml.safe\_load(file)  
            \# Ép kiểu và kiểm định tự động thông qua Pydantic  
            self.\_config \= ModelRegistrySchema(\*\*raw\_yaml)  
            logger.info("Successfully loaded and validated Centralized Dynamic Registry.")  
        except FileNotFoundError:  
            logger.error(f"Critical System Error: YAML config not found at {filepath}")  
            raise  
        except Exception as e:  
            logger.error(f"Schema validation failed for AI Registry: {str(e)}")  
            raise

    @classmethod  
    def get\_config(cls) \-\> ModelRegistrySchema:  
        if cls.\_config is None:  
            raise RuntimeError("RegistryManager is not initialized. Ensure app startup event calls load().")  
        return cls.\_config
```
Quá trình khởi tạo lớp RegistryManager được đăng ký vào chu kỳ khởi động của FastAPI (Lifespan event trong app/main.py), đảm bảo rằng toàn bộ thông số định tuyến và cấu hình mạng lưới đã được nạp vào RAM trước khi nhận bất kỳ yêu cầu kết nối nào từ phía các lớp dịch vụ (Client Layer). Bất kỳ thay đổi thông số nào không hợp lệ đều sẽ gây ra lỗi tại thời điểm hệ thống bắt đầu chạy (fail-fast), một đặc tính vô cùng quan trọng để ngăn chặn lỗi hệ thống tĩnh lan truyền trong suốt quá trình chạy.

## **4\. Tái Thiết Kế Luồng Điều Phối Sinh Văn Bản (Generation Services & RAG Orchestration)**

Một trong những quy trình phức tạp nhất trong kiến trúc FANG là luồng truy vấn đàm thoại qua 12 bước chi tiết được điều khiển bởi tệp app/services/rag\_orchestrator.py và app/services/rag\_query.py. Luồng thông tin bắt đầu từ việc xác thực ứng viên (bước 1), nạp lịch sử tương tác đàm thoại không dùng khung trượt (bước 7), lắp ghép ngữ cảnh đa nguồn (bước 6), trước khi thực hiện bước thứ 10 là Gọi mô hình ngôn ngữ (LLM Invocation) kết hợp chính sách retry dự phòng và kết thúc tại việc duy trì hệ thống kiểm toán lưu trữ (Bước 11 & 12).1

Sự xuất hiện của công nghệ LiteLLM thay đổi hoàn toàn cục diện cách khối điều phối (Orchestrator) được triển khai. Nó đảm nhận vai trò quản lý vòng đời (lifecycle management) đối với các lệnh gọi, đồng thời kết xuất dữ liệu đo lường theo dõi tài nguyên ngân sách.

### **4.1. Cơ Chế Ủy Quyền Dự Phòng Tự Động (Fallback Delegation)**

Trước đây, khi nhóm hệ thống gọi một chế độ auto-lite, một quy trình được phân rã thủ công thông qua 3 khối Try-Catch phải được cấu trúc để truyền tài liệu cho Gemini Flash Lite (Tier 1), nếu thất bại với các lỗi API quá tải (Rate limit), nó phải tự khởi tạo lại đường truyền đến phiên bản GPT-mini (Tier 2), và kế tiếp là Gemini Flask (Tier 3).1 Với nguyên lý thiết kế hệ thống LiteLLM, nhà phát triển cấu trúc lại việc định tuyến này thông qua một thông số danh sách thuần túy (tham số fallbacks=...).1 Mã nguồn xử lý lõi của khối Điều Phối Trí Tuệ RAG (RAG Orchestrator) được làm sạch triệt để.

Dưới đây là một ví dụ chuyên sâu về việc thiết kế lớp RAGOrchestrator trong FastAPI với vai trò tiêu chuẩn hóa mô hình đàm thoại đa nhà cung cấp, với chú giải cho các quyết định kiến trúc:


```python
\# app/services/rag\_orchestrator.py  
import logging  
from typing import List, Dict, Any  
from litellm import completion  
from litellm.exceptions import RateLimitError, APIError, ContextWindowExceededError  
from app.core.models.registry\_schema import RegistryManager  
from app.core.config import settings \# Lưu trữ hằng số CONTEXT\_BUDGET\_WARNING\_THRESHOLD

logger \= logging.getLogger(\_\_name\_\_)

class RAGOrchestrator:  
    """  
    Trái tim của hệ thống Luồng Truy Vấn Đàm Thoại RAG (Bước 10).  
    Đảm nhận việc quản lý ngữ cảnh đàm thoại, gọi thư viện LiteLLM,   
    ủy quyền dự phòng và kiểm tra ngân sách từ vựng.  
    """  
    def \_\_init\_\_(self):  
        \# Lấy tham chiếu siêu dữ liệu tĩnh từ RAM  
        self.registry \= RegistryManager.get\_config()  
        self.warning\_threshold \= getattr(settings, 'CONTEXT\_BUDGET\_WARNING\_THRESHOLD', 0.8)

    def invoke\_generation(  
        self,   
        assembled\_messages: List\],   
        model\_mode: str,   
        stream: bool \= True  
    ) \-\> Dict\[str, Any\]:  
        """  
        Gửi yêu cầu tới nền tảng LLM theo chế độ model\_mode xác định   
        (ví dụ: 'auto-lite', 'direct-gpt-mini', 'auto-pro').  
        """  

        \# Bước 10.1: Phân giải định tuyến từ Nguồn Chân Lý  
        if model\_mode not in self.registry.routing\_modes:  
            raise ValueError(f"Hệ thống không nhận dạng model\_mode: {model\_mode}. Kiểm tra yaml.")  
              
        routing\_cfg \= self.registry.routing\_modes\[model\_mode\]  
        primary\_key \= routing\_cfg.primary  
          
        \# Tra cứu tiền tố chuẩn (ví dụ: 'gemini/gemini-3-flash')  
        primary\_model\_path \= self.registry.generation\_models\[primary\_key\].litellm\_path  
          
        \# Ánh xạ các key dự phòng thành các đường dẫn tương ứng  
        fallback\_paths \= \[  
            self.registry.generation\_models\[fb\_key\].litellm\_path   
            for fb\_key in routing\_cfg.fallbacks  
        \]

        logger.info(f"Khởi động RAG Orchestrator. Tuyến chính: {primary\_model\_path}. Dự phòng: {fallback\_paths}")

        try:  
            \# Tham số then chốt: stream\_options={"include\_usage": True}  
            \# Yêu cầu bắt buộc để bước 8 (Budget Check) có dữ liệu định lượng  
            stream\_config \= {"include\_usage": True} if stream else None

            \# Bước 10.2: Ủy quyền Dự phòng (Fallback Delegation) vào LiteLLM SDK  
            response \= completion(  
                model=primary\_model\_path,  
                messages=assembled\_messages,  
                fallbacks=fallback\_paths if fallback\_paths else None,  
                stream=stream,  
                stream\_options=stream\_config  
            )  
              
            \# Nếu phản hồi theo dạng luồng (stream), hệ thống FastAPI Generator sẽ   
            \# chịu trách nhiệm đọc và trả các chunk, đồng thời phân tích đối tượng usage ở mảnh cuối cùng.  
            if stream:  
                return {"type": "streaming\_response", "data": response, "model\_key": primary\_key}  
            else:  
                \# Phục vụ luồng phân giải CV Parser (Không stream)  
                return {  
                    "type": "static\_response",   
                    "content": response.choices.message.content,  
                    "usage": response.usage.model\_dump() if response.usage else None,  
                    "model\_key": primary\_key  
                }

        \# Xử lý các lỗi được LiteLLM chuẩn hóa thay cho lỗi phân mảnh của SDK nhà cung cấp  
        except RateLimitError as e:  
            logger.error(f"Khóa tài nguyên cạn kiệt (Rate Limit Exhausted) trên toàn bộ chuỗi Fallback: {str(e)}")  
            raise RuntimeError("Hệ thống AI hiện đang quá tải. Xin vui lòng thử lại sau ít phút.")  
              
        except ContextWindowExceededError as e:  
            logger.error(f"Tràn khung ngữ cảnh: {str(e)}")  
            raise ValueError("Kích thước hội thoại đã vượt quá năng lực mô hình. Đề xuất tạo hội thoại mới.")  
              
        except APIError as e:  
            logger.error(f"Lỗi cổng giao tiếp trung tâm (Upstream Gateway Failure): {str(e)}")  
            raise SystemError("Tuyến kết nối hệ thống AI bị gián đoạn.")
```
Sự loại bỏ của rag\_model\_adapters.py là một chiến thắng thiết kế đáng kể.1 Mã nguồn không còn chứa các lệnh import google.generativeai hay import anthropic. Lớp RAGOrchestrator trở nên tinh gọn, thuần túy là một cơ sở hạ tầng mạng nhận dữ liệu từ các khối đa nguồn (JobPosting, Candidate Profile, Retrieved CV Chunks) 1 và điều phối thông qua chức năng duy nhất litellm.completion().1 Khả năng tương thích nền tảng, cơ chế retry khi trễ mạng và phân tích chuỗi văn bản bị đứt gãy hoàn toàn được quản lý tự động bởi LiteLLM.

### **4.2. Giải Quyết Vấn Đề Quản Lý Ngân Sách Khung Ngữ Cảnh**

Bước 8 trong chu trình là Kiểm tra Ngân sách (Budget Check). Bối cảnh đặc thù của hệ thống RAG đàm thoại cho nhân sự HR tại FANG là việc ghép nối một số lượng dữ liệu lớn tại bước 6: "Context Assembly" (Lắp ghép Ngữ Cảnh).1 System Prompt chuyên dụng được chèn hàng loạt các khối văn bản (blocks) thông tin: , , và đặc biệt là (nội dung bình duyệt nhiều vòng từ interviewer).1

Sự phình to của chuỗi System Prompt, kết hợp với thực tế v2 loại bỏ cơ chế "Sliding Window" (Xóa bớt lịch sử cũ) tại bước 7 nhằm giữ vững dòng suy luận của AI 1, dẫn đến một rủi ro hiện hữu: Tràn giới hạn token của mô hình (ví dụ Claude Haiku chỉ đạt 200,000 max context).1

Đoạn mã cấu hình stream\_options={"include\_usage": True} từ LiteLLM SDK đóng vai trò sống còn trong chiến lược bảo vệ hệ thống.1 Khi API FastAPI của lõi thực thi việc tiêu thụ đoạn văn bản theo luồng (chunk streaming), đối tượng cuối cùng được trả về sẽ mang theo gói dữ liệu đo lường thông số token (prompt\_tokens \+ completion\_tokens).

FastAPI tại điểm cuối (Endpoint) sẽ đọc thông số này, đối chiếu với chỉ số context\_window thuộc về model\_key đang thao tác đã cấu hình trong models\_registry.yaml. Phép toán logic được kích hoạt:

*Tính Tổng Mức Tiêu Thụ (%)* \= (Tổng token mới nhất/Giới hạn context_window \* 100)

Nếu giá trị vượt quá hằng số hệ thống CONTEXT\_BUDGET\_WARNING\_THRESHOLD (mặc định 80%), tầng Middleware của lớp Dịch Vụ sẽ tự động đẩy một thẻ cảnh báo contextWarning vào một kênh phụ trong kiến trúc kết xuất phía Web.1 Cảnh báo này cung cấp cho người dùng nhân sự hai tuỳ chọn xử lý khẩn cấp: (1) "Tóm tắt & tiếp tục" (hệ thống sẽ tự động gửi toàn bộ văn bản cho một mô hình Tier 1 giá cực rẻ để nén lại trước khi tái khởi động chuỗi RAG); hoặc (2) "Bắt đầu hội thoại mới".1 Phương pháp Tóm tắt-Thay thế (Token Budget \+ Summarization) này giải quyết được điểm yếu chí mạng của hệ thống Sliding Window cũ là đánh mất các dữ kiện nền của phiên phỏng vấn đầu tiên.1

## **5\. Tái Kiến Trúc Đường Ống Xử Lý Đầu Vào (Ingestion Flow) & ProTierGate**

Quy trình nạp dữ liệu ứng viên (Ingestion Flow) với mục đích biến một tệp tài liệu PDF lý lịch trích ngang (CV) hỗn loạn thành tập hợp các vector tri thức là luồng API quan trọng bậc nhất, được khai báo thông qua phương thức POST /v2/ingestion/jobs.1 Lộ trình dữ liệu trải qua 6 công đoạn khép kín: Nhận sự kiện (Trigger) chứa tải trọng jobAppId và URL của CV (cvSnapUrl), chuyển đổi PDF sang dạng JSON thông qua cơ chế Fallback phân cấp (5-Tier), chuyển đổi sang kết cấu Markdown, phân mảnh văn bản hỗn hợp (Hybrid Chunking), Nhúng Vector (Embedding) và cuối cùng là Lưu trữ (Persistence).1

Giai đoạn phức tạp và tiêu hao chi phí lớn nhất nằm ở bước thứ 2: Bộ Phân Giải 5 Cấp Độ (5-Tier Parser).1 Tương tự như hệ thống RAG đàm thoại, bộ phân giải này tận dụng năng lực phân cấp mô hình nhưng tuân thủ một bộ quy tắc khắt khe hơn: Nó dựa vào Cổng Phân Loại Nâng Cao (ProTierGate).1

### **5.1. Triết Lý Thiết Kế Của Cổng Phân Loại ProTierGate**

Sự phân nhóm giữa Lite Tiers (gemini-3.1-flash-lite-preview, gpt-5.4-mini, gemini-3.1-flash, claude-4.5-haiku) và Pro Tiers (gemini-3.1-pro-preview, gpt-5.4) là ranh giới của bài toán tối ưu chi phí (Cost Optimization). Ưu điểm của nhóm Lite là chi phí vận hành siêu thấp (từ $0.25 đến $0.75 cho 1M input tokens) và tốc độ trả kết quả nhanh (363 tokens/giây), vô cùng phù hợp cho các luồng phân giải CV đại trà.1 Tuy nhiên, các CV có kết cấu đa cột, định dạng phi truyền thống hoặc cấu trúc câu trúc trắc thường gây nhầm lẫn cho khả năng thiết lập JSON của Lite models. Khi đó, nhóm mô hình Pro \- với giá trị kinh tế từ $2.00 đến $2.50 cho input, cao gấp 5 đến 10 lần chi phí vận hành \- cần được huy động bởi khả năng lập luận đa không gian mạnh mẽ.1

Chốt kiểm soát chất lượng (Quality Gate) ProTierGate được cấu thành bởi các thuật toán chẩn đoán tự động (Heuristic Analysis). Theo các nguyên lý thiết kế, FANG thực thi quy định "Chỉ leo lên tầng cao cấp khi sai phạm thuộc về chất lượng, không leo thang nếu nguyên nhân do hạ tầng mạng".1 Nghĩa là, nếu toàn bộ 3 tầng cấp Lite đều trả về RateLimitError hoặc Timeout, hệ thống sẽ bảo lưu trạng thái hệ thống, trả về lỗi hạ tầng và không kích hoạt mô hình Pro nhằm ngăn việc tiêu hao hàng chục đô-la vào một trung tâm dữ liệu đang bảo trì.1 Ngược lại, nếu văn bản JSON trả về bị ngắn bất thường (dưới 50 ký tự) hoặc chứa các câu từ chối phục vụ (ví dụ: "Tôi không có thông tin", "Tôi không thể"), hệ thống sẽ gán cờ low\_confidence\_output và chuyển tiếp luồng yêu cầu cho nhóm Pro.1

### **5.2. Chuyển Đổi Logic Bộ Phân Giải Với LiteLLM**

Cơ chế ủy quyền tự động của cấu hình định tuyến thông qua tệp YAML (auto-lite với 3 cấp độ dự phòng) đảm nhiệm toàn bộ phần quản lý mạng lưới (Network Reliability), giải phóng ứng dụng FastAPI khỏi các vòng lặp xử lý lỗi vô ích. Khối lượng mã nguồn nghiệp vụ trong app/services/cv\_parser.py nay chỉ còn lại một giao diện kiểm soát Heuristic gọn gàng.1

```python
\# app/services/cv\_parser.py  
import json  
import logging  
from app.services.rag\_orchestrator import RAGOrchestrator

logger \= logging.getLogger(\_\_name\_\_)

class QualityGateException(Exception):  
    """Ngoại lệ chuyên dụng đánh dấu kết quả trả về từ mô hình có chất lượng thấp."""  
    pass

class CVParserService:  
    """  
    Điều phối Bước 2 trong luồng Ingestion Flow: Chuyển hóa CV nguyên bản sang JSON.  
    Thiết kế tận dụng tối đa kiến trúc phân tách ProTierGate.  
    """  
    def \_\_init\_\_(self):  
        self.orchestrator \= RAGOrchestrator()

    def \_quality\_gate\_passed(self, raw\_text: str) \-\> bool:  
        """  
        Thực thi quy tắc đánh giá Heuristic:   
        1\. Độ dài văn bản phải lớn hơn 50 ký tự.  
        2\. Không chứa các cụm từ chối trả lời do lớp lọc an toàn của LLM kích hoạt.  
        """  
        if not raw\_text or len(raw\_text.strip()) \< 50:  
            logger.warning("Quality Gate Failed: Text length under 50 characters.")  
            return False  
              
        denial\_phrases \= \["tôi không thể", "không có thông tin", "i cannot", "unable to process"\]  
        lower\_text \= raw\_text.lower()  
        if any(phrase in lower\_text for phrase in denial\_phrases):  
            logger.warning("Quality Gate Failed: Denial signal detected in output.")  
            return False  
              
        return True

    def \_format\_to\_json(self, raw\_text: str) \-\> dict:  
        """Làm sạch và ép kiểu chuỗi văn bản về JSON Object."""  
        \# Bỏ qua các dấu code block (\`\`\`json... \`\`\`) để parse  
        clean\_text \= raw\_text.replace("\`\`\`json", "").replace("\`\`\`", "").strip()  
        try:  
            return json.loads(clean\_text)  
        except json.JSONDecodeError:  
            raise QualityGateException("JSON structure corrupted.")

    def parse\_cv\_to\_json(self, cv\_raw\_text: str) \-\> dict:  
        """  
        Giao diện chính phục vụ việc phân giải (Parsing) sử dụng chiến lược 5-Tier Fallback.  
        """  
        messages \=  
          
        try:  
            \# GIAI ĐOẠN 1: Tiến hành chuỗi Fallback Nội bộ Khối Lite (Flash \-\> Mini \-\> Haiku)  
            \# Cơ chế ủy quyền mạng lưới LiteLLM thực hiện tuần tự và tự động trả kết quả.  
            logger.info("Executing Auto-Lite fallback chain for Ingestion.")  
            response\_lite \= self.orchestrator.invoke\_generation(  
                assembled\_messages=messages,   
                model\_mode="auto-lite",   
                stream=False  
            )  
              
            output\_content \= response\_lite.get("content", "")  
              
            \# GIAI ĐOẠN 2: Thử nghiệm Cổng Kiểm Soát Chất Lượng ProTierGate  
            if self.\_quality\_gate\_passed(output\_content):  
                return self.\_format\_to\_json(output\_content)  
            else:  
                \# Kích hoạt leo thang thông qua cờ chất lượng  
                raise QualityGateException("low\_confidence\_output")

        except QualityGateException as qg\_err:  
            \# GIAI ĐOẠN 3: Leo thang chiến lược (Escalation) sang chuỗi Pro Tiers   
            \# Nguyên nhân: Nhóm Lite xử lý được nhưng chất lượng ngữ nghĩa quá kém.  
            \# Chuỗi tự động kích hoạt: Gemini Pro \-\> GPT 5.5  
            logger.warning(f"ProTierGate activated due to {str(qg\_err)}. Escalating to auto-pro chain.")  
            response\_pro \= self.orchestrator.invoke\_generation(  
                assembled\_messages=messages,   
                model\_mode="auto-pro",   
                stream=False  
            )  
              
            output\_pro\_content \= response\_pro.get("content", "")  
            if self.\_quality\_gate\_passed(output\_pro\_content):  
                return self.\_format\_to\_json(output\_pro\_content)  
            else:  
                \# Ngay cả Pro Tiers cũng thất bại trong việc thiết lập dữ liệu  
                raise RuntimeError("Luồng xử lý từ chối phân giải. CV quá phức tạp hoặc định dạng dị thường.")  
              
        except Exception as e:  
            \# Nếu gặp sự cố hạ tầng (như APIError hoặc RateLimitError) từ Orchestrator,   
            \# hệ thống sẽ TỪ CHỐI leo thang Pro Tiers (Tiết kiệm chi phí).   
            \# Nó truyền trực tiếp lỗi về lớp Client để người dùng đợi hoặc hệ thống tự cron-job gọi lại.  
            logger.error(f"Ingestion bị đình chỉ bởi sự cố hạ tầng AI: {str(e)}")  
            raise
```
Mã nguồn triển khai phía trên giải quyết trọn vẹn yêu cầu phân tách logic: LiteLLM là người chịu trách nhiệm cho đường dẫn truyền dữ liệu (Transport Layer), còn hệ thống FANG và ứng dụng nội bộ nắm giữ quyền kiểm soát chất lượng dữ liệu đầu ra và tối ưu chi phí tài nguyên (Business Layer).1 Sự leo thang cấp độ chỉ xảy ra khi và chỉ khi bộ máy Heuritic của FANG đưa ra kết luận (Verdict) rằng năng lực tư duy của mô hình AI thuộc nhóm Lite là không đủ. Kết quả trả về sau đó tiếp tục bước sang giai đoạn biến đổi từ JSON thành Markdown để giữ kết cấu tiêu đề, phục vụ cho quá trình trích xuất thông tin chung (global\_context) và Phân Mảnh (Hybrid Chunking) tại bước 3 và bước 4\.1 Ở bước 4, mảnh ngữ cảnh chung chứa Tên, Năm Kinh Nghiệm và Kỹ Năng của ứng viên sẽ được "tiêm" thêm vào phần đầu của mỗi khối chunk bị cắt nhỏ.1

## **6\. Chiến Lược Kỹ Thuật Lớp Nhúng Vector (Embedding Layer) & Chuẩn Hóa Không Gian Đệm (Zero-Padding)**

Sau quá trình băm nhỏ văn bản (Chunking), dữ liệu đi vào bước 5: Nhúng Vector (Embedding).1 Mỗi văn bản con lúc này là một đối tượng ChunkPayload đi kèm bộ nhận diện biến môi trường (gồm thuộc tính content \- văn bản, tokenCount \- độ dài token, và chunkIndex \- thứ tự đoạn).1 Lớp dịch vụ Nhúng (app/services/embedding.py) tại hệ thống FANG hiện đang vận hành dựa trên một kiến trúc cố định: sử dụng mô hình gốc text-embedding-3-small từ nhà cung cấp OpenAI.1

Quá trình cấu hình đã xác định việc nén từ không gian nguyên bản 1536 chiều của mô hình xuống còn mức 1024 chiều là lựa chọn phù hợp trên môi trường thử nghiệm nhằm cân bằng giữa việc giảm kích thước bộ nhớ chỉ mục (HNSW index) trong bảng AIDOCUMENTCHUNK của lược đồ Postgres và việc duy trì hiệu suất tính toán ngữ nghĩa.1 Đồng thời, kiểu dữ liệu lưu trữ dưới dạng nửa phân giải halfvec(1024) được khai thác tối đa.1 Biến số EMBEDDING\_VECTOR\_TYPE cho phép nhà quản trị kiểm soát động kịch bản thay đổi sang kiểu dữ liệu vector đầy đủ, song song với việc cung cấp khả năng đánh giá điểm chuẩn (benchmark) giữa chi phí và độ chính xác.1

Tuy nhiên, định dạng cơ sở dữ liệu khóa tĩnh (Hard-locked DB Schema) tạo ra một điểm mù chí mạng: Sự bất đồng bộ không gian (Spatial Dimensionality Mismatch) khi thay đổi nhà cung cấp AI. Nếu trong tương lai, một mô hình giá rẻ hoặc mô hình nguồn mở miễn phí cung cấp các vector ở định dạng 768 chiều (ví dụ: dòng mô hình BERT), cấu trúc cơ sở dữ liệu halfvec(1024) sẽ từ chối truy cập qua một lỗi tràn hệ thống.

Quyết định chiến lược được đánh dấu từ "NOTE FROM Hưng" đã chốt phương án giải quyết bài toán hóc búa này. Việc sửa đổi mô hình cơ sở dữ liệu (Migration) hoặc viết các kịch bản sao chép lược đồ phức tạp trong một môi trường tài nguyên eo hẹp là rủi ro tuyệt đối không thể chấp nhận được.1 Giải pháp đưa ra là phải ưu tiên một cơ chế đệm chuẩn hóa tại lớp ứng dụng, lấy 1024 làm thước đo tiêu chuẩn.1 Hệ thống sẽ thiết kế sử dụng thuật toán Đệm Số Không (Zero-Padding) làm cơ chế phòng thủ tạm thời (Stopgap measure) nhằm cố định kích thước, tạo điều kiện giữ cho đường ống hoạt động độc lập và lên lịch cho việc thiết lập lộ trình nhúng lại toàn bộ các đối tượng lưu trữ (Re-embed) sau này khi năng lực kỹ thuật máy chủ mạnh hơn.1

### **6.1. Triển Khai Mã Nguồn Chuẩn Hóa Bằng Numpy**

Lớp dịch vụ cấu trúc Nhúng (Embedding) sẽ trực tiếp tích hợp khối tiêu chuẩn LiteLLM cho giao tiếp mạng, sử dụng cấu trúc động từ Nguồn Chân Lý, và bổ sung thêm hàm Toán học xử lý tensor không gian bằng thư viện NumPy cực kỳ hiệu quả.1

```python
\# app/services/embedding.py  
import logging  
import numpy as np  
from typing import List, Any  
from litellm import embedding  
from app.core.models.registry\_schema import RegistryManager

logger \= logging.getLogger(\_\_name\_\_)

class EmbeddingService:  
    """  
    Quản lý quy trình (Pipeline) biến đổi đối tượng ngữ nghĩa thành vector toán học.  
    Đảm bảo 100% tuân thủ lược đồ cấu trúc Postgres pgvector (halfvec(1024)).  
      
    Kiến trúc thiết kế:  
    - Sử dụng LiteLLM SDK thông qua cấu hình dynamic từ EmbeddingRegistry (Pydantic)  
    - Trích xuất model\_path từ embedding\_models registry, mặc định là "gemini-embedding-001"  
    - Chuẩn hóa dimension: Zero-Padding nếu native\_dimension < 1024; Truncation nếu > 1024  
    - Xác thực bắt buộc: Mô hình embedding phải định nghĩa native\_dimension để tính toán padding/truncation  
    """  
    def \_\_init\_\_(self):  
        \# Truy xuất thông tin cấu hình Nhúng từ Registry  
        self.registry \= RegistryManager.get\_config()  
        embed\_config \= self.registry.embedding\_models  
          
        self.target\_dim \= embed\_config.target\_dimension \# Bắt buộc là 1024  
          
        \# Mặc định gọi model đã quy định trong default\_provider  
        default\_provider \= embed\_config.default\_provider  
        \# Tra cứu cấu hình mô hình mặc định (gemini-embedding-001 từ Google)  
        default\_model\_key \= "gemini-embedding-001"  
        \# Giải nén đường dẫn LiteLLM từ cấu hình models registry  
        self.model\_path \= embed\_config.models\[default\_model\_key\].litellm\_path  
        self.native\_dimension \= embed\_config.models\[default\_model\_key\].native\_dimension

    def \_normalize\_spatial\_dimension(self, raw\_vector: List\[float\]) \-\> List\[float\]:  
        """  
        Thực thi quyết định kiến trúc cốt lõi: Chuẩn hóa bất đồng bộ kích thước vector.  
        Đảm bảo lược đồ cơ sở dữ liệu halfvec(1024) không bị lỗi.  
        """  
        current\_dim \= len(raw\_vector)  
          
        \# Tối ưu hóa: Nếu đã khớp kích thước, trả về trực tiếp  
        if current\_dim \== self.target\_dim:  
            return raw\_vector  
              
        \# Biến đổi thành ma trận Numpy (mảng 1 chiều) để vận hành hàm số  
        vector\_np \= np.array(raw\_vector, dtype=np.float32)  
          
        if current\_dim \< self.target\_dim:  
            \# THUẬT TOÁN ĐỆM SỐ KHÔNG (ZERO-PADDING)  
            \# Áp dụng cho các mô hình có số chiều nhỏ (ví dụ: 768).  
            \# Bổ sung các giá trị 0 vào phía cuối chiều không gian để lấp đầy khoảng trống.  
            padding\_length \= self.target\_dim \- current\_dim  
            padded\_vector \= np.pad(  
                vector\_np,   
                (0, padding\_length),   
                mode='constant',   
                constant\_values=0  
            )  
            logger.warning(f"Chuẩn hóa không gian: Bổ sung không gian từ {current\_dim} lên {self.target\_dim} (Zero-Padding).")  
            return padded\_vector.tolist()  
              
        else:  
            \# THUẬT TOÁN CẮT CỤT (TRUNCATION)  
            \# Áp dụng cho mô hình nguyên thủy OpenAI trả về 1536 chiều.  
            \# Tiến hành loại bỏ các chiều thông tin phía sau.  
            truncated\_vector \= vector\_np\[:self.target\_dim\]  
            logger.warning(f"Chuẩn hóa không gian: Cắt xén thông tin từ {current\_dim} xuống {self.target\_dim} (Truncation).")  
            return truncated\_vector.tolist()

    def generate\_embeddings(self, chunks: List\[Any\]) \-\> List\[List\[float\]\]:  
        """  
        Ánh xạ danh sách đối tượng ChunkPayload sang hệ vector không gian (Bước 5\)  
        """  
        \# Mỗi ChunkPayload bao gồm thuộc tính '.content' đã qua khâu chèn global\_context  
        texts \= \[chunk.content for chunk in chunks\]  
          
        try:  
            \# Giao tiếp với nhà cung cấp bằng giao thức đồng nhất LiteLLM  
            response \= embedding(  
                model=self.model\_path,  
                input\=texts  
            )  
              
            processed\_embeddings \=  
              
            \# Xử lý theo lô (batch processing) đầu ra và ánh xạ 1-1  
            for item in response.data:  
                raw\_vec \= item\["embedding"\]  
                  
                \# Đi qua trạm chuẩn hóa an toàn  
                normalized\_vec \= self.\_normalize\_spatial\_dimension(raw\_vec)  
                processed\_embeddings.append(normalized\_vec)  
                  
            return processed\_embeddings  
              
        except Exception as e:  
            logger.error(f"Sự cố hệ thống Nhúng dữ liệu: {str(e)}")  
            raise
```
### **6.2. Phân Tích Đánh Đổi Trong Toán Học Vectơ Và Sự Kiện Đồng Bộ Hóa**

Biện luận phía sau quyết định toán học này có giá trị cực kỳ lớn về mặt học thuật ứng dụng (applied academic implications).

Thuật toán Chỉ mục HNSW (Hierarchical Navigable Small World) được cấu hình tại Postgres sử dụng khoảng cách Cosine (Cosine Similarity) để xác định biên độ song song giữa hai vector.1 Công thức tính độ tương đồng bằng thương số giữa Tích vô hướng (Dot Product) và Tích các Độ dài (Magnitude).

Khi hệ thống áp dụng kỹ thuật đệm số 0 (Zero-Padding) cho các mô hình có độ phân giải thấp (như 768 chiều), việc bổ sung 256 con số không ở phần đuôi véc-tơ (tail) thực chất hoàn toàn không làm thay đổi giá trị Tích vô hướng của các hệ tọa độ tương đồng; đồng thời, các giá trị 0 không làm thay đổi Độ lớn tổng thể của véc-tơ ban đầu.1 Sự dịch chuyển này làm sai lệch nhẹ cấu trúc vi mô phân phối xác suất hình học, nhưng giữ lại được phương hướng nền tảng. Khi cả đoạn văn bản truy vấn (Prompt) và đoạn khối (Chunks) trong DB đều được xử lý qua cùng một khối băng thông bù số lượng này, sự tương đương Cosine được bảo toàn gần như nguyên vẹn, đảm bảo hệ thống tìm kiếm vector ở bước 4 của quy trình truy vấn đàm thoại diễn ra suôn sẻ.1

Ngược lại, với kỹ thuật cắt cụt (Truncation) cho không gian 1536 chiều, việc loại bỏ hẳn đi 512 biến không gian ở cuối đồng nghĩa với sự mất mát thông tin thực sự (Data Loss) về các yếu tố ngữ nghĩa thứ cấp. Điểm đánh đổi duy nhất được chấp thuận ở đây là bảo vệ nguyên trạng chi phí phát triển và cấu trúc DB hiện tại. Như một phương án thay thế, hệ thống đã đưa việc "nhúng lại (Re-embed) dữ liệu khi có nguồn lực hạ tầng" thành định hướng chuẩn trong tương lai.1 Nó hoàn toàn không cản trở việc luồng dữ liệu (Persistence) bước số 6 diễn ra liên tục, phân bổ các bản ghi vector vào bảng AIDOCUMENTCHUNK và bảng lưu nội dung nguyên gốc CVPARSED cho mục đích truy xuất gốc rễ về sau.1

## **7\. Các Phương Án Quản Lý Lưu Trữ và Theo Dõi Giám Sát Nền Tảng (Telemetry)**

Với sự di dời logic giao tiếp sang SDK LiteLLM, tầng Dữ Liệu (Data Layer) tiếp tục vận hành mạnh mẽ trên nền tảng PostgreSQL mà không phải chịu ảnh hưởng do thay đổi khung luồng truy vấn API.1

Việc đảm bảo tính ổn định bền vững (Persistence) đối với phiên trò chuyện được điều khiển qua hai tệp app/services/chat\_persistence.py và app/services/persistence.py. Nhóm tệp tin này trực tiếp tham gia quản lý việc nhập lịch sử vào các bảng AICHATCONVERSATION và AICHATMESSAGE, hiện thực hóa kiến trúc quản lý đa kênh lịch sử ATS của FANG.1

### **7.1. Bổ Sung Cơ Chế Theo Dõi Nền Tảng**

Một tính năng vô cùng đáng giá được cấu hình đi kèm chính là việc LiteLLM tự động cho phép theo dõi chi phí cấp phân luồng (request-level tracking).1 Nhóm kỹ sư có thể tích hợp một số thư viện theo dõi hiệu năng và ngân sách nền tảng ngay bên trong tệp Cấu hình Khởi động config.py để ghi log toàn bộ lưu lượng tính bằng USD vào hệ thống giám sát. Cụ thể, các thuộc tính chi phí bao gồm cost\_per\_1m\_input và cost\_per\_1m\_output tại YAML sẽ được cung cấp động để tính hóa đơn tiêu dùng. Khối lượng và chi phí từng phiên đàm thoại (conversation ID) nay đã có cơ sở hạ tầng mạnh mẽ để hỗ trợ minh bạch.1

### **7.2. Phương Thức Vận Hành Kịch Bản Thử Nghiệm**

Khi tiến hành di dời và hợp nhất mã nguồn, yêu cầu bắt buộc là không được làm hỏng chuỗi thao tác kịch bản đã được định hình tại hệ thống v2.1 Do mọi tệp mã nguồn nghiệp vụ import openai hoặc import google.generativeai đều đã bị gỡ bỏ trong nhóm lớp Dịch Vụ, đội ngũ kỹ sư sẽ kiểm nghiệm trạng thái hệ thống sử dụng các đường truyền kịch bản khói (smoke tests) điển hình.

Quá trình chạy lệnh thực thi python smoke\_tests/test\_e2e\_pipeline.py (chạy trên toàn bộ luồng pipeline) và kịch bản test\_parser.py (kịch bản chỉ dành riêng đánh giá CV) phải được tiến hành bằng việc đưa các mã API Khóa (API keys) như OPENAI\_API\_KEY, GEMINI\_API\_KEY và ANTHROPIC\_API\_KEY vào tệp .env môi trường của lõi máy chủ FANG. Thông qua SDK tích hợp, tiến trình phân tích tự động (parser) có thể tiếp cận mọi dịch vụ trung tâm thông qua các kết nối được ủy quyền (Delegation Connection), không đòi hỏi sự rườm rà. Nếu hệ thống cơ sở dữ liệu vô tình thay đổi kích thước vector do thay đổi nhà cung cấp tại cấu hình, kịch bản test\_chunking.py và test\_parser\_db.py sẽ bảo vệ hệ thống khỏi ngoại lệ sụp đổ, cung cấp một khoảng thời gian trống cho phép xử lý và dọn dẹp môi trường thử nghiệm cục bộ thông qua khối lệnh scripts/reset\_and\_seed\_db.py nhắm tới micareer\_lite\_db.

## **8\. Kết Luận Nâng Cấp Hệ Thống Toàn Diện**

Phân tích định hướng thiết kế cấu trúc mạng lưới dịch vụ thông minh (AI Services) cho nền tảng FANG FastAPI đã trình bày một lộ trình tiến hóa sâu sắc và dứt khoát. Việc loại bỏ các bộ điều hợp thủ công (manual adapter chains) phức tạp để tích hợp giải pháp uỷ quyền mạng lưới proxy cục bộ từ LiteLLM SDK tạo ra một sự thay đổi mô hình thiết kế quan trọng từ mã hóa cứng sang tiếp cận khai báo (declarative approach).1 Bằng cách di dời cấu hình, quyết định leo thang (escalation matrix), chỉ số token và chuỗi dự phòng sang một tệp "Nguồn chân lý duy nhất" models\_registry.yaml, lớp xử lý AI Core (lõi FANG) đã đạt được khả năng độc lập hệ thống toàn diện, bất khả tri về mô hình mạng và tối đa hóa khả năng vận hành.1

Những quyết định về chiến lược quản lý xử lý lỗi dựa trên mạng phân tầng đa cấp (6-Tier parser & Fallback strategy) giữ vai trò như một màng lọc tối ưu, hạn chế hiện tượng tràn lưu lượng tài chính (Cost Spillover), sử dụng các mô hình cấp thấp làm đệm trước khi điều động tài nguyên Pro Tiers phức tạp.1 Song song với đó, nguyên lý đảm bảo không can thiệp cơ sở dữ liệu của hạ tầng đang chạy, vốn được phê chuẩn ở giai đoạn trước, được bảo vệ thành công bởi các thuật toán nhồi số không và cắt cụt toán học tensor tại bước nhúng (Embedding zero-padding), biến nhược điểm giới hạn lưu trữ dữ liệu halfvec trở thành một chốt chặn chống gián đoạn ổn định.1 Nhìn chung, kết cấu kiến trúc đề xuất giải quyết bài toán giảm thiểu nợ kỹ thuật (Technical Debt Reduction) triệt để và đặt nền tảng sẵn sàng cho sự thay đổi mạnh mẽ của các thế hệ LLM và hệ thống nhúng trong tương lai mà không ảnh hưởng tới trải nghiệm người dùng cuối ở nhánh Thin Client.

**NOTE FROM HƯNG**: Đã đọc, không thay đổi gì thêm -  10/05/2026

#### **Nguồn trích dẫn**

1. embedding\_strategy.md
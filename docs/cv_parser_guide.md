# Hướng dẫn Module xử lý CV (`cv_parser.py`)

Tài liệu này giải thích chi tiết về cách hoạt động của module `app/services/cv_parser.py`, "trái tim" của giai đoạn 1 trong dự án FANG. Module này chịu trách nhiệm nhận một file CV dạng PDF và biến nó thành dữ liệu có cấu trúc (JSON) bằng cách sử dụng Gemini API.

## 1. Luồng hoạt động (Workflow)

Quá trình xử lý CV được thực hiện hoàn toàn tự động và có cơ chế dự phòng để tăng độ tin cậy. Dưới đây là các bước chi tiết:

1.  **Tiếp nhận file
    :** Hàm `parse_to_raw_and_json` nhận đầu vào là `cv_bytes` (nội dung của file PDF).
2.  **Thử nghiệm với Tier 1:**
    *   Hệ thống bắt đầu lần xử lý đầu tiên bằng cách gọi hàm `_parse_cv_with_gemini` với model `gemini-3.1-flash` (được định nghĩa là `TIER_1_MODEL`).
    *   **Tải file lên Gemini:** Nội dung `cv_bytes` được tải lên Gemini Files API. Thao tác này trả về một định danh file tạm thời.
    *   **Gửi yêu cầu xử lý:** Hệ thống gửi một yêu cầu đến Gemini, bao gồm:
        *   **Prompt:** Một chuỗi chỉ dẫn rõ ràng (`CV_PARSE_PROMPT`).
        *   **File:** Định danh file đã tải lên.
        *   **Schema:** Cấu trúc JSON mong muốn, được định nghĩa bởi Pydantic model `ParsedCV`.
    *   **Nhận và xác thực kết quả:**
        *   Gemini xử lý file PDF dựa trên prompt và trả về một đối tượng JSON.
        *   Hệ thống sử dụng `ParsedCV.model_validate` để xác thực và ép kiểu dữ liệu nhận được. Nếu dữ liệu không tuân thủ schema, một lỗi sẽ được nêu ra.
    *   **Dọn dẹp:** Dù thành công hay thất bại, file tạm đã tải lên Gemini Files API sẽ bị xóa để tránh lãng phí tài nguyên.
3.  **Dự phòng với Tier 2 (Fallback):**
    *   Nếu quá trình Tier 1 gặp bất kỳ lỗi nào (lỗi mạng, API, không phân tích được CV,...) , hệ thống sẽ tự động bắt lỗi, ghi log, và thực hiện lại toàn bộ quy trình từ Bước 2 với model `gemini-3.1-pro` (`TIER_2_MODEL`).
4.  **Trả về kết quả hoặc Báo lỗi:**
    *   Nếu một trong hai Tier thành công, hàm sẽ trả về `rawText` (văn bản thô) và một dictionary của `ParsedCV`.
    *   Nếu cả hai Tier đều thất bại, một ngoại lệ `CVParsingError` sẽ được nêu ra, chứa thông tin lỗi từ cả hai lần thử.

## 2. Chiến lược Prompt (`CV_PARSE_PROMPT`)

Prompt là yếu tố quyết định chất lượng của kết quả trả về. Prompt của FANG được thiết kế để:

*   **Rõ ràng và có quy tắc:** Cung cấp một loạt các quy tắc ngắn gọn, dễ hiểu cho AI.
*   **Bám sát sự thật:** Yêu cầu AI chỉ sử dụng thông tin có trong CV, không tự ý suy diễn (`Do not invent values`).
*   **Định dạng hóa dữ liệu:** Yêu cầu chuẩn hóa ngày tháng về định dạng `YYYY-MM` và sử dụng `present` cho các công việc/học vấn hiện tại.
*   **Yêu cầu JSON:** Ra lệnh cho AI trả về kết quả dưới dạng JSON theo schema đã cung cấp.

```python
CV_PARSE_PROMPT = """
Extract the candidate's CV from the uploaded PDF into the provided JSON schema.

Rules:
- Use only information explicitly present in the PDF.
- Do not invent values. Use null for unknown scalar fields and [] for unknown lists.
- Normalize startDate and endDate to YYYY-MM whenever a month is available.
- Use "present" only when the CV clearly indicates an ongoing role or education entry.
- Keep summary concise and factual.
- Put the CV's plain extracted text into rawText.
- Return only the structured data required by the schema.
""".strip()
```

## 3. Xử lý và Xác thực Schema (`ParsedCV`)

Đây là một trong những tính năng mạnh mẽ nhất của Gemini API kết hợp với Pydantic.

*   **Schema Enforcement:** Thay vì chỉ nhận text và tự parse, chúng ta khai báo `response_schema=ParsedCV` khi gọi API. Gemini sẽ cố gắng hết sức để trả về một JSON tuân thủ 100% cấu trúc của lớp `ParsedCV`.
*   **Data Validation:** Ngay cả khi Gemini trả về đúng cấu trúc, chúng ta vẫn cẩn thận validate lại dữ liệu bằng `ParsedCV.model_validate_json(response.text)`. Điều này đảm bảo tính toàn vẹn của dữ liệu trước khi lưu vào database, đặc biệt là các quy tắc như `pattern` của `CVDate`.
*   **An toàn:** Việc này giúp loại bỏ rất nhiều code xử lý chuỗi và kiểm tra lỗi phức tạp, làm cho module trở nên gọn gàng và dễ bảo trì hơn.

## 4. Cơ chế xử lý lỗi và Model Resolution

*   **`CVParsingError`:** Một exception tùy chỉnh được tạo ra để đóng gói lỗi, giúp việc bắt lỗi ở tầng service cao hơn trở nên tường minh.
*   **Model Resolution & Caching:**
    *   Hàm `_resolve_model_name` cho phép sử dụng một tên model "ảo" (như `gemini-3.1-flash`).
    *   Nó sẽ tìm trong danh sách các model thực tế (`MODEL_CANDIDATES`) xem model nào đang có sẵn trên hệ thống của Google và chọn model phù hợp nhất.
    *   Kết quả sẽ được cache lại trong `_MODEL_RESOLUTION_CACHE` để các lần gọi sau không cần thực hiện lại việc tra cứu này.

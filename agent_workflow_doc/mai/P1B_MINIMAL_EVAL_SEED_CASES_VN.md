# Bộ dữ liệu đánh giá tối thiểu (Seed Cases) cho các Prompt P1 – P8

Tài liệu này mô tả tập dữ liệu kiểm thử tối thiểu được sử dụng để đánh giá chất lượng của các prompt trong hệ thống. Mỗi trường hợp kiểm thử (test case) bao gồm:

- Dữ liệu đầu vào.
- Ngữ cảnh được cung cấp cho mô hình (nếu có).
- Kết quả mong đợi.
- Tiêu chí đánh giá đạt/không đạt.

Các trường hợp kiểm thử được xây dựng nhằm mô phỏng môi trường vận hành thực tế, bao gồm các dữ liệu được chèn động trong quá trình thực thi như danh mục kỹ năng, danh sách tỉnh thành hoặc cấu trúc JSON Schema.

## Mẫu test case (Template)

Hướng dẫn ngắn: ghi phần mô tả **bằng tiếng Việt** (dữ liệu đầu vào, ngữ cảnh, kết quả mong đợi) rồi thêm khối JSON machine-readable ngay phía dưới. Biến/khóa trong JSON phải trùng với tên trường trong code (ví dụ `rawText`, `parserSelfReport`, `expectedSalaryMin`).

Ví dụ template (sao chép và chỉnh sửa cho mỗi test case):

```json
{
  "id": "P1-<n>",
  "prompt_id": "P1",
  "input_text": "<Toàn bộ text đầu vào - ghi bằng tiếng Việt hoặc bản gốc>",
  "injected_data": { /* danh mục hoặc schema nếu cần */ },
  "expected": {
    "rawText": "<nguyên văn hoặc chuẩn hóa nếu cần>",
    "work": [ { "company": "<tên>", "startDate": "YYYY-MM", "endDate": "YYYY-MM|present" } ],
    "languages": [ { "language": "<tên>", "proficiency": "<N1|N2|N3|...|null>" } ],
    "expectedSalaryMin": <số hoặc null>,
    "expectedSalaryMax": <số hoặc null>,
    "parserSelfReport": { "confidence": <số|null>, "issues": [], "uncertainFields": [] }
  }
}
```

Gợi ý: có thể thêm trường `assertions` (mảng) để mô tả các kiểm tra tự động, ví dụ: `{ "assertions": [ { "type": "has_field", "path": "work[0].startDate" } ] }`.

---

# P1 – Kiểm thử Prompt Phân tích CV
**Nguồn:** `app/services/cv_parser_adapters.py`

## Trường hợp P1-1: CV đầy đủ thông tin

### Dữ liệu đầu vào
CV chứa các thông tin:

- Họ tên: Nguyễn Văn A.
- Kinh nghiệm làm việc từ tháng 06/2020 đến tháng 08/2022.
- Ngoại ngữ: Tiếng Nhật trình độ N3.
- Mức lương mong đợi: 25 triệu đồng.

### Kết quả mong đợi

- Toàn bộ nội dung CV được lưu trong trường `rawText`.
- Thời gian làm việc được chuẩn hóa theo định dạng `YYYY-MM`.
- Thông tin ngoại ngữ được giữ nguyên:

```
{
  "language": "Japanese",
  "proficiency": "N3"
}
```

- Mức lương được chuẩn hóa thành:

```
{
  "expectedSalaryMin": 25000000,
  "expectedSalaryMax": 25000000
}
```

- Có trường `parserSelfReport` bao gồm:confidence
- issues
- uncertainFields



### Tiêu chí đạt

- JSON hợp lệ.
- Lương được chuẩn hóa chính xác.
- Trình độ ngoại ngữ không bị thay đổi.
- Thời gian được chuẩn hóa đúng định dạng.

```json
{
  "id": "P1-1",
  "prompt_id": "P1",
  "input_text": "Họ tên: Nguyen Van A\nKinh nghiệm: 06/2020 - 08/2022 tại Acme Corp\nNgoại ngữ: Japanese N3\nMức lương mong đợi: 25 triệu VND\n",
  "injected_data": {},
  "expected": {
    "rawText": "Họ tên: Nguyen Van A\nKinh nghiệm: 06/2020 - 08/2022 tại Acme Corp\nNgoại ngữ: Japanese N3\nMức lương mong đợi: 25 triệu VND\n",
    "work": [{ "company": "Acme Corp", "startDate": "2020-06", "endDate": "2022-08" }],
    "languages": [{ "language": "Japanese", "proficiency": "N3" }],
    "expectedSalaryMin": 25000000,
    "expectedSalaryMax": 25000000,
    "parserSelfReport": { "confidence": null, "issues": [], "uncertainFields": [] }
  }
}
```

---

## Trường hợp P1-2: CV thiếu thông tin

### Dữ liệu đầu vào
CV chỉ chứa:

- Họ tên.
- Một kinh nghiệm làm việc.
- Ngoại ngữ: English.
- Không có thông tin lương.

### Kết quả mong đợi

- `expectedSalaryMin` và `expectedSalaryMax` có giá trị `null`.
- Ngoại ngữ được biểu diễn dưới dạng:

```
{
  "language": "English",
  "proficiency": null
}
```

- Trường `uncertainFields` ghi nhận các thông tin còn thiếu

### Tiêu chí đạt

- Các giá trị thiếu được biểu diễn bằng `null` hoặc danh sách rỗng.
- Báo cáo tự đánh giá (`parserSelfReport`) được sinh đầy đủ.

```json
{
  "id": "P1-2",
  "prompt_id": "P1",
  "input_text": "Name: Le Thi B\nWork: 2018-01 to 2019-12 at Small Co.\nLanguages: English\n",
  "injected_data": {},
  "expected": {
    "expectedSalaryMin": null,
    "expectedSalaryMax": null,
    "languages": [{ "language": "English", "proficiency": null }],
    "parserSelfReport": { "uncertainFields": ["expectedSalary"] }
  }
}
```

---

## Trường hợp P1-3: Định dạng thời gian không rõ ràng

### Dữ liệu đầu vào
Khoảng thời gian làm việc:

```
2019 - Present
```

### Kết quả mong đợi

- Nếu công việc vẫn đang tiếp diễn, `endDate` được gán là `"present"`.
- Nếu không thể chuẩn hóa chính xác, hệ thống phải ghi nhận vào danh sách cảnh báo hoặc trường không chắc chắn.

### Tiêu chí đạt

- Xử lý chính xác từ khóa "Present".
- Hoặc ghi nhận rõ ràng sự không chắc chắn trong kết quả.

```json
{
  "id": "P1-3",
  "prompt_id": "P1",
  "input_text": "Name: Tran C\nWork: 2019 - Present at Startup XYZ\n",
  "injected_data": {},
  "expected": {
    "work": [{ "startDate": "2019", "endDate": "present" }],
    "parserSelfReport": { "issues": ["ambiguous_end_date"] }
  }
}
```

---

# P2 – Kiểm thử Prompt Ràng buộc JSON Schema
**Nguồn:** `app/services/cv_parser_adapters.py`

## Trường hợp P2-1: Kết quả đúng Schema

### Kết quả mong đợi

- Mô hình trả về JSON đúng theo Schema được quy định.
- Dữ liệu vượt qua bước xác thực Schema.

### Tiêu chí đạt

- Không có lỗi định dạng.
- Không xuất hiện trường ngoài Schema.

```json
{
  "id": "P2-1",
  "prompt_id": "P2",
  "injected_data": { "schema": "path/to/parsed_cv_schema.json" },
  "input_text": "<same as P1-1>",
  "expected": { "schema_validate": true }
}
```

---

## Trường hợp P2-2: Mô hình trả về dữ liệu sai định dạng

### Kết quả mong đợi

- Hệ thống phát hiện lỗi.
- Ghi log phục vụ kiểm tra.
- Kích hoạt cơ chế xử lý lỗi phù hợp.

### Tiêu chí đạt

- Lỗi được phát hiện và ghi nhận đầy đủ.

```json
{
  "id": "P2-2",
  "prompt_id": "P2",
  "injected_data": { "schema": "path/to/parsed_cv_schema.json" },
  "input_text": "<malformed output simulation>",
  "expected": { "parseable": false }
}
```

---

# P3 – Kiểm thử Prompt HR Co-pilot
**Nguồn:** `app/services/rag_query.py`

## Trường hợp P3-1: Có đủ thông tin ứng viên

### Ngữ cảnh
Thông tin công việc:

- Vị trí: Software Engineer.
- Yêu cầu: Backend, Python.

Thông tin ứng viên:

- Họ tên: Trần B.
- Kinh nghiệm: 3 năm.
- Mô tả: Backend Developer.

Dữ liệu tham chiếu:

- Có 3 năm kinh nghiệm với Django và PostgreSQL.

### Câu hỏi

```
Ứng viên có phù hợp không?
```

### Kết quả mong đợi

- Đưa ra đánh giá ngắn gọn.
- Nêu rõ đánh giá dựa trên dữ liệu được cung cấp.
- Liệt kê các thông tin còn thiếu nếu có.

### Tiêu chí đạt

- Không suy diễn ngoài dữ liệu.
- Có cấu trúc rõ ràng bằng tiêu đề hoặc danh sách.

```json
{
  "id": "P3-1",
  "prompt_id": "P3",
  "injected_data": {
    "job": {"title":"Software Engineer","description":"Backend, Python"},
    "candidate": {"fullname":"Tran B","expyears":3,"bio":"Backend developer"},
    "chunks": ["Has 3 years experience in Django and Postgres."]
  },
  "user_question": "Ứng viên có phù hợp không?",
  "expected": { "must_contain": "Dựa trên thông tin được cung cấp" }
}
```

---

## Trường hợp P3-2: Thiếu dữ liệu

### Ngữ cảnh
Chỉ có tên vị trí tuyển dụng.

### Câu hỏi

```
Cho đánh giá nhanh.
```

### Kết quả mong đợi

- Mô hình phải thông báo thiếu dữ liệu.
- Liệt kê các thông tin cần bổ sung.

### Tiêu chí đạt

- Không tự tạo thông tin về ứng viên.

```json
{
  "id": "P3-2",
  "prompt_id": "P3",
  "injected_data": { "job": { "title": "Software Engineer" } },
  "user_question": "Cho đánh giá nhanh.",
  "expected": { "must_list_missing_items": true }
}
```

---

# P6 – Kiểm thử Ánh xạ Địa chỉ sang Mã tỉnh
**Nguồn:** `app/services/nmaiex_mapper_service.py`

Danh sách tỉnh sử dụng trong kiểm thử:

- HAIPHONG: Hai Phong
- TPHCM: Ho Chi Minh City
- HANOI: Ha Noi
## Trường hợp P6-1: Khớp chính xác

### Đầu vào
```
Thành phố Hải Phòng
```

### Kết quả mong đợi
```
HAIPHONG
```

### Tiêu chí đạt
- Chỉ trả về duy nhất một mã tỉnh.
- Không có nội dung bổ sung.

```json
{
  "id": "P6-1",
  "prompt_id": "P6",
  "injected_data": { "province_catalog": { "HAIPHONG": "Hai Phong", "TPHCM": "Ho Chi Minh City", "HANOI": "Ha Noi" } },
  "input_text": "Thành phố Hải Phòng",
  "expected": { "output": "HAIPHONG" }
}
```

---

## Trường hợp P6-2: Tên địa phương cũ

### Đầu vào
```
Bình Dương
```

### Kết quả mong đợi
- Trả về mã tỉnh mới tương ứng theo quy tắc ánh xạ.
- Hoặc `UNKNOWN` nếu không xác định được.

### Tiêu chí đạt
- Kết quả đúng với quy tắc ánh xạ đã cung cấp.

```json
{
  "id": "P6-2",
  "prompt_id": "P6",
  "injected_data": { "province_catalog": { "HAIPHONG": "Hai Phong", "TPHCM": "Ho Chi Minh City", "HANOI": "Ha Noi" }, "mappings": { "Binh Duong": "TPHCM" } },
  "input_text": "Bình Dương",
  "expected": { "output": "TPHCM" }
}
```

---

## Trường hợp P6-3: Không xác định được

### Đầu vào
```
Trung tâm đô thị XYZ
```

### Kết quả mong đợi
```
UNKNOWN
```

```json
{
  "id": "P6-3",
  "prompt_id": "P6",
  "input_text": "Trung tâm đô thị XYZ",
  "expected": { "output": "UNKNOWN" }
}
```

---

# P7 – Kiểm thử Ánh xạ Kỹ năng
**Nguồn:** `app/services/nmaiex_mapper_service.py`

Danh mục kỹ năng:

- 101: Python
- 102: SQL
- 103: Django
## Trường hợp P7-1: Có kỹ năng khớp và không khớp

### Đầu vào
```
[
  "Python",
  "Excel Advanced",
  "Django Rest Framework"
]
```

### Kết quả mong đợi
```
{
  "matched_ids": [101],
  "unmatched_texts": [
    "Excel Advanced",
    "Django Rest Framework"
  ]
}
```

### Tiêu chí đạt
- Chỉ trả về JSON.
- Chỉ sử dụng ID tồn tại trong danh mục.
- Giữ nguyên kỹ năng không khớp.

```json
{
  "id": "P7-1",
  "prompt_id": "P7",
  "injected_data": { "skill_catalog": { "101": "Python", "102": "SQL", "103": "Django" } },
  "input_list": ["Python", "Excel Advanced", "Django Rest Framework"],
  "expected": { "matched_ids": [101], "unmatched_texts": ["Excel Advanced", "Django Rest Framework"] }
}
```

---

## Trường hợp P7-2: JSON không hợp lệ

### Kết quả mong đợi
- Hệ thống phát hiện lỗi.
- Chuyển toàn bộ kỹ năng sang danh sách `unmatched_texts`.

### Tiêu chí đạt
- Kích hoạt đúng cơ chế xử lý lỗi.

```json
{
  "id": "P7-2",
  "prompt_id": "P7",
  "input_list": ["Python", "Excel Advanced", "Django Rest Framework"],
  "expected": { "parseable": false }
}
```

---

# P8 – Kiểm thử Chuẩn hóa Trình độ Ngoại ngữ
**Nguồn:** `app/services/nmaiex_mapper_service.py`

## Trường hợp P8-1: Trình độ JLPT

### Đầu vào
```
N3
```

### Kết quả mong đợi
```
INTERMEDIATE
```

```json
{
  "id": "P8-1",
  "prompt_id": "P8",
  "input_text": "N3",
  "expected": { "output": "INTERMEDIATE" }
}
```

---

## Trường hợp P8-2: Điểm IELTS

### Đầu vào
```
IELTS 7.5
```

### Kết quả mong đợi
```
ADVANCED
```

```json
{
  "id": "P8-2",
  "prompt_id": "P8",
  "input_text": "N4",
  "expected": { "output": "ADVANCED" }
}
```

---

## Trường hợp P8-3: Giá trị không xác định

### Đầu vào
```
xyz
```

### Kết quả mong đợi
```
BASIC
```

```json
{
  "id": "P8-3",
  "prompt_id": "P8",
  "input_text": "N2",
  "expected": { "output": "BASIC" }
}
```

---

# Ghi chú triển khai
Mỗi trường hợp kiểm thử cần bao gồm:

- Dữ liệu được chèn động trong quá trình thực thi (catalog, province list, schema...).
- Nội dung prompt hoàn chỉnh (system message và user message).
- Bộ tiêu chí kiểm tra tự động khi có thể.

Ngoài ra, cần lưu lại:

- Kết quả đầu ra.
- Thông tin confidence.
- Các cảnh báo hoặc trường dữ liệu không chắc chắn.

Những thông tin này giúp hỗ trợ quá trình đánh giá, phân tích lỗi và cải thiện chất lượng prompt trong các phiên bản tiếp theo.   

---


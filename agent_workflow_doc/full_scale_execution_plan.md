# 📋 Hướng Dẫn & Checklist Xác Nhận Trước Khi Chạy (Tick thủ công)

> [!IMPORTANT]
> **Hãy hoàn thành và đánh dấu tích `[x]` vào các mục dưới đây trước khi khởi chạy pipeline lớn:**
> - [x] **Cấu hình 9Router:** Đã cài đặt API Key trong file `.env` hoặc `synthetic_data/config.py` và xác nhận proxy `9Router` đang chạy tại cổng `20128`.
> - [x] **Kích hoạt Virtual Environment (venv):** Đã kích hoạt môi trường ảo Python thành công trong Terminal (bằng lệnh `.\venv\Scripts\activate` trên Windows).
> - [x] **Khởi động Backend Server:** FANG API Server đã được bật và đang lắng nghe ổn định tại địa chỉ `http://localhost:8000`.
> - [x] **Khởi động Frontend Server:** miCareer-mini Streamlit App đã được bật và đang chạy tại địa chỉ `http://192.168.0.101:8501`.

---

# Kế Hoạch Triển Khai Sinh Dữ Liệu Lớn (Full Scale — 500 CV + 15 Jobs)

Tài liệu này tổng hợp toàn bộ các bảng CSDL chịu tác động và cung cấp quy trình từng bước để thực hiện sinh và nạp 500 CV cùng 15-20 Tin tuyển dụng (Jobs) phục vụ huấn luyện và kiểm thử thuật toán xếp hạng NMAIex.

---

## I. Tổng Quan Các Bảng Dữ Liệu Được Ghi Nhận (CSDL)

Dưới đây là danh sách các bảng trong PostgreSQL `micareer_lite_db` chịu tác động và loại thông tin được nạp bởi pipeline:

| Tên Bảng | Loại Dữ Liệu Ghi Nhận | Các Trường Thông Tin Chính |
| :--- | :--- | :--- |
| **`"user"`** | Tài khoản ứng viên | `userId` (PK), `userName` (e.g. `candidate_batch_001_5`), `fName`, `lName` (tách từ tên Việt Nam do AI sinh), `email` (synth-unique), `phone` (synth-unique), `provId` (34 tỉnh chuẩn), `role = 'CANDIDATE'`. |
| **`CANDIDATE`** | Hồ sơ năng lực ứng viên | `userId` (FK), `bio` (Tóm tắt bản thân lấy từ `summary` của ParsedCV), `cvUrl` (URI giả lập của file CV), `expyears` (Số năm kinh nghiệm theo Persona). |
| **`JOBAPPLICATION`** | Hồ sơ ứng tuyển (Khóa ngoại) | `jobAppId` (PK), `candidateId` (FK), `jobPostId` (FK - trỏ tới Job đầu tiên làm placeholder), `stat = 'PENDING'`, `cvSnapUrl`. |
| **`CVPARSED`** | Kết quả phân tích CV | `cvParsedId` (PK), `jobAppId` (FK), `rawText` (Văn bản CV thô), `parsedJson` (JSON cấu trúc ParsedCV chuẩn), `parserVer = 'synth-pipeline-v1'`. |
| **`AIDOCUMENTCHUNK`** | Phân mảnh văn bản + Vector | `chunkId` (PK), `jobAppId` (FK đa hình), `sourceType` (`'CV'` hoặc `'JOB'`), `content` (Đã tiêm bối cảnh Section-Pinning giàu thông tin), `chunkIndex`, `tokenCount`, `metadata` (Gộp trường gốc FANG & Pipeline), `embedding` (Vector 1536 chiều, kiểu `halfvec`). |
| **`JOBPOSTING`** | Tin tuyển dụng | `jobPostId` (PK), `compId` (FK đến 15 công ty hạ tầng), `title` (Tiêu đề job), `description` (Mô tả chi tiết), `minSalary`, `maxSalary`, `workMode` (`ONSITE`/`HYBRID`/`REMOTE`), `provId` (34 tỉnh). |
| **`JOB_LEVEL_MAP`** | Cấp bậc yêu cầu | `jobPostId` (FK), `levelId` (FK cấp bậc: Intern, Fresher, Junior, Middle, Senior, Lead...). |
| **`JOB_CATEGORY_MAP`** | Ngành nghề yêu cầu | `jobPostId` (FK), `catId` (FK danh mục công việc: Backend, Frontend, DevOps...). |
| **`JOBREQUIREMENT`** | Kỹ năng Catalog (Tầng 1) | `jobPostId` (FK), `skillId` (FK kỹ năng khớp chuẩn với hệ thống). |
| **`JOB_SKILL_RAW`** | Kỹ năng Tự do (Tầng 2) | `jobSkillRawId` (PK), `jobPostId` (FK), `skillName` (Tên kỹ năng tự do), `embedding` (Vector nhúng 256 chiều phục vụ so khớp fuzzy). |
| **`JOB_LANG_REQUIREMENT`** | Yêu cầu ngoại ngữ | `jobPostId` (FK), `langId` (FK), `reqType` (`REQUIRED`/`PREFERRED`), `minLevel` (`BASIC`/`INTERMEDIATE`...). |

---

## II. Quy Trình Chạy Sinh Dữ Liệu Full Scale (500 CVs + 15+ Jobs)

Quy trình nạp dữ liệu lớn được thiết kế để **tiết kiệm tối đa API Key (resume-able)** nhờ cơ chế cache tệp phẳng tại `synthetic_data/output/`.

> [!IMPORTANT]
> **Khởi động 9Router trước khi chạy:** Đảm bảo proxy 9Router đã được khởi động ở cổng `20128` (hoặc cổng cấu hình) trước khi chạy lệnh sinh dữ liệu.

### Bước 1: Reset CSDL về trạng thái sạch sẽ
Lệnh này xóa sạch các bảng và nạp lại 15 công ty cùng 15 HR đại diện:
```bash
.\venv\Scripts\python.exe scripts/reset_and_seed_db.py --reset
```

### Bước 2: Sinh dữ liệu thô (LLM Generation)

1. **Sinh 15-20 công việc (Jobs) mẫu:**
   ```bash
   .\venv\Scripts\python.exe -m synthetic_data.run_pipeline generate-jobs
   ```
   * *Đầu ra:* Các file lưu tại `synthetic_data/output/jobs/`.

2. **Sinh 500 CV theo 8 Persona (Batched):**
   ```bash
   .\venv\Scripts\python.exe -m synthetic_data.run_pipeline generate-cvs --total 500
   ```
   * Lệnh này sẽ gọi Gemini qua 9Router theo batch (5 CV/batch).
   * Nếu bị lỗi mạng hoặc dừng giữa chừng, chỉ cần chạy lại lệnh trên, pipeline sẽ tự động **nhận diện các batch đã sinh trong thư mục cache và chạy tiếp** mà không sinh lại từ đầu.

### Bước 3: Nạp dữ liệu vào DB & Tính toán Vector (DB Writing & Ingestion)

1. **Ghi nhận Jobs vào CSDL trước:**
   ```bash
   .\venv\Scripts\python.exe -m synthetic_data.run_pipeline write-jobs
   ```
   * Tự động tạo bản ghi `JOBPOSTING`, map `level`, `category`, ngôn ngữ, gọi nhúng **kỹ năng raw (256 chiều)** và nhúng **JD chunks (1536 chiều)**.

2. **Ghi nhận 500 CV vào CSDL:**
   ```bash
   .\venv\Scripts\python.exe -m synthetic_data.run_pipeline write-cvs --total 500
   ```
   * Khởi tạo tài khoản Candidate, tạo hồ sơ ứng tuyển, lưu JSON parsed.
   * Thực hiện chunking Markdown, tiêm bối cảnh Section-Pinning và nhúng **CV chunks (1536 chiều)** qua 9Router.
   * *Thời gian ước tính:* Khoảng 8 - 10 phút cho 500 CV.

---

## III. Xác Minh & Giám Sát Sau Khi Nạp

Sau khi tiến trình nạp hoàn thành, chạy script xác thực để kiểm tra tính nhất quán:

```bash
.\venv\Scripts\python.exe synthetic_data/verifier.py
```

### Tiêu chí thành công (Success Criteria):
1. **Counts:**
   * Bảng `CANDIDATE`: ~500 bản ghi.
   * Bảng `JOBPOSTING`: ~15-20 bản ghi.
   * Bảng `AIDOCUMENTCHUNK` (sourceType='CV'): >1500 chunks.
   * Bảng `AIDOCUMENTCHUNK` (sourceType='JOB'): >50 chunks.
2. **Dimensions:**
   * CV & JOB chunk embedding dimensions: **1536** (Gemini native).
3. **API Smoke Tests:**
   * J→C ranking API hoạt động bình thường, trả về danh sách ứng viên kèm `score_breakdown` chuẩn.
   * C→J ranking API hoạt động bình thường, trả về danh sách công việc phù hợp với điểm số trong khoảng `[0.0, 1.0]`.

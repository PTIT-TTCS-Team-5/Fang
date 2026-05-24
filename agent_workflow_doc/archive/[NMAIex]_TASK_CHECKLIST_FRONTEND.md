# [NMAIex] Checklist Frontend (miCareer-mini)

Tài liệu checklist thực thi cho Frontend. AI Agent tick `[x]` khi hoàn thành, `[/]` khi đang làm.
Tham chiếu: `[NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md`

---

## Phase 1: Chuẩn Hóa Input Components (Master Data Dropdown)

Chuyển các ô nhập text tự do sang Dropdown gọi API `/v2/nmaiex/master/*`.

- [ ] **LocationSelector**: Thay thế text input địa điểm bằng Dropdown 2 cấp (Region → Province). Gọi `GET /v2/nmaiex/master/provinces`, group theo `regId`.
- [ ] **SkillSelector**: Chuyển sang Multi-select Dropdown. Gọi `GET /v2/nmaiex/master/skills`. Hỗ trợ tìm kiếm (filter) trong dropdown.
  - *Lưu ý: Component này dùng cho cả Candidate search và HR Job form. Phía Candidate: dropdown only. Phía HR Job form: kèm thêm text-free input (xem Phase 1.5).*

- [ ] **LevelSelector**: Dropdown đơn. Gọi `GET /v2/nmaiex/master/levels`.
- [ ] **CategorySelector**: Dropdown Multi-select (một Job có thể thuộc nhiều Category). Gọi `GET /v2/nmaiex/master/categories`.
- [ ] Áp dụng các component trên cho form **Đăng Job** (HR) và form **Tìm kiếm** (Candidate).

---

## Phase 1.5: Trang Quản Lý Job (HR) — Mới

> **Bối cảnh [2026-04-29]:** Frontend hiện tại không có trang quản lý Job cho HR. Cần bổ sung để hỗ trợ NMAIex ranking (HR cần gắn provId, levelId, catId, skillId chuẩn cho từng Job Posting). Việc HR sửa Job có cascade impact nên UI phải phân biệt rõ 2 loại thay đổi.

- [ ] **Trang `HR / Job Management`** — Danh sách Job Postings của HR:
  - Hiển thị list job với tình trạng (active/closed) và nút action (Edit / View Ranking).

- [ ] **Form tạo / sửa Job** — Sử dụng các component chuẩn hóa:
  - `LocationSelector` (provId), `LevelSelector` (levelIds), `CategorySelector` (catIds).
  - Field salary: `minSalary`, `maxSalary` (number input).
  - **Skill Input — Hybrid:**
    - **Dropdown** (`SkillSelector`): chọn skill có sẵn trong catalog.
    - **Text-free Tag Input**: HR gõ skill tùy ý + Enter → hiện thị chip màu khác (phân biệt catalog chip vs. custom chip). Backend sẽ chạy LLM mapper khi save: match → `JOBREQUIREMENT`; unmatched → embed → `JOB_SKILL_RAW`.
  - **Tách biệt 2 nút Save** để phân loại cascade impact:
    - **"Lưu Nội dung"** (`PATCH /v2/nmaiex/jobs/{id}/content`): Gửi `title` + `description`. Backend trigger async re-ingest → re-embed vector chunks. Thông báo: *"Nội dung đang được cập nhật, ranking có thể chưa chính xác trong vài phút."*
    - **"Lưu Cài đặt"** (`PATCH /v2/nmaiex/jobs/{id}/structured`): Gửi skills (cả catalog IDs + custom texts), province, levels, categories, salary. Backend xử lý ngay (không re-embed). Tức thì.

- [ ] Sau khi tạo xong form, **liên kết** với nút "AI Ranking" trong Phase 3.




*Lưu ý: `cvUrl` và `cvSnapUrl` đã có sẵn trong DB FANG. Cần xây dựng UI để quản lý.*

- [ ] Thêm section **"Hồ sơ của tôi"** trong trang Profile ứng viên:
  - Hiển thị `bio` (text) + nút Edit.
  - Hiển thị CV hiện tại (`cvUrl`) + nút Upload CV mới.
  - Upload CV: Gửi lên Cloud Storage (Cloudinary/Supabase theo `NMAIEX_CLOUD_STORAGE_PROVIDER`), nhận URL, lưu vào `CANDIDATE.cvUrl` qua API PATCH.

- [ ] Cập nhật luồng **Apply Job**:
  - Khi ứng viên nhấn Apply → Hiện modal: **"Dùng CV hiện tại"** hoặc **"Upload CV mới cho đơn này"**.
  - Lựa chọn 1 (CV hiện tại): Tạo snapshot từ `cvUrl`, lưu vào `JOBAPPLICATION.cvSnapUrl`.
  - Lựa chọn 2 (Upload mới): Upload file → Cloud Storage → URL mới → lưu vào `cvSnapUrl`.
  - Sau khi apply: Trigger FANG Ingestion API cho `cvSnapUrl` này.

---

## Phase 3: Tích Hợp API Ranking

- [ ] Tạo service `nmaiexRankingService.js` (hoặc `.ts`):
  - `getCandidatesForJob(jobId, params)` → `GET /v2/nmaiex/ranking/candidates/{jobId}`
  - `getJobsForCandidate(candidateId, params)` → `GET /v2/nmaiex/ranking/jobs/{candidateId}`

- [ ] **Màn hình HR - Danh sách Ứng viên** (cho 1 Job Posting):
  - Thêm nút / tab **"AI Ranking"** bên cạnh danh sách ứng viên thông thường.
  - Khi bấm: Gọi `getCandidatesForJob`, hiển thị danh sách xếp hạng với `match_score` (%).
  - Filter: Dropdown `province_id`, `work_mode`, input `limit`.
  - Giữ thiết kế đơn giản (card list, không cần biểu đồ).

- [ ] **Màn hình Candidate - Gợi ý Công việc**:
  - Thêm section **"Việc làm phù hợp với bạn"** trên trang Home hoặc Job Search.
  - Gọi `getJobsForCandidate`, hiển thị top 10-20 job cards có `match_score`.
  - Filter: `work_mode`, `province_id`.

- [ ] **Dev Mode Score Badge**: Trên mỗi card kết quả ranking, hiển thị badge nhỏ `[Score: 87%]` và tooltip chi tiết `score_breakdown` (rrf, skill_overlap, penalties). Chỉ hiển thị khi có env flag `VITE_DEV_MODE=true` (hoặc tương đương).

---

## Phase 4: Kiểm Thử Thủ Công

- [ ] Mở màn hình HR, chọn Job **"Backend Developer (Java/Spring Boot)"**, chạy AI Ranking.
  - Xác nhận ứng viên **Nguyễn Văn An** (Java, Spring Boot, 3 năm) xuất hiện top 1-3.
  - Xác nhận ứng viên **Vũ Thị Phương** (0 năm KN, intern) có `seniority_penalty` và bị hạng thấp.
- [ ] Mở màn hình Candidate (login Nguyễn Văn An), xem gợi ý Công việc.
  - Các job Backend nên xuất hiện đầu tiên.
- [ ] Kiểm tra Hard Filter: Chọn Province = `DANANG`, xác nhận không có job nào tại Hà Nội xuất hiện.

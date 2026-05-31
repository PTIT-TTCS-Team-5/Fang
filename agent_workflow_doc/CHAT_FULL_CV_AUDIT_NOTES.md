# CHAT_FULL_CV — Phase 0 Audit Notes

Ngày: 2026-05-29
Owner: CHAT_FULL_CV
Trạng thái: Phase 0.2 done — chuẩn bị vào Phase 1.

> Notes file private (không phải deliverable cho user). Mục đích: khoá ground truth từ code/schema/UI hiện tại để các phase sau không suy đoán.

---

## 0.1 — Decision constraints (Open Questions defaults)

Áp dụng các default đã đề xuất (lead Hưng để mình tự quyết):

| # | Câu hỏi | Quyết định | Lý do ngắn |
|---|---|---|---|
| 1 | `topK` trả về | **`0`** | Phản ánh đúng behavior. Cần update miCareer-mini wording (xem 0.2.6). |
| 2 | EmailLog | **Recent 5 emails, body truncate 300 chars, marker untrusted** | Cân bằng evidence vs budget; tránh prompt injection. |
| 3 | Over hard budget | **Deterministic warning + gợi ý summarize/branch** | Đã có flow `/summarize` & `/branch-new`. Auto-compact để phase sau. |
| 4 | PII masking | **Không mask** | HR workflow nội bộ, đã có quyền hợp pháp. |
| 5 | Offer history | **3 versions gần nhất theo `subAt DESC`** | Đủ để theo dõi negotiation; giới hạn budget. |

Mọi câu trong các phase sau phải reference quyết định ở đây hoặc một dòng audit cụ thể bên dưới.

---

## 0.2 — Audit findings

### 0.2.1 `ParsedCV` schema (`app/models/cv_models.py:97-141`)

Field tồn tại thực tế (sau khi đọc code):

| Field | Type | Required | Ghi chú |
|---|---|---|---|
| `candidateInfo` | `list[CandidateInfo]` | Optional (default `[]`) | Một số CV có thể >1 entry; `markdown_builder._get_primary_candidate()` chỉ lấy phần tử [0] |
| `education` | `list[Education]` | Optional | |
| `experience` | `list[Experience]` | Optional | startDate/endDate format `YYYY-MM` hoặc `"present"` |
| `skills` | `list[str]` | Optional | |
| `certificates` | `list[str]` | Optional | |
| `languages` | `list[LanguageEntry]` | Optional | **Breaking change Phase 2.5f**: trước là `list[str]`, giờ `{language, proficiency}`. **Legacy parsedJson dạng `list[str]` sẽ FAIL validate**. |
| `summary` | `str` | default `""` | |
| `rawText` | `str` | **REQUIRED, min_length=1** | Không validate được parsedJson nếu thiếu `rawText` ngay cả khi muốn dùng parsedJson. |
| `parserVer` | `str \| None` | Optional | |
| `expectedSalaryMin/Max` | `int \| None` | Optional | Có thể dùng làm context bổ sung. |
| `parserSelfReport` | `ParserSelfReport \| None` | Optional | confidence, issues, uncertainFields. Có thể dùng làm tín hiệu để cảnh báo HR. |

**`CandidateInfo`**: `fullName`, `emails: list[str]`, `phones: list[str]`, `location` — đều optional.

**`Experience`**: `company`, `title`, `startDate`, `endDate`, `description` — đều optional.

**`Education`**: `school`, `degree`, `startDate`, `endDate` — đều optional.

**`LanguageEntry`**: `language` REQUIRED, `proficiency` optional (raw string như "N3", "Fluent", "B2").

**Hệ quả cho fallback ladder**:
- `ParsedCV.model_validate(parsedJson)` cần `rawText` (min_length=1). Nếu DB cũ có `parsedJson` không chứa `rawText` (vì rawText tách bảng), phải inject `rawText` từ row `CVPARSED.rawText` trước khi validate.
- Legacy CV với `languages: list[str]` → FAIL → trigger fallback rawText.
- `convert_json_to_markdown(parsed_cv)` trong `app/services/markdown_builder.py:35` đã handle thiếu field, output có thể là markdown rỗng nếu mọi field rỗng → cần check empty trước khi dùng.

### 0.2.2 `EMAILLOG` schema (`database/schema_web_core.sql`)

```sql
CREATE TABLE EMAILLOG (
  logId    SERIAL PRIMARY KEY,
  tmplId   INT NOT NULL,
  jobAppId INT NOT NULL,
  hrId     INT NOT NULL,
  "content" TEXT NOT NULL,
  sentAt   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  rcvEmail VARCHAR(255) NOT NULL,
  FOREIGN KEY (tmplId)   REFERENCES EMAILTEMPLATE(tmplId),
  FOREIGN KEY (jobAppId) REFERENCES JOBAPPLICATION(jobAppId),
  FOREIGN KEY (hrId)     REFERENCES HR(userId)
);
```

**Notes**:
- Field tên là `"content"` (lowercase, có ngoặc kép trong DDL) — query phải dùng `"content"` hoặc alias.
- KHÔNG có subject riêng. Subject nằm ở `EMAILTEMPLATE.subj` → cần JOIN nếu muốn show subject.
- KHÔNG có `stat`/`sent` flag → mọi row trong EMAILLOG đều là "đã gửi".

**Query đề xuất Phase 2**:
```sql
SELECT
  el.logId, el.sentAt, el.rcvEmail,
  et.subj AS subject,
  LEFT(el."content", 300) AS body_snippet
FROM EMAILLOG el
JOIN EMAILTEMPLATE et ON et.tmplId = el.tmplId
WHERE el.jobAppId = $1
ORDER BY el.sentAt DESC
LIMIT 5;
```

### 0.2.3 `OFFER` schema

```sql
CREATE TABLE OFFER (
  offerId     SERIAL PRIMARY KEY,
  jobAppId    INT NOT NULL,
  salary      INT NOT NULL,
  description TEXT,
  stat        VARCHAR(20) NOT NULL,
  subAt       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ver         INT NOT NULL,
  hrId        INT NOT NULL,
  ...
);
```

**Notes**: Field rõ ràng. `stat` không có CHECK constraint nên giá trị có thể đa dạng — paste raw vào context.

**Query đề xuất Phase 2**:
```sql
SELECT offerId, ver, salary, description, stat, subAt
FROM OFFER
WHERE jobAppId = $1
ORDER BY subAt DESC
LIMIT 3;
```

### 0.2.4 `JOBPOSTING` field hiện có (extra để enrichment)

```sql
JOBPOSTING:
  jobPostId, title, description, minSalary, maxSalary,
  workLoc, workMode (ONSITE|HYBRID|REMOTE), provId, createdAt, expAt, compId
```

Liên quan để enrichment:
- Salary range: `minSalary, maxSalary` (cả hai nullable).
- Work mode/location: `workMode`, `workLoc`, `provId` (FK → PROVINCE.provName).
- Skills: `JOBREQUIREMENT (jobPostId, skillId)` → `SKILL.skillName`.
- Levels: `JOB_LEVEL_MAP (jobPostId, levelId)` → `JOBLEVEL.levelName`.
- Categories: `JOB_CATEGORY_MAP (jobPostId, catId)` → `JOBCATEGORY.catName`.
- Language req: `JOB_LANG_REQUIREMENT`.

Query enrichment có thể thành 1 main + 3-4 phụ. Nếu join hết trong 1 query thì cardinality nhân lên → nên fetch riêng rồi gộp ở Python.

### 0.2.5 `topK` nullability ở các bảng

| Table | Cột | NULL allowed? | Hệ quả |
|---|---|---|---|
| `AIQUERYLOG` | `topK INT NOT NULL` | **KHÔNG** | Phải insert giá trị, dùng `0` cho full-CV path. |
| `AICHATMESSAGE` | `topK INT` | **CÓ** | Có thể truyền NULL; mình vẫn nên truyền `0` để consistent với response. |

→ **Không cần migration DB**. Chỉ cần truyền `top_k=0` khi gọi `insert_message()` và `insert_query_log()`.

### 0.2.6 miCareer-mini consumer

**File `core/fang_client.py`** (`miCareer-mini/core/fang_client.py:46-67`):
```
def chat_query(...) -> dict:
    # Trả về dict với keys:
    # conversationId, messageId, response, model, modelMode,
    # fallbackPath, latencyMs, topK, contextWarning (nullable)
```
→ Client chỉ là pass-through, không validate schema. Thêm field `contextSource` mới sẽ KHÔNG vỡ client.

**File `app.py:340-350`** — UI hiển thị:
```python
st.caption(
    f"🔧 Model: `{result.get('model', 'N/A')}` "
    f"| ⏱ {result.get('latencyMs', 0)}ms "
    f"| 📚 top-{result.get('topK', 0)} chunks"   # ← VẤN ĐỀ
)
st.session_state[ctx_warning_key] = result.get("contextWarning")
```

**Phát hiện quan trọng**:
- UI **hardcode** chuỗi `"top-{topK} chunks"` → nếu trả `topK=0` từ FANG, UI sẽ hiển thị "📚 top-0 chunks" (gây nhầm lẫn).
- **PHẢI patch miCareer-mini** ở Phase 3.4:
  - Cách 1: Nếu response có `contextSource == "full_cv_markdown"` → đổi caption thành `"📄 Full CV context"`.
  - Cách 2: Bỏ phần `top-X chunks` hoàn toàn, không phụ thuộc vào field nào.
- `contextWarning` đã được handle (lưu vào session_state) → mở rộng warning type vẫn ok nếu giữ `type/usedPercent/options`.

**File `app.py:171, 229, 329`** — các string khác có chữ "RAG":
```
"Đánh giá RAG"           (button)
"Chat RAG chỉ khả dụng..."
"⚙️ FANG đang xử lý RAG pipeline..."
```
→ Wording "RAG" vẫn chính xác về bản chất (full-CV vẫn là RAG nghĩa rộng), nhưng nên review với người làm thành viên thứ 3 (Option A).

### 0.2.7 Sample CV data (từ `database/seed_data.sql`)

CV chính trong seed (`nguyenvanan`):
```
Backend Developer với 3 năm kinh nghiệm phát triển ứng dụng web bằng Java/Spring Boot.
Tốt nghiệp Cử nhân CNTT tại Học viện Công nghệ Bưu chính Viễn thông (PTIT), loại Giỏi.

Kinh nghiệm:
- 2 năm tại ABC Tech: Phát triển RESTful API ...
- 1 năm tại startup XYZ: Xây dựng microservices ...
```

**Ước tính token** (CHARS_PER_TOKEN = 3.5):
- Bio đầy đủ (~1500 chars) ≈ **430 tokens**.
- Markdown convert hết CV có summary + 2-3 experience + 5-8 skills + 1 education ≈ **800-1500 tokens** (ước tính dựa trên format `convert_json_to_markdown`).
- JD description trong seed ≈ 500-1000 tokens.
- 3 offers + 5 emails truncated (300 chars each) ≈ 500-1500 tokens.
- **Tổng context tối thiểu ước tính: 2-5k tokens** cho 1 message.

**Budget hiện tại** (cần verify trong `app/core/config.py`):
- `context_budget_lite` — dùng cho Lite chain (Gemini Flash, GPT-mini, Haiku).
- `context_budget_pro` — dùng cho Pro chain.

→ Phase 0.2 chưa đọc `config.py` nên chưa biết giá trị thực. **Phase 1.3 phải verify**.

→ Với threshold warn 60% / hard 85% giả định budget Lite ~32k, hard limit = ~27k tokens → CV thông thường 2-5k tokens KHÔNG bị block. Long-tail (CV 20+ trang, nhiều experience) mới rủi ro.

### 0.2.8 Verify trên DB thật (chưa chạy)

**Items chặn xác nhận tại runtime** (KHÔNG chặn Phase 1 vì có thể chạy local Postgres):

| Query | Mục đích |
|---|---|
| `SELECT cvParsedId, length(rawText), (parsedJson IS NOT NULL) AS has_json, parserVer FROM CVPARSED LIMIT 20` | Đếm row legacy `parsedJson=NULL` có bao nhiêu; phân bố `parserVer`. |
| `SELECT jsonb_typeof(parsedJson->'languages') FROM CVPARSED WHERE parsedJson IS NOT NULL` | Phát hiện legacy `languages: list[str]` (kết quả `'array'` nhưng phần tử `string` — phải check kỹ hơn). |
| `SELECT COUNT(*) FROM OFFER GROUP BY jobAppId ORDER BY COUNT DESC LIMIT 10` | Đo số offer thực tế trên 1 jobApp → xác nhận giới hạn 3 versions là đủ. |
| `SELECT COUNT(*), AVG(length(content)) FROM EMAILLOG GROUP BY jobAppId LIMIT 10` | Đo độ dài body email → xác nhận truncate 300 chars là OK. |

→ Đề xuất chạy 4 query này ở đầu Phase 1 nếu có DB chạy được.

---

## 0.3 — Implications cho roadmap

| Implication | Phase ảnh hưởng |
|---|---|
| `ParsedCV.rawText` REQUIRED min_length=1 → khi load từ `parsedJson` phải merge `CVPARSED.rawText` vào dict trước `model_validate` | Phase 1.2 |
| Legacy `languages: list[str]` sẽ FAIL → fallback rawText quan trọng | Phase 1.2 + test |
| `EMAILLOG.content` lowercase → query phải quote `"content"` | Phase 2.1 |
| `EMAILLOG` không có subject → JOIN `EMAILTEMPLATE.subj` | Phase 2.1 |
| `AIQUERYLOG.topK NOT NULL` → insert `0`, không NULL | Phase 1.4 |
| miCareer-mini hardcode "top-{topK} chunks" trong UI | Phase 3.4 phải patch |
| Field `contextSource` mới không vỡ client vì client chỉ pass-through dict | Phase 1.5 / response schema |
| Token CV thực tế ~800-1500 → block budget hiếm xảy ra với CV thông thường | Phase 1.3 (test edge case CV dài) |
| `parserSelfReport.confidence` có thể dùng làm warning trong context | Optional — Phase 2 nếu rảnh |
| `expectedSalaryMin/Max` có thể đưa vào context CV markdown | Optional — extend `convert_json_to_markdown`? Không, để phase sau, scope creep |

---

## 0.4 — Items chưa audit (không chặn Phase 1)

- `app/core/config.py` giá trị thực của `context_budget_lite/pro`, `context_budget_warning_threshold` → đọc đầu Phase 1.3.
- `app/services/embedding.py` — chỉ cần đảm bảo KHÔNG gọi trong path full-CV; không cần đọc sâu.
- `docs/strategy/rag_query_strategy.md` hiện tại — đọc khi sang Phase 3.3 để archive đúng nội dung.
- 4 DB query xác minh ở 0.2.8 — chạy nếu có DB local.

---

## 0.5 — Sẵn sàng Phase 1?

✅ Tất cả ground truth cần để vào Phase 1.1 (refactor service boundary) đã có.
✅ Fallback ladder logic đã rõ ràng (nhờ phát hiện `rawText` REQUIRED + legacy `languages` issue).
✅ miCareer-mini impact đã được scope (patch 1 chỗ `app.py:346`).
⚠️ Phase 1.3 phải verify budget thực tế từ `config.py` trước khi viết threshold cụ thể.

**Đề xuất**: vào Phase 1.1 ngay; mở `config.py` đầu Phase 1.3.

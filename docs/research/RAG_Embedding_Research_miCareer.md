# Báo Cáo Nghiên Cứu: Text Embedding cho RAG Song Ngữ (VN/EN) — miCareer-x-Fang

> **Role:** Research Lead – AI Core  
> **Ngày:** 29/03/2026  
> **Phiên bản DB:** PostgreSQL 18.3 + pgvector 0.8.2  
> **Tham chiếu schema:** AIDocumentChunk, CVParsed, AIIndexJob, AIQueryLog (Sprint 1&2 Data Core)

---

## I. BỐI CẢNH HỆ THỐNG (TỪ TÀI LIỆU DỰ ÁN)

### Luồng dữ liệu AI Core

```
Web Core (Java Servlet)
    │
    ├── Upload CV → Cloud Storage → cvSnapUrl
    ├── POST {jobAppId, cvSnapUrl} → AI Core (FlaskAPI)
    │
    └── AI Core:
         CVParsed: extract rawText từ file CV
              ↓
         AIDocumentChunk: chunk text → embed → lưu vector
              ↓ (khi HR query)
         AIQueryLog: embed query → cosine search → trả kết quả
```

### Schema quan trọng (AIDocumentChunk)

```sql
AIDocumentChunk(
  chunkId       PK,
  jobAppId      FK → JobApplication,
  sourceType    VARCHAR,   -- 'CV' | 'COVER_LETTER' | 'JD'
  content       TEXT,
  chunkIndex    INT,
  tokenCount    INT,
  embedding     vector(1536),  -- CẦN QUYẾT ĐỊNH CHIỀU NÀY
  createdAt     TIMESTAMP
)
```

Cột `embedding` hiện giữ `vector(1536)` nhưng **linh hoạt** — đây là quyết định cốt lõi của báo cáo này.

---

## II. ƯỚC LƯỢNG WORKLOAD ATS

### Quy mô dữ liệu giả định (1K ứng viên)

| Đơn vị | Ước lượng | Lý do |
|---|---|---|
| Số ứng viên (Candidate) | 1.000 | Mục tiêu benchmark |
| Số job postings (JD) | 100 | ~10 JD/công ty × 10 công ty |
| Tỉ lệ ứng tuyển | 60% | ~600 JobApplication thực tế |
| CoverLetter có nội dung | 70% | ~420 CoverLetter |

### Ước lượng token và chunk

**CV (PDF parsed):**
- CV trung bình: **600–1.000 tokens** sau khi parse PDF sang text
- Chunk size: **300 tokens**, overlap: **50 tokens**
- Số chunk/CV: **(600–1000) / 250 ≈ 3–5 chunks** (trung bình ~4)

**Cover Letter:**
- Trung bình: **150–300 tokens**
- Số chunk/CoverLetter: **1–2** (trung bình ~1)

**Job Description (JD):**
- Mô tả công việc: **300–600 tokens**
- Số chunk/JD: **1–2** (trung bình ~2)

### Tổng vector lưu trữ (1K ứng viên scenario)

| Nguồn | Số lượng | Chunk/doc | Tổng vector |
|---|---|---|---|
| CV chunks | 600 applications | 4 | 2.400 |
| Cover Letter chunks | 420 | 1 | 420 |
| JD chunks | 100 JDs | 2 | 200 |
| **TỔNG** | | | **~3.020 vectors** |

> **Lưu ý:** Mini-ATS này là hệ nghiên cứu. Quy mô thực tế ~3K vectors — **rất nhỏ**, không cần lo lắng về hiệu năng index. Ước lượng chi phí vẫn được trình bày để chuẩn bị cho PROD.

### Workload truy vấn (Query)

- HR sessions/ngày: **10–20** (hệ thống demo)
- Queries/session: **5–15** (hỏi đáp về ứng viên)
- Tổng queries/ngày: **~150**
- Tokens/query: **50–150** (câu hỏi HR)
- **Top-k = 20** (lấy 20 chunks tương đồng nhất)

---

## III. KHẢO SÁT CÁC MÔ HÌNH EMBEDDING

### 3.1 OpenAI `text-embedding-3-small`

| Thuộc tính | Giá trị |
|---|---|
| Chiều mặc định | **1.536** |
| Chiều tùy chỉnh | **256, 512, 1.024, 1.536** (Matryoshka/`dimensions` param) |
| Context tối đa | 8.192 tokens |
| Giá | **$0,02 / 1M tokens** (Standard); $0,01 (Batch) |
| Hỗ trợ VN/EN | ✅ Multilingual; MIRACL benchmark: **44,0%** (vs ada-002: 31,4%) |
| MTEB (EN) | **62,3%** |
| Matryoshka (không re-embed) | ✅ Cắt suffix — `dimensions` param khi gọi API |
| Latency | Thấp; throughput cao |
| Free tier | $5 credits cho user mới (~250M tokens) |

**Cơ chế giảm chiều:** OpenAI train cả hai model embedding-3 bằng kỹ thuật Matryoshka. Khi gọi API với `dimensions=768`, mô hình trả về vector 768 chiều — **không cần re-embed lại toàn bộ data** (server-side truncation tại thời điểm inference, không phải client-side slice). Tuy nhiên, nếu đã lưu vector 1536 chiều trong DB thì vẫn cần re-embed nếu muốn chuyển sang 768.

### 3.2 OpenAI `text-embedding-3-large`

| Thuộc tính | Giá trị |
|---|---|
| Chiều mặc định | **3.072** |
| Chiều tùy chỉnh | **256 → 3.072** (Matryoshka) |
| Context tối đa | 8.192 tokens |
| Giá | **$0,13 / 1M tokens** (Standard); $0,065 (Batch) |
| Hỗ trợ VN/EN | ✅ MIRACL: **54,9%** (+24% so với ada-002) |
| MTEB (EN) | tốt hơn 3-small |
| Matryoshka | ✅ Tương tự 3-small |

**Lưu ý quan trọng:** text-embedding-3-large tại dimension 256 vẫn outperform ada-002 tại dimension 1536 trên MTEB — minh chứng mạnh cho Matryoshka.

### 3.3 Google `gemini-embedding-001`

| Thuộc tính | Giá trị |
|---|---|
| Chiều mặc định | **3.072** |
| Chiều tùy chỉnh | **768, 1.536, 3.072** (MRL — `output_dimensionality`) |
| Context tối đa | **2.048 tokens** ⚠️ |
| Giá | **$0,15 / 1M tokens**; Batch API: $0,075 |
| Hỗ trợ VN/EN | ✅ **100+ ngôn ngữ, bao gồm tiếng Việt** (listed trong docs) |
| MTEB Multilingual | **68,32** — top MTEB Multilingual leaderboard |
| Matryoshka | ✅ MRL prefix truncation |
| Lưu ý API | Vertex AI: mỗi request chỉ 1 input text |

**Điểm mạnh VN:** gemini-embedding-001 consistently dẫn đầu MTEB Multilingual, đặc biệt tốt cho các ngôn ngữ châu Á. Tiếng Việt được liệt kê explicit trong danh sách ngôn ngữ hỗ trợ.

**Lưu ý context 2.048 tokens:** Với CV dài (nhiều trang), cần chunking cẩn thận để không vượt giới hạn này. OpenAI cho phép 8.192 tokens/chunk.

### 3.4 Google `gemini-embedding-2-preview` (Multimodal)

| Thuộc tính | Giá trị |
|---|---|
| Chiều mặc định | **3.072** |
| Chiều tùy chỉnh | **128, 256, 512, 768, 1.536, 2.048** (MRL) |
| Modalities | Text, image, video, audio, document |
| Giá | **$0,20 / 1M text tokens**; Batch: $0,10 |
| Hỗ trợ VN | ✅ 100+ ngôn ngữ |
| Trạng thái | ⚠️ **Preview (Pre-GA)** — không phù hợp production |
| Incompatibility | ⚠️ **Embedding space khác hoàn toàn** so với embedding-001 |

**Đánh giá cho dự án này:** Khả năng multimodal (nhúng trực tiếp file CV dạng ảnh) thú vị về lý thuyết, nhưng **không nên dùng cho R&D giai đoạn này** vì: (1) còn Preview, (2) giá cao hơn, (3) nếu sau chuyển sang embedding-001 sẽ phải re-embed toàn bộ do incompatible embedding space.

### 3.5 Cohere `embed-multilingual-v3.0`

| Thuộc tính | Giá trị |
|---|---|
| Chiều | **1.024** (cố định, không tùy chỉnh) |
| Context tối đa | 512 tokens ⚠️ |
| Giá | ~$0,10 / 1M tokens (ước tính từ Cohere API) |
| Hỗ trợ VN | ✅ 100+ ngôn ngữ |
| Matryoshka | ❌ Không hỗ trợ |
| input_type | Cần phân biệt `search_document` / `search_query` |
| MTEB | BEIR state-of-the-art (English-heavy benchmark) |

**Hạn chế lớn:** Context **512 tokens** là quá ngắn cho CV/JD parsing — phải chunk rất nhỏ. Không có Matryoshka → không thể giảm chiều mà không re-embed.

### 3.6 Cohere `embed-v4.0` (thế hệ mới nhất)

| Thuộc tính | Giá trị |
|---|---|
| Chiều | **1.536** |
| Context tối đa | Dài hơn v3 |
| Giá | **$0,12 / 1M text tokens** |
| Hỗ trợ VN | ✅ 100+ ngôn ngữ |
| Matryoshka | ✅ Hỗ trợ nhiều output dimensions |
| Multimodal | ✅ Text + image |

---

## IV. BẢNG SO SÁNH TỔNG HỢP

| Model | Default dim | Dim tùy chỉnh | Giá/1M token | VN Support | MTEB Multi | Context max | Matryoshka | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| `text-embedding-3-small` | 1.536 | 256–1.536 | **$0,02** | ✅ Tốt | 44,0% | 8.192 | ✅ | GA ✅ |
| `text-embedding-3-large` | 3.072 | 256–3.072 | $0,13 | ✅ Tốt | 54,9% | 8.192 | ✅ | GA ✅ |
| `gemini-embedding-001` | 3.072 | 768/1.536/3.072 | $0,15 | ✅ **Tốt nhất** | **68,32** | **2.048** ⚠️ | ✅ | GA ✅ |
| `gemini-embedding-2-preview` | 3.072 | 128–2.048 | $0,20 | ✅ Tốt | N/A | 2.048 | ✅ | ⚠️ Preview |
| `embed-multilingual-v3.0` | **1.024** (fixed) | ❌ Không | ~$0,10 | ✅ Tốt | Tốt | **512** ⚠️ | ❌ | GA ✅ |
| `embed-v4.0` (Cohere) | 1.536 | ✅ Matryoshka | $0,12 | ✅ Tốt | Tốt | Khá | ✅ | GA ✅ |

### Pros/Cons chi tiết

**text-embedding-3-small**
- ✅ Rẻ nhất (6.5× rẻ hơn 3-large, 7.5× rẻ hơn gemini-001)
- ✅ Context 8.192 tokens — chunking linh hoạt
- ✅ Matryoshka → migrate xuống 768 mà không cần re-embed (chỉ cần alter column + reindex)
- ✅ Free $5 credits = 250M tokens — đủ cho cả R&D sprint
- ⚠️ MIRACL VN/EN thấp hơn gemini-001 (~36% gap)
- ⚠️ Proprietary — data gửi đến OpenAI servers

**text-embedding-3-large**
- ✅ Chất lượng cao nhất trong nhóm OpenAI
- ✅ Matryoshka mạnh (dim 256 vẫn beat ada-002 dim 1536)
- ❌ Đắt 6.5× so với 3-small, không justify cho R&D
- ❌ Storage lớn hơn nếu dùng 3.072 dim

**gemini-embedding-001**
- ✅ **Chất lượng VN tốt nhất** — MTEB Multilingual 68,32 (top leaderboard)
- ✅ MRL với 3 mức dimension
- ✅ Context 2.048 tokens đủ cho most CV chunks
- ❌ $0,15/1M — đắt hơn 3-small 7.5×
- ❌ Vertex AI API setup phức tạp hơn (cần GCP project)
- ⚠️ Context limit 2.048 — cần cẩn thận với CV dài

**Cohere embed-multilingual-v3.0**
- ✅ Dimension 1024 — cân bằng tốt storage vs quality
- ❌ Context **512 tokens** — phải chunk rất nhỏ, tăng số vector
- ❌ **Không có Matryoshka** — khóa vào 1024 chiều
- ❌ `input_type` mandatory → phải tách embed_document / embed_query

---

## V. THIẾT KẾ THÍ NGHIỆM (MINI BENCHMARK)

### 5.1 Bộ test song ngữ VN/EN

Đề xuất tập test queries cho hệ ATS (15 câu):

**English queries (HR perspective):**
1. "Does the candidate have experience with Java Spring Boot?"
2. "What is the candidate's highest level of education?"
3. "Has this applicant worked on RESTful API development?"
4. "Does the candidate have leadership or team management experience?"
5. "What programming languages does the candidate know?"

**Vietnamese queries (HR perspective):**
1. "Ứng viên có kinh nghiệm làm việc với Java không?"
2. "Trình độ học vấn của ứng viên là gì?"
3. "Ứng viên đã từng làm dự án về API chưa?"
4. "Ứng viên có kỹ năng quản lý nhóm không?"
5. "Ứng viên biết những ngôn ngữ lập trình nào?"

**Cross-lingual (VN query → EN CV):**
1. "Ứng viên có kinh nghiệm backend không?" → Expected: retrieve chunks mentioning "backend developer", "server-side"
2. "Mô tả kinh nghiệm làm việc của ứng viên" → Expected: retrieve work experience sections

**Bộ ngữ cảnh mẫu (CV chunks):**
- CV1: Junior Backend Dev, Java/Spring Boot, 1 năm kinh nghiệm (tiếng Anh)
- CV2: Senior Full-stack, React + Node.js, 4 năm (tiếng Việt)  
- CV3: Data Analyst, Python/SQL, 2 năm (mix VN/EN)

### 5.2 Thí nghiệm giảm chiều (Matryoshka)

**Test dimensions:** 512 / 768 / 1.024 / 1.536 / 3.072

**Metric:** Recall@5, Recall@10, Recall@20

**Cách đánh giá:** Dùng brute-force cosine (sequential scan, không index) làm ground truth, so sánh với kết quả từ các dimension khác nhau.

**Kết luận dự đoán từ OpenAI benchmark:**

| Model | Dim 512 | Dim 768 | Dim 1.024 | Dim 1.536 | Dim 3.072 |
|---|---|---|---|---|---|
| 3-small | ~87% | ~91% | ~94% | 100% (ref) | N/A |
| 3-large | ~90% | ~94% | ~96% | ~98% | 100% (ref) |
| gemini-001 | N/A | ~93% | ~96% | ~98% | 100% (ref) |

> Các số trên là ước tính dựa theo benchmark MTEB/MIRACL của từng model. Cần thực nghiệm với dữ liệu CV/JD thực tế bằng tiếng Việt.

### 5.3 Script thí nghiệm mẫu (Python / FlaskAPI)

```python
import openai
import numpy as np
from typing import List

def embed_openai(texts: List[str], model="text-embedding-3-small", dim=1024):
    response = openai.embeddings.create(
        model=model, input=texts, dimensions=dim
    )
    return [e.embedding for e in response.data]

def recall_at_k(query_vec, doc_vecs, relevant_ids, k=10):
    """Tính Recall@k bằng cosine similarity."""
    sims = [np.dot(query_vec, d) for d in doc_vecs]
    top_k = set(np.argsort(sims)[::-1][:k])
    return len(top_k & set(relevant_ids)) / len(relevant_ids)

# Test các dimension
for dim in [512, 768, 1024, 1536]:
    embeddings = embed_openai(test_chunks, dim=dim)
    recall = recall_at_k(query_embed, embeddings, relevant_ids, k=10)
    print(f"dim={dim}: Recall@10 = {recall:.3f}")
```

---

## VI. KHUYẾN NGHỊ CHÍNH

### 6.1 Khuyến nghị DEV/DEMO (Sprint hiện tại)

**✅ Model: `text-embedding-3-small`**  
**✅ Dimension: `1.024`** (dùng `dimensions=1024` khi gọi API)

**Lý do:**
1. **Miễn phí trong giai đoạn R&D:** $5 credits = 250M tokens. Với workload ~3K vectors × 800 tokens = 2,4M tokens → **$0,05** — không đáng kể. Các HR queries 150/ngày × 100 tokens = 0,015M tokens/ngày → vài cent/tháng.
2. **Matryoshka strategy:** Chọn dim=1024 (không phải 1536) ngay từ đầu để tiết kiệm storage/RAM 33% mà ít mất recall. Khi cần upgrade lên 1536/3072, chỉ cần re-embed một lần.
3. **SDK đơn giản:** `openai` Python package, không cần setup GCP project.
4. **Context 8.192 tokens:** Không lo vượt limit với bất kỳ CV nào.

**SQL setup DEV:**
```sql
-- Thay đổi cột embedding từ vector(1536) → vector(1024)
ALTER TABLE AIDOCUMENTCHUNK 
  ALTER COLUMN embedding TYPE vector(1024);

-- Tạo HNSW index với Cosine
CREATE INDEX CONCURRENTLY idx_aidocchunk_hnsw_cosine
  ON AIDOCUMENTCHUNK
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
-- ef_construction=64 đủ cho DEV (<10K vectors)
```

### 6.2 Khuyến nghị PROD (khi ra mắt thực)

**✅ Model: `gemini-embedding-001`**  
**✅ Dimension: `768`** (dùng `output_dimensionality=768`)

**Lý do:**
1. **Chất lượng VN cao nhất:** MTEB Multilingual 68,32 — vượt xa tất cả model cùng tier. Vì hệ thống phục vụ user VN, đây là ưu tiên hàng đầu.
2. **Dim 768 với MRL:** Tại 768 chiều, gemini-001 giữ ~93% recall so với 3072 — chấp nhận được cho ATS. Storage và RAM index giảm 75%.
3. **Batch API:** Giá giảm 50% → $0,075/1M tokens khi embedding hàng loạt CV.
4. **Context 2.048 tokens:** Đủ cho 99% CV sau chunking 300-token strategy.

**Trade-off:** Đắt hơn 3-small ~7.5×, cần GCP project setup. Không phù hợp giai đoạn R&D hiện tại.

### 6.3 Bảng so sánh DEV vs PROD

| | DEV/DEMO | PROD |
|---|---|---|
| Model | `text-embedding-3-small` | `gemini-embedding-001` |
| Dimension | **1.024** | **768** |
| VN Quality | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Giá/1M tokens | $0,02 | $0,075 (batch) |
| Chi phí 1K CV lưu trữ | **~$0,05** | ~$0,18 |
| Chi phí queries/tháng | ~$0,01 | ~$0,04 |
| Index RAM (1K CVs, HNSW) | ~20 MB | ~15 MB |
| Setup complexity | ⭐ (pip install openai) | ⭐⭐⭐ (GCP setup) |
| Re-embed khi upgrade | Chỉ 1 lần (→ PROD) | Không (production stable) |

---

## VII. KẾ HOẠCH MIGRATION

### 7.1 Migration từ DEV (1024d) lên PROD (768d hoặc model mới)

#### Bước 0: Backup an toàn

```sql
-- Tạo backup toàn bộ bảng trước khi migrate
CREATE TABLE AIDOCUMENTCHUNK_BACKUP AS 
  SELECT * FROM AIDOCUMENTCHUNK;

-- Verify count
SELECT COUNT(*) FROM AIDOCUMENTCHUNK;
SELECT COUNT(*) FROM AIDOCUMENTCHUNK_BACKUP;
```

#### Bước 1: Drop index cũ

```sql
-- Drop index HNSW/IVFFlat hiện tại (nhanh)
DROP INDEX CONCURRENTLY IF EXISTS idx_aidocchunk_hnsw_cosine;
```

#### Bước 2: Thêm cột embedding mới song song (Zero Downtime)

```sql
-- Thêm cột mới, giữ cột cũ
ALTER TABLE AIDOCUMENTCHUNK 
  ADD COLUMN embedding_new vector(768);  -- hoặc chiều mới

-- Migrate dữ liệu: re-embed bằng script Python (background job)
-- (xem script bên dưới)

-- Sau khi migrate xong, rename columns
ALTER TABLE AIDOCUMENTCHUNK 
  RENAME COLUMN embedding TO embedding_old;
ALTER TABLE AIDOCUMENTCHUNK 
  RENAME COLUMN embedding_new TO embedding;

-- Drop cột cũ sau khi verify
ALTER TABLE AIDOCUMENTCHUNK 
  DROP COLUMN embedding_old;
```

#### Bước 3: Script re-embed Python

```python
import psycopg2
import openai  # hoặc google.genai cho PROD

def re_embed_all(batch_size=50):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Lấy tất cả chunks cần re-embed
    cur.execute("""
        SELECT chunkId, content FROM AIDOCUMENTCHUNK 
        WHERE embedding_new IS NULL
        ORDER BY chunkId
    """)
    
    chunks = cur.fetchmany(batch_size)
    while chunks:
        ids = [c[0] for c in chunks]
        texts = [c[1] for c in chunks]
        
        # Gọi embedding API
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
            dimensions=768  # hoặc gemini với output_dimensionality=768
        )
        embeddings = [e.embedding for e in response.data]
        
        # Lưu vào DB
        for chunk_id, emb in zip(ids, embeddings):
            cur.execute(
                "UPDATE AIDOCUMENTCHUNK SET embedding_new = %s WHERE chunkId = %s",
                (emb, chunk_id)
            )
        conn.commit()
        chunks = cur.fetchmany(batch_size)
    
    conn.close()
    print("Re-embedding hoàn tất!")
```

#### Bước 4: Tạo index mới

```sql
-- SET memory trước khi build HNSW (PROD)
SET maintenance_work_mem = '512MB';

-- HNSW với Cosine distance (khuyến nghị)
CREATE INDEX CONCURRENTLY idx_aidocchunk_hnsw_cosine
  ON AIDOCUMENTCHUNK
  USING hnsw (embedding vector_cosine_ops)
  WITH (
    m = 16,              -- connections/node, 16 là balance tốt
    ef_construction = 128 -- tăng từ 64 lên 128 cho PROD
  );

-- Kiểm tra index đã được tạo
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'aidocumentchunk';
```

#### Bước 5: Warm-up và Analyze

```sql
-- ANALYZE để planner cập nhật statistics
ANALYZE AIDOCUMENTCHUNK;

-- Warm-up: chạy 1 query test để load index vào RAM
SELECT chunkId, content, 
       embedding <=> '[0.1, 0.2, ...]'::vector AS distance
FROM AIDOCUMENTCHUNK
ORDER BY embedding <=> '[0.1, 0.2, ...]'::vector
LIMIT 20;

-- Set ef_search cho queries (mặc định = 40)
SET hnsw.ef_search = 60;  -- tăng nhẹ để recall tốt hơn

-- VACUUM nếu có nhiều dead tuples sau migration
VACUUM ANALYZE AIDOCUMENTCHUNK;
```

#### Bước 6: Rollback Plan

```sql
-- Nếu cần rollback về data cũ
TRUNCATE AIDOCUMENTCHUNK;
INSERT INTO AIDOCUMENTCHUNK SELECT * FROM AIDOCUMENTCHUNK_BACKUP;

-- Recreate index cũ
CREATE INDEX CONCURRENTLY idx_aidocchunk_hnsw_cosine
  ON AIDOCUMENTCHUNK
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

### 7.2 Checklist an toàn migration

```
PRE-MIGRATION:
□ Backup AIDOCUMENTCHUNK → AIDOCUMENTCHUNK_BACKUP
□ Xác nhận count rows khớp giữa backup và original
□ Test re-embed script trên 10 rows mẫu
□ Có downtime window (hoặc dùng zero-downtime strategy với cột mới)
□ Note model cũ và mới để rollback nếu cần

DURING MIGRATION:
□ Monitor API rate limits (OpenAI: 3.000 RPM free tier)
□ Log errors từng batch
□ Verify embedding_new IS NOT NULL count tăng dần

POST-MIGRATION:
□ COUNT(*) WHERE embedding IS NULL = 0
□ Chạy test queries và verify kết quả semantically correct
□ ANALYZE bảng
□ Drop AIDOCUMENTCHUNK_BACKUP sau 1 tuần

ROLLBACK TRIGGERS:
□ >5% queries trả kết quả sai về mặt ngữ nghĩa
□ Latency tăng >3× so với trước migration
□ API errors không recovery được
```

---

## PHỤ LỤC A: CÔNG THỨC ƯỚC LƯỢNG CHI PHÍ

### A.1 Chi phí lưu trữ (Ingestion)

```
Chi phí embed 1 CV:
  tokens_per_cv = 800 (trung bình)
  cost_per_cv = (tokens_per_cv / 1_000_000) × price_per_1M
  
  3-small: (800 / 1_000_000) × $0.02 = $0.000016 / CV
  gemini-001: (800 / 1_000_000) × $0.15 = $0.00012 / CV

Chi phí cho 1.000 CV:
  3-small: 1000 × $0.000016 = $0.016 ≈ $0.02
  gemini-001: 1000 × $0.00012 = $0.12
  
  Bao gồm JD + CoverLetter (~+20%):
  3-small: ~$0.024 tổng
  gemini-001: ~$0.14 tổng
```

### A.2 Chi phí truy vấn (Query)

```
queries_per_day = 150
tokens_per_query = 100 (trung bình)
days_per_month = 30

tokens_per_month = 150 × 100 × 30 = 450.000 tokens = 0.45M tokens

cost_per_month:
  3-small: 0.45 × $0.02 = $0.009/tháng ≈ $0.01
  gemini-001: 0.45 × $0.15 = $0.068/tháng ≈ $0.07
```

### A.3 Chi phí RAM cho HNSW index

```
Bộ nhớ xấp xỉ mỗi vector trong HNSW:
  memory_per_vector ≈ (4 × dimensions + 8) bytes × overhead_factor(~3)
  
  dim=768:  (4×768 + 8) × 3 ≈ 9.240 bytes ≈ 9 KB/vector
  dim=1024: (4×1024 + 8) × 3 ≈ 12.312 bytes ≈ 12 KB/vector
  dim=1536: (4×1536 + 8) × 3 ≈ 18.432 bytes ≈ 18 KB/vector

Với 3.020 vectors (1K CV scenario):
  dim=768:  3020 × 9 KB ≈ 27 MB RAM
  dim=1024: 3020 × 12 KB ≈ 36 MB RAM
  dim=1536: 3020 × 18 KB ≈ 54 MB RAM

→ Với mini-ATS này, RAM không phải vấn đề. Cả 3 đều nhỏ hơn 100MB.
→ Với 100K vectors (scale PROD lớn): dim=768 cần ~870MB RAM cho HNSW.
```

---

## PHỤ LỤC B: HƯỚNG DẪN INDEX TRONG PGVECTOR

### B.1 Khi nào dùng HNSW vs IVFFlat?

| Tiêu chí | HNSW | IVFFlat |
|---|---|---|
| Recall | ⭐⭐⭐⭐⭐ Cao hơn | ⭐⭐⭐ Thấp hơn |
| Build time | ⭐⭐ Chậm hơn | ⭐⭐⭐⭐ Nhanh hơn |
| RAM usage | ⭐⭐ Nhiều hơn | ⭐⭐⭐⭐ Ít hơn |
| Query speed | ⭐⭐⭐⭐⭐ Nhanh hơn | ⭐⭐⭐ |
| Insert sau index | ✅ OK (graph tự update) | ⚠️ Recall giảm dần |
| Cần load data trước? | ❌ Không cần | ✅ Cần data đầy đủ |
| Phù hợp | **Dùng cho dự án này** | Static datasets lớn |

**Kết luận:** Dùng **HNSW** cho miCareer vì:
1. Dataset nhỏ (<10K vectors) — build time không thành vấn đề
2. Data ingestion liên tục (mỗi application mới thêm chunks)
3. Recall cao hơn quan trọng với RAG accuracy

### B.2 Cosine vs L2 — khi nào dùng gì?

**Dùng Cosine (`<=>`) khi:**
- So sánh ngữ nghĩa văn bản (semantic similarity)
- Vectors không normalized (OpenAI, Gemini output not guaranteed normalized)
- **→ Đây là trường hợp của miCareer:** so sánh CV với query HR

**Dùng L2 (`<->`) khi:**
- Vectors đã được normalize (magnitude = 1)
- Euclidean distance có ý nghĩa trong feature space
- Một số model cụ thể khuyến nghị L2

> **Lưu ý pgvector:** Với normalized vectors, cosine distance và L2 distance cho kết quả ranking **giống nhau**. OpenAI và Gemini không đảm bảo normalize → **dùng Cosine** để an toàn.

### B.3 Tham số HNSW tối ưu cho dự án này

```sql
-- DEV (< 5K vectors):
CREATE INDEX CONCURRENTLY idx_hnsw_dev
  ON AIDOCUMENTCHUNK
  USING hnsw (embedding vector_cosine_ops)
  WITH (
    m = 16,               -- kết nối/node (mặc định 16, tốt cho small dataset)
    ef_construction = 64  -- search width khi build (mặc định 64)
  );
-- Runtime query parameter:
SET hnsw.ef_search = 40;  -- mặc định, đủ cho demo

-- PROD (10K–100K vectors):
SET maintenance_work_mem = '1GB';  -- Tăng trước khi build
CREATE INDEX CONCURRENTLY idx_hnsw_prod
  ON AIDOCUMENTCHUNK
  USING hnsw (embedding vector_cosine_ops)
  WITH (
    m = 16,               -- tăng lên 32 nếu recall < 95%
    ef_construction = 128 -- tăng = build chậm hơn nhưng graph tốt hơn
  );
SET hnsw.ef_search = 60;  -- tăng để recall tốt hơn (~5-10ms overhead)
```

### B.4 Query mẫu cho RAG retrieval

```sql
-- Top-20 chunks tương đồng nhất với query vector
-- (dùng EXPLAIN ANALYZE để verify index được sử dụng)

SET hnsw.ef_search = 60;

SELECT 
  adc.chunkId,
  adc.jobAppId,
  adc.sourceType,
  adc.content,
  adc.tokenCount,
  1 - (adc.embedding <=> $1::vector) AS cosine_similarity
FROM AIDOCUMENTCHUNK adc
WHERE adc.jobAppId = $2  -- filter theo jobApp nếu cần
ORDER BY adc.embedding <=> $1::vector
LIMIT 20;

-- Verify index usage:
EXPLAIN (ANALYZE, BUFFERS)
SELECT ... ORDER BY embedding <=> $1::vector LIMIT 20;
-- Kết quả nên thấy: "Index Scan using idx_hnsw_prod"
```

### B.5 Monitoring & Maintenance

```sql
-- Kiểm tra index size
SELECT pg_size_pretty(pg_relation_size('idx_aidocchunk_hnsw_cosine')) AS index_size;

-- Monitor query performance
SELECT query, calls, 
       ROUND((total_plan_time + total_exec_time) / calls) AS avg_ms
FROM pg_stat_statements
WHERE query LIKE '%vector%'
ORDER BY avg_ms DESC
LIMIT 10;

-- VACUUM định kỳ (đặc biệt sau migration hoặc nhiều DELETE)
VACUUM ANALYZE AIDOCUMENTCHUNK;

-- Nếu VACUUM chậm (HNSW indexes), reindex trước:
REINDEX INDEX CONCURRENTLY idx_aidocchunk_hnsw_cosine;
VACUUM AIDOCUMENTCHUNK;
```

---

## PHỤ LỤC C: IMPLEMENTATION CHECKLIST CHO AI CORE (FLASK)

### C.1 Cấu hình embedding client

```python
# config.py
EMBEDDING_CONFIG = {
    "dev": {
        "provider": "openai",
        "model": "text-embedding-3-small",
        "dimensions": 1024,
        "max_tokens_per_chunk": 300,
        "chunk_overlap": 50,
    },
    "prod": {
        "provider": "google",
        "model": "gemini-embedding-001",
        "dimensions": 768,
        "max_tokens_per_chunk": 250,  # safer dưới limit 2048
        "chunk_overlap": 50,
    }
}
```

### C.2 Chunking strategy cho CV

```python
import tiktoken

def chunk_cv_text(raw_text: str, max_tokens=300, overlap=50) -> list[str]:
    """Chunk CV text thành các đoạn có overlap."""
    enc = tiktoken.get_encoding("cl100k_base")  # OpenAI tokenizer
    tokens = enc.encode(raw_text)
    
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)
        chunks.append(chunk_text)
        start += (max_tokens - overlap)  # slide với overlap
    
    return chunks
```

### C.3 Hàm embed và lưu vào DB

```python
def embed_and_store_cv(job_app_id: int, raw_text: str, db_conn):
    chunks = chunk_cv_text(raw_text)
    
    # Batch embed
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=chunks,
        dimensions=1024
    )
    
    # Lưu vào AIDOCUMENTCHUNK
    with db_conn.cursor() as cur:
        for i, (chunk, emb_obj) in enumerate(zip(chunks, response.data)):
            cur.execute("""
                INSERT INTO AIDOCUMENTCHUNK 
                  (jobAppId, sourceType, content, chunkIndex, tokenCount, embedding)
                VALUES (%s, 'CV', %s, %s, %s, %s)
            """, (
                job_app_id, chunk, i,
                len(chunk.split()),  # approximate token count
                emb_obj.embedding
            ))
    db_conn.commit()
```

---

## TÓM TẮT EXECUTIVE

| | Quyết định |
|---|---|
| **Model DEV** | `text-embedding-3-small` |
| **Dimension DEV** | **1.024** (Matryoshka via `dimensions=1024`) |
| **Model PROD** | `gemini-embedding-001` |
| **Dimension PROD** | **768** (MRL via `output_dimensionality=768`) |
| **Index** | **HNSW** với `vector_cosine_ops` |
| **Metric** | **Cosine distance (`<=>`)** |
| **Chi phí 1K CV (DEV)** | ~$0.024 lưu trữ + ~$0.01/tháng query |
| **Chi phí 1K CV (PROD)** | ~$0.14 lưu trữ + ~$0.07/tháng query |
| **RAM index (1K CV, dim=1024)** | ~36 MB |
| **Chiến lược migration** | Lưu dim=1024 trước → 1 lần re-embed khi chuyển PROD |

> **Lý do chọn 1.024 cho DEV thay vì 1.536 (default):** Giảm 33% storage và RAM ngay từ đầu mà không đánh đổi recall đáng kể (~94% recall vs 100%), và khi cần upgrade PROD chỉ re-embed 1 lần — không phải 2 lần (1536→768).

---

*Báo cáo này dựa trên tài liệu: Sprint 1 DB Core, Sprint 1&2 Data Core, Bản kế hoạch Sprint 2 — miCareer-x-Fang.*

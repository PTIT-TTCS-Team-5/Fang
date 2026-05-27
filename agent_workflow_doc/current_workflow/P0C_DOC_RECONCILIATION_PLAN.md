# P0-C Documentation Reconciliation Plan

> **Ngày tạo**: 23/05/2026
> **Đầu vào**: P0-A Repo Reality Audit Report + User Notes, P0-B AI/LLM Inventory Report, FANG_NEXT_PHASE_DECISIONS, P0-A User Note Triage
> **Phương pháp**: Đọc toàn bộ `docs/strategy/`, `docs/guide/`, `README.md`, `docs/system_architecture.md`, `docs/testing_guide.md`, `agent_workflow_doc/` rồi đối chiếu với code reality + quyết định đã chốt
> **Mục tiêu**: Xác định truth source, phân loại drift, lập checklist thực thi cho tier 2

---

## 1. Documentation Truth-Source Map

Bảng dưới đây xác định file nào là nguồn chuẩn (canonical) cho từng chủ đề. Khi có mâu thuẫn giữa các tài liệu, truth source được chọn dựa trên code reality + quyết định đã chốt của user trong P0-A.

| Chủ đề | Truth Source | Ghi chú |
|---|---|---|
| Kiến trúc tổng thể FANG | Code runtime (`app/main.py`, `app/api/`, `app/services/`) + `docs/system_architecture.md` | `system_architecture.md` đã tương đối chính xác, ít drift |
| NMAIex boundary/status | **Code** (`app/main.py` mount NMAIex routers) + quyết định user: NMAIex là module chính thức của FANG | Mọi docs gọi NMAIex là "extension tách biệt" phải sửa |
| Embedding provider/model/dims | **Code** (`app/services/embedding.py`, `app/core/config.py`): Gemini `gemini-embedding-001`, mặc định 1536 dims | Rất nhiều docs/guide vẫn nói OpenAI `text-embedding-3-small` 1024 dims — phải sửa hết |
| CV Parser architecture | **Code** (`app/services/cv_parser.py`): 5-tier fallback + ProTierGate | `docs/guide/cv_parser_guide.md` đã chính xác |
| Generation/RAG architecture | **Code** (`app/services/rag_model_adapters.py`, `rag_orchestrator.py`): 7 modelMode, auto-lite/auto-pro chains, **không có** Lite-to-Pro escalation | README và một số strategy docs nhầm generation cũng dùng 5-tier + ProTierGate |
| RAG chat context hiện tại | **Code** (`app/services/rag_query.py`): top-k vector search trên `AIDOCUMENTCHUNK` | Quyết định chuyển sang full CV markdown đã chốt nhưng **chưa implement** — docs nên ghi rõ trạng thái này |
| NMAIex ranking scoring | **Code** (`app/services/nmaiex_ranking_service.py`): raw score mặc định, không clip (`NMAIEX_ENABLE_SCORE_CLIP=false`) | `nmaiex_ranking_strategy.md` và `nmaiex_ranking_guide.md` đã đúng |
| NMAIex management route | **Code** + quyết định user: canonical là `/v2/nmaiex/management/jobs/{id}/content` | Chưa có docs nào ghi route management — cần bổ sung |
| NMAIex enrichment lifecycle | **Code** (commit `b8d0544`): sidecar enrichment tách khỏi ingestion chính, có bảng trạng thái riêng | Chưa có docs nào phản ánh — cần bổ sung |
| Ingestion pipeline | **Code** (`app/api/routes_ingestion.py`): `download_cv` → parse → validate → markdown → chunk → embed → save | `docs/strategy/integration_strategy.md` mô tả đúng flow nhưng thiếu NMAIex sidecar |
| Context budget | **Code** (`app/services/rag_query.py`): group Lite 180k / Pro 960k, trả warning nhưng **vẫn gọi LLM** | `docs/strategy/rag_query_strategy.md` nói per-model budget và recommend không gọi LLM khi vượt ngưỡng — drift D2, thuộc phần việc CHAT_FULL_CV + P1_A_B_inc |
| Chunking | **Code** (`app/services/chunking.py`): deterministic, zero-LLM-cost | `docs/strategy/chunking_strategy.md` và `docs/guide/chunking_guide.md` đã chính xác |
| Testing | **Code** (`tests/unit/`): 5 file, 29 tests pass (sau fix) | `docs/testing_guide.md` đã cập nhật đúng theo tier 2 task |
| API contract | **Code** (`app/api/routes_*.py`) | `docs/strategy/integration_strategy.md` có một số drift nhỏ (path `/v1/` thay vì `/v2/`) |
| Agent workflow coordination | `agent_workflow_doc/FANG_NEXT_PHASE_DECISIONS.md` | Là decision source hiện tại; các NEXT_PHASE spec khác là input/output của từng pha |
| Prompt inventory | `agent_workflow_doc/P0B_AI_LLM_INVENTORY_REPORT.md` | Nguồn chuẩn cho toàn bộ prompt/model/fallback/use case |

---

## 2. Drift Register

Mỗi drift được phân loại theo 5 class đã định nghĩa trong P0-C spec:
- **D1**: Code là reality, docs cũ → sửa docs theo code hoặc đánh dấu legacy
- **D2**: Docs là quyết định đã chốt nhưng code chưa kịp theo → giữ docs, tạo work package
- **D3**: Docs và code đều cũ vì user vừa đổi quyết định → viết decision/update plan trước
- **D4**: Hai docs mâu thuẫn nhau → chọn truth source hoặc archive/merge
- **D5**: Docs nói có test/file/flow nhưng repo không có → sửa docs và/hoặc tạo test gap work package

### DR-01: NMAIex vẫn được gọi là "extension" thay vì "module chính thức"

| Field | Giá trị |
|---|---|
| **Class** | D1 |
| **Impact** | Trung bình — gây hiểu nhầm về architecture boundary, ảnh hưởng onboarding và phân chia responsibility |
| **Quyết định đã chốt** | NMAIex là module chính thức của FANG. Giữ tên gọi NMAIex để dễ phân biệt. |
| **File bị ảnh hưởng** | `README.md` (L90), `docs/strategy/README.md` (L25), `docs/strategy/nmaiex_ranking_strategy.md` (L3), `agent_workflow_doc/AI_WORKFLOW_INIT.md` (L4) |
| **Hướng xử lý** | Sửa docs: thay "extension" bằng "module" hoặc cụm từ tương đương. `AI_WORKFLOW_INIT.md` cần update tổng thể (xem DR-10). |

---

### DR-02: Embedding provider/model/dims — OpenAI 1024 thay vì Gemini 1536

| Field | Giá trị |
|---|---|
| **Class** | D1 |
| **Impact** | **Nghiêm trọng** — đây là drift lan rộng nhất, ảnh hưởng đến onboarding, troubleshooting, và hiểu biết về hệ thống |
| **Code reality** | `app/services/embedding.py` + `app/core/config.py`: Gemini `gemini-embedding-001`, mặc định `embedding_dim=1536`. NMAIex skill embedding dùng 256 dims. |
| **Quyết định đã chốt** | Sửa docs theo code. |
| **File bị ảnh hưởng** | |

| File | Dòng | Vấn đề cụ thể |
|---|---|---|
| `docs/strategy/embedding_strategy.md` | L17-19, L21, L76 | Nói "Provider: OpenAI", "Model: text-embedding-3-small", "Dimension: 1024", "halfvec(1024)" |
| `docs/strategy/rag_query_strategy.md` | L437 | "vector 1024d" |
| `docs/guide/embedding_guide.md` | L4, L12, L19, L35-36, L44-46, L60, L97, L157 | Toàn bộ file nói OpenAI, text-embedding-3-small, 1024 dims |
| `docs/guide/database_guide.md` | L25 | "halfvec(1024)... text-embedding-3-small" |
| `docs/guide/input_processing_guide.md` | L8, L24 | "1024 chiều", "OpenAI text-embedding-3-small dimensions=1024" |
| `docs/guide/rag_query_guide.md` | L10 | "1024-dim" |

| **Đã đúng** | `docs/testing_guide.md` (L22, L55, L89), `docs/strategy/nmaiex_ranking_strategy.md` (L166, L183), `docs/strategy/chunking_strategy.md` (L95) |
| **Hướng xử lý** | Tier 2 sửa tất cả file bị ảnh hưởng: thay OpenAI → Gemini, text-embedding-3-small → gemini-embedding-001, 1024 → 1536 (hoặc configurable với mặc định 1536). Giữ nguyên các file đã đúng. |

---

### DR-03: README và integration_strategy nói Generator cũng dùng 5-tier + ProTierGate

| Field | Giá trị |
|---|---|
| **Class** | D1 |
| **Impact** | Cao — gây hiểu nhầm về cost/fallback behavior của generation |
| **Code reality** | Parser: 5-tier fallback + ProTierGate. Generation: 7 modelMode (auto-lite, auto-pro, 5 specific modes), **không có** Lite-to-Pro escalation. |
| **Quyết định đã chốt** | Sửa docs theo code. |
| **File bị ảnh hưởng** | |

| File | Dòng | Vấn đề cụ thể |
|---|---|---|
| `README.md` | L38-39 | "Cả Parser và Generator đều sử dụng chung một cơ chế 5-Tier Fallback với ProTierGate" |
| `docs/strategy/integration_strategy.md` | L26-27 | "5-tier model invocation + fallback" — ngụ ý generation cũng dùng 5-tier |

| **Đã đúng** | `docs/strategy/rag_query_strategy.md` Section 4-5 (mô tả đúng 7 modelMode, ProTierGate chỉ parser), `docs/guide/cv_parser_guide.md` |
| **Hướng xử lý** | Sửa README tách rõ: Parser dùng 5-tier + ProTierGate; Generation dùng 7 modelMode với auto-lite/auto-pro chains. Sửa `integration_strategy.md` tương tự. |

---

### DR-04: GPT model naming không nhất quán trong rag_query_strategy.md

| Field | Giá trị |
|---|---|
| **Class** | D4 (mâu thuẫn nội tại trong cùng một docs) |
| **Impact** | Thấp-Trung bình — gây nhầm lẫn khi đọc strategy |
| **Vấn đề** | Trong `docs/strategy/rag_query_strategy.md`: L48 (Tier 5 = `gpt-5.5`), L87 (`gpt-full` maps to "GPT-5.4"), L96 (auto-pro nói "GPT 5.4"), L324-327 (context budget bảng nói "GPT-5.5 mini") |
| **Truth source** | P0-B inventory: `gpt-full` = `gpt-5.5 → gpt-5.4 → gpt-5.4-pro` (intra-provider fallback) |
| **Hướng xử lý** | Tier 2 thống nhất model naming theo P0-B inventory report. |

---

### DR-05: Docs chưa phản ánh NMAIex enrichment sidecar architecture

| Field | Giá trị |
|---|---|
| **Class** | D1 |
| **Impact** | Cao — docs ngụ ý ingestion monolithic, không phản ánh sidecar enrichment riêng biệt đã implement (commit `b8d0544`) |
| **Code reality** | `AIINDEXJOB.SUCCESS` chỉ đại diện pipeline ingestion chính (parse → chunk → embed → save). NMAIex enrichment (skill mapping, expyears, province mapping) chạy riêng với bảng trạng thái riêng, retry/backfill script riêng, fail không chặn chat/RAG. |
| **File bị ảnh hưởng** | `docs/strategy/integration_strategy.md` (L190 — chỉ có PENDING/PROCESSING/SUCCESS/FAILED), `README.md` (L23 — ngụ ý status đơn) |
| **File chưa ghi** | Không có docs nào mô tả enrichment sidecar lifecycle |
| **Hướng xử lý** | Bổ sung mô tả enrichment sidecar vào `integration_strategy.md` và README. Ghi rõ `AIINDEXJOB.SUCCESS` chỉ cho ingestion chính; enrichment có status/retry riêng. |

---

### DR-06: NMAIex management route chưa được document

| Field | Giá trị |
|---|---|
| **Class** | D5 (docs không nói có route management nhưng code có) |
| **Impact** | Trung bình — frontend/client không biết canonical route nào để gọi |
| **Quyết định đã chốt** | Canonical là `/v2/nmaiex/management/jobs/{id}/content`. Route root `/v2/nmaiex/jobs/{id}/content` cần align hoặc deprecate. |
| **File bị ảnh hưởng** | `docs/strategy/nmaiex_ranking_strategy.md` (L350-358 — chỉ list ranking/master endpoints), `docs/guide/nmaiex_ranking_guide.md` (L248-254 — tương tự) |
| **Hướng xử lý** | Bổ sung API management endpoints vào strategy và guide. Ghi rõ canonical route. |

---

### DR-07: integration_strategy.md dùng sai API path `/v1/`

| Field | Giá trị |
|---|---|
| **Class** | D1 |
| **Impact** | Thấp — gây nhầm lẫn nhưng không ảnh hưởng runtime |
| **Vấn đề** | `docs/strategy/integration_strategy.md` L39: dùng `GET /v1/ingestion/jobs/{id}` thay vì `/v2/` |
| **Code reality** | Primary prefix là `/v2/`; `/v1/` vẫn backward-compatible nhưng `/v2/` là canonical |
| **Hướng xử lý** | Sửa thành `/v2/`. |

---

### DR-08: Docs chưa ghi nhận quyết định chuyển JobApplication chat sang full CV markdown

| Field | Giá trị |
|---|---|
| **Class** | D2 (quyết định đã chốt, code/docs chưa theo) |
| **Impact** | Trung bình — docs hiện tại ngụ ý top-k RAG là thiết kế lâu dài |
| **Quyết định đã chốt** | JobApplication chat sẽ dùng full CV markdown context thay vì fixed chunk-RAG. Implementation sẽ có work package riêng (CHAT_FULL_CV). |
| **File bị ảnh hưởng** | `docs/guide/rag_query_guide.md` (L54 — chỉ mô tả current state), `docs/strategy/rag_query_strategy.md` (L214-217 — top-k only) |
| **Hướng xử lý** | **Không sửa content chi tiết** (vì code chưa đổi). Thêm một note/section ngắn trong strategy và guide ghi rõ: "Quyết định đã chốt: chuyển sang full CV markdown. Xem `FANG_NEXT_PHASE_DECISIONS.md`. Tài liệu chi tiết sẽ cập nhật khi implementation hoàn tất." |

---

### DR-09: Context budget behavior — docs mô tả khác code

| Field | Giá trị |
|---|---|
| **Class** | D2 |
| **Impact** | Trung bình — thuộc phần việc CHAT_FULL_CV + P1_A_B_inc |
| **Vấn đề** | `docs/strategy/rag_query_strategy.md` nói per-model budget và recommend không gọi LLM khi vượt ngưỡng. Code thì dùng group Lite/Pro budget và vẫn gọi LLM + trả warning. |
| **Hướng xử lý** | **Không sửa trong P0-C**. Ghi note trong docs: behavior hiện tại là group budget + warning-only. Per-model budget và stop-at-threshold thuộc CHAT_FULL_CV + P1_A_B_inc work package. |

---

### DR-10: `AI_WORKFLOW_INIT.md` stale — NMAIex "đang nghiên cứu" + chỉ đọc research docs

| Field | Giá trị |
|---|---|
| **Class** | D1 |
| **Impact** | Trung bình — gây hiểu nhầm cho agent mới khi init context |
| **Vấn đề** | L4: "NMAIex - đang nghiên cứu". L25-27: chỉ dẫn đọc `docs/research/` cho NMAIex. Thực tế NMAIex đã implement xong và là module chính thức. |
| **Hướng xử lý** | Update: NMAIex là module chính thức, đã implement. Bỏ hoặc giảm hướng dẫn đọc research docs cho NMAIex. Giữ research docs như tham khảo nền, không phải mandatory reading. |

---

### DR-11: `rag_query_strategy.md` và `rag_query_guide.md` — multi-source context rộng hơn code thực tế

| Field | Giá trị |
|---|---|
| **Class** | D2 |
| **Impact** | Trung bình — thuộc phần việc CHAT_FULL_CV + P1_A_B_inc |
| **Vấn đề** | Strategy mô tả context gồm job requirements/salary/work mode/level, candidate skills, offers, emails. Code chỉ fetch job title/description, candidate basic fields, interview feedback. |
| **Hướng xử lý** | **Không sửa content trong P0-C.** Thêm note: "Các nguồn context bổ sung (skills, offers, emails) thuộc phần việc CHAT_FULL_CV và P1_A_B_inc. Code hiện tại chỉ fetch: job title/description, candidate basic fields, interview feedback." |

---

### DR-12: Agent workflow doc files cần archive

| Field | Giá trị |
|---|---|
| **Class** | D1 |
| **Impact** | Thấp — gây nhầm lẫn giữa tài liệu historical và active |
| **Quyết định P0-A** | `[NMAIex]_TASK_CHECKLIST_BACKEND.md`, `[NMAIex]_TASK_CHECKLIST_FRONTEND.md`, `[NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md`, `[NMAIex]_DOC_UPDATE_INSTRUCTIONS.md` → chuyển vào `agent_workflow_doc/archive/`. |
| **Vấn đề thêm** | Các file này chứa thông tin conflict với quyết định mới (clip score, OpenAI embedding, NMAIex extension) nhưng vì là historical nên chỉ cần archive, không cần sửa content. |
| **Hướng xử lý** | Di chuyển vào `agent_workflow_doc/archive/`. |

---

### DR-13: `KINH_NGHIEM.md` tham chiếu file sẽ bị archive

| Field | Giá trị |
|---|---|
| **Class** | D1 |
| **Impact** | Thấp |
| **Vấn đề** | L38 tham chiếu `[NMAIex]_TASK_CHECKLIST_BACKEND.md` và `[NMAIex]_TASK_CHECKLIST_FRONTEND.md` trong phần "prompt mồi". Hai file này sẽ bị archive. |
| **Hướng xử lý** | Cập nhật tham chiếu: ghi rõ các checklist đã archive, thay bằng tham chiếu tới `P0B_AI_LLM_INVENTORY_REPORT.md` và `FANG_NEXT_PHASE_DECISIONS.md` nếu cần context NMAIex. |

---

### DR-14: `docs/strategy/embedding_strategy.md` — cần viết lại phần lớn

| Field | Giá trị |
|---|---|
| **Class** | D1 |
| **Impact** | Nghiêm trọng — file này là strategy chính cho embedding nhưng sai gần như toàn bộ provider/model/dims |
| **Vấn đề** | Toàn bộ file viết cho OpenAI `text-embedding-3-small` 1024 dims. Bao gồm cả phần storage strategy (`halfvec(1024)`), migration path, fallback consideration. |
| **Hướng xử lý** | **Lưu bản cũ vào `docs/archive/`** trước khi viết lại. Viết lại toàn bộ theo Gemini `gemini-embedding-001`, 1536 dims mặc định, 256 dims cho NMAIex skill embedding. Giữ lại structure/format gốc, chỉ thay nội dung sai. |

---

### DR-15: `docs/guide/embedding_guide.md` — cần viết lại phần lớn

| Field | Giá trị |
|---|---|
| **Class** | D1 |
| **Impact** | Nghiêm trọng — tương tự DR-14, guide thực thi cũng sai toàn bộ provider/model |
| **Hướng xử lý** | **Lưu bản cũ vào `docs/archive/`** trước khi viết lại. Viết lại theo code reality: Gemini SDK, `embed_chunks()`, native dims, batch_size cấu hình. Tham chiếu P0-B UC-2 để đảm bảo consistency. |

---

## 3. Tier-2 Execution Checklist

> **Quy tắc chung cho tier 2:**
> - Không đổi kiến trúc hoặc behavior code.
> - Không sửa file ngoài checklist.
> - Khi gặp conflict mới chưa có trong drift register, ghi lại và dừng mục đó.
> - Khi thay thế nội dung lớn trong docs/strategy hoặc docs/guide, lưu bản cũ vào `docs/archive/` trước.
> - Viết bằng tiếng Việt, giữ thuật ngữ chuyên ngành/kỹ thuật bằng tiếng Anh.

---

### T2-01: Sửa NMAIex "extension" → "module chính thức" (DR-01)

**Files cần sửa:**

| File | Hành động |
|---|---|
| `README.md` L90 | Thay "NMAIex Extension" → "NMAIex Module" hoặc "NMAIex (Nhập môn AI module, tích hợp chính thức trong FANG)". Giữ tên gọi NMAIex. |
| `docs/strategy/README.md` L25 | Thay "NMAI extension" → "NMAIex module" |
| `docs/strategy/nmaiex_ranking_strategy.md` L3 | Thay "NMAIex (Nhập môn AI extension)" → "NMAIex (Nhập môn AI module — tích hợp chính thức trong FANG)" |

**Không được đụng:**
- Nội dung kỹ thuật ranking/scoring/mapper. Chỉ thay đổi wording boundary.
- Các file `agent_workflow_doc/` historical (sẽ archive thay vì sửa).

**Acceptance criteria:**
- Không còn từ "extension" hay "tách biệt khỏi TTCS" khi nói về NMAIex trong các file active docs.
- Tên gọi "NMAIex" vẫn được giữ nguyên.

---

### T2-02: Sửa embedding provider/model/dims (DR-02, DR-14, DR-15)

**Bước 1 — Archive bản cũ:**

```
docs/strategy/embedding_strategy.md → docs/archive/embedding_strategy_openai_legacy.md
docs/guide/embedding_guide.md → docs/archive/embedding_guide_openai_legacy.md
```

**Bước 2 — Viết lại `docs/strategy/embedding_strategy.md`:**

Nội dung mới phải phản ánh:
- **Provider**: Google (Gemini)
- **Model**: `gemini-embedding-001`
- **Dimension mặc định**: 1536 (cấu hình qua `EMBEDDING_DIM` trong `.env`)
- **NMAIex skill embedding**: 256 dims (cấu hình qua `NMAIEX_SKILL_EMBEDDING_DIM`)
- **Storage**: `halfvec` trong pgvector (`halfvec(1536)` cho document chunks, `vector(256)` cho skill embedding)
- **Batch size**: 32 (cấu hình qua `EMBEDDING_BATCH_SIZE`)
- **Fallback**: Không có fallback provider — chỉ Gemini
- **Retry**: Không có retry ở layer embedding (risk đã ghi nhận trong P0-B F2)
- **Matryoshka-compatible truncation**: Hỗ trợ qua `output_dimensionality`
- Giữ lại phần structure/format gốc nếu phù hợp, chỉ thay nội dung sai

Tham chiếu khi viết: P0-B UC-2, `app/services/embedding.py`, `app/core/config.py`

**Bước 3 — Viết lại `docs/guide/embedding_guide.md`:**

Nội dung mới phải phản ánh:
- Entry point: `embedding.py:embed_chunks()`
- SDK: `google.genai` (không phải `AsyncOpenAI`)
- Config vars: `GOOGLE_API_KEY`, `EMBEDDING_DIM=1536`, `EMBEDDING_BATCH_SIZE=32`
- Validation: 5 bước kiểm tra (theo P0-B UC-2)
- I/O contract: `List[str]` → `List[List[float]]`
- Persistence: `_serialize_embedding()` trong `persistence.py`
- Test: `unit_test_embedding.py` mock `FakeGeminiClient` (đã fix)
- Common errors: cập nhật theo Gemini errors thay vì OpenAI

Tham chiếu khi viết: P0-B UC-2, `app/services/embedding.py`, `tests/unit/unit_test_embedding.py`

**Bước 4 — Sửa các file khác chứa drift embedding:**

| File | Dòng | Sửa thành |
|---|---|---|
| `docs/strategy/rag_query_strategy.md` | L437 | "vector 1024d" → "vector 1536d" |
| `docs/guide/database_guide.md` | L25 | "halfvec(1024)... text-embedding-3-small" → "halfvec(1536)... gemini-embedding-001" |
| `docs/guide/input_processing_guide.md` | L8 | "1024 chiều" → "1536 chiều" |
| `docs/guide/input_processing_guide.md` | L24 | "OpenAI text-embedding-3-small với dimensions=1024" → "Gemini gemini-embedding-001 với dimensions=1536 (mặc định)" |
| `docs/guide/rag_query_guide.md` | L10 | "1024-dim" → "1536-dim" |

**Không được đụng:**
- `docs/testing_guide.md` — đã đúng
- `docs/strategy/chunking_strategy.md` — đã đúng (L95 nói 1536)
- `docs/strategy/nmaiex_ranking_strategy.md` — đã đúng (L166, L183)
- `docs/guide/nmaiex_ranking_guide.md` — đã đúng
- Code files — không sửa code trong P0-C

**Acceptance criteria:**
- `grep -r "text-embedding-3-small" docs/` trả về 0 kết quả trong file active (archive không tính).
- `grep -r "1024" docs/strategy/ docs/guide/` không còn chỉ embedding dims (có thể vẫn xuất hiện cho context khác).
- Nội dung mới khớp P0-B UC-2.

---

### T2-03: Sửa README và integration_strategy — Generator architecture (DR-03)

**Files cần sửa:**

| File | Hành động |
|---|---|
| `README.md` L38-39 | Tách phần "5-Tier LLM Architecture" thành hai subsection: (1) **CV Parser**: 5-tier fallback + ProTierGate, (2) **RAG Generation**: 7 modelMode (auto-lite, auto-pro, 5 specific modes). Bỏ câu "Cả Parser và Generator đều sử dụng chung". |
| `docs/strategy/integration_strategy.md` L26-27 | Sửa "5-tier model invocation + fallback" → ghi rõ: Parser dùng 5-tier + ProTierGate; Generation dùng 7 modelMode. |

**Tham chiếu khi sửa:** P0-B Appendix A (Model/Fallback Map), `app/services/cv_parser.py`, `app/services/rag_model_adapters.py`

**Không được đụng:**
- `docs/strategy/rag_query_strategy.md` Section 4-5 — đã mô tả đúng 7 modelMode
- `docs/guide/cv_parser_guide.md` — đã đúng

**Acceptance criteria:**
- README không còn nói Parser và Generator dùng chung cơ chế.
- integration_strategy phân biệt rõ parser vs generation architecture.

---

### T2-04: Thống nhất GPT model naming trong rag_query_strategy.md (DR-04)

**File cần sửa:** `docs/strategy/rag_query_strategy.md`

**Hành động:** Thống nhất tất cả model naming theo P0-B Appendix A:

| ModelMode | Model chính | Candidates (intra-provider fallback) |
|---|---|---|
| `gpt-mini` / `gpt-5.4-mini` | `gpt-5.4-mini` | `gpt-5.4-mini → gpt-5-mini` |
| `gpt-full` / `gpt-5.5` | `gpt-5.5` | `gpt-5.5 → gpt-5.4 → gpt-5.4-pro` |
| auto-pro chain | | `gemini-pro → gpt-5.5` |

Sửa tất cả chỗ nói "GPT-5.4" khi ý nghĩa là `gpt-full` thành "GPT-5.5 (gpt-5.5)".
Sửa bảng context budget ở L324-327 cho nhất quán.

**Acceptance criteria:**
- Không còn mâu thuẫn model naming nội tại trong file.

---

### T2-05: Sửa API path `/v1/` trong integration_strategy (DR-07)

**File cần sửa:** `docs/strategy/integration_strategy.md` L39

**Hành động:** Sửa `GET /v1/ingestion/jobs/{id}` → `GET /v2/ingestion/jobs/{id}`. Ghi note nếu cần: `/v1/` vẫn backward-compatible nhưng `/v2/` là canonical.

**Acceptance criteria:**
- integration_strategy dùng `/v2/` path.

---

### T2-06: Bổ sung NMAIex enrichment sidecar vào docs (DR-05)

**Files cần sửa:**

| File | Hành động |
|---|---|
| `docs/strategy/integration_strategy.md` | Thêm section hoặc subsection mới mô tả enrichment sidecar lifecycle: (1) Ingestion chính: parse → chunk → embed → save → `AIINDEXJOB.SUCCESS`. (2) NMAIex enrichment: chạy riêng, có bảng trạng thái riêng, fail không chặn chat/RAG, có retry/backfill script. |
| `README.md` | Cập nhật mô tả ingestion pipeline: ghi rõ NMAIex enrichment chạy sidecar sau ingestion chính. |

**Tham chiếu khi sửa:** P0-A triage Section 4 (NMAIex post-ingestion semantics: Done), walkthrough_full_system_test.md, `app/api/routes_ingestion.py`, `app/services/nmaiex_candidate_enrichment.py`

**Không được đụng:**
- Code files
- `docs/strategy/nmaiex_ranking_strategy.md` — vì ranking pipeline không liên quan enrichment lifecycle

**Acceptance criteria:**
- Docs mô tả rõ: `AIINDEXJOB.SUCCESS` chỉ cho ingestion chính; NMAIex enrichment có status riêng.
- Ghi rõ fail enrichment không chặn chat.

---

### T2-07: Bổ sung NMAIex management route vào docs (DR-06)

**Files cần sửa:**

| File | Hành động |
|---|---|
| `docs/strategy/nmaiex_ranking_strategy.md` | Thêm API management endpoints vào bảng endpoint (gần L350-358). Ghi rõ canonical route `/v2/nmaiex/management/jobs/{id}/content` cho job content update/re-ingestion. |
| `docs/guide/nmaiex_ranking_guide.md` | Thêm tương tự (gần L248-254). |

**Tham chiếu khi sửa:** `app/api/nmaiex_routes_management.py`

**Acceptance criteria:**
- Route management canonical `/v2/nmaiex/management/jobs/{id}/content` được ghi rõ trong docs.

---

### T2-08: Thêm note quyết định full CV markdown vào RAG docs (DR-08)

**Files cần sửa:**

| File | Hành động |
|---|---|
| `docs/strategy/rag_query_strategy.md` | Thêm một alert/note ở đầu hoặc cuối section liên quan: "⚠️ **Quyết định đã chốt:** JobApplication chat sẽ chuyển từ fixed chunk-RAG sang full CV markdown context. Xem `agent_workflow_doc/FANG_NEXT_PHASE_DECISIONS.md`. Code và tài liệu chi tiết sẽ cập nhật khi implementation hoàn tất (work package CHAT_FULL_CV)." |
| `docs/guide/rag_query_guide.md` | Thêm note tương tự ở đầu hoặc gần L54. |

**Không được đụng:**
- Nội dung chi tiết mô tả pipeline hiện tại — vẫn chính xác cho code hiện tại.
- Không viết hướng dẫn chi tiết cho full CV vì chưa implement.

**Acceptance criteria:**
- Reader biết pipeline hiện tại sẽ thay đổi và ở đâu tìm thêm thông tin.
- Nội dung mô tả pipeline hiện tại vẫn chính xác.

---

### T2-09: Thêm note về context budget behavior hiện tại (DR-09)

**Files cần sửa:**

| File | Hành động |
|---|---|
| `docs/strategy/rag_query_strategy.md` | Gần phần context budget, thêm note: "⚠️ **Trạng thái hiện tại:** Code dùng group budget (Lite 180k, Pro 960k) và vẫn gọi LLM khi vượt ngưỡng, chỉ trả `contextWarning`. Per-model budget và stop-at-threshold behavior thuộc phần việc CHAT_FULL_CV + P1_A_B_inc." |

**Không được đụng:**
- Phần recommend/strategy gốc — giữ nguyên như là target design.

**Acceptance criteria:**
- Reader phân biệt được behavior hiện tại vs behavior mong muốn.

---

### T2-10: Update `AI_WORKFLOW_INIT.md` (DR-10)

**File cần sửa:** `agent_workflow_doc/AI_WORKFLOW_INIT.md`

**Hành động:**
1. L4: Sửa "NMAIex - đang nghiên cứu" → "NMAIex — module chính thức của FANG, đã implement"
2. L20: Update note cho nhất quán
3. L25-27: Bỏ hoặc giảm hướng dẫn bắt buộc đọc research docs cho NMAIex. Thay bằng: "NMAIex đã implement; context chính nằm trong `docs/strategy/nmaiex_ranking_strategy.md`, `docs/guide/nmaiex_ranking_guide.md` và `P0B_AI_LLM_INVENTORY_REPORT.md`. Research docs (`docs/research/`) là tham khảo nền, không phải mandatory reading."

**Không được đụng:**
- Phần hướng dẫn chung về workflow (vẫn hữu ích)
- Các tham chiếu tới `docs/strategy` và `docs/guide` (đã đúng)

**Acceptance criteria:**
- File không còn mô tả NMAIex là "đang nghiên cứu".
- Agent mới init context không bị dẫn vào research docs dài mà không cần thiết.

---

### T2-11: Archive agent_workflow_doc historical files (DR-12)

**Files cần di chuyển vào `agent_workflow_doc/archive/`:**

```
[NMAIex]_TASK_CHECKLIST_BACKEND.md    → archive/[NMAIex]_TASK_CHECKLIST_BACKEND.md
[NMAIex]_TASK_CHECKLIST_FRONTEND.md   → archive/[NMAIex]_TASK_CHECKLIST_FRONTEND.md
[NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md → archive/[NMAIex]_DETAILED_IMPLEMENTATION_PLAN.md
[NMAIex]_DOC_UPDATE_INSTRUCTIONS.md   → archive/[NMAIex]_DOC_UPDATE_INSTRUCTIONS.md
```

**Hành động bổ sung:**
- Cập nhật `agent_workflow_doc/archive/README.md` thêm 4 file mới vào danh sách.
- Cập nhật `KINH_NGHIEM.md` (DR-13): sửa tham chiếu tới checklist đã archive.

**Không được đụng:**
- Nội dung các file đó — chỉ di chuyển, không sửa content (vì là historical).
- `[NMAIex]_PROVINCE_MERGER_GUIDE.md` — vẫn là active reference data, giữ nguyên.

**Acceptance criteria:**
- 4 file nằm trong `agent_workflow_doc/archive/`.
- `archive/README.md` liệt kê đầy đủ.
- `KINH_NGHIEM.md` tham chiếu chính xác.

---

### T2-12: Thêm note về multi-source context gap (DR-11)

**Files cần sửa:**

| File | Hành động |
|---|---|
| `docs/strategy/rag_query_strategy.md` | Gần phần mô tả multi-source context, thêm note: "⚠️ **Trạng thái hiện tại:** Code chỉ fetch: job title/description, candidate basic fields (tên/email/phone/bio/expyears/location), interview feedback. Các nguồn bổ sung (skills, salary/work mode/level, offers, emails) thuộc phần việc CHAT_FULL_CV và P1_A_B_inc." |
| `docs/guide/rag_query_guide.md` | Thêm note tương tự. |

**Acceptance criteria:**
- Reader biết context nào thực sự có trong prompt hiện tại vs kế hoạch mở rộng.

---

## 4. Review Checklist (Tier 1)

Sau khi tier 2 hoàn tất, tier 1 dùng checklist dưới đây để kiểm tra.

### 4.1 Kiểm tra tổng thể

- [ ] `grep -ri "extension" README.md docs/strategy/ docs/guide/` — không còn gọi NMAIex là "extension" trong context active docs
- [ ] `grep -ri "text-embedding-3-small" docs/strategy/ docs/guide/` — trả về 0 kết quả (chỉ archive mới có)
- [ ] `grep -ri "openai" docs/strategy/embedding_strategy.md docs/guide/embedding_guide.md` — trả về 0 kết quả (files đã viết lại cho Gemini)
- [ ] `grep -r "1024" docs/strategy/ docs/guide/` — không còn chỉ embedding dims
- [ ] `grep -r "đang nghiên cứu" agent_workflow_doc/AI_WORKFLOW_INIT.md` — trả về 0 kết quả
- [ ] README section "5-Tier LLM Architecture" — tách rõ parser vs generation

### 4.2 Kiểm tra từng drift resolution

| DR | Kiểm tra | Cách verify |
|---|---|---|
| DR-01 | NMAIex gọi đúng "module" | Đọc 3 file đã sửa |
| DR-02 | Embedding docs đúng Gemini 1536 | Đọc `embedding_strategy.md`, `embedding_guide.md` mới; spot-check 5 file khác |
| DR-03 | Parser vs Generation tách rõ | Đọc README L38-39, integration_strategy L26-27 |
| DR-04 | GPT naming nhất quán | Đọc `rag_query_strategy.md` — ctrl+f "GPT" |
| DR-05 | Enrichment sidecar documented | Đọc integration_strategy section mới + README |
| DR-06 | Management route documented | Đọc nmaiex_ranking_strategy.md + nmaiex_ranking_guide.md endpoint tables |
| DR-07 | API path `/v2/` | Đọc integration_strategy L39 |
| DR-08 | Full CV markdown note | Đọc rag_query_strategy.md + rag_query_guide.md — có note quyết định |
| DR-09 | Context budget note | Đọc rag_query_strategy.md — có note trạng thái hiện tại |
| DR-10 | AI_WORKFLOW_INIT updated | Đọc file — NMAIex không còn "đang nghiên cứu" |
| DR-11 | Archive done | Xác nhận 4 file nằm trong archive, archive/README.md cập nhật |
| DR-12 | Multi-source context note | Đọc 2 file — có note context gap |
| DR-13 | KINH_NGHIEM tham chiếu đúng | Kiểm tra tham chiếu không trỏ tới file đã archive |

### 4.3 Kiểm tra không tạo drift mới

- [ ] Nội dung mô tả pipeline hiện tại (top-k RAG, ingestion flow) vẫn chính xác
- [ ] Không có docs nói full CV markdown đã implement (chưa implement)
- [ ] Không có docs sửa behavior code
- [ ] Các file archive có bản cũ đầy đủ (embedding_strategy, embedding_guide)
- [ ] Không sửa `docs/testing_guide.md`, `docs/strategy/chunking_strategy.md`, `docs/guide/cv_parser_guide.md`, `docs/guide/nmaiex_ranking_guide.md` (đã đúng — chỉ bổ sung management route cho nmaiex guide)

### 4.4 Kiểm tra formatting/link

- [ ] Tất cả internal links trong docs mới vẫn valid
- [ ] Không có file reference trỏ tới file không tồn tại
- [ ] Markdown render đúng (headings, tables, alerts)

---

## 5. Tóm tắt phạm vi "Không đụng" trong P0-C

Các file và nội dung sau đây **KHÔNG ĐƯỢC SỬA** trong P0-C:

| Category | Files/Content | Lý do |
|---|---|---|
| Code files | Tất cả `app/`, `tests/`, `scripts/`, `database/` | P0-C chỉ sửa docs |
| Docs đã đúng | `docs/testing_guide.md`, `docs/strategy/chunking_strategy.md`, `docs/guide/chunking_guide.md`, `docs/guide/cv_parser_guide.md`, `docs/system_architecture.md` | Không có drift |
| Nội dung CHAT_FULL_CV | Chi tiết pipeline full CV markdown, prompt mới cho full CV | Thuộc work package CHAT_FULL_CV |
| Nội dung P1_A_B_inc | Per-model budget, prompt rewrite, eval rubric | Thuộc work package P1-A/P1-B |
| Research docs | `docs/research/*` | Không phải runtime truth, chỉ tham khảo |
| Historical archived files | Content trong `agent_workflow_doc/archive/` | Giữ lịch sử, không sửa |
| `FANG_NEXT_PHASE_DECISIONS.md` | Decision source hiện tại | Chỉ đọc, không edit |
| NMAIex ranking scoring/config | Nội dung kỹ thuật ranking formulas | Không có drift |
| Score clipping docs | `nmaiex_ranking_strategy.md`, `nmaiex_ranking_guide.md` | Đã đúng |

---

## 6. Thứ tự thực thi khuyến nghị

Tier 2 nên thực thi theo thứ tự sau để giảm rủi ro conflict:

1. **T2-11** — Archive historical files trước (dọn dẹp, tránh nhầm lẫn)
2. **T2-02** — Embedding docs (drift lớn nhất, nhiều file, cần archive trước viết lại)
3. **T2-01** — NMAIex wording (nhỏ, nhanh)
4. **T2-03** — README + integration_strategy generator architecture
5. **T2-04** — GPT model naming
6. **T2-05** — API path
7. **T2-06** — Enrichment sidecar docs
8. **T2-07** — Management route docs
9. **T2-08** — Full CV markdown note
10. **T2-09** — Context budget note
11. **T2-10** — AI_WORKFLOW_INIT update
12. **T2-12** — Multi-source context note
13. **T2-13 (=DR-13)** — KINH_NGHIEM references

---

## 7. Drift thuộc work package khác (Không xử lý trong P0-C)

| Drift | Work package | Ghi chú |
|---|---|---|
| DR-08 full CV markdown implementation | CHAT_FULL_CV | P0-C chỉ thêm note quyết định |
| DR-09 context budget behavior | CHAT_FULL_CV + P1_A_B_inc | P0-C chỉ thêm note trạng thái |
| DR-11 multi-source context | CHAT_FULL_CV + P1_A_B_inc | P0-C chỉ thêm note gap |
| P0-B F1-F11 failure handling gaps | P1-A/P1-B hoặc implementation riêng | Không thuộc P0-C |
| P0-B O1-O10 observability gaps | P1-A/P1-B hoặc implementation riêng | Không thuộc P0-C |
| `/v2/nmaiex/master/languages` chưa implement | User sẽ quyết định | Docs đã ghi rõ chưa implement |

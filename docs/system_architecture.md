# Kiến trúc hệ thống FANG v2

Tài liệu này mô tả kiến trúc tổng thể của FANG sau khi nâng cấp lên v2, hỗ trợ 5-tier parser và hệ thống RAG Chat tập trung.

## 1. Mô hình "Thin Client" (FANG-Centered)
Kiến trúc v2 định nghĩa FANG là trung tâm trí tuệ (AI Core). Các ứng dụng như `miCareer-mini` chỉ đóng vai trò là giao diện người dùng (Thin Client).

```mermaid
graph LR
    subgraph "Client Layer<br/>(miCareer-mini)"
      UI[Streamlit UI]
      FC[fang_client.py]
    end

    subgraph "AI Core<br/>(FANG)"
      API[FastAPI V2]
      PAR[5-Tier Parser]
      RAG[RAG Orchestrator]
      EMB[Embedding Service]
      CHT[Chat Manager]
    end

    subgraph "Data Layer"
      DB[(PostgreSQL + pgvector)]
      CLD[Cloudinary Storage]
    end

    UI --> FC
    FC -->|"JSON API /v2/"| API
    API --> PAR
    API --> RAG
    RAG --> EMB
    RAG --> CHT
    PAR --> DB
    EMB --> DB
    CHT --> DB
    FC -.->|Upload| CLD
```

## 2. Luồng Ingestion (CV Parse -> Chunk -> Embed)
Sử dụng kiến trúc **5-Tier** với cơ chế **ProTierGate**.

```mermaid
graph TD
    A[POST /v2/ingestion/jobs] --> B[process_ingestion_task]
    B --> C[download_cv]
    C --> D[parse_to_raw_and_json]
    
    subgraph "🟢 Lite Tiers (Fallback tuần tự)"
      E1[Tier 1: Gemini Flash]
      E2[Tier 2: GPT-5.4 mini]
      E3[Tier 3: Claude 4.5 Haiku]
    end
    
    subgraph "ProTierGate (Heuristic Quality Gate)"
      G[Kiểm tra chất lượng<br/>Lite Tiers]
    end
    
    subgraph "🟠 Pro Tiers (Chỉ leo khi<br/>Lite chất lượng thấp)"
      P4[Tier 4:<br/>Gemini Pro]
      P5[Tier 5:<br/>GPT-5.4]
    end

    D --> E1
    E1 -->|Fail/Low Quality| E2
    E2 -->|Fail/Low Quality| E3
    E3 -->|Low Quality| G
    G -->|Escalate| P4
    P4 -->|Fail/Low Quality| P5
    
    E1 & E2 & E3 & P4 & P5 -->|Success| H[save_parsed_cv]
    
    H --> I[split_into_chunks]
    I --> J[embed_chunks]
    J --> K[save_document_chunks]
    K --> L[update_index_job_status=SUCCESS]
```

## 3. Luồng RAG Query (Chatbot)
Điều phối thông qua `rag_orchestrator.py` với 7 chế độ `modelMode`.

1. **Context Assemble**: Kết hợp chunks từ Vector DB + JobPosting + Candidate Profile + ATS History.
2. **Token Budget Management**: Kiểm tra dung lượng hội thoại, tự động trả về `contextWarning` (80% threshold).
3. **Generation Orchestrator**:
   - `auto-lite`: Fallback qua 3 model Lite.
   - `auto-pro`: Fallback qua 2 model Pro.
   - `Specific mode`: Chỉ gọi đúng model được chọn.

## 4. Thành phần chính (Core Components)

### `app/services/rag_orchestrator.py`
- Điều phối việc sinh phản hồi AI.
- Quản lý Quality Gate cho phần trả lời (refusal detection).
- Tích hợp retry tenacity.

### `app/services/chat_persistence.py`
- Quản lý bảng `AICHATCONVERSATION` và `AICHATMESSAGE`.
- Duy trì lịch sử hội thoại tập trung tại FANG.

### `app/services/rag_model_adapters.py`
- Adapter layer cho 5 model (Gemini, OpenAI, Anthropic).
- Sử dụng `MODEL_CANDIDATES` để tự động resolve tên model thực tế.

## 5. Cấu hình & Bảo mật
- **API v2**: Toàn bộ endpoint được chuyển sang tiền tố `/v2/` để đảm bảo tương thích ngược.
- **CORS**: Cho phép tích hợp linh hoạt với các domain frontend qua `CORS_ALLOWED_ORIGINS`.
- **Database Safeguard**: Reset script chỉ cho phép chạy trên đúng DB `micareer_lite_db`.

---
*Tài liệu cập nhật ngày 13/04/2026 cho kiến trúc v2 Pha 1 hoàn chỉnh.*

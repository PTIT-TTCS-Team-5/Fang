# Hình, bảng, sơ đồ Chương 2

File này chứa riêng các bảng, hình và sơ đồ cho Chương 2. Khi đưa vào DOCX, phần văn xuôi trong `chuong_2_ban_hoan_chinh_lan_1.txt` tham chiếu theo đúng số: `Bảng 2.1`, `Hình 2.1`, `Hình 2.2`, `Hình 2.3`, `Hình 2.4`, `Hình 2.5`, `Bảng 2.2`.

## Bảng 2.1. So sánh hai chiều NMAIex J->C và C->J

Tham chiếu trong mục 2.1.

| Tiêu chí | J->C: HR tìm ứng viên | C->J: Candidate tìm job |
|---|---|---|
| Actor chính | HR hoặc nhà tuyển dụng | Candidate |
| Câu hỏi nghiệp vụ | Job này nên xem ứng viên nào trước? | Tôi nên xem job nào trước khi apply? |
| Input trung tâm | `job_id` / `jobPostId` | `candidate_id` |
| Pool được xếp hạng | Candidate / JobApplication | JobPosting |
| Retrieval chính | Vector CV chunk + text rank | Text rank + title rank |
| Feature nổi bật | Skill, seniority, language | Skill, title, salary, language |
| Metric phù hợp | MRR, precision top-k | nDCG@10, recall top-k |
| Output | Ranked candidates | Recommended jobs |
| Giải thích | `score_breakdown` theo từng ứng viên | `score_breakdown` theo từng job |
| Rủi ro chính | Đẩy ứng viên tốt xuống sâu | Bỏ sót cơ hội phù hợp |

## Hình 2.1. NMAIex Ranking hai chiều

Tham chiếu trong mục 2.1.

```mermaid
flowchart LR
    subgraph JC["J→C: HR tìm ứng viên"]
        J1["JobPosting\nyêu cầu tuyển"]
        J2["Candidate pool\nJobApplications"]
        J3["Vector search\n+ text rank"]
        J4["RRF + scoring\nskill/seniority"]
        J5["Ranked candidates\nscore_breakdown"]
        J1 --> J3
        J2 --> J3
        J3 --> J4
        J4 --> J5
    end

    subgraph CJ["C→J: Candidate tìm job"]
        C1["Candidate profile\nCV hiện có"]
        C2["JobPosting pool\nopen jobs"]
        C3["Text/title rank\n+ feature score"]
        C4["Recommended jobs\nscore_breakdown"]
        C1 --> C3
        C2 --> C3
        C3 --> C4
    end
```

## Hình 2.2. Candidate dùng NMAIex trước khi apply

Tham chiếu trong mục 2.2.

```mermaid
sequenceDiagram
    autonumber
    participant C as Candidate
    participant UI as miCareer-mini
    participant API as NMAIex API
    participant DB as Database
    participant ING as Ingestion API

    C->>UI: Xem hồ sơ và CV hiện có
    UI->>DB: Load profile và CV URL
    DB-->>UI: Profile + CV hiện tại
    C->>UI: Mở job gợi ý trước khi apply
    UI->>API: GET ranking jobs theo candidateId
    API->>DB: Load candidate và job pool
    API-->>UI: Recommended jobs + score_breakdown
    C->>UI: Xem job detail
    C->>UI: Apply bằng CV cũ hoặc upload mới
    UI->>DB: Create application với cvSnapUrl
    UI->>ING: POST ingestion jobAppId + cvSnapUrl
    ING-->>UI: indexJobId và status
```

## Hình 2.3. Synthetic data, ground truth và Optuna tuning

Tham chiếu trong mục 2.3.

```mermaid
flowchart LR
    P["Persona set\n8 nhóm CV"]
    G["Generate CV/JD\nqua 9Router"]
    V["Validate/cache\nPydantic schema"]
    S["Seed database\njob + candidate"]
    GT["LLM judge\nground truth 0-4"]
    F["Precompute feature\nJ→C và C→J"]
    O["Optuna TPE\ntuning trọng số"]
    M["MRR / nDCG@10\nbenchmark thử"]
    C["Caveat\nsynthetic only"]

    P --> G --> V --> S --> GT --> F --> O --> M --> C
```

## Hình 2.4. JobApplication Chat theo jobAppId

Tham chiếu trong mục 2.4.

```mermaid
sequenceDiagram
    autonumber
    participant HR as HR
    participant API as Chat API
    participant SVC as rag_query.py
    participant DB as PostgreSQL
    participant LLM as LLM Provider

    HR->>API: POST /chat/query (jobAppId + prompt)
    API->>SVC: process_chat_query scope jobAppId
    SVC->>DB: Load CVPARSED và JD/context
    SVC->>SVC: Build prompt full-CV context
    SVC->>SVC: Check budget warn/block
    SVC->>LLM: Generate answer guarded prompt
    LLM-->>SVC: Grounded answer
    SVC->>DB: Persist chat message + log
    API-->>HR: Response + metadata/warning
```

## Hình 2.5. JobPosting Agent theo jobPostId

Tham chiếu trong mục 2.5.

```mermaid
flowchart TB
    HR["HR question\nscope jobPostId"]
    API["Agent API\n/query"]
    RUN["Runtime\ntool-calling loop"]
    POL["Policy gates\nscope + read-only"]
    TOOLS["Allowed tools\nranking/filter/CV"]
    RANK["Ranking tool\ntop candidates"]
    FILTER["Filter tools\nskill/lang/salary"]
    CV["Full-CV tool\nPII masked"]
    DB["PostgreSQL\nweb + AI data"]
    STATE["Working set\nstate + warnings"]
    ANS["Grounded answer\nwith evidence"]

    HR --> API --> RUN
    RUN --> POL --> TOOLS
    TOOLS --> RANK --> DB
    TOOLS --> FILTER --> DB
    TOOLS --> CV --> DB
    TOOLS --> STATE
    RUN --> ANS
```

## Bảng 2.2. Trade-off giữa Ranking, Chat và Agent

Tham chiếu trong mục 2.6.

| Tiêu chí | NMAIex Ranking | JobApplication Chat | JobPosting Agent |
|---|---|---|---|
| Scope chính | J->C hoặc C->J | Một `jobAppId` | Một `jobPostId` |
| Actor chính | HR hoặc candidate | HR | HR |
| Câu hỏi phù hợp | Ai/job nào nên xem trước? | Hồ sơ này nói gì? | Job này có nhóm ứng viên nào? |
| Input chính | Job, candidate, filters | CV/JD/application context | Job, tools, working set |
| Output | Danh sách đã xếp hạng | Câu trả lời grounded | Câu trả lời kèm tool trace |
| Điểm mạnh | So sánh nhiều đối tượng | Hỏi sâu một hồ sơ | Phân tích nhiều ứng viên |
| Cơ chế chính | Retrieval + scoring | Full-CV prompt | Tool-calling read-only |
| Khả năng giải thích | `score_breakdown` | Evidence trong context | Tool calls + preview |
| Giới hạn | Phụ thuộc trọng số/dữ liệu | Phụ thuộc parse/budget | Cần eval và hardening |
| Rủi ro cần kiểm soát | Overclaim ranking quality | Prompt injection, hallucination | Scope leak, PII leak |

# WS-A — Agent Runtime and Tool Calling Decision

**Workstream**: WS-A - Agent Runtime and Tool Calling Decision  
**Ngày lập**: 2026-05-28  
**Loại tài liệu**: Discovery Report / Decision Input cho Synthesis  
**Output cho**: `FANG_NEXT_PHASE_JOBPOSTING_C3_OFFICIAL_IMPLEMENTATION_PLAN.md`  
**Tác giả**: Tier 1 Discovery Agent (WS-A)

> [!IMPORTANT]
> Tài liệu này là **discovery input**, KHÔNG phải implementation plan chính thức.
> Không có quyền code, sửa file runtime, hay tạo migration.

---

## 1. Executive Summary

WS-A khảo sát toàn bộ runtime hiện tại của FANG (orchestrator, adapters, chat models, query pipeline) và xác nhận:

1. **Hệ thống hiện tại hoàn toàn là text-in → text-out**: Không có tool calling, function declaration, hay agentic loop ở bất kỳ layer nào.
2. **Google GenAI SDK `google-genai==1.69.0` hỗ trợ native function calling đầy đủ** cho cả `gemini-3.5-flash` và `gemini-3.1-flash-lite`, bao gồm cả async (`client.aio`).
3. **Recommendation**: Tạo module agent runtime riêng biệt (`jobposting_agent_runtime.py`), sử dụng trực tiếp Google GenAI SDK native tool calling, **KHÔNG mở rộng** `rag_model_adapters.py` / `rag_orchestrator.py`.
4. **Không cần LangGraph/MCP** trong phase 1 — native tool calling của SDK đủ cho single-agent read-only use case.
5. **Một model mặc định**: `gemini-3.1-flash-lite` cho agent runtime; `gemini-3.5-flash` là option upgrade nếu cần reasoning phức tạp hơn.

---

## 2. Current Runtime Reality

### 2.1. Generation Pipeline Hiện Tại

Dựa trên phân tích code thực tế:

| Layer | File | Chức năng | Tool Calling? |
|---|---|---|---|
| **Orchestrator** | [`rag_orchestrator.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/rag_orchestrator.py) | Entry point `invoke_generation(messages, model_mode)` → `GenerationTrace` | ❌ Không |
| **Adapters** | [`rag_model_adapters.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/rag_model_adapters.py) | ABC `GenerationAdapter.generate()` → `tuple[str, str]` (text, model) | ❌ Không |
| **Chat Models** | [`chat.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/chat.py) | `ChatQueryRequest/Response` — `response: str` | ❌ Không |
| **Query Pipeline** | [`rag_query.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/rag_query.py) | `process_chat_query()` — 12-step RAG pipeline, single `invoke_generation` call | ❌ Không |

### 2.2. Những Gì Đã Có Và Tái Sử Dụng Được

**Tái sử dụng được (cho agent runtime):**
1. ✅ `_resolve_gemini_model_name()` trong [`cv_parser_adapters.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/cv_parser_adapters.py#L245-L300) — dynamic model candidate resolution + caching. Agent runtime nên dùng pattern tương tự.
2. ✅ Error classification hierarchy: `TransientProviderError`, `NonRetryableProviderError`, `ProviderConfigurationError` — agent runtime nên reuse.
3. ✅ `GOOGLE_API_KEY` config đã có trong [`config.py`](file:///c:/Users/os/Desktop/cur_prj/Fang/app/core/config.py) — không cần thêm key riêng.
4. ✅ `tenacity` retry pattern từ orchestrator — agent loop có thể dùng cho từng tool step.
5. ✅ Async patterns: tất cả adapters đã dùng `async with client.aio as aio_client` — agent runtime sẽ dùng cùng pattern.

**KHÔNG tái sử dụng được:**
1. ❌ `GenerationAdapter` ABC — return type `tuple[str, str]` không chứa tool calls. Không nên sửa vì sẽ break JobApplication chat.
2. ❌ `invoke_generation()` — text-only, không có tool loop.
3. ❌ `GenerationTrace` — thiếu tool call tracking.
4. ❌ `_generation_quality_gate()` — dựa trên text heuristic, sẽ false-positive trên tool call responses.
5. ❌ `ChatQueryRequest/Response` — hardcoded `jobAppId`, response là `str`.
6. ❌ `MODEL_MODE_REGISTRY` / `AUTO_MODE_CHAINS` — multi-provider fallback không phù hợp cho agent (agent cần consistency trong cùng conversation).

### 2.3. Specific Code Evidence

**`GeminiGenerationAdapter._generate()` (L100-188):**
```python
# HIỆN TẠI — chỉ text generation
config = types.GenerateContentConfig(
    temperature=temperature,
    max_output_tokens=max_tokens,
    # ❌ Không có: tools=[...], tool_config=...
)
response = await aio_client.models.generate_content(
    model=resolved_model, contents=gemini_contents, config=config
)
text = response.text  # ❌ Chỉ lấy text, bỏ qua function_call parts
```

**`GenerationMessage` type (L35-37):**
```python
GenerationMessage = dict[str, str]  # CHỈ {role, content}
# ❌ Không hỗ trợ: tool role, function_call, tool_result
```

**`process_chat_query()` — single generation call:**
```python
# L10 trong 12-step pipeline:
trace = await invoke_generation(llm_messages, model_mode)
# ❌ Một lần gọi duy nhất, không loop, không tool execution
```

### 2.4. Model Registry Hiện Tại

```
7 valid model modes:
├── Specific (5):
│   ├── gemini-flash  → Gemini Flash (candidate: gemini-3.1-flash, ...)
│   ├── gpt-mini      → GPT-5.4-mini
│   ├── claude-haiku  → Claude 4.5 Haiku
│   ├── gemini-pro    → Gemini Pro (candidate: gemini-3.1-pro-preview, ...)
│   └── gpt-full      → GPT-5.5
│
└── Auto (2):
    ├── auto-lite → gemini-flash → gpt-mini → claude-haiku
    └── auto-pro  → gemini-pro → gpt-full
```

**Gemini model candidates hiện tại** (từ `GEMINI_MODEL_CANDIDATES`):

| Requested | Candidates tried (in order) |
|---|---|
| `gemini-flash` | `gemini-flash`, `gemini-3.1-flash`, `gemini-3.1-flash-preview`, `gemini-3.1-flash-lite-preview`, `gemini-2.5-flash`, `gemini-flash-latest` |
| `gemini-pro` | `gemini-3.1-pro-preview`, `gemini-3.1-pro`, `gemini-pro` |

> [!WARNING]
> Candidate list cho `gemini-flash` hiện bao gồm cả `-lite-preview` variant, nhưng **không có `gemini-3.5-flash`** — model mới nhất đã GA. Agent runtime cần candidate list riêng với models đã xác nhận hỗ trợ function calling.

---

## 3. Tool Calling Options

### 3.1. Option R1 — Fake JSON Loop (LOẠI BỎ)

**Mô tả**: Prompt model trả JSON dạng `{"action": "tool_name", "args": {...}}`, parse bằng regex/json, chạy tool, feed kết quả lại vào prompt.

**Đánh giá**:
- ❌ Fragile: JSON generation không đảm bảo valid, cần retry/fix
- ❌ Không có parallel function calling
- ❌ Không có schema enforcement từ model side
- ❌ Prompt engineering overhead lớn
- ❌ Model không biết tool nào available ở architectural level, chỉ biết qua prompt text

**Kết luận**: Loại bỏ. Planning Brief đã khóa ưu tiên R2.

### 3.2. Option R2 — Native Tool Calling (CHỌN)

**Mô tả**: Dùng Google GenAI SDK native function calling — truyền `tools` vào `GenerateContentConfig`, model trả `function_call` parts, backend execute và feed `function_response` parts.

**Đánh giá**:
- ✅ SDK `google-genai==1.69.0` hỗ trợ đầy đủ
- ✅ Cả `gemini-3.5-flash` và `gemini-3.1-flash-lite` đều support function calling + parallel calling
- ✅ SDK tự chuyển Python functions thành schema (type hints + docstrings → declarations)
- ✅ Có cả automatic mode (SDK xử lý loop) và manual mode (ta kiểm soát loop)
- ✅ Async support đầy đủ qua `client.aio`
- ✅ ID matching cho Gemini 3 models — mỗi function call có unique `id`, response phải match

**Kết luận**: Chọn R2. Native tool calling là lựa chọn đúng cho C3.

### 3.3. Option R3 — LangGraph/MCP (LOẠI BỎ CHO PHASE 1)

**Đánh giá**:
- ❌ Overhead kiến trúc lớn: cần thêm dependencies, state graph, node definitions
- ❌ FANG chỉ cần single-agent loop đơn giản, không cần multi-agent orchestration
- ❌ Planning Brief khóa: "Không LangGraph/MCP nếu WS-A không chứng minh cần"
- ❌ Không có use case multi-provider tool calling trong phase 1 (chỉ Gemini)
- ❌ Google GenAI SDK đã có manual function calling loop — đủ dùng

**Kết luận**: Không cần. Native SDK loop là đủ. Có thể xem xét lại ở phase 2+ nếu:
- Cần multi-agent (e.g., separate ranking agent + analysis agent)
- Cần multi-provider tool calling với fallback
- Cần complex state graph (branching, conditional, human-in-the-loop)

---

## 4. Recommended Runtime Design

### 4.1. Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                  HTTP Request Layer                       │
│         routes_jobposting_agent.py                       │
│         JobPostingAgentQueryRequest → Response            │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│              Query Orchestration Layer                    │
│         jobposting_agent_query.py                        │
│  - Validate request (jobPostId, hrId)                    │
│  - Load/create conversation + state                      │
│  - Persist user message                                  │
│  - Call agent_runtime.run_agent_turn()                    │
│  - Persist assistant message + tool call logs            │
│  - Return response                                       │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│              Agent Runtime Layer (MỚI)                   │
│         jobposting_agent_runtime.py                      │
│  ┌───────────────────────────────────────┐               │
│  │         AGENT LOOP                     │               │
│  │  1. Build system prompt + policy       │               │
│  │  2. Load history + state               │               │
│  │  3. Send to Gemini with tools          │               │
│  │  4. If function_call → execute tool    │               │
│  │     └→ Append function_response        │               │
│  │     └→ Loop back to 3 (max N steps)    │               │
│  │  5. If text response → return          │               │
│  │  6. Enforce guardrails at each step    │               │
│  └───────────────────────────────────────┘               │
└────────────────┬─────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────┐
│              Tool Functions Layer                        │
│         jobposting_tools.py                              │
│  - get_job_posting_context()                             │
│  - get_job_candidate_ranking()                           │
│  - search_job_applications_text()                        │
│  - get_job_application_summary()                         │
│  - get_job_application_full_cv()                         │
│  - get_candidate_ats_history()                           │
│  - count_job_applications()                              │
│  (Tất cả read-only, scoped by jobPostId)                │
└──────────────────────────────────────────────────────────┘
```

### 4.2. Tại Sao Tách Module Riêng

| Tiêu chí | Mở rộng `rag_model_adapters.py` | Module riêng |
|---|---|---|
| Risk cho JobApp chat | Cao — sửa ABC/return type sẽ break | ❌ Không |
| Interface complexity | Phải backward-compatible text + tool | Chỉ tool calling |
| Provider scope | Multi-provider (3 adapters) | Single provider (Gemini) |
| Quality gate | Text heuristic — xung đột với tool calls | Agent-specific checks |
| Conversation model | `jobAppId`-scoped | `jobPostId`-scoped |
| State management | Không có | Working set, filters, summaries |
| Testing | Phải test regression trên tất cả 7 modes | Isolated test suite |

**Kết luận**: Module riêng là đúng. Không chạm vào `rag_orchestrator.py` hay `rag_model_adapters.py`.

### 4.3. Proposed File Layout

```
app/
├── services/
│   ├── jobposting_agent_runtime.py    # [NEW] Agent loop + Gemini tool calling
│   ├── jobposting_agent_query.py      # [NEW] Request orchestration + persistence
│   └── jobposting_tools.py            # [NEW] Tool function implementations
├── models/
│   └── jobposting_agent.py            # [NEW] Request/response/state Pydantic models
├── api/
│   └── routes_jobposting_agent.py     # [NEW] HTTP endpoints
├── core/
│   └── config.py                      # [MODIFY] Thêm agent config fields
```

---

## 5. Provider/Model Decision

### 5.1. Model Verification

Dựa trên Google documentation và SDK verification (May 2026):

| Model | Model ID chính thức | Function Calling | Parallel FC | Status |
|---|---|---|---|---|
| Gemini 3.5 Flash | `gemini-3.5-flash` | ✅ Có | ✅ Có | GA |
| Gemini 3.1 Flash-Lite | `gemini-3.1-flash-lite` | ✅ Có | ✅ Có | GA |

**Cả hai model đều support function calling đầy đủ.**

### 5.2. Agent Model Candidate List (Mới)

Cần tạo candidate list riêng cho agent runtime, tách biệt khỏi `GEMINI_MODEL_CANDIDATES` hiện tại:

```python
AGENT_MODEL_CANDIDATES: dict[str, list[str]] = {
    # Default — Flash-Lite: low latency, high volume, function calling
    "agent-lite": [
        "gemini-3.1-flash-lite",
        "gemini-flash-lite-latest",
    ],
    # Upgrade — Flash: stronger reasoning, agentic workflows
    "agent-pro": [
        "gemini-3.5-flash",
        "gemini-flash-latest",
    ],
}
```

### 5.3. Model Routing Strategy

**Default (Phase 1)**: Một model duy nhất — `gemini-3.1-flash-lite` (via `agent-lite`).

**Lý do chọn Flash-Lite làm default:**
1. User chỉ rõ: "nếu chỉ chọn một model thì chọn Flash-Lite"
2. Low latency — quan trọng cho agentic loop (nhiều round-trip)
3. Cost thấp hơn — agent gọi nhiều lần per turn
4. Function calling đầy đủ — không thiếu tính năng cần thiết

**Upgrade path (Phase 1+)**: Nếu Flash-Lite cho kết quả phân tích yếu (e.g., so sánh ứng viên phức tạp), có thể:
1. Thêm config `JOBPOSTING_AGENT_MODEL=agent-pro` để switch sang Flash
2. Hoặc hybrid: Flash-Lite cho tool decision, Flash cho final synthesis
3. Quyết định này để lại cho testing/evaluation sau khi code

### 5.4. Single Provider — Không Fallback Cross-Provider

**Quyết định**: Agent runtime chỉ dùng Google/Gemini, KHÔNG có fallback sang OpenAI/Anthropic.

**Lý do:**
1. Tool calling format khác nhau giữa providers — function_call schema, response format, ID matching
2. Mid-conversation fallback sẽ break tool call history (tool call IDs không cross-compatible)
3. Planning Brief khóa: "single provider first"
4. Nếu Gemini down, agent trả error rõ ràng (503) — HR dùng lại sau

---

## 6. Agent Loop Contract

### 6.1. Pseudocode

```python
async def run_agent_turn(
    conversation_id: UUID,
    job_post_id: int,
    hr_id: int,
    user_message: str,
    state: AgentState,
    history: list[AgentMessage],
) -> AgentTurnResult:
    """Chạy một turn của agent loop."""
    
    # 1. Build system prompt
    system_prompt = build_agent_system_prompt(job_post_id, state)
    
    # 2. Build tool declarations
    tool_functions = get_tool_registry(job_post_id)
    
    # 3. Build Gemini content từ history + user message
    contents = build_gemini_contents(history, user_message)
    
    # 4. Agent loop
    tool_call_log: list[ToolCallRecord] = []
    step = 0
    
    while step < MAX_TOOL_STEPS:
        # Gọi Gemini với tools
        response = await gemini_generate_with_tools(
            model=resolve_agent_model(),
            system_prompt=system_prompt,
            contents=contents,
            tools=tool_functions,
        )
        
        # Kiểm tra response
        candidate = response.candidates[0]
        parts = candidate.content.parts
        
        # Có function_call?
        function_calls = [p for p in parts if p.function_call]
        
        if not function_calls:
            # Model trả text → done
            final_text = "".join(p.text for p in parts if p.text)
            break
        
        # Execute từng tool call
        for fc in function_calls:
            # Guardrail check
            if not is_tool_allowed(fc.name, fc.args, state, step):
                # Trả error cho model
                function_response = make_error_response(fc, "Exceeded limit")
            else:
                # Execute tool
                result = await execute_tool(fc.name, fc.args, job_post_id)
                function_response = make_success_response(fc, result)
            
            # Log tool call
            tool_call_log.append(ToolCallRecord(
                tool_name=fc.name,
                args=fc.args,
                result_summary=summarize_result(result),
                step=step,
            ))
            
            # Append model response + function response vào contents
            contents.append(candidate.content)
            contents.append(Content(
                role="user",
                parts=[function_response],
            ))
        
        step += 1
    
    if step >= MAX_TOOL_STEPS:
        final_text = "Tôi đã thực hiện quá nhiều bước. Xin hãy thu hẹp câu hỏi."
    
    # 5. Update state
    new_state = update_state(state, tool_call_log)
    
    return AgentTurnResult(
        response_text=final_text,
        model=resolved_model,
        tool_calls=tool_call_log,
        updated_state=new_state,
        steps_used=step,
    )
```

### 6.2. Tool Declaration Format

Sử dụng Python functions với type hints — SDK tự chuyển thành schema:

```python
def get_job_candidate_ranking(
    job_post_id: int,
    limit: int = 10,
    province_id: str | None = None,
    work_mode: str | None = None,
) -> dict:
    """Lấy danh sách ứng viên được xếp hạng cho một job posting.
    
    Args:
        job_post_id: ID của job posting cần xếp hạng ứng viên.
        limit: Số lượng ứng viên tối đa trả về. Mặc định 10, tối đa 25.
        province_id: Lọc theo tỉnh/thành (optional).
        work_mode: Lọc theo hình thức làm việc: ONSITE, REMOTE, HYBRID (optional).
    
    Returns:
        Dict chứa danh sách ứng viên với match_score và score_breakdown.
    """
    ...
```

SDK tự tạo `FunctionDeclaration` schema:
```json
{
  "name": "get_job_candidate_ranking",
  "description": "Lấy danh sách ứng viên được xếp hạng cho một job posting.",
  "parameters": {
    "type": "object",
    "properties": {
      "job_post_id": {"type": "integer", "description": "..."},
      "limit": {"type": "integer", "description": "..."},
      "province_id": {"type": "string", "description": "..."},
      "work_mode": {"type": "string", "description": "..."}
    },
    "required": ["job_post_id"]
  }
}
```

### 6.3. Manual vs Automatic Function Calling

**Quyết định: Manual function calling.**

**Lý do:**
1. Cần guardrail checks trước khi execute tool (max steps, max CV loads, scope validation)
2. Cần log mỗi tool call vào DB (tool call log table từ WS-B)
3. Cần update state sau mỗi tool call (working set, filters)
4. Cần kiểm soát parallel vs sequential execution
5. Automatic mode không cho kiểm soát ở mức này

**Implication**: Agent runtime phải tự implement loop — nhận `function_call` parts, execute, gửi `function_response` parts, loop lại.

### 6.4. Gemini API Flow Chi Tiết

```python
from google import genai
from google.genai import types

async def gemini_generate_with_tools(
    model: str,
    system_prompt: str,
    contents: list,
    tools: list,
) -> types.GenerateContentResponse:
    """Một lần gọi Gemini với tool declarations."""
    
    client = genai.Client(api_key=settings.google_api_key)
    
    try:
        async with client.aio as aio_client:
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=tools,
                temperature=0.2,  # Low temperature cho agent — cần deterministic
                max_output_tokens=4096,
                # KHÔNG dùng automatic_function_calling — ta kiểm soát loop
            )
            
            response = await aio_client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            
            return response
    finally:
        client.close()
```

**Xử lý response:**
```python
# Kiểm tra function_call parts
candidate = response.candidates[0]
for part in candidate.content.parts:
    if part.function_call:
        # Model muốn gọi tool
        call_name = part.function_call.name
        call_args = dict(part.function_call.args)
        call_id = part.function_call.id  # Gemini 3 unique ID
        
        # Execute tool...
        result = await execute_tool(call_name, call_args)
        
        # Build function_response part
        function_response = types.Part.from_function_response(
            name=call_name,
            response={"result": result},
            # id=call_id  # Match ID cho Gemini 3
        )
    elif part.text:
        # Model trả text — final answer
        final_text = part.text
```

---

## 7. Failure Semantics and Guardrails

### 7.1. Hard Limits (Controller-Enforced, Không Chỉ Prompt)

| Limit | Default | Config Var | Hành vi khi vượt |
|---|---|---|---|
| Max tool steps per turn | 8 | `JOBPOSTING_AGENT_MAX_TOOL_STEPS` | Trả message "quá nhiều bước, thu hẹp câu hỏi" |
| Max full CV loads per turn | 3 | `JOBPOSTING_AGENT_MAX_FULL_CV_LOADS` | Từ chối load thêm, gợi ý dùng summary |
| Max compare/deep analysis set | 25 | `JOBPOSTING_AGENT_MAX_COMPARE` | Từ chối so sánh, gợi ý top N hoặc filter |
| Default top N | 10 | `JOBPOSTING_AGENT_DEFAULT_TOP_N` | Dùng khi HR không chỉ rõ số lượng |
| HR max top N | 25 | `JOBPOSTING_AGENT_HR_MAX_TOP_N` | Từ chối nếu HR yêu cầu > 25 |
| Max turn latency | 60s | `JOBPOSTING_AGENT_MAX_TURN_SECONDS` | Timeout toàn bộ turn, trả error |

### 7.2. Guardrail Implementation Points

```
Agent receives user message
    │
    ▼
[GUARDRAIL] Validate jobPostId exists and HR has access
    │
    ▼
Agent loop starts
    │
    ▼
[GUARDRAIL] Step count check (step < MAX_TOOL_STEPS)
    │
    ▼
Model returns function_call
    │
    ▼
[GUARDRAIL] Tool name must be in allowed tool registry
[GUARDRAIL] job_post_id arg must match conversation scope
[GUARDRAIL] job_app_id arg must belong to this job_post_id
[GUARDRAIL] limit arg capped at HR_MAX_TOP_N
[GUARDRAIL] Full CV load count tracked per turn
[GUARDRAIL] Compare set size check
    │
    ▼
Execute tool (read-only, DB query only)
    │
    ▼
[GUARDRAIL] Tool result size check — truncate if too large
[GUARDRAIL] PII filter on tool result before sending to model
    │
    ▼
Loop back to model
```

### 7.3. Error Categories

| Error | Hành vi | HTTP Response |
|---|---|---|
| Gemini API down/timeout | Retry 2 lần → trả 503 | `503 Service Unavailable` |
| Gemini rate limit | Retry 1 lần → trả 429 | `429 Too Many Requests` |
| Model returns no candidates | Trả error message | `200` với error trong response |
| Tool execution fails (DB) | Feed error vào model → model có thể retry tool hoặc giải thích | N/A (trong loop) |
| Max steps exceeded | Trả warning message | `200` với warning |
| Invalid jobPostId/hrId | Reject ngay | `400/403` |
| Tool call với wrong jobPostId | Block tool call, feed error vào model | N/A (trong loop) |

### 7.4. Retry Strategy

**Phân biệt 2 loại retry:**

1. **Gemini API retry** (transient errors):
   - Max attempts: 3
   - Backoff: 1s → 2s → 4s (exponential)
   - Chỉ retry `TransientProviderError` (429, 5xx, timeout)
   - Reuse `tenacity` pattern từ `rag_orchestrator.py`

2. **Tool re-invocation** (model tự quyết):
   - Nếu tool trả error, model nhận error message và có thể quyết định:
     - Gọi lại tool với args khác
     - Bỏ qua và trả lời dựa trên data đã có
     - Giải thích cho HR tại sao không lấy được data
   - Controller chỉ enforce max steps, không can thiệp vào model logic

---

## 8. Required Config

### 8.1. Thêm Vào `config.py` (`Settings`)

```python
# --- JobPosting Agent (C3) ---
jobposting_agent_model: str = "agent-lite"
jobposting_agent_max_tool_steps: int = 8
jobposting_agent_max_full_cv_loads: int = 3
jobposting_agent_max_compare: int = 25
jobposting_agent_default_top_n: int = 10
jobposting_agent_hr_max_top_n: int = 25
jobposting_agent_max_turn_seconds: int = 60
jobposting_agent_temperature: float = 0.2
jobposting_agent_max_output_tokens: int = 4096
```

### 8.2. `.env` Additions

```bash
# --- JobPosting Agent (C3) ---
# Model mode: "agent-lite" (gemini-3.1-flash-lite) hoặc "agent-pro" (gemini-3.5-flash)
JOBPOSTING_AGENT_MODEL=agent-lite

# Runtime limits
JOBPOSTING_AGENT_MAX_TOOL_STEPS=8
JOBPOSTING_AGENT_MAX_FULL_CV_LOADS=3
JOBPOSTING_AGENT_MAX_COMPARE=25
JOBPOSTING_AGENT_DEFAULT_TOP_N=10
JOBPOSTING_AGENT_HR_MAX_TOP_N=25
JOBPOSTING_AGENT_MAX_TURN_SECONDS=60

# Generation params
JOBPOSTING_AGENT_TEMPERATURE=0.2
JOBPOSTING_AGENT_MAX_OUTPUT_TOKENS=4096
```

### 8.3. KHÔNG Cần Thêm

- ❌ `GOOGLE_API_KEY` — đã có
- ❌ Thêm dependency mới — `google-genai==1.69.0` đã có, function calling built-in
- ❌ `JOBPOSTING_AGENT_PROVIDER` — khóa Gemini only

---

## 9. Impact on Other Workstreams

### 9.1. Impact on WS-B (Conversation Tables + Memory)

| WS-A Decision | Impact on WS-B |
|---|---|
| Manual function calling → cần log mỗi tool call | WS-B phải có `AIJOBPOSTINGTOOLCALLLOG` table với fields: `toolCallId`, `messageId`, `toolId/toolName`, `inputArgs`, `outputSummary`, `status`, `latencyMs`, `stepIndex` |
| State per turn: working set, filters | WS-B phải có state table/column lưu JSON: `workingSetJobAppIds`, `activeFilters`, `lastRankingMeta` |
| Gemini content format — `Content(role, parts[])` | WS-B conversation message format phải support: `role` in (`user`, `model`, `function_call`, `function_response`), `content` as JSON (not just text) |
| Max 8 steps per turn | WS-B tool call log per message có thể có tối đa 8 records |
| Model info per turn | WS-B message table nên có `model` column cho agent messages |

### 9.2. Impact on WS-C (Tool Contract)

| WS-A Decision | Impact on WS-C |
|---|---|
| Tool functions = Python functions với type hints + docstrings | WS-C tool contract phải output: function signature, docstring, return type — SDK tự tạo schema |
| `job_post_id` scope enforcement ở controller | WS-C tools không cần tự validate scope — controller đã validate trước khi execute |
| Tool result gửi lại model qua `function_response` | WS-C tool output phải serializable thành dict → JSON |
| Max result size cần truncation | WS-C tools nên trả dạng structured dict với field rõ ràng, không trả raw text blob |
| Single-provider (Gemini) function calling | WS-C tool schema phải compatible với Gemini function declaration format |

### 9.3. Impact on WS-D (API/UI Contract)

| WS-A Decision | Impact on WS-D |
|---|---|
| Agent trả text + tool call metadata | WS-D response schema cần: `response`, `toolCalls[]`, `stepsUsed`, `model` |
| Tool call log available | WS-D UI có thể show tool usage detail (tool name, args summary, latency) |
| Max turn latency 60s | WS-D UI nên show loading state, có thể cần streaming trong phase 2 |
| No streaming phase 1 | WS-D API là request-response, không SSE/WebSocket |

### 9.4. Dependency on Normalized Data (NMAIex Bug)

WS-A ghi nhận dependency:
- Agent runtime **giả định** language/province data đã normalized ở parse/enrichment stage.
- Tool `get_job_candidate_ranking()` sẽ gọi `rank_candidates_for_job()` — hàm này đọc `CVPARSED.parsedJson.languages` và kỳ vọng proficiency đã là enum chuẩn.
- Nếu normalization chưa fix (WS-C scope), agent filter "tiếng Anh hạng C trở lên" sẽ cho kết quả sai.
- WS-A **không thiết kế normalization workaround** trong runtime — đúng boundary theo planning brief.

---

## 10. Open Questions for Synthesis

### 10.1. Cần Quyết Định Ở Synthesis

| # | Question | Options | WS-A Recommendation |
|---|---|---|---|
| Q1 | Agent model resolution: dùng `_resolve_gemini_model_name()` chung hay tạo resolver riêng? | A) Reuse, thêm candidates vào `GEMINI_MODEL_CANDIDATES`. B) Tạo `_resolve_agent_model_name()` riêng. | **B** — tách biệt, tránh ảnh hưởng text generation flows |
| Q2 | Agent system prompt nên include gì ngoài tool policy? | A) Minimal: chỉ policy + role. B) Include job posting context summary. | **B** — giúp model hiểu context nhanh hơn, giảm tool calls không cần thiết |
| Q3 | Parallel function calling: cho phép trong phase 1? | A) Có — cho model quyết định. B) Không — chỉ sequential. | **A** — Gemini support, giảm round-trips; controller vẫn validate từng call |
| Q4 | Tool result nên gửi full cho model hay truncated? | A) Full result. B) Truncated + summary. | **B** — tránh context window overflow, đặc biệt ranking results dài |
| Q5 | Conversation history cho agent: bao gồm cả tool call messages hay chỉ user/assistant? | A) Full history gồm tool calls. B) Chỉ user/assistant + state summary. | **B cho history load, A cho current turn** — history dài sẽ blow up context window |

### 10.2. Cần Input Từ Các WS Khác

| Cần từ | Input | Tại sao |
|---|---|---|
| WS-B | Exact schema cho `AIJOBPOSTINGCHATSTATE` JSON | Agent runtime cần biết state structure để read/write |
| WS-B | Conversation message persistence format | Agent cần biết lưu tool call messages thế nào |
| WS-C | Exact tool function signatures và return schemas | Agent runtime cần import và register tools |
| WS-C | NMAIex normalization fix status | Ảnh hưởng tới language filter tool behavior |
| WS-D | Request/response schema cho agent endpoint | Agent query layer cần implement |

---

## 11. Acceptance Criteria

### 11.1. Agent Runtime Module

- [ ] `jobposting_agent_runtime.py` implement manual function calling loop với Gemini SDK
- [ ] Loop enforce max steps, max CV loads, max compare set, scope validation
- [ ] Model resolution dùng `AGENT_MODEL_CANDIDATES` riêng
- [ ] Retry cho transient Gemini errors (429, 5xx, timeout)
- [ ] Trả `AgentTurnResult` với text + tool call log + updated state + latency

### 11.2. Integration Contract

- [ ] Agent runtime KHÔNG import từ `rag_orchestrator.py` hay `rag_model_adapters.py`
- [ ] Agent runtime KHÔNG sửa bất kỳ file hiện tại nào
- [ ] Agent runtime dùng `GOOGLE_API_KEY` đã có trong `config.py`
- [ ] Agent runtime dùng `google.genai` SDK trực tiếp (not through adapter layer)
- [ ] Tool functions là Python async functions với type hints + docstrings

### 11.3. Config

- [ ] Tất cả limits có default values hợp lý
- [ ] Tất cả limits configurable qua `.env`
- [ ] Model mode configurable: `agent-lite` (default) hoặc `agent-pro`

### 11.4. Non-Goals Verified

- [ ] KHÔNG dùng LangGraph/MCP
- [ ] KHÔNG multi-provider fallback
- [ ] KHÔNG sửa `GenerationAdapter` ABC
- [ ] KHÔNG thêm tool calling vào existing chat flows
- [ ] KHÔNG streaming/SSE trong phase 1

---

## Recommended Decisions For Synthesis

1. **Chọn R2 — Native tool calling** với Google GenAI SDK `google-genai==1.69.0`.
2. **Manual function calling loop** — controller kiểm soát mỗi step, không dùng automatic mode.
3. **Default model: `gemini-3.1-flash-lite`** qua candidate `agent-lite`; upgrade path là `gemini-3.5-flash` qua `agent-pro`.
4. **Module riêng** — `jobposting_agent_runtime.py` + `jobposting_tools.py` + `jobposting_agent_query.py`, KHÔNG mở rộng adapters hiện tại.
5. **Không LangGraph/MCP** trong phase 1.
6. **Single provider (Gemini)**, không cross-provider fallback cho agent.
7. **8 guardrails** enforce ở controller level, không chỉ prompt.

## Risks If Ignored

| Risk | Hậu quả | Probability |
|---|---|---|
| Dùng R1 (fake JSON loop) thay R2 | Fragile, khó debug, không parallel FC | Cao nếu dev vội code trước khi đọc doc |
| Mở rộng `rag_model_adapters.py` | Break JobApp chat regression | Cao |
| Không enforce guardrails ở controller | Model load bulk CV, so sánh 500 ứng viên, timeout | Cao |
| Dùng automatic function calling | Mất control trên tool execution, không log được | Trung bình |
| Không verify model IDs trước code | `gemini-3.1-flash-lite` resolve fail → runtime crash | Trung bình |
| Không tách model candidate list | Agent resolution conflict với text gen resolution | Trung bình |
| Bỏ qua NMAIex normalization dependency | Language filter tool trả kết quả sai → HR mất tin tưởng | Cao (phụ thuộc WS-C) |

## Inputs Needed From Other Workstreams

| Từ WS | Input cần | Blocking? |
|---|---|---|
| WS-B | State JSON schema → agent runtime read/write | Có — cần trước khi code runtime |
| WS-B | Tool call log table schema → agent runtime persist | Có — cần trước khi code persistence |
| WS-B | Conversation message format (support tool roles) | Có |
| WS-C | Tool function signatures + return types | Có — cần trước khi code runtime |
| WS-C | NMAIex normalization fix plan | Có — blocking cho language filter tool correctness |
| WS-D | Request/response schema cho HTTP layer | Không — có thể code song song |

## Checklist For Official Implementation Plan

- [ ] Xác nhận model candidates: `gemini-3.1-flash-lite`, `gemini-3.5-flash` — verify trên environment thực
- [ ] Xác nhận `google-genai==1.69.0` function calling API ổn định (không deprecated)
- [ ] Define `AgentTurnResult` dataclass đầy đủ
- [ ] Define `AgentState` schema (coordinate với WS-B)
- [ ] Define tool function signatures (coordinate với WS-C)
- [ ] Viết system prompt template cho agent
- [ ] Viết guardrail validation functions
- [ ] Viết model candidate resolution cho agent
- [ ] Viết agent loop unit tests: happy path, max steps, tool error, scope violation
- [ ] Viết integration test: mock Gemini API responses với function_call + text
- [ ] Update `.env.example` với agent config
- [ ] Update `config.py` với agent settings
- [ ] Document agent loop sequence diagram cho team

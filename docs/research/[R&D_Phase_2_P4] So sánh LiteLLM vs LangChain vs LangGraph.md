# So Sánh LiteLLM vs LangChain vs LangGraph và Công Nghệ Tương Tự

## 📋 Tóm Tắt Nhanh

| Tiêu Chí | LiteLLM | LangChain | LangGraph |
|---------|---------|-----------|-----------|
| **Mục Đích** | Unified LLM Gateway | RAG & Chain Framework | Stateful Agent Orchestration |
| **Level** | Thấp (Low-level) | Cao (High-level) | Thấp (Low-level) |
| **Chủ Yếu Giải Quyết** | Provider diversity, Fallback, Cost tracking | Composable components, Integrations | State management, Long-running agents |
| **Phạm Vi** | LLM API layer | Entire LLM application | Workflow/Agent execution |
| **Phù Hợp Với FANG?** | ✅ Hoàn Hảo | ❌ Quá Nặng | ⚠️ Có Thể Dùng (Future) |

---

## 1. **LiteLLM - Unified LLM Gateway**

### 📌 Định Nghĩa
LiteLLM là một **lightweight Python SDK + Proxy Server** cung cấp một unified interface để gọi 100+ LLM providers (OpenAI, Anthropic, Gemini, Azure, AWS Bedrock, v.v) với định dạng OpenAI standard.

### 🎯 Chức Năng Chính

#### **1.1 Unified API Interface**
```python
# Tất cả providers dùng cùng interface - OpenAI format
from litellm import completion

# Gọi OpenAI
response = completion(model="openai/gpt-4o", messages=[...])

# Gọi Anthropic - cùng interface
response = completion(model="anthropic/claude-opus", messages=[...])

# Gọi Gemini - cùng interface  
response = completion(model="gemini/gemini-pro", messages=[...])
```

#### **1.2 Retry & Fallback Logic**
```python
# Fallback chuỗi tự động
response = completion(
    model="openai/gpt-4",
    messages=[...],
    fallbacks=["anthropic/claude-opus", "gemini/gemini-pro"],  # Thứ tự dự phòng
    max_retries=3
)
# Nếu gpt-4 fail → thử claude → thử gemini
```

#### **1.3 Cost Tracking & Spend Management**
- Tự động tính toán chi phí mỗi lệnh gọi
- Hỗ trợ virtual keys với spend limits
- Multi-tenant cost tracking

#### **1.4 Proxy Server / AI Gateway**
```bash
# Chạy như một centralized gateway service
litellm --model gpt-4o

# Sau đó bất cứ app nào có thể dùng
curl -X POST "http://0.0.0.0:4000/chat/completions" \
  -H "Authorization: Bearer sk-xxx" \
  -d '{"model": "gpt-4o", "messages": [...]}'
```

### ✅ Ưu Điểm
1. **Cực kỳ đơn giản** - 1 dòng code gọi 100+ LLMs
2. **Drop-in replacement** - chỉ cần thay đổi model name
3. **Production-ready** - đã được Stripe, Google, Netflix sử dụng
4. **Overhead thấp** - 8ms P95 latency ở 1k RPS
5. **Exception mapping** - chuẩn hóa lỗi từ mọi provider thành OpenAI exceptions

### ❌ Hạn Chế
1. **Chỉ quản lý LLM calls** - không xử lý flow/orchestration
2. **Không có memory** - không lưu state giữa calls
3. **Không có tool/function calling** built-in (nhưng hỗ trợ passthrough)
4. **Cần tự xử lý RAG logic** - chỉ cung cấp LLM layer

### 🎓 Khi Nào Dùng LiteLLM?
- ✅ Cần gọi LLM từ nhiều providers khác nhau
- ✅ Muốn fallback/load-balancing tự động
- ✅ Cần cost tracking & spend management
- ✅ Muốn giải pháp lightweight (không muốn framework nặng)
- ✅ **FANG case**: Đúng 100% - cần định tuyến Lite/Pro, fallback, cost control

---

## 2. **LangChain - RAG & Composition Framework**

### 📌 Định Nghĩa
LangChain là một **high-level framework** cung cấp composable components (Tools, Retriever, Memory, Chains, RAG) để xây dựng LLM applications. Nó là một **ecosystem** bao gồm:
- **Core SDK** (chains, agents, tools)
- **LangSmith** (observability platform)
- **Integrations** (100+ plugins)
- **LangGraph** (low-level agent orchestration)

### 🎯 Chức Năng Chính

#### **2.1 Composable Chains & LCEL**
```python
from langchain.prompts import ChatPromptTemplate
from langchain.llms import OpenAI
from langchain.schema.runnable import RunnablePassthrough

# LCEL - declarative composition
prompt = ChatPromptTemplate.from_template("Translate {text} to French")
model = OpenAI()
chain = prompt | model

# Có thể chain nhiều thành phần
full_chain = (
    RunnablePassthrough.assign(context=retriever) 
    | prompt 
    | model 
    | output_parser
)

result = full_chain.invoke({"text": "Hello"})
```

#### **2.2 Built-in Integrations**
- 100+ LLM providers
- 100+ vector stores (Pinecone, Weaviate, Milvus, v.v)
- 100+ tools & APIs
- 100+ retrievers & loaders

#### **2.3 RAG Out-of-the-Box**
```python
from langchain.chains import RetrievalQA

qa = RetrievalQA.from_chain_type(
    llm=OpenAI(),
    chain_type="stuff",
    retriever=vectorstore.as_retriever()
)
answer = qa.run("Who is CEO of OpenAI?")
```

#### **2.4 Memory Management**
```python
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory()
conversation = ConversationChain(
    llm=OpenAI(),
    memory=memory,
    prompt=prompt_template
)
```

#### **2.5 Agent Framework**
```python
from langchain.agents import initialize_agent, Tool

tools = [Tool(...), Tool(...)]
agent = initialize_agent(
    tools,
    llm,
    agent="zero-shot-react-description",
    verbose=True
)
agent.run("What is the weather in NYC?")
```

### ✅ Ưu Điểm
1. **All-in-one framework** - có tất cả components cần thiết
2. **Khổng lồ ecosystem** - 100+ integrations
3. **Quick prototyping** - nhanh chóng xây dựng RAG/Agents
4. **LangSmith integration** - observability tuyệt vời
5. **Community & docs** - cực kỳ chi tiết
6. **LCEL** - declarative syntax, dễ hiểu

### ❌ Hạn Chế
1. **Nặng & phức tạp** - rất nhiều abstraction layers
2. **Performance overhead** - chậm hơn raw API calls
3. **Opinionated** - binding kết quả tới các kiến trúc cụ thể
4. **Chuyên RAG, không chuyên Agents** - LangGraph là cái chuyên
5. **Dependency chain dài** - khó maintain khi phải update
6. **Vendor lock-in** - phụ thuộc vào LangChain ecosystem

### 🎓 Khi Nào Dùng LangChain?
- ✅ Cần xây dựng RAG application nhanh chóng
- ✅ Cần nhiều integrations & tools
- ✅ Team có kinh nghiệm với LangChain
- ✅ Prototype/POC nhanh
- ❌ **FANG case**: Không phù hợp - FANG có custom logic phức tạp (5-tier parser, ProTierGate), không muốn opinionated framework, cần lightweight + control

---

## 3. **LangGraph - Stateful Agent Orchestration**

### 📌 Định Nghĩa
LangGraph là một **low-level orchestration framework** cho xây dựng long-running, stateful agents. Nó tập trung vào workflow/state management, không phải LLM calls hay RAG.

### 🎯 Chức Năng Chính

#### **3.1 State Machine / Graph-based Execution**
```python
from langgraph.graph import StateGraph, END

# Định nghĩa state
class AgentState(TypedDict):
    input: str
    output: str
    messages: list

# Tạo graph
graph = StateGraph(AgentState)

# Thêm nodes (hành động)
graph.add_node("node_1", process_step_1)
graph.add_node("node_2", process_step_2)

# Thêm edges (transitions)
graph.add_edge("node_1", "node_2")
graph.add_edge("node_2", END)

# Compile thành executable
runnable = graph.compile()

# Chạy
result = runnable.invoke({"input": "..."})
```

#### **3.2 Durable Execution - Persistence**
```python
# Workflows có thể fail & resume
runnable.invoke(
    input,
    config={"checkpointer": PostgresSaver()}  # Persist state
)
# Nếu crash → restart tự động từ state cuối cùng
```

#### **3.3 Human-in-the-Loop / Interrupts**
```python
# Tạm dừng execution để human review
graph.add_conditional_edges(
    "review_node",
    route_after_review,  # Hỏi human tiếp tục hay không
    {
        "approve": "next_node",
        "reject": "correction_node"
    }
)
```

#### **3.4 Comprehensive Memory**
```python
# Short-term: working memory (state)
# Long-term: persistent store (checkpointer)
# Message history: konversasi multi-turn

# Kết hợp cả hai loại
state = {
    "working_memory": {...},  # Short-term (trong execution)
    "persistent_memory": {...}  # Long-term (cross-session)
}
```

#### **3.5 Debugging with LangSmith**
- Visualization của execution paths
- State transitions tracing
- Runtime metrics

### ✅ Ưu Điểm
1. **Durable execution** - tự động persist & resume
2. **Human-in-the-loop** - dễ integrate human oversight
3. **Fine-grained control** - low-level, có thể custom mọi thứ
4. **Stateful** - giữ state giữa steps
5. **Deterministic** - production-ready, no magic
6. **LangSmith integration** - debugging tuyệt vời

### ❌ Hạn Chế
1. **Không xử lý LLM calls** - cần integrate LiteLLM hay gì đó tương tự
2. **Phức tạp setup** - cần định nghĩa state, nodes, edges
3. **Boilerplate code** - nhiều lệnh setup
4. **Không built-in RAG** - cần tự xây
5. **Không agent-specific** - chỉ là orchestration framework

### 🎓 Khi Nào Dùng LangGraph?
- ✅ Cần long-running, stateful workflows
- ✅ Cần human-in-the-loop
- ✅ Cần durable execution & fault recovery
- ✅ Complex multi-step agents
- ⚠️ **FANG case**: Có thể dùng ở tương lai (Phase 3, 4) khi extend sang complex agent workflows, nhưng không cần cho phase 2 refactor hiện tại

---

## 4. **So Sánh Trực Tiếp - 3 Công Nghệ**

### 📊 Bảng So Sánh Chi Tiết

| Tiêu Chí | LiteLLM | LangChain | LangGraph |
|---------|---------|-----------|-----------|
| **Abstraction Level** | Low | High | Low |
| **Scope** | LLM API layer | Entire app | Workflow/State |
| **Learning Curve** | Rất Dễ (1 ngày) | Trung Bình (1 tuần) | Khó (1-2 tuần) |
| **Code Size** | 50-100 lines | 200-500 lines | 300-800 lines |
| **Performance** | Rất Nhanh | Chậm (abstraction overhead) | Trung Bình |
| **Flexibility** | Cực Cao | Trung Bình | Cực Cao |
| **Production-Ready** | Tuyệt Vời | Tốt | Tuyệt Vời |
| **Community Size** | Nhỏ (nhưng tăng) | Rất Lớn | Lớn |
| **LLM Call Management** | ✅ Tuyệt Vời | ✅ Tốt | ❌ Không |
| **RAG Support** | ❌ Không | ✅ Tuyệt Vời | ❌ Không |
| **State Management** | ❌ Không | ❌ Không | ✅ Tuyệt Vời |
| **Fallback/Retry** | ✅ Built-in | ❌ Không | ❌ Không |
| **Cost Tracking** | ✅ Built-in | ❌ Không | ❌ Không |
| **Observability** | Cơ Bản | ✅ LangSmith | ✅ LangSmith |

### 🔍 Use Case Comparison

```
┌─────────────────────────────────────────────┐
│ Tôi cần gọi LLM từ nhiều providers?        │
├─────────────────────────────────────────────┤
│ → LiteLLM (PERFECT)                         │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Tôi cần xây dựng RAG application nhanh?    │
├─────────────────────────────────────────────┤
│ → LangChain (GOOD) hoặc LiteLLM + custom    │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Tôi cần long-running agent workflow?       │
├─────────────────────────────────────────────┤
│ → LangGraph (PERFECT)                       │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Tôi cần complex orchestration + RAG + LLM? │
├─────────────────────────────────────────────┤
│ → LangGraph (orchestration) + LiteLLM (LLM)│
│   + Custom RAG logic                         │
└─────────────────────────────────────────────┘
```

---

## 5. **Công Nghệ Tương Tự & Alternatives**

### 🚀 Các Framework Tương Tự

#### **5.1 Instructor (Response Parsing)**
- **Mục đích**: Parse LLM output thành structured data
- **Phù hợp khi**: Cần validate & extract data từ LLM
- **Ví dụ**:
```python
from instructor import Instructor
from pydantic import BaseModel

class ExtractedData(BaseModel):
    name: str
    age: int

client = Instructor(openai.Client())
result = client.chat.completions.create(
    model="gpt-4",
    response_model=ExtractedData,
    messages=[...]
)
# Tự động parse + validate thành Pydantic model
```
- **Hạn chế**: Chỉ xử lý response parsing, không xử lý LLM call management

#### **5.2 Pydantic AI (Type-safe AI)**
- **Mục đích**: Type-safe LLM interactions
- **Phù hợp khi**: Muốn runtime type validation
- **Ưu điểm**: Lightweight, Pydantic integration
- **Hạn chế**: Quá mới, ecosystem chưa mature

#### **5.3 Anthropic SDK (Batch API)**
- **Mục đích**: Batch processing LLM calls
- **Phù hợp khi**: Cần batch inference giá rẻ
- **Ví dụ**: Process 1000 CVs cùng lúc
- **Hạn chế**: Chỉ Anthropic, không unified

#### **5.4 OpenAI SDK (Native)**
- **Mục đích**: OpenAI API wrapper
- **Phù hợp khi**: Dùng OpenAI exclusively
- **Ưu điểm**: Official, lightweight, well-maintained
- **Hạn chế**: Không support providers khác

#### **5.5 vLLM (Local LLM Inference)**
- **Mục đích**: Run LLMs locally
- **Phù hợp khi**: Cần on-premise inference, privacy critical
- **Ưu điểm**: Cực kỳ nhanh (10x faster than Huggingface)
- **Hạn chế**: Cần GPU resources

#### **5.6 Claude SDK (Anthropic)**
- **Mục đích**: Anthropic's native SDK
- **Phù hợp khi**: Dùng Claude exclusively
- **Ưu điểm**: Official, thought tokens, extended thinking
- **Hạn chế**: Anthropic only

#### **5.7 Portkey (AI Gateway + Guardrails)**
- **Mục đích**: LLM Gateway + Safety guardrails
- **Phù hợp khi**: Cần production gateway + compliance
- **Ưu điểm**: Enterprise features, audit logs
- **Hạn chế**: Paid service (unlike LiteLLM OSS)

---

## 6. **FANG's Decision: Tại Sao Chọn LiteLLM?**

### 🎯 Quyết Định Thiết Kế

#### **6.1 Yêu Cầu Hệ Thống**
1. **Multi-provider support** (Gemini, OpenAI, Anthropic)
2. **Fallback từ Lite → Pro tự động**
3. **Cost tracking & spend control**
4. **ProTierGate quality gate** (heuristic-based)
5. **Custom RAG logic** (5-tier parser, hybrid chunking)
6. **Lightweight, maintainable**

#### **6.2 Tại Sao LiteLLM Perfect?**
```
✅ Multi-provider support:
   - OpenAI (gpt-5.4-mini, gpt-5.4)
   - Anthropic (claude-4.5-haiku, claude-opus)
   - Gemini (gemini-3.1-flash, gemini-3.1-pro)
   → Unified interface: litellm.completion()

✅ Fallback logic:
   - Routing modes YAML-driven
   - Auto-fallback chain: Lite1 → Lite2 → Lite3 → Pro
   → completion(..., fallbacks=["model_a", "model_b"])

✅ Cost tracking:
   - Automatic cost calculation
   - Built-in spend tracking
   → Tính toán chi phí mỗi call

✅ Control & Flexibility:
   - LiteLLM xử lý LLM layer
   - FANG xử lý ProTierGate (quality gate)
   - FANG xử lý RAG (chunking, retrieval)
   → Clean separation of concerns

✅ Lightweight:
   - Không overhead framework
   - 8ms P95 latency
   - Production-ready (used by Netflix, Stripe)
```

#### **6.3 Tại Sao KHÔNG Chọn LangChain?**
```
❌ Quá nặng:
   - FANG có custom logic phức tạp
   - LangChain opinionated, không flexible
   - Nhiều dependencies, khó maintain

❌ RAG đã custom:
   - 5-tier parser là custom
   - Hybrid chunking là custom
   - Embedding normalization (zero-padding) là custom
   - LangChain RAG không phù hợp

❌ Không cần high-level chains:
   - FANG đã tách bạch rõ: LLM layer, RAG layer, orchestration
   - Không cần RetrievalQA, ConversationChain abstractions
```

#### **6.4 Tại Sao KHÔNG Chọn LangGraph?**
```
❌ Không cần state machine (hiện tại):
   - FANG 12-step RAG query không cần state persistence
   - Workflow là synchronous (request → response)
   - Không cần human-in-the-loop (Phase 2)

⚠️ Future: Có thể dùng LangGraph ở Phase 3, 4 khi:
   - Xây dựng complex multi-turn agents
   - Cần durable execution & fault recovery
   - Cần human review points
   → Khi đó: LangGraph (orchestration) + LiteLLM (LLM calls)
```

---

## 7. **Architecture Pattern: LiteLLM trong FANG**

### 📐 How It Fits

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  RAG Orchestrator (app/services/rag_query.py)  │   │
│  │  - Lắp ghép context (JD + CV + Feedback)      │   │
│  │  - Tính toán ngân sách (step 8)               │   │
│  │  - Kiểm tra context warnings                  │   │
│  └─────────────────────────────────────────────────┘   │
│                         ↓                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  LiteLLM Integration Layer                     │   │
│  │  - completion(..., model, fallbacks)           │   │
│  │  - Exception handling (RateLimitError, etc)    │   │
│  │  - Cost calculation (response.usage)           │   │
│  │  - Stream options (include_usage: True)        │   │
│  └─────────────────────────────────────────────────┘   │
│                         ↓                                 │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Models Registry (models_registry.yaml)         │   │
│  │  - Primary model + fallback chain               │   │
│  │  - Context window, cost per token              │   │
│  │  - Tier definition (1-6)                       │   │
│  └─────────────────────────────────────────────────┘   │
│                         ↓                                 │
│  ┌──────────────────────────────┐  ┌──────────────────┐ │
│  │ External LLM Providers       │  │ ProTierGate      │ │
│  │ - OpenAI (gpt-5.4)           │  │ - Quality check  │ │
│  │ - Anthropic (claude-opus)    │  │ - Heuristics    │ │
│  │ - Gemini (gemini-3.1-pro)    │  │ - Leo thang call │ │
│  └──────────────────────────────┘  └──────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 💡 Key Integration Points

```python
# app/services/rag_orchestrator.py
from litellm import completion
from app.core.models.registry_schema import RegistryManager

class RAGOrchestrator:
    async def invoke_model(self, prompt, routing_mode):
        # 1. Lấy config từ registry
        model_config = RegistryManager.get_routing_mode(routing_mode)
        
        # 2. Gọi LiteLLM với fallback chain
        response = completion(
            model=model_config.primary_model,
            messages=[{"role": "system", "content": prompt}],
            fallbacks=model_config.fallback_chain,  # Auto fallback
            stream=True,
            stream_options={"include_usage": True}  # Track tokens
        )
        
        # 3. Xử lý response
        tokens_used = response.usage.prompt_tokens
        cost = calculate_cost(response.model, tokens_used)
        
        # 4. ProTierGate quality check
        quality_gate = ProTierGate(response.content)
        if not quality_gate.is_valid():
            # Auto escalate to Pro tier
            return self.invoke_model(prompt, "auto-pro")
        
        return response
```

---

## 8. **Future Roadmap: Khi Nào Xem Xét Alternatives?**

### 📅 Phase Roadmap

#### **Phase 2 (Hiện Tại)**
- ✅ LiteLLM (LLM layer)
- ✅ Custom RAG (5-tier parser)
- ✅ models_registry.yaml (config)
- ❌ LangChain (quá nặng)
- ❌ LangGraph (không cần)

#### **Phase 3 (Q3 2026)**
- ✅ LiteLLM (keep)
- ✅ Custom RAG (keep)
- ⚠️ Instructor (parsing output structure)
- ⚠️ Pydantic AI (type safety)
- ❌ LangGraph (chưa cần)

#### **Phase 4 (Q4 2026 - Complex Agents)**
- ✅ LiteLLM (keep)
- ✅ LangGraph (orchestration cho agent workflows)
- ⚠️ LangSmith (monitoring agents)
- ✅ Custom RAG (keep)

#### **Future (2027+)**
- Có thể xem xét Portkey (enterprise gateway)
- Có thể chuyển sang on-prem inference (vLLM) nếu scale

---

## 📝 Kết Luận

### 🎯 FANG's Best Fit Pyramid

```
                    ┌─────────┐
                    │LangSmith│ (Monitoring, future)
                    └────┬────┘
                         │
                ┌────────┴────────┐
                │   LangGraph     │ (Phase 4+)
                │  (Orchestration)│ (Complex agents)
                └────────┬────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
    ┌───┴───┐      ┌────┴─────┐     ┌───┴────┐
    │LiteLLM│      │ Custom RAG│     │Pydantic│
    │ (LLM) │      │(Chunking) │     │  (Parse)│
    └─────────┘    └──────────┘     └────────┘
        ↓              ↓                 ↓
    Unified API  5-Tier Parser      Output Validation
```

### ✅ Quyết Định: LiteLLM = Perfect Choice
- **Mục đích**: Unified LLM API layer ✅
- **Fallback/Retry**: Tự động ✅
- **Cost tracking**: Built-in ✅
- **Lightweight**: Production-ready ✅
- **Control**: Không opinionated ✅
- **Separation of concerns**: Clean architecture ✅

---

**Bản cập nhật**: May 13, 2026  
**Source**: 
- LiteLLM GitHub: https://github.com/BerriAI/litellm
- LangChain: https://langchain.com
- LangGraph: https://github.com/langchain-ai/langgraph

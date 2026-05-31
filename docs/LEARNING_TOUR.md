# FANG v2 Guided Learning Tour
## Understanding the AI Core from Entry Point to Implementation

This guided tour walks developers through the FANG v2 FastAPI codebase, progressively deepening understanding from system architecture to implementation details. Each step builds on the previous, creating a coherent narrative of how FANG ingests CVs and answers RAG queries.

---

## 🎯 Tour Overview

The tour consists of **9 interconnected steps** that follow the natural flow of data and control through the system:

| Step | Focus | Purpose |
|------|-------|---------|
| 1 | Entry Point & Startup | Understand how the app boots and what routers are loaded |
| 2 | Configuration Layer | See how all system behavior is parametrized via `Settings` |
| 3 | Multi-Provider Architecture | Learn the adapter pattern for unified LLM access |
| 4-6 | Provider Implementations | Deep-dive into Gemini, OpenAI, and Anthropic implementations |
| 7 | RAG Query Pipeline | Understand the core chat pipeline from prompt to response |
| 8 | REST API Endpoints | See the public contract and how endpoints map to pipelines |
| 9 | Integration & Documentation | Learn how frontend developers use the system |

---

## Step 1: Entry Point — How FANG Starts ✨

**File:** [app/main.py](../app/main.py)

### What You'll Learn
- How the FastAPI app initializes
- Database lifecycle management (connect on startup, disconnect on shutdown)
- Router registration and API versioning
- CORS configuration driven by settings

### Why This Matters
Before understanding any detail, you need to see the "skeleton" of the application. This file answers:
- What routers exist? (/v2/ingestion, /v2/chat, /v2/nmaiex, etc.)
- How is the app constructed? (FastAPI + middleware + lifespan context manager)
- When does the database connect/disconnect?

### Key Patterns
- **Lifespan context manager**: Async startup/shutdown lifecycle
- **Router composition**: Multiple routers included at different prefixes
- **Middleware chain**: CORS configured from settings

### Next Step
Understanding the routers requires knowing *how they're configured*. Move to Step 2.

---

## Step 2: Configuration Layer — The System's Brain 🧠

**File:** [app/core/config.py](../app/core/config.py)

### What You'll Learn
- All system parameters are externalized to Pydantic `Settings`
- Database, embedding, LLM, and RAG parameters are all here
- How retry policies, context budgets, and fallback strategies are configured
- Environment variables drive runtime behavior

### Why This Matters
**FANG is highly parameterized.** Before touching any service layer code, you must understand:
- How embedding dimensions work (Gemini: 1536-dim vectors)
- Why retry policies exist (handle transient API failures)
- How context budgets prevent token overflow
- What parser quality thresholds are enforced

### Key Settings to Understand
```python
# Embedding: Defines the vector search dimensionality
embedding_provider: str = "gemini"
embedding_model: str = "gemini-embedding-001"
embedding_dim: int = 1536

# Parser retry: Handles LLM API transient failures
parser_retry_enabled: bool = True
parser_retry_attempts: int = 3

# RAG: Context budget prevents prompt overflow
context_budget_lite: int = 180_000   # Claude Haiku safe window
context_budget_pro: int = 960_000    # Gemini Pro / GPT-5.5 window
context_budget_hard_limit: float = 0.95  # Beyond this, reject generation

# Fallback model tiers
google_api_key: str | None = None
openai_api_key: str | None = None
claude_api_key: str | None = None
```

### Next Step
These settings **drive LLM calls**. To understand how, you need to see the adapter pattern that abstracts different providers. Move to Step 3.

---

## Step 3: Multi-Provider Abstraction — The Adapter Pattern 🔌

**File:** [app/services/cv_parser_adapters.py](../app/services/cv_parser_adapters.py)  
**Key Classes:** `ProviderAdapter` (abstract base), `ProviderInvocationError`

### What You'll Learn
- **The Adapter Pattern**: Abstract interface (`ProviderAdapter`) that all LLM providers implement
- Why multi-provider abstraction exists: cost optimization + resilience
- How the system handles provider-specific API responses
- The error hierarchy for unified error handling

### Why This Matters
This is the **critical abstraction** that makes FANG's fallback strategy possible:
- If Gemini fails, code doesn't break — it falls back to OpenAI
- New providers can be added without changing service layer logic
- All providers present the same interface: `invoke_parse()` returns `ParsedCV`

### Key Concepts
```python
# Base adapter defines the contract
class ProviderAdapter(ABC):
    @abstractmethod
    async def invoke_parse(self, pdf_base64: str) -> ParsedCV:
        """All implementations must return ParsedCV, regardless of provider."""

# Error hierarchy allows caller to handle any provider failure uniformly
class ProviderInvocationError(Exception):
    def __init__(self, provider: str, model: str, message: str, ...):
        self.provider = provider  # Which provider failed?
        self.model = model        # Which model?
```

### Fallback Strategy (5-Tier)
The adapters are used in a **5-tier fallback chain**:
1. **Lite Tier (cost-optimized):** Gemini Flash → GPT-5.4 mini → Claude Haiku
2. **Pro Tier (quality-focused):** Gemini Pro → GPT-5.5 (only if Lite fails catastrophically)

### Next Step
Now that you understand the interface, see how **each provider implements it**. Steps 4-6 dive into Gemini, OpenAI, and Anthropic implementations.

---

## Step 4: Gemini Provider Implementation 🟢

**File:** [app/services/cv_parser_adapters.py](../app/services/cv_parser_adapters.py)  
**Class:** `GeminiProviderAdapter`

### What You'll Learn
- How to call Google's Generative AI API with vision capabilities
- Model resolution strategy (fallback candidate lists for forward compatibility)
- Vision-to-text parsing: PDF as base64 → Gemini vision model → JSON
- Schema enforcement via structured output

### Why This Matters
Gemini is the **primary parser choice** in FANG (cost-optimized, fast). Understanding its implementation shows:
- How to encode PDFs for LLM vision models
- How to enforce JSON schema on LLM output
- How model name resolution works (e.g., "gemini-flash" → actual model name)

### Key Patterns
```python
# Model resolution: attempt fallback candidates for forward compatibility
GEMINI_MODEL_CANDIDATES: dict[str, list[str]] = {
    "gemini-flash": [
        "gemini-3.1-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.5-flash",
        "gemini-flash-latest",
    ],
}

# Vision API call with PDF base64 + JSON schema
async def invoke_parse(self, pdf_base64: str) -> ParsedCV:
    # Send: [PDF binary part, schema constraint]
    # Receive: Structured JSON matching ParsedCV model
```

### Next Step
Different providers have different APIs. Step 5 shows OpenAI's approach.

---

## Step 5: OpenAI Provider Implementation 🔵

**File:** [app/services/cv_parser_adapters.py](../app/services/cv_parser_adapters.py)  
**Class:** `OpenAIProviderAdapter`

### What You'll Learn
- How to call OpenAI's JSON mode (structured output)
- Difference between Vision API and text-only approaches
- Rate limiting and timeout handling for GPT models
- Cost tradeoff: GPT-5.5 (full) vs GPT-5.4-mini (economical)

### Why This Matters
OpenAI is the **second-choice fallback** in FANG. This implementation demonstrates:
- Alternative LLM API patterns (not all providers use vision)
- How to enforce schema via JSON mode instead of multimodal input
- Handling provider-specific rate limits and retries

### Key Differences from Gemini
- OpenAI uses **text-based encoding** (not vision)
- JSON mode is enforced via `response_format`
- Different timeout/retry strategies

### Next Step
OpenAI handles text; Anthropic has its own approach. Step 6 explores Claude.

---

## Step 6: Anthropic Provider Implementation 🔴

**File:** [app/services/cv_parser_adapters.py](../app/services/cv_parser_adapters.py)  
**Class:** `AnthropicProviderAdapter`

### What You'll Learn
- How Claude API differs from Gemini and OpenAI
- Anthropic's approach to PDF parsing (base64 + media type headers)
- Claude's context window and token counting
- Why Claude is the fallback of last resort (most reliable but higher cost)

### Why This Matters
Claude is the **safety net** — most reliable but most expensive. This implementation shows:
- Different model parameters (e.g., `max_tokens` requirement for Claude)
- How context windows vary by provider
- When to choose reliability over cost

### Key Claude-Specific Patterns
```python
# Claude requires explicit max_tokens
response = client.messages.create(
    model=model_name,
    max_tokens=8192,  # Must be explicit for Claude
    messages=[...],
)

# Claude's media type header approach for PDFs
content=[
    {"type": "image", "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_base64}},
]
```

### Reflection: The Adapter Pattern in Action
After steps 3-6, you see the power of the adapter pattern:
- **Three implementations**, same interface
- **Fallback chain** works because all return `ParsedCV`
- **New provider**? Just add another `ProviderAdapter` subclass

### Next Step
You understand *how* providers are invoked. Step 7 shows the *RAG pipeline* that uses parsed CVs.

---

## Step 7: RAG Query Pipeline — The Chat Engine 🚀

**File:** [app/services/rag_query.py](../app/services/rag_query.py)

### What You'll Learn
- The complete flow from prompt → response in RAG chat
- How context is bundled (CV chunks, job posting, candidate data, ATS history)
- Context window budget management (prevent token overflow)
- Message persistence and conversation tracking

### Why This Matters
This is where **everything comes together**. The RAG pipeline:
- Receives a user prompt (from `/v2/chat/query` endpoint)
- Retrieves vector-search results from parsed CV embeddings
- Bundles context from multiple sources
- Checks context budget (will the message fit?)
- Invokes LLM generation (using the adapters!)
- Persists conversation history

### Key Data Structures
```python
@dataclass
class CvContext:
    """CV as markdown, ready to inject into prompt."""
    markdown: str
    source: CvContextSource  # "parsed_json" or "raw_text"
    warnings: list[str]

@dataclass
class ApplicationContext:
    """All context around 1 job application."""
    job_posting: dict | None
    candidate: dict | None
    ats_history: list[dict]
    offers: list[dict]        # Phase 2
    emails: list[dict]        # Phase 2

@dataclass
class BudgetResult:
    """Token budget check result."""
    total_tokens: int
    budget: int
    used_percent: int
    action: BudgetAction      # "proceed", "warn_proceed", "block"
    messages: list[dict]      # Final message array for LLM
```

### The Budget Management Pattern
FANG implements **sophisticated context budget management**:
- **Lite budget** (180k tokens): Safe for Claude Haiku's 200k window
- **Pro budget** (960k tokens): For Gemini Pro / GPT-5.5's 1M+ windows
- **Warning threshold** (80%): Alert when approaching budget
- **Hard limit** (95%): Reject generation beyond this

This prevents the LLM from seeing truncated context or failing mid-generation.

### Next Step
Now understand the *API endpoint* that triggers this pipeline. Step 8 shows the REST contract.

---

## Step 8: REST API Endpoints — The Public Contract 📡

**File:** [app/api/routes_chat.py](../app/api/routes_chat.py)  
**Endpoint:** `POST /v2/chat/query`

### What You'll Learn
- The REST API contract for chat (request/response shapes)
- How endpoints map to service layer functions
- Validation and error handling at the boundary
- Versioning strategy (v2 primary, v1 backward-compatible)

### Why This Matters
This is where **external systems interact** with FANG. Frontend developers and integrators must understand:
- What parameters to send?
- What can go wrong (errors)?
- How is the response structured?
- What do I do if the chat hits context budget?

### Key Endpoints (from README)
```
POST /v2/chat/query
  → Invoke chat_query() → RAG pipeline → response

GET /v2/chat/conversations
  → List HR's conversations

GET /v2/chat/conversations/{id}/messages
  → Get message history

POST /v2/chat/conversations/{id}/summarize
  → Summarize old messages (context window reduction)

POST /v2/chat/conversations/{id}/branch-new
  → Create new conversation with context summary
```

### Next Step
You understand the *what* (endpoints). Steps 9 explains the *how* (integration and setup).

---

## Step 9: Integration Guides & Documentation 📚

**Files:**
- [docs/guide/integration_guide.md](../docs/guide/integration_guide.md) — Frontend integration
- [docs/guide/job_application_full_cv_chat_guide.md](../docs/guide/job_application_full_cv_chat_guide.md) — Full-CV architecture
- [docs/guide/embedding_guide.md](../docs/guide/embedding_guide.md) — Embedding configuration
- [docs/guide/database_guide.md](../docs/guide/database_guide.md) — Database schema

### What You'll Learn
- How to integrate FANG into a frontend
- Full-CV chat architecture (Phase 1 vs Phase 2 features)
- Embedding model selection and configuration
- PostgreSQL + pgvector schema design

### Why This Matters
You've learned the *internals*; now learn the *integration patterns*:
- Where to make API calls?
- How to manage conversations?
- What database tables store what?
- When to use Gemini Flash vs Pro?

### Integration Workflow for Frontend Devs
```
1. Create conversation: POST /v2/chat/conversations
2. For each user question:
   a. POST /v2/chat/query {conversationId, prompt, jobApplicationId}
   b. Check response status (proceed, warn, block)
   c. If blocked, offer: summarize, branch, or reduce context
3. Retrieve history: GET /v2/chat/conversations/{id}/messages
```

### Database Design Highlights
- **conversations**: Chat sessions, linked to HR user
- **messages**: Each exchange (user prompt + LLM response)
- **parsed_cv**: Structured CV data (JSONB)
- **cv_chunks**: Semantic chunks with embeddings (pgvector)
- **query_logs**: Audit trail (models used, token counts, budget actions)

---

## 🎓 Learning Outcomes

After completing this tour, you should understand:

✅ **Architecture**: How FANG ingests CVs and answers RAG queries  
✅ **Abstraction**: Why multi-provider adapters enable cost-optimized fallback  
✅ **Configuration**: How `Settings` parametrize the entire system  
✅ **Pipelines**: CV parsing (5-tier) and RAG chat (vector search → LLM → persistence)  
✅ **REST API**: The public contract and integration patterns  
✅ **Database**: The data model and embedding storage  
✅ **Resilience**: Context budgets, retries, and fallback strategies  

---

## 🔍 Recommended Next Steps

After this tour, explore:

1. **Run the system locally**  
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Test the API**  
   Use the Postman collection in `postman/FANG_v2_Collection.postman_collection.json`

3. **Trace a request**  
   Add breakpoints in `app/api/routes_chat.py::chat_query()` and step through to RAG pipeline

4. **Examine the database**  
   ```bash
   psql -U postgres -d micareer_lite_db
   \d conversations
   \d messages
   \d cv_chunks
   ```

5. **Read the strategy docs**  
   - `docs/strategy/rag_query_strategy.md` — Detailed RAG design
   - `docs/strategy/integration_strategy.md` — API contract details

---

## 📖 Quick Reference

| Topic | File | Class/Function |
|-------|------|-----------------|
| App startup | `app/main.py` | `app`, `lifespan()` |
| Settings | `app/core/config.py` | `Settings` class |
| Provider interface | `app/services/cv_parser_adapters.py` | `ProviderAdapter` ABC |
| Gemini impl | `app/services/cv_parser_adapters.py` | `GeminiProviderAdapter` |
| OpenAI impl | `app/services/cv_parser_adapters.py` | `OpenAIProviderAdapter` |
| Anthropic impl | `app/services/cv_parser_adapters.py` | `AnthropicProviderAdapter` |
| RAG pipeline | `app/services/rag_query.py` | `CvContext`, `BudgetResult` |
| Chat endpoint | `app/api/routes_chat.py` | `chat_query()` |
| Ingestion | `app/api/routes_ingestion.py` | `ingest_cv()` |
| Database | `app/core/database.py` | `DatabaseConnection` |

---

## 🤔 Common Questions Answered

**Q: Why multiple providers?**  
A: Cost optimization. Gemini Flash is ~10x cheaper than GPT-5.5. We use Lite (cheap, fast) first, then Pro (expensive, reliable) only if needed.

**Q: What's the fallback strategy?**  
A: 5-tier for parsing: Gemini Flash → GPT-5.4 mini → Claude Haiku → (Pro Tier) Gemini Pro → GPT-5.5  
7 modes for generation: auto-lite, auto-pro, gemini-flash, gpt-mini, claude-haiku, gemini-pro, gpt-full

**Q: How do context budgets work?**  
A: Each model has a safe token window (e.g., Claude Haiku: 200k). We allocate a budget (180k) and track usage. If >80%, warn HR. If >95%, reject (ask them to summarize/branch).

**Q: What's the difference between Phase 1 and Phase 2?**  
A: Phase 1: CV + Job + Candidate + ATS history in context  
Phase 2 (coming): + Offers and Email history for richer context

**Q: How are CVs stored and searched?**  
A: CVs are parsed → chunked into semantic segments → embedded as vectors (1536-dim) → stored in pgvector → vector search retrieves top-K chunks for RAG context

---

## 📝 Notes for Contributors

- Always check `Settings` before hardcoding values
- When adding a new provider, extend `ProviderAdapter`
- Update retry policies in `Settings`, not in service code
- Context budget checks prevent token overflow — don't bypass them
- Test with multiple providers to validate fallback chain

---

*Last updated: May 2026*  
*For questions, see `docs/strategy/` for detailed architecture docs*

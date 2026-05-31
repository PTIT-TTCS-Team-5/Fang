# FANG v2 Learning Tour — Quick Reference & Navigation Guide

## 🚀 How to Use This Guide

This quick reference complements the full learning tour in `LEARNING_TOUR.md`. Use this to:
1. **Jump to specific topics** without reading the full narrative
2. **Understand where code lives** for each architectural concept
3. **Find examples** of key patterns (adapters, context management, etc.)
4. **Test locally** using provided commands

---

## 📋 Tour Steps at a Glance

### Step 1: Entry Point
**File:** `app/main.py`  
**Time to read:** 5 min  
**Key lines:** 1-48  
**Concepts:** FastAPI initialization, lifespan context manager, router registration

**Run the app:**
```bash
uvicorn app.main:app --reload
# Server starts at http://localhost:8000
```

**Verify it works:**
```bash
curl http://localhost:8000/docs
# Opens Swagger UI with all endpoints documented
```

---

### Step 2: Configuration Layer
**File:** `app/core/config.py`  
**Time to read:** 10 min  
**Key sections:**
- Lines 1-40: Database, embedding, logging
- Lines 41-65: LLM provider API keys
- Lines 66-95: Parser retry policy
- Lines 96-110: RAG query (context budget management)

**Key settings to understand:**
```python
# Embedding dimensionality for vector search
embedding_dim: int = 1536

# Context budgets prevent token overflow
context_budget_lite: int = 180_000   # Claude Haiku safe
context_budget_pro: int = 960_000    # Gemini Pro / GPT-5.5

# Hard limit: Beyond 95%, reject generation
context_budget_hard_limit: float = 0.95
```

**Test your .env:**
```bash
python -c "from app.core.config import settings; print(f'DB: {settings.database_url}'); print(f'Embedding: {settings.embedding_dim}D')"
```

---

### Step 3: Multi-Provider Abstraction
**File:** `app/services/cv_parser_adapters.py`  
**Time to read:** 15 min  
**Key sections:**
- Lines 1-80: Import, constants, model candidates
- Lines 81-120: `ProviderInvocationError` class
- Lines 121-160: Abstract `ProviderAdapter` base class

**Key concept:** All providers implement the same interface
```python
class ProviderAdapter(ABC):
    @abstractmethod
    async def invoke_parse(self, pdf_base64: str) -> ParsedCV:
        """All implementations return ParsedCV, regardless of provider."""
```

**Why this matters:** Enables 5-tier fallback without changing caller code.

---

### Step 4: Gemini Provider
**File:** `app/services/cv_parser_adapters.py`  
**Time to read:** 20 min  
**Key sections:** Lines 200-350 (approximately)  
**Key class:** `GeminiProviderAdapter`

**Unique patterns:**
- Uses Google Generative AI vision API
- Base64-encoded PDF + schema constraint
- Model resolution via candidate list for forward compatibility

**Test Gemini locally:**
```bash
# Set GOOGLE_API_KEY in .env
python -c "
from app.services.cv_parser_adapters import GeminiProviderAdapter
import asyncio
adapter = GeminiProviderAdapter()
# See method signatures in the class
"
```

---

### Step 5: OpenAI Provider
**File:** `app/services/cv_parser_adapters.py`  
**Time to read:** 20 min  
**Key sections:** Lines 350-500 (approximately)  
**Key class:** `OpenAIProviderAdapter`

**Unique patterns:**
- JSON mode for structured output (not vision)
- Different rate limit handling
- GPT-5.5 (Tier 5 pro) vs GPT-5.4-mini (Tier 2 lite)

**Test OpenAI locally:**
```bash
# Set OPENAI_API_KEY in .env
# Run the test suite
pytest smoke_tests/test_parser.py -k openai -v
```

---

### Step 6: Anthropic Provider
**File:** `app/services/cv_parser_adapters.py`  
**Time to read:** 20 min  
**Key sections:** Lines 500-650 (approximately)  
**Key class:** `AnthropicProviderAdapter`

**Unique patterns:**
- Requires explicit `max_tokens`
- Media type headers for PDFs
- Context window management for Claude

**Test Anthropic locally:**
```bash
# Set CLAUDE_API_KEY in .env
# Run the test suite
pytest smoke_tests/test_parser.py -k anthropic -v
```

---

### Step 7: RAG Query Pipeline
**File:** `app/services/rag_query.py`  
**Time to read:** 30 min  
**Key sections:**
- Lines 1-60: Type definitions (CvContext, ApplicationContext, BudgetResult)
- Lines 61-150: Budget management logic
- Lines 151-250: Vector search and context bundling
- Lines 251-350: Generation invocation

**Key data structures:**
```python
@dataclass
class BudgetResult:
    total_tokens: int
    budget: int
    used_percent: int
    action: BudgetAction  # "proceed", "warn_proceed", "block"
    messages: list[dict]  # Ready for LLM
```

**Trace a request:**
1. Request arrives at `POST /v2/chat/query`
2. Prompt is embedded
3. Vector search retrieves CV chunks
4. Context is bundled (job, candidate, ATS)
5. Budget is checked
6. LLM is invoked (with fallback)
7. Response is persisted

**Debug with logging:**
```bash
# In .env, set LOG_LEVEL=DEBUG
# Tail logs to see pipeline stages
tail -f /var/log/fang.log
```

---

### Step 8: REST API Endpoints
**File:** `app/api/routes_chat.py`  
**Time to read:** 15 min  
**Key function:** `async def chat_query(request: ChatQueryRequest)`

**Key endpoints:**
```
POST /v2/chat/query
  Body: {conversationId, prompt, jobApplicationId, modelMode}
  Response: {status, message, tokenUsage, budget}

GET /v2/chat/conversations
  Query: ?limit=20
  Response: [conversations]

GET /v2/chat/conversations/{id}/messages
  Response: [messages]

POST /v2/chat/conversations/{id}/summarize
  Body: {summaryModel}
  Response: {newSummary, tokensRecovered}
```

**Test endpoints:**
```bash
# Using curl
curl -X POST http://localhost:8000/v2/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "conv-123",
    "prompt": "What are this candidate skills?",
    "jobApplicationId": "app-456",
    "modelMode": "auto-lite"
  }'

# Using Postman
# Import: postman/FANG_v2_Collection.postman_collection.json
```

---

### Step 9: Integration Guides & Documentation
**Files:**
- `docs/guide/integration_guide.md` — Frontend integration patterns
- `docs/guide/job_application_full_cv_chat_guide.md` — Full-CV architecture
- `docs/guide/embedding_guide.md` — Embedding model selection
- `docs/guide/database_guide.md` — Schema design

**Time to read:** 60 min total  

**Integration workflow:**
```python
# 1. Create conversation
POST /v2/chat/conversations
  → conversationId: "conv-abc-123"

# 2. Send prompt
POST /v2/chat/query {
  conversationId: "conv-abc-123",
  prompt: "...",
  jobApplicationId: "app-456"
}
→ { status: "proceed", message: "...", budget: "75%" }

# 3. If budget is 80%+, offer options
POST /v2/chat/conversations/{id}/summarize
  → Reduce token usage by summarizing old messages

POST /v2/chat/conversations/{id}/branch-new
  → Start fresh conversation with context summary
```

**Database schema:**
```sql
-- Conversations store chat sessions
SELECT * FROM conversations WHERE hr_user_id = 'user-123';

-- Messages store exchanges
SELECT * FROM messages WHERE conversation_id = 'conv-123' ORDER BY timestamp DESC;

-- CV chunks with embeddings for vector search
SELECT id, parsed_cv_id, text, embedding <-> query_embedding AS distance 
FROM cv_chunks 
ORDER BY distance LIMIT 3;
```

---

## 🧪 Hands-On Exercises

### Exercise 1: Trace a Parse Request (30 min)
**Objective:** Understand the full parsing pipeline

1. **Set breakpoint** in `app/api/routes_ingestion.py::ingest_cv()`
2. **Run with debugger** in VS Code
3. **Step through** to `ProviderAdapter.invoke_parse()`
4. **Watch fallback:** If Gemini fails, catch the error and see OpenAI attempted
5. **Inspect result:** `ParsedCV` object with structured fields

**Run:**
```bash
# Terminal 1: Run with debugger
python -m debugpy.adapter --listen 5678 -m uvicorn app.main:app

# Terminal 2: Send test request
curl -X POST http://localhost:8000/v2/ingestion/jobs \
  -d '{
    "jobApplicationId": "test-123",
    "cvUrl": "https://..."
  }'
```

---

### Exercise 2: Inspect Context Budget (20 min)
**Objective:** See budget management in action

1. **Find** `BudgetResult` class in `app/services/rag_query.py`
2. **Add logging** in the budget check function
3. **Send long prompt** to see budget warnings
4. **Review logs** to see token counts and budget percentages

**Code snippet to add:**
```python
logger.info(f"Budget check: {result.total_tokens}/{result.budget} tokens ({result.used_percent}%)")
if result.action == "warn_proceed":
    logger.warning(f"Context budget warning: {result.used_percent}% used")
elif result.action == "block":
    logger.error(f"Context budget exceeded: {result.used_percent}% used, BLOCKING generation")
```

---

### Exercise 3: Test Fallback Chain (30 min)
**Objective:** Verify multi-provider fallback

1. **Create test** in `smoke_tests/test_parser.py`
2. **Mock providers:** Gemini always fails, OpenAI always fails, Claude succeeds
3. **Verify** that fallback chain is triggered (log should show 3 attempts)
4. **Final response** should use Claude (Tier 3)

**Test code:**
```python
@pytest.mark.asyncio
async def test_fallback_chain():
    # Set up mocks where Gemini and OpenAI fail
    with patch('app.services.cv_parser_adapters.GeminiProviderAdapter.invoke_parse', side_effect=Exception("Gemini down")):
        with patch('app.services.cv_parser_adapters.OpenAIProviderAdapter.invoke_parse', side_effect=Exception("OpenAI down")):
            # Only Anthropic succeeds
            result = await parse_cv_with_fallback(pdf_base64)
            assert result is not None
            assert result.candidateName == "..."  # Verify parsed data
```

---

### Exercise 4: Query Vector Search (20 min)
**Objective:** Understand embeddings and vector search

1. **Connect** to database: `psql -U postgres -d micareer_lite_db`
2. **Query CV chunks:**
   ```sql
   SELECT id, parsed_cv_id, text, embedding::text 
   FROM cv_chunks 
   LIMIT 1;
   ```
3. **View embedding dimension:** `SELECT array_length(embedding, 1);` → Should be 1536
4. **Test vector distance:**
   ```sql
   SELECT id, text, embedding <-> (SELECT embedding FROM cv_chunks LIMIT 1) AS distance
   FROM cv_chunks
   ORDER BY distance
   LIMIT 5;
   ```

---

## 📊 Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    FastAPI App (main.py)                 │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  POST /v2/chat/query  (routes_chat.py)            │  │
│  │  POST /v2/ingestion/jobs (routes_ingestion.py)    │  │
│  └─────────────┬──────────────────────────┬──────────┘  │
│                │                          │              │
│      ┌─────────▼─────────┐    ┌──────────▼──────────┐   │
│      │   RAG Query       │    │  CV Parser          │   │
│      │  (rag_query.py)   │    │ (routes_ingestion) │   │
│      │                   │    │                    │   │
│      │ • Context Bundle  │    │ 1. invoke_parse()  │   │
│      │ • Vector Search   │    │ 2. chunk()         │   │
│      │ • Budget Check    │    │ 3. embed()         │   │
│      │ • Generation      │    │ 4. save()          │   │
│      └────────┬──────────┘    └────────┬───────────┘   │
│              │                        │                 │
│              └────────┬───────────────┘                 │
│                       │                                 │
│      ┌────────────────▼─────────────────┐               │
│      │  Multi-Provider Adapter Layer     │               │
│      │  (cv_parser_adapters.py)          │               │
│      │                                   │               │
│      │  ProviderAdapter (ABC)            │               │
│      │  ├── GeminiProviderAdapter        │               │
│      │  ├── OpenAIProviderAdapter        │               │
│      │  └── AnthropicProviderAdapter     │               │
│      │                                   │               │
│      │  Fallback: Gem→GPT→Claude→...    │               │
│      └────────────────┬────────────────┘               │
│                       │                                 │
│      ┌────────────────▼─────────────────┐               │
│      │     External LLM APIs             │               │
│      │  • Google Generative AI           │               │
│      │  • OpenAI GPT                     │               │
│      │  • Anthropic Claude               │               │
│      └────────────────────────────────────┘               │
│                                                          │
│      ┌─────────────────────────────────┐                │
│      │  PostgreSQL + pgvector           │                │
│      │  • conversations                 │                │
│      │  • messages                      │                │
│      │  • cv_chunks (embeddings)        │                │
│      │  • parsed_cv                     │                │
│      └─────────────────────────────────┘                │
│                                                          │
│      ┌──────────────────────────────────┐               │
│      │  Settings (config.py)             │               │
│      │  • Embedding config              │               │
│      │  • Retry policies                │               │
│      │  • Context budgets               │               │
│      │  • API keys (from .env)          │               │
│      └──────────────────────────────────┘               │
└──────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Concepts Checklist

Use this to verify your understanding:

- [ ] **Lifespan management**: FastAPI uses async context managers for startup/shutdown
- [ ] **Settings pattern**: All configuration is externalized to Pydantic Settings
- [ ] **Adapter pattern**: Abstract `ProviderAdapter` enables provider-agnostic code
- [ ] **Fallback strategy**: 5-tier for parsing (lite→lite→lite→pro→pro)
- [ ] **Vector search**: CVs are chunked and embedded (1536-dim) for semantic search
- [ ] **Context budgets**: RAG prevents token overflow with soft warnings and hard limits
- [ ] **Persistence**: All conversations/messages are stored in PostgreSQL
- [ ] **API versioning**: /v2 primary, /v1 backward-compatible
- [ ] **Cost optimization**: Cheap providers (Gemini Flash) used first, expensive (GPT-5.5) only if needed

---

## 🔗 Important Files Quick Links

| Concept | File | Lines |
|---------|------|-------|
| **App Entry** | `app/main.py` | 1-48 |
| **Configuration** | `app/core/config.py` | Full file |
| **Provider Interface** | `app/services/cv_parser_adapters.py` | 121-160 |
| **Gemini** | `app/services/cv_parser_adapters.py` | 200-350 |
| **OpenAI** | `app/services/cv_parser_adapters.py` | 350-500 |
| **Claude** | `app/services/cv_parser_adapters.py` | 500-650 |
| **RAG Pipeline** | `app/services/rag_query.py` | Full file |
| **Chat API** | `app/api/routes_chat.py` | Full file |
| **Database** | `app/core/database.py` | Full file |
| **Data Models** | `app/models/cv_models.py` | Full file |

---

## 🆘 Troubleshooting

**Q: API won't start**  
A: Check `.env` file has `DATABASE_URL`. Run `python -m app.core.config` to validate.

**Q: Vector search returns no results**  
A: Verify `embedding_provider` is set correctly in `.env`. Check pgvector extension: `psql -c "CREATE EXTENSION IF NOT EXISTS vector;"`

**Q: Parser always fails**  
A: Check API keys for all 3 providers in `.env`. Enable DEBUG logging: `LOG_LEVEL=DEBUG`

**Q: Context budget keeps blocking**  
A: Increase `context_budget_pro` or implement conversation summarization in frontend.

---

*Last updated: May 2026*

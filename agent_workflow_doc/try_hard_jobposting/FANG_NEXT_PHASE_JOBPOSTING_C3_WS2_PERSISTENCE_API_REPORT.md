# FANG Next Phase JobPosting C3 WS2 Persistence/API Shell Report

## 1. Summary
This report details the implementation of the **JobPosting Agent persistence layer and API shell (WS2)** for FANG JobPosting Agent C3.1. 

The API layer namespace is structured under `/v2/agent/job-posting/*` and is completely isolated from the existing `/v2/chat/*` system. Pydantic models have been designed without exposing `modelMode` to the HR users, conforming to the C3 Official Implementation Plan. A dedicated persistence service utilizing the newly created database tables handles conversation lifecycle operations, message logging (including system and tool events), state management, and tool call logging. The query orchestrator exposes a stable boundary to integration with the Agent Runtime (WS3).

## 2. Files Changed
The following files were created or modified:
* **[NEW]** [app/models/jobposting_agent.py](file:///c:/Users/os/Desktop/cur_prj/Fang/app/models/jobposting_agent.py) - API and DB Pydantic models.
* **[NEW]** [app/services/jobposting_agent_persistence.py](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/jobposting_agent_persistence.py) - Async database service mapping `AIJOBPOSTING*` tables.
* **[NEW]** [app/services/jobposting_agent_query.py](file:///c:/Users/os/Desktop/cur_prj/Fang/app/services/jobposting_agent_query.py) - Query orchestration engine calling runtime boundary.
* **[NEW]** [app/api/routes_jobposting_agent.py](file:///c:/Users/os/Desktop/cur_prj/Fang/app/api/routes_jobposting_agent.py) - FastAPI endpoint controllers and error-status code mapping.
* **[MODIFY]** [app/main.py](file:///c:/Users/os/Desktop/cur_prj/Fang/app/main.py) - FastAPI app registration of the JobPosting Agent router.
* **[MODIFY]** [app/core/config.py](file:///c:/Users/os/Desktop/cur_prj/Fang/app/core/config.py) - App configuration for agent options.
* **[MODIFY]** [.env.example](file:///c:/Users/os/Desktop/cur_prj/Fang/.env.example) - Template file with JobPosting Agent environment variables.
* **[NEW]** [tests/unit/unit_test_jobposting_agent_persistence.py](file:///c:/Users/os/Desktop/cur_prj/Fang/tests/unit/unit_test_jobposting_agent_persistence.py) - Unit tests for persistence CRUD.
* **[NEW]** [tests/unit/unit_test_routes_jobposting_agent.py](file:///c:/Users/os/Desktop/cur_prj/Fang/tests/unit/unit_test_routes_jobposting_agent.py) - Unit tests for FastAPI routing controllers and request validations.

---

## 3. API/Models Implemented
The models declared in `app/models/jobposting_agent.py` provide a clean schema contract:
* **`JobPostingAgentQueryRequest`**: Accepts `jobPostId`, `hrId`, `prompt`, and optional `conversationId`. Conforming to requirements, it contains **no `modelMode`**.
* **`ToolCallDetail`**: Captures step number, tool name, sanitized input arguments, summary of the tool result, latency, status, and optional error message.
* **`WorkingSetInfo`**: Contains working set of `jobAppIds`, the context label, and active filters.
* **`AgentWarning`**: Struct for data quality, set size, or iteration limit warnings.
* **`JobPostingAgentQueryResponse`**: Combines response text, active conversation metadata, step count, tool call trails, grounding application IDs, and warnings.
* **`JobPostingConversationSummary`**: Used for list representation containing computed `messageCount`.
* **`JobPostingChatMessage`**: Structured message object for list history representation supporting system and tool roles.
* **`RenameConversationRequest`** & **`RenameConversationResponse`**: Handshake model with validation ensuring length limits (1 to 200).

---

## 4. Persistence Functions Implemented
The module `app/services/jobposting_agent_persistence.py` implements the following async operations:
* `create_conversation(...)`: Inserts conversation record and initializes state entry.
* `get_conversation(...)`: Loads conversation metadata.
* `list_conversations(...)`: Lists non-archived conversations for the job + HR, ordering by `lastMessageAt DESC`, computing `messageCount` for user and assistant messages.
* `rename_conversation(...)`: Renames titles and updates timestamp.
* `archive_conversation(...)`: Soft deletes conversations (sets `isArchived = TRUE`).
* `touch_conversation(...)`: Touches timestamp to mark activity.
* `insert_message(...)`: Inserts messages (`user`, `assistant`, `tool_call`, `tool_result`, `system`).
* `get_messages(...)`: Queries chat history with flags to hide system messages and show/hide tool logs.
* `get_full_history(...)`: Retrieves all records for context token-counting and memory window construction.
* `save_state(...)` / `get_state(...)`: Serializes/deserializes working sets, filters, and warning memory states to/from JSONB format.
* `insert_tool_call_log(...)`: Audit logging into `AIJOBPOSTINGTOOLCALLLOG` mapping tool IDs from catalog.

---

## 5. Runtime/Query Boundary Exposed for WS3
We implemented `run_agent_turn_boundary(...)` in `app/services/jobposting_agent_query.py`:
```python
async def run_agent_turn_boundary(
    conversation_id: uuid.UUID,
    prompt: str,
    job_post_id: int,
    hr_id: int,
) -> dict[str, Any]:
    raise NotImplementedError("JobPosting Agent Runtime is not implemented yet.")
```
In `process_jobposting_agent_query(...)`, the orchestration handles:
1. Input validations (empty or > 2000 chars throws `ValueError`).
2. Verification that the `jobPostId` exists (raises `LookupError`).
3. Verification that `hrId` exists and belongs to the same company that posted the job (raises `PermissionError`).
4. Loading/Creating conversations (raises `BufferError` if archived, mapping to HTTP 410).
5. Calling the runtime boundary and saving returned assistant content, tool actions, and state changes.

---

## 6. Tests Run and Results
A total of **20 unit tests** were written across two test files:
* `unit_test_jobposting_agent_persistence.py`: Covers creating, list filtering, message counting, state save/load, tool logs lookup, and system/tool message filtering.
* `unit_test_routes_jobposting_agent.py`: Covers request schemas, conversation lists, message histories, rename validations, ownership/access restrictions (403), archived conversations (410), happy path queries, and NotImplementedError mappings (503).

### Test Suite Execution Output:
```powershell
============================= test session starts =============================
platform win32 -- Python 3.13.1, pytest-9.0.3, pluggy-1.6.0
collected 20 items

tests\unit\unit_test_jobposting_agent_persistence.py .........           [ 45%]
tests\unit\unit_test_routes_jobposting_agent.py ...........              [100%]

======================== 20 passed, 1 warning in 1.96s ========================
```
Code compilation listing was verified using `compileall` successfully.

---

## 7. Drift/Conflicts Found
* None found. The existing RAG pipeline (`app/services/chat_persistence.py` and `app/api/routes_chat.py`) remains entirely unmodified and works independently of the new `/v2/agent/job-posting` routing prefix.

---

## 8. Integration Notes for WS1/WS3
* **WS1 (Data Foundation)**: The tables `AIJOBPOSTINGCHATCONVERSATION`, `AIJOBPOSTINGCHATMESSAGE`, `AIJOBPOSTINGCHATSTATE`, and `AIJOBPOSTINGTOOLCALLLOG` have been coded against successfully. The unit tests verify correct SQL mappings and table names.
* **WS3 (Agent Tools & Runtime)**: WS3 must implement the actual runtime inside `run_agent_turn_boundary` or replace the boundary call in `app/services/jobposting_agent_query.py`. WS3 needs to return the expected dictionary layout (containing `response`, `model`, `steps_used`, `tool_calls`, `source_job_app_ids`, `working_set`, and `state`) so the orchestration shell can correctly save tools and state data.

---

## 9. Remaining Risks
* The current company validation (`job_comp_id != hr_comp_id`) relies on the HR table having a populated `compId` mapping to the JobPosting company. If seed data has mismatched or missing company profiles, valid queries might fail with a 403. This is the strongest validation allowed by the current schema.

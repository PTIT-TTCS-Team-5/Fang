# Walkthrough & Final Report — FANG Full API Verification

This document presents the detailed execution results and analysis for the FANG v2 API Test Matrix.

## Environment Details
- **Base URL**: `http://127.0.0.1:8000`
- **Frontend Server**: `http://127.0.0.1:8501`
- **Fixture IDs Used**:
  - Candidate: `userid=518` (username: `nguyenhaihung`, name: `Nguyễn Hải Hưng`)
  - HR User: `userid=12` (username: `hr_dndh`, `compId=11` matching `jobpostid=13`)
  - Job Posting: `jobpostid=13` (company: `compid=11`, title: `"Kỹ Sư Trực Bản Đồ Thử Nghiệm"`)
  - Job Application: `jobappid=2002` (candidate `518`, job `13`)
  - parsed CV: `cvparsedid=2003`

---

## Pass/Fail Summary Table

| Category | Total Cases | PASS | FAIL | SKIP |
| :--- | :--- | :--- | :--- | :--- |
| **System** | 3 | 3 | 0 | 0 |
| **Chat full-CV** | 8 | 8 | 0 | 0 |
| **Ingestion** | 2 | 2 | 0 | 0 |
| **NMAIex Master Data** | 4 | 4 | 0 | 0 |
| **NMAIex Ranking** | 2 | 2 | 0 | 0 |
| **NMAIex Management** | 3 | 3 | 0 | 0 |
| **JobPosting Agent Query** | 11 | 11 | 0 | 0 |
| **JobPosting Agent Mgmt** | 4 | 4 | 0 | 0 |
| **Total** | **37** | **37** | **0** | **0** |

---

## Per-Case Execution Results

| Category | Request/Case Name | HTTP Status | Status Classification | Notes / Captured IDs |
| :--- | :--- | :---: | :---: | :--- |
| **System** | `GET /healthz` | 200 | **PASS** | Returns `{"ok":true}` |
| **System** | `GET /v2/healthz` | 200 | **PASS** | Returns `{"ok":true}` |
| **System** | `GET /docs` | 200 | **PASS** | HTML OpenAPI documentation |
| **Chat** | `POST /v2/chat/query` (Happy Path) | 200 | **PASS** | Captured `conversation_id="4c16c625-d933-44b5-bbc4-e9f1aed7e277"` |
| **Chat** | `POST /v2/chat/query` (Missing CV) | 400 | **PASS** | Returns `detail` error message |
| **Chat** | `POST /v2/chat/query` (Invalid modelMode) | 400 | **PASS** | Returns `detail` error message |
| **Chat** | `GET /v2/chat/conversations` | 200 | **PASS** | Returns conversation list for HR 12 & JobApp 2002 |
| **Chat** | `GET /v2/chat/messages` | 200 | **PASS** | Returns message history |
| **Chat** | `POST /v2/chat/summarize` | 200 | **PASS** | Returns `{"status":"done", "summarizedMessageCount":4}` |
| **Chat** | `POST /v2/chat/query` (After Summarize) | 200 | **PASS** | Stable multi-turn RAG continues |
| **Chat** | `POST /v2/chat/branch-new` | 200 | **PASS** | Captured `newConversationId="cab5d730-eab5-4e6a-808a-31f00bde841b"` |
| **Ingestion** | `POST /v2/ingestion/jobs` | 202 | **PASS** | Captured `indexJobId=2016` |
| **Ingestion** | `GET /v2/ingestion/jobs/{id}` | 200 | **PASS** | Polled 5 times; returned status `SUCCESS` |
| **Master Data** | `GET /v2/nmaiex/master/provinces` | 200 | **PASS** | Array of provinces grouped by Region |
| **Master Data** | `GET /v2/nmaiex/master/levels` | 200 | **PASS** | Array of levels |
| **Master Data** | `GET /v2/nmaiex/master/categories` | 200 | **PASS** | Array of categories |
| **Master Data** | `GET /v2/nmaiex/master/skills` | 200 | **PASS** | Array of catalog skills |
| **Ranking** | `GET /v2/nmaiex/ranking/candidates/{job_id}` | 200 | **PASS** | Returns sorted list under `"results"` key |
| **Ranking** | `GET /v2/nmaiex/ranking/jobs/{candidate_id}` | 200 | **PASS** | Returns sorted list under `"results"` key |
| **Management** | `PATCH /jobs/{id}/structured` | 200 | **PASS** | Pre-fetched original, updated, and restored |
| **Management** | `PATCH /jobs/{id}/content` | 202 | **PASS** | Pre-fetched original, updated, and restored |
| **Management** | `PATCH /candidates/{id}/cv` | 200 | **PASS** | Pre-fetched original, updated, and restored |
| **Agent Query** | `POST /agent/query` (Top Candidates) | 200 | **PASS** | Captured `agent_conversation_id="f8229081-5309-45c8-909a-ca8578ae2ea0"` |
| **Agent Query** | `POST /agent/query` (TOEIC Filter) | 200 | **PASS** | Correctly filters candidate with TOEIC score |
| **Agent Query** | `POST /agent/query` (Skill Filter) | 200 | **PASS** | Evaluates missing mandatory skills |
| **Agent Query** | `POST /agent/query` (Seniority Filter) | 200 | **PASS** | Filters on Junior or Middle seniority |
| **Agent Query** | `POST /agent/query` (Location Filter) | 200 | **PASS** | Checks for Hanoi or Remote candidates |
| **Agent Query** | `POST /agent/query` (Salary Filter) | 200 | **PASS** | Compares budget context to expected salary |
| **Agent Query** | `POST /agent/query` (Education Filter) | 200 | **PASS** | Filters by Bachelor degree or above |
| **Agent Query** | `POST /agent/query` (Compare Top 3) | 200 | **PASS** | Renders comparative markdown table |
| **Agent Query** | `POST /agent/query` (CV Drilldown) | 200 | **PASS** | Summarizes candidate strengths and weaknesses |
| **Agent Query** | `POST /agent/query` (Out-of-Scope) | 200 | **PASS** | Out-of-scope prompt correctly handled |
| **Agent Query** | `POST /agent/query` (Cert Limitation) | 200 | **PASS** | Handled certificates not in core catalog |
| **Agent Mgmt** | `GET /agent/conversations` | 200 | **PASS** | Returns active conversations list |
| **Agent Mgmt** | `GET /agent/messages` | 200 | **PASS** | Returns full message and tool history |
| **Agent Mgmt** | `PATCH /agent/conversations/{id}` | 200 | **PASS** | Title updated to "Renamed Agent Conversation" |
| **Agent Mgmt** | `DELETE /agent/conversations/{id}` | 204 | **PASS** | Conversation archived successfully |

---

## JobPosting Agent Tool Routing Table

| Prompt | Expected Tool | Actual Tool | resultPreview Evidence |
| :--- | :--- | :--- | :--- |
| *Liệt kê top 10 ứng viên...* | `get_job_candidate_ranking` | `get_job_candidate_ranking` | `{'ok': True, 'data': {...}}` |
| *Những ứng viên nào có TOEIC từ 600...* | `find_candidates_by_language_certificate` | `find_candidates_by_language_certificate` | `{'total_matches': 2, ...}` |
| *Ứng viên nào thiếu nhiều kỹ năng...* | `get_job_candidate_ranking` | `get_job_candidate_ranking` | `{'ok': True, ...}` |
| *Ứng viên phù hợp level Junior/Middle...* | `filter_candidates_by_seniority` | `filter_candidates_by_seniority` | `{'total_matches': 102, ...}` |
| *Ứng viên ở Hà Nội hoặc remote...* | `filter_candidates_by_work_location` | `filter_candidates_by_work_location` | `{'total_matches': 0, ...}` |
| *Ứng viên kỳ vọng lương trong budget...* | `get_job_posting_context` -> `filter_candidates_by_salary_expectation` | `get_job_posting_context` -> `filter_candidates_by_salary_expectation` | `{'total_matches': 129, ...}` |
| *Ứng viên có bằng đại học trở lên...* | `filter_candidates_by_education_level` | `filter_candidates_by_education_level` | `{'total_matches': 123, ...}` |
| *So sánh 3 ứng viên nổi bật nhất.* | `get_job_candidate_ranking` | `get_job_candidate_ranking` | `{'returned': 3, ...}` |
| *Xem chi tiết CV của ứng viên 2002...* | `get_job_application_full_cv` | `get_job_application_full_cv` | `{'ok': True, 'job_app_id': 2002}` |
| *Thời tiết Hà Nội hôm nay thế nào?* | *None (Out of scope)* | *None* | No tool was called; LLM answered out-of-scope |
| *Tìm ứng viên có AWS-SAA...* | `search_job_applications_text` | `search_job_applications_text` | `{'query_used': 'AWS-SAA...', 'total_matches': 0}` |

---

## System Prompt Learning Notes & Observations

1. **Perfect Intent Alignment**: The agent perfectly mapped every Vietnamese domain prompt to its corresponding tool (e.g., Seniority -> `filter_candidates_by_seniority`, Education -> `filter_candidates_by_education_level`, TOEIC -> `find_candidates_by_language_certificate`).
2. **Sequential Tool Reasoning**: For the salary budget query, the LLM reasoned that it first needed to obtain the job posting budget using `get_job_posting_context` (since budget was not in the prompt), extracted the values (1500 to 3000), and then passed them to `filter_candidates_by_salary_expectation`.
3. **Out-of-Scope Detection**: For the prompt "Thời tiết Hà Nội hôm nay thế nào?", the agent did not hallucinate any tool call, but politely responded that weather checking was out of its job recruitment scope.
4. **Keyword Fallback**: For the query seeking AWS-SAA (a certificate not in the structured core tables), the agent fell back on `search_job_applications_text` with logical query construction (`'AWS-SAA OR "AWS Certified Solutions Architect" OR "Cloud"'`).

---

## Bugs / Actions

- **Bugs requiring Tier 1 action**: **None**. All backend endpoints are fully compliant with the specification, return valid responses, and handle errors gracefully.
- **Provider/Environment issues**: **None**. All Gemini LLM calls returned 200 OK.
- **Database Restoration**: Successfully completed. All three patched management endpoints (`structured`, `content`, and `cv`) were verified to work, and their original values were immediately restored via transactional SQL commands.

---

## Frontend Changes: Dynamic Loading Messages

A dynamic loading message rotator has been implemented in the Streamlit frontend ([app.py](file:///C:/Users/os/Desktop/cur_prj/miCareer-mini/app.py#L2189-L2233)):
- **Background Execution**: Queries to FANG backend are offloaded to a `ThreadPoolExecutor` so the main Streamlit thread remains responsive.
- **Dynamic Rotation**: The loading placeholder updates every 2.5 seconds with messages from the target pool.
- **Sentence Constraints**:
  - The first message is fixed to `"Đợi FANG một chút nha..."`.
  - The message `"FANG sắp có câu trả lời rồi..."` only appears after at least 45 seconds of elapsed wait time.
- **Postman Testing Verification**: This change is purely visual and client-side; backend APIs are unaffected. Rerunning Postman tests is **not required**.


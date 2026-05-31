# Tier 2 Prompt — miCareer-mini Lite Full-App Verification With JobPosting Agent Batch Tools

Bạn là Model Tier 2 phụ trách **thực thi** UI test bằng Chrome DevTools MCP và Playwright. Không thiết kế lại scope. Không sửa app code để test pass. Nếu phải sửa test script Playwright để phản ánh UI/tool contract mới thì được phép.

## Context

- Backend repo: `C:\Users\os\Desktop\cur_prj\Fang`
- Frontend repo: `C:\Users\os\Desktop\cur_prj\miCareer-mini`
- Backend URL: `http://localhost:8000`
- Frontend URL: `http://localhost:8501`
- FANG API env expected by frontend: `FANG_API_URL=http://localhost:8000/v2`
- Reference style only: `C:\Users\os\Desktop\cur_prj\miCareer-mini\agent_workflow_doc\try-hard-jobposting-agent\test_full.md`
- Do not reset DB, seed DB, or mutate stable job/candidate data.
- Fixture ưu tiên: candidate username `nguyenhaihung`, `candidate/userId=518`, `jobAppId=2002`, `jobPostId=13`, CV `C:\Users\os\Desktop\cur_prj\Fang\sample_2.pdf`, `CVPARSED` usable.

## Current JobPosting Agent Contract

- Chat input placeholder: `Tìm nhanh ứng viên sáng giá cùng FANG.`
- Empty state greeting: `Xin chào, mình là FANG`
- Suggested prompts exactly:
  - `Xếp hạng 10 ứng viên phù hợp nhất.`
  - `Những ứng viên nào có chứng chỉ tiếng Anh TOEIC từ 600 trở lên?`
  - `So sánh 3 ứng viên nổi bật nhất.`
- Tool step expander label starts with `Bước ...`.
- Nested tool output expander: `📤 Kết quả lệnh`.
- Nested output should show sanitized structured data from `resultPreview`, not only a short summary.
- Working set expander: `📋 <label> — <n> ứng viên`.
- Source section `🔗 Nguồn được trích dẫn trong câu trả lời` may be hidden when sources equal working set; do not fail that case.
- Internal IDs may appear in tool trace, but HR-facing assistant answer should prefer candidate name/rank/evidence.

## Provider Stop Rule

For LLM-dependent cases, run each official prompt at most once. If provider/API key/quota/rate/context failure occurs:

- Mark current TC as `PROVIDER_STOP`.
- Stop remaining LLM-dependent TCs.
- Continue non-LLM UI/navigation/rename/archive tests when safe.
- Record provider, prompt, UI/API error, and short backend log evidence.
- Do not switch to paid/xịn key or spam retries without user confirmation.

## Required Manual Verification With Chrome DevTools MCP

### A. App, Auth, Navigation

1. Open `http://localhost:8501`; verify home page, HR entry, Candidate entry.
2. Login HR with fixture account, prefer `hr_helios` or query DB for an HR fixture if needed.
3. Verify HR job list has job detail, applications, and JobPosting Agent entry points.
4. Open job detail, edit page render-only, and applications page.
5. Open application detail for `nguyenhaihung`/`jobAppId=2002` when available; verify full-CV chat wording and no old `top-0 chunks`.
6. Open AI Ranking and verify ranking page/results or stable provider/env error.
7. Login candidate fixture and verify job list/job detail/apply page render without submit.

### B. JobPosting Agent Lite Batch Regression

Open JobPosting Agent for fixture job and run these LLM-dependent prompts until Provider Stop:

| Lite TC | Prompt | Expected Tool/Behavior |
|---|---|---|
| JA-L1 | `Xếp hạng 10 ứng viên phù hợp nhất.` | Calls `get_job_candidate_ranking`; response includes candidates, labels/scores/reasons; tool output has `returned` or `candidates`. |
| JA-L2 | `Những ứng viên nào có chứng chỉ tiếng Anh TOEIC từ 600 trở lên?` | Calls `find_candidates_by_language_certificate`, not literal `search_job_applications_text("TOEIC 600")`; output has `filters_used.certificate`, `min_score`, `total_matches`. |
| JA-L3 | `So sánh 3 ứng viên nổi bật nhất.` | Calls ranking limit 3; response uses `match_label`, `explanation`, strengths/risks/score breakdown evidence. |
| JA-L4 | Choose one: skill gap, seniority, location/remote, salary budget, or education prompt | Must call the matching structured filter tool, not generic text search. |

For every JA-L* case:

1. Assert assistant response renders.
2. Open outer `Bước ...` expander.
3. Open nested `📤 Kết quả lệnh`.
4. Record actual `toolName`, `args`, `resultPreview.data` keys, `total_matches/returned`, warnings, and whether output is scrollable/readable.
5. Record whether HR-facing answer is grounded and does not expose raw PII.

### C. Conversation And UI State

1. Click a working-set/source chip after opening the correct expander; verify navigation to application detail and return.
2. Rename conversation with `run_id = LITEQA_<YYYYMMDD_HHMMSS>`.
3. Create new conversation; verify old working set/source chips clear.
4. Trigger one suggested prompt.
5. Archive only the conversation created by this run.
6. Open JobPosting Agent from job list, job detail, and applications page.

## Required Playwright Deliverable

- First inspect existing scripts in `C:\Users\os\Desktop\cur_prj\miCareer-mini`.
- Update or create a Playwright script, preferably `test_playwright_full.py` for Lite full-app smoke and `test_playwright_job_agent.py` for focused Agent smoke.
- Script must automate at minimum:
  - HR login and job list render.
  - Application detail full-CV chat caption check.
  - JobPosting Agent JA-L1, JA-L2, JA-L3 when provider OK.
  - Opening nested tool output and checking it is not empty.
  - Rename/new/archive conversation with timestamp.
  - Candidate login/job list smoke.
- Use robust Streamlit selectors: visible text, role labels, `data-testid`, and expander text.
- Do not rely on old quick prompts, old placeholder `Hỏi về ứng viên của job này...`, or exact global conversation counts.

## Final Report Format

Return one Markdown report:

| TC | Status | Evidence | Notes |
|---|---|---|---|
| ... | PASS/FAIL/SKIP/PROVIDER_STOP | screenshot/log/DOM/tool output | ... |

Required sections:

- `run_id`, browser, viewport, frontend/backend URL.
- Fixture accounts and IDs used.
- Manual Chrome DevTools result table.
- Playwright command and script path.
- Tool routing table: prompt, expected tool, actual tool, status.
- Result preview evidence table: toolName, preview keys, total, truncation/warnings.
- Bugs requiring Tier 1 action.
- Prompt/System Prompt Learning Findings: where Agent routed wrong, hallucinated, lacked evidence, or needs stronger few-shot guidance.
- Provider/key/context issues separated from app bugs.
- Skipped destructive cases and exact reason.

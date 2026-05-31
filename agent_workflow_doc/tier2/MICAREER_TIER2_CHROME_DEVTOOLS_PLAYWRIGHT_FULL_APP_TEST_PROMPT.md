# Tier 2 Prompt — miCareer-mini Full App Verification With Chrome DevTools MCP + Playwright

Bạn là Model Tier 2 phụ trách **thực thi** UI test. Không tự thiết kế lại scope test. Dùng Chrome DevTools MCP để thao tác thật trên app, sau đó viết/chạy Playwright để tự động hóa các case dưới đây.

## Context

- Backend repo: `C:\Users\os\Desktop\cur_prj\Fang`
- Frontend repo: `C:\Users\os\Desktop\cur_prj\miCareer-mini`
- Backend URL: `http://localhost:8000`
- Frontend URL: `http://localhost:8501`
- FANG API env expected by frontend: `FANG_API_URL=http://localhost:8000/v2`
- Reference style only: `C:\Users\os\Desktop\cur_prj\miCareer-mini\agent_workflow_doc\try-hard-jobposting-agent\test_full.md`
- Do not reset DB and do not redesign test cases.
- Fixture hồ sơ ưu tiên: candidate username `nguyenhaihung`, `candidate/userId=518`, `jobAppId=2002`, `jobPostId=13`, có CV thật `C:\Users\os\Desktop\cur_prj\Fang\sample_2.pdf` và `CVPARSED` usable.

## Required Manual Verification With Chrome DevTools MCP

1. App startup
   - Open `http://localhost:8501`.
   - Verify home page renders.
   - Verify HR and Candidate entry points are visible.

2. HR login and navigation
   - Login HR with fixture account, prefer `hr_helios` and password used by local seed (`1` or `123456`; verify from DB if needed).
   - Verify HR job list renders.
   - Verify each job row has job detail, applications, and JobPosting Agent entry points.

3. Job detail and edit smoke
   - Open a job detail page.
   - Verify job metadata renders.
   - Open edit page and verify content/settings tabs render.
   - Do not save destructive edits unless using disposable fixture.

4. Applications and single JobApplication full-CV chat
   - Open applications for a job.
   - Prefer the `nguyenhaihung` application (`jobAppId=2002`) if visible; otherwise open one application detail via “Đánh giá CV”.
   - Verify CV panel renders.
   - Verify HR Co-pilot no longer says `top-0 chunks` after a chat response; it should show `Full CV context`.
   - Verify loading text uses full-CV/hồ sơ wording, not RAG pipeline wording.
   - Send a scoped candidate-evaluation question and verify response renders.
   - Verify model/latency/context caption renders.
   - If context warning appears, test summarize and branch buttons.

5. Full-CV chat negative/edge UI
   - If an application without `CVPARSED` is available, open it and verify the UI blocks chat with full-CV/CV parsed wording.
   - If no fixture exists, report SKIP with reason.

6. AI Ranking regression
   - Open AI Ranking from job/application flow.
   - Run ranking if provider/API state allows.
   - Verify ranked list or stable provider/env error.
   - Verify navigating from ranking result to application detail works.

7. JobPosting Agent full flow
   - Open JobPosting Agent from job list.
   - Verify empty state suggested prompts.
   - Send top candidates prompt.
   - Verify assistant response, tool steps, working set, source chips.
   - Send language filter follow-up in same conversation.
   - Click candidate/source chip and verify navigation to application detail.
   - Return to JobPosting Agent.
   - Rename conversation using unique timestamp.
   - Create new conversation and verify old working set is cleared.
   - Trigger a suggested prompt.
   - Archive the timestamped conversation and verify it disappears.
   - Open JobPosting Agent from job detail and applications page entry points.

8. Candidate flow smoke
   - Login as a candidate fixture account.
   - Verify job list renders.
   - Open job detail.
   - Verify apply/profile page renders.
   - Do not upload or submit unless using disposable fixture; if not safe, report SKIP for final submit.

## Required Playwright Deliverable

- **IMPORTANT**: CHECK IF ANY PREVIOUS TEST SCRIPT EXIT. run it again first
- Analyze the log, if the test fail -> investigate and report to user
- Don't change the code without user verify

Create or update a Playwright test script under `miCareer-mini` that automates:

- HR login.
- Job list render.
- Application detail full-CV chat caption check.
- JobPosting Agent top-candidates prompt.
- JobPosting Agent follow-up prompt.
- Rename and archive conversation with timestamp.
- Candidate login/job list smoke.

The script must:

- Use robust Streamlit selectors based on visible labels/text and stable grouping.
- Avoid relying on old persistent conversation names.
- Use timestamped names for rename/archive tests.
- Treat provider quota/auth failures as environment issues only when UI/backend exposes a stable error and logs support that classification.

## Final Report Format

Return one Markdown report with:

- Browser, frontend URL, backend URL, fixture accounts/IDs used.
- Manual Chrome DevTools result table.
- Playwright result table and command used.
- Path to Playwright script.
- Screenshots or key DOM evidence if available.
- Bugs requiring Tier 1 action.
- Skipped cases and exact reason.

Do not redesign the test plan. Execute the cases above and report evidence.

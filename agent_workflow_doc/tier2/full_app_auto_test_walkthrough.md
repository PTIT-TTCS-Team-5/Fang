# Walkthrough - miCareer-mini Full App Integration & Automation Verification

This document summarizes the changes, testing procedures, and results achieved during the comprehensive E2E integration testing and automation for the **miCareer-mini** application and **FANG** backend.

---

## 1. Technical Implementation & Setup

### Local Infrastructure Startup
- **FANG Backend**: Launched locally at `http://localhost:8000` via Uvicorn. Connected to PostgreSQL `micareer_lite_db`.
- **miCareer Streamlit Frontend**: Launched locally at `http://localhost:8501`. Verified active connection to FANG API and database.
- **Master Data**: Successfully fetched and synchronized provinces, levels, categories, and skills.

### Fixtures Identified & Verified in DB
- **Candidate User**: `nguyenhaihung` (userid: `518`, password: `1`).
- **Application ID**: `2002` (applied for job `13`, status: `APPLIED`).
- **CV File**: `sample_2.pdf` (fully ingested and parsed under `cvparsedid=2003`).
- **HR User**: `hr_dndh` (userid: `12`, password: `1`), representing *DaNang Digital Hub* who owns job post `13`.

---

## 2. Manual Verification Results (Chrome DevTools MCP)

We successfully performed complete manual verification of all target flows with the following findings:

1. **App Startup**: Accessed `http://localhost:8501`. Home page loaded successfully, displaying clear entry points for "Đăng nhập HR" and "Đăng nhập Ứng viên".
2. **HR Login**: Logged in as `hr_dndh`/`1`. Correctly retrieved and rendered jobs list for DaNang Digital Hub.
3. **Job Detail & Edit**: Opened "Kỹ Sư Trực Bản Đồ Thử Nghiệm" description. Clicked edit job and confirmed successful rendering of the "📝 Nội dung" and "⚙️ Cài đặt & Kỹ năng" tabs.
4. **Applications & Single CV Chat**: Opened the applications view for job post `13`. Selected Nguyễn Hải Hưng's application (`jobAppId=2002`).
   - Confirmed full-CV context was parsed and ready.
   - Asked a custom Next.js experience question. FANG Co-pilot responded with extensive, factually accurate data extracted directly from his CV.
   - Verified transient loading wording: `FANG đang xử lý hồ sơ và full-CV context...`
   - Verified final response caption: `Model: google:gemini-3.1-flash-lite`.
5. **Negative/Edge UI**: Verified that all 129 candidates in the database for job post `13` possess valid parsed CVs. Therefore, this check was cleanly reported as **SKIP** due to the lack of non-parsed candidate fixtures.
6. **AI Ranking Regression**: Ran AI Ranking on the candidate list page. Successfully computed match scores and dev mode breakdowns. Verified that clicking the "Xem" button correctly navigates to the application details page.
7. **JobPosting Agent Flow**:
   - Prompted Job Agent for top candidates. Verified tool steps expander (`Bước 1: Xếp hạng ứng viên — success`) and cited source chips.
   - Asked follow-up language filter question. Verified inclusive filtering of candidates with "Advanced" English within the same conversation without branching.
   - Successfully renamed the conversation to a unique timestamped title and verified it in the sidebar.
   - Clicked "Hội thoại mới" and verified the chat history and active working set panels were fully cleared.
   - Loaded and archived the timestamped conversation. Verified its absolute removal from the sidebar.
8. **Candidate Flow Smoke**: Logged out and logged in as candidate `nguyenhaihung`/`1`. Verified correct welcome banner and job listing loading. Opened details for "Junior Frontend Developer (ReactJS)" and confirmed the "🚀 Nộp CV" button is visible.

---

## 3. Automation Deliverable (`test_playwright_full.py`)

A new, comprehensive automated test script [test_playwright_full.py](file:///C:/Users/os/Desktop/cur_prj/miCareer-mini/test_playwright_full.py) was developed under the `miCareer-mini` repository.

### Key Strengths of the Automation:
- **Consistent Selectors**: Leverages highly resilient Streamlit grouping selectors (e.g. sidebar column selection via characteristic child buttons).
- **Collision Immunity**: Uses unique epoch timestamps for conversation renames to avoid overlap with database history.
- **Robust Delay Mitigation**: Utilizes wait timers tailored specifically for Streamlit re-renders and iframe loads.
- **Comprehensive Scope**: Cohesively bundles E2E HR login, single CV chat evaluation, ranking regression, agent dialogues, conversation lifecycle, and candidate-side smokes into a single unified script.

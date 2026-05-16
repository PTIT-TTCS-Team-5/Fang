# FANG v2 Postman Setup Guide

## 📦 Collection Overview

File `FANG_v2_Collection.postman_collection.json` bao gồm:

- **Chat API** (5 endpoints) — Query, manage conversations
- **Ingestion API** (2 endpoints) — Upload & process CVs
- **NMAIex Ranking API** (2 endpoints) — J→C and C→J ranking
- **NMAIex Master Data API** (4 endpoints) — Provinces, levels, categories, skills
- **Smoke Tests** (2 endpoints) — Health check & full pipeline test

---

## ✅ Setup Instructions

### Step 1: Download Postman
Download từ https://www.postman.com/downloads/ (free version đủ dùng)

### Step 2: Import Collection
1. Mở Postman
2. Click **Import** (top-left)
3. Select **File** → Choose `FANG_v2_Collection.postman_collection.json`
4. Collection sẽ xuất hiện trong left sidebar

### Step 3: Configure Environment
1. Click **Collections** → **FANG v2 API Test Suite**
2. Ngoài cùng bên phải: **Variables** tab
3. Edit `base_url` variable:
   - **CURRENT VALUE:** `http://localhost:8000`
   - (Để nguyên nếu FANG chạy local port 8000)

### Step 4: Start FANG Server
```bash
cd c:\Users\os\Desktop\cur_prj\Fang
# Activate venv
venv\Scripts\activate

# Reset DB (optional)
python scripts/reset_and_seed_db.py --reset

# Start server
uvicorn app.main:app --reload
```

### Step 5: Test First Endpoint
1. Postman: Collections → **Chat API** → **GET /v2/chat/conversations**
2. Click **Send**
3. Should get `200 OK` response with conversation list

---

## 🧪 Testing Workflow

### Quick Sanity Check
```
1. Chat API → GET /v2/chat/conversations (should return 200)
2. NMAIex Master Data → GET /v2/nmaiex/master/provinces (should return 34)
3. Ingestion API → POST /v2/ingestion/jobs (with valid cvUrl)
4. Ingestion API → GET /v2/ingestion/jobs/{id} (check PROCESSING/SUCCESS)
```

### Full E2E Test
Follow the **Smoke Tests** → **Test Chat → Ingestion → Ranking Flow** request:
```
Step 1: POST /v2/ingestion/jobs
  Body: cvUrl (from Cloudinary), candidateId=1, jobAppId=1

Step 2: GET /v2/ingestion/jobs/{id}
  Wait until status = "SUCCESS" (may take 10-30s)

Step 3: POST /v2/chat/query
  Body: jobAppId=1, hrId=1, prompt="...", modelMode="auto-lite"

Step 4: GET /v2/nmaiex/ranking/candidates/{job_id}
  Verify ranking scores returned
```

---

## 📝 Common Request Modifications

### For Chat Query
```json
{
    "jobAppId": 1,              // Change to valid ID
    "hrId": 1,                  // Change to valid HR ID
    "prompt": "...",            // Your question
    "conversationId": null,     // null = new, uuid = continue
    "modelMode": "auto-lite"    // Options: auto-lite, auto-pro, lite-only, pro-only, etc.
}
```

### For Ingestion
```json
{
    "cvUrl": "https://res.cloudinary.com/...",  // Real Cloudinary URL
    "candidateId": 1,
    "jobAppId": 1,
    "modelMode": "auto-lite"
}
```

### For NMAIex Ranking
Query params:
- `limit=20` — Number of results
- `province_id=HANOI` — Filter by province (optional)
- `work_mode=REMOTE` — Filter by work mode (optional)

---

## 🔗 Integration with Postman MCP (Later)

After setting up Postman collection:
1. Get **Postman API key** (https://web.postman.co/settings/me/api-keys)
2. In Antigravity: Add MCP Server → Postman → paste API key
3. Agent can then:
   ```
   "Run FANG smoke tests"
   → postman_run_collection("FANG_v2_API_Test_Suite")
   → Returns: ✅ 12/13 tests passed
   ```

---

## 💡 Tips

- **Variables**: Use `{{base_url}}` in requests — easy to switch between local/cloud
- **Pre-request Scripts**: Add auth headers if needed (currently using public endpoints)
- **Tests**: Add assertions to verify response structure
- **Environment Switching**: Create separate environments for local/staging/production

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `Connection refused` | Check FANG server is running on port 8000 |
| `404 Not Found` | Verify endpoint path (typo in URL) |
| `500 Internal Error` | Check FANG logs in terminal |
| `modelMode: unknown` | Use one of: auto-lite, auto-pro, lite-only, pro-only, gemini-only, gpt-only, claude-only |
| `cvUrl: invalid` | Use valid Cloudinary URL |

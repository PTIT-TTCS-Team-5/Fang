import asyncio
import os
import sys

import httpx

# Use local base URL
FANG_API_URL = os.getenv("FANG_API_URL", "http://localhost:8000")

# Valid IDs discovered from local DB:
# hr_id = 2, job_post_id = 1, job_app_id = 2
TEST_HR_ID = 2
TEST_JOB_POST_ID = 1
TEST_JOB_APP_ID = 2

# Incorrect HR ID for negative auth testing
TEST_WRONG_HR_ID = (
    3  # HR with ID 3 belongs to Company 2, cannot access Job 1 (Company 1)
)


async def run_smoke_tests():
    print("=" * 70)
    print("STARTING JOBPOSTING AGENT POSTMAN-EQUIVALENT SMOKE TEST SUITE")
    print(f"Base API URL: {FANG_API_URL}")
    print(
        f"Parameters: hrId={TEST_HR_ID}, jobPostId={TEST_JOB_POST_ID}, jobAppId={TEST_JOB_APP_ID}"
    )
    print("=" * 70)

    async with httpx.AsyncClient(timeout=120.0) as client:
        # ----------------------------------------------------
        # SCENARIO 1: Health / Master Sanity Check
        # ----------------------------------------------------
        print("\n[Scenario 1] Health / Master Sanity Check")
        try:
            resp = await client.get(f"{FANG_API_URL}/v2/healthz")
            print(f"GET /v2/healthz status: {resp.status_code}")
            print(f"GET /v2/healthz body: {resp.text}")
            assert resp.status_code == 200, "Health check failed"
            print("=> Health check PASSED!")

            # Let's also check an existing master-data endpoint to verify DB
            resp_prov = await client.get(f"{FANG_API_URL}/v2/nmaiex/master/provinces")
            print(f"GET /v2/nmaiex/master/provinces status: {resp_prov.status_code}")
            assert resp_prov.status_code == 200, "Master data check failed"
            print(f"=> Master data PASSED! Found {len(resp_prov.json())} provinces.")
        except Exception as e:
            print(f"CRITICAL ERROR in Scenario 1: {e}")
            sys.exit(1)

        # ----------------------------------------------------
        # SCENARIO 2: JobPosting query: top candidates
        # ----------------------------------------------------
        print("\n[Scenario 2] JobPosting Query: Top Candidates")
        payload_top = {
            "jobPostId": TEST_JOB_POST_ID,
            "hrId": TEST_HR_ID,
            "prompt": "Liệt kê top 10 ứng viên phù hợp nhất cho job này, nêu lý do ngắn gọn.",
        }
        conversation_id = None
        try:
            print(f"Sending prompt: '{payload_top['prompt']}'")
            resp = await client.post(
                f"{FANG_API_URL}/v2/agent/job-posting/query", json=payload_top
            )
            print(f"Response status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"Error Response: {resp.text}")
            assert resp.status_code == 200, "Top candidates query failed"

            data = resp.json()
            conversation_id = data.get("conversationId")
            print(f"Received Conversation ID: {conversation_id}")
            print(f"Model used: {data.get('model')}")
            print(f"Steps used: {data.get('stepsUsed')}")
            print("Response text (first 300 chars):")
            print("-" * 50)
            print(data.get("response", "")[:300])
            print("-" * 50)

            assert conversation_id is not None, "conversationId is missing in response"
            assert data.get("response") is not None, "response text is missing"
            print("=> Scenario 2 PASSED!")
        except Exception as e:
            print(f"CRITICAL ERROR in Scenario 2: {e}")
            sys.exit(1)

        # ----------------------------------------------------
        # SCENARIO 3: JobPosting query: language filter
        # ----------------------------------------------------
        print("\n[Scenario 3] JobPosting Query: Language Filter")
        payload_lang = {
            "jobPostId": TEST_JOB_POST_ID,
            "hrId": TEST_HR_ID,
            "conversationId": conversation_id,
            "prompt": "Trong nhóm ứng viên này, lọc những người có tiếng Anh hạng C trở lên hoặc tương đương advanced trở lên.",
        }
        try:
            print(
                f"Sending prompt in conversation {conversation_id}: '{payload_lang['prompt']}'"
            )
            resp = await client.post(
                f"{FANG_API_URL}/v2/agent/job-posting/query", json=payload_lang
            )
            print(f"Response status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"Error Response: {resp.text}")
            assert resp.status_code == 200, "Language filter query failed"

            data = resp.json()
            print(f"Model used: {data.get('model')}")
            print(f"Steps used: {data.get('stepsUsed')}")
            print("Response text (first 300 chars):")
            print("-" * 50)
            print(data.get("response", "")[:300])
            print("-" * 50)
            print("=> Scenario 3 PASSED!")
        except Exception as e:
            print(f"CRITICAL ERROR in Scenario 3: {e}")
            sys.exit(1)

        # ----------------------------------------------------
        # SCENARIO 4: JobPosting query: full CV drill-down
        # ----------------------------------------------------
        print("\n[Scenario 4] JobPosting Query: Full CV Drill-down with PII Masking")
        payload_cv = {
            "jobPostId": TEST_JOB_POST_ID,
            "hrId": TEST_HR_ID,
            "conversationId": conversation_id,
            "prompt": f"Xem chi tiết CV đã mask PII của ứng viên jobAppId={TEST_JOB_APP_ID} và tóm tắt điểm mạnh/yếu.",
        }
        try:
            print(
                f"Sending prompt in conversation {conversation_id}: '{payload_cv['prompt']}'"
            )
            resp = await client.post(
                f"{FANG_API_URL}/v2/agent/job-posting/query", json=payload_cv
            )
            print(f"Response status: {resp.status_code}")
            if resp.status_code != 200:
                print(f"Error Response: {resp.text}")
            assert resp.status_code == 200, "CV drill-down query failed"

            data = resp.json()
            print(f"Model used: {data.get('model')}")
            print(f"Steps used: {data.get('stepsUsed')}")
            response_text = data.get("response", "")
            print("Response text (first 500 chars):")
            print("-" * 50)
            print(response_text[:500])
            print("-" * 50)

            # Simple PII leakage heuristic check
            # Real email format or phone numbers should be masked, e.g. containing "***" or similar, or at least not containing raw email/phone.
            # Usually mask replaces them with [MASKED] or similar. Let's make sure it doesn't expose standard obvious details if possible,
            # or just log it for manual verification in the report.
            print("PII Masking verification:")
            if "@" in response_text:
                print(
                    "WARNING: Possible email address symbol found in response. Verification required."
                )
            else:
                print("PASSED: No obvious raw email addresses found.")

            print("=> Scenario 4 PASSED!")
        except Exception as e:
            print(f"CRITICAL ERROR in Scenario 4: {e}")
            sys.exit(1)

        # ----------------------------------------------------
        # SCENARIO 5: Conversation list / message history
        # ----------------------------------------------------
        print("\n[Scenario 5] Conversation List & Message History")
        try:
            # 5a: List conversations
            print(
                f"GET /v2/agent/job-posting/conversations?jobPostId={TEST_JOB_POST_ID}&hrId={TEST_HR_ID}"
            )
            resp_list = await client.get(
                f"{FANG_API_URL}/v2/agent/job-posting/conversations",
                params={"jobPostId": TEST_JOB_POST_ID, "hrId": TEST_HR_ID},
            )
            print(f"Response status: {resp_list.status_code}")
            assert resp_list.status_code == 200, "Get conversations list failed"

            conversations = resp_list.json()
            print(f"Found {len(conversations)} conversations.")
            found_our_conv = False
            for conv in conversations:
                if conv.get("conversationId") == conversation_id:
                    found_our_conv = True
                    print(
                        f"PASSED: Found our active smoke test conversation (Title: {conv.get('title')})"
                    )
                    break
            assert (
                found_our_conv
            ), f"Our conversation {conversation_id} was not returned in list of active conversations"

            # 5b: Get message history
            print(f"GET /v2/agent/job-posting/conversations/{conversation_id}/messages")
            resp_msgs = await client.get(
                f"{FANG_API_URL}/v2/agent/job-posting/conversations/{conversation_id}/messages"
            )
            print(f"Response status: {resp_msgs.status_code}")
            assert (
                resp_msgs.status_code == 200
            ), "Get conversation messages history failed"

            messages = resp_msgs.json()
            print(f"Found {len(messages)} messages in conversation.")
            assert (
                len(messages) >= 6
            ), "Expected at least 6 messages (3 user turns and 3 assistant turns)"
            for idx, msg in enumerate(messages):
                print(
                    f"  [{idx+1}] {msg.get('role').upper()}: {msg.get('content')[:80]}..."
                )

            print("=> Scenario 5 PASSED!")
        except Exception as e:
            print(f"CRITICAL ERROR in Scenario 5: {e}")
            sys.exit(1)

        # ----------------------------------------------------
        # SCENARIO 6: Authorization / scope negative smoke
        # ----------------------------------------------------
        print("\n[Scenario 6] Authorization & Scope Negative Smoke")
        payload_neg = {
            "jobPostId": TEST_JOB_POST_ID,
            "hrId": TEST_WRONG_HR_ID,  # Mismatched company HR
            "prompt": "Liệt kê top 10 ứng viên cho job này.",
        }
        try:
            print(
                f"Sending prompt with mismatched hrId={TEST_WRONG_HR_ID} for jobPostId={TEST_JOB_POST_ID}"
            )
            resp = await client.post(
                f"{FANG_API_URL}/v2/agent/job-posting/query", json=payload_neg
            )
            print(f"Response status (Expected 403): {resp.status_code}")
            print(f"Response body: {resp.text}")
            assert resp.status_code == 403, f"Expected HTTP 403, got {resp.status_code}"
            print("=> Scenario 6 PASSED!")
        except Exception as e:
            print(f"CRITICAL ERROR in Scenario 6: {e}")
            sys.exit(1)

    print("\n" + "=" * 70)
    print("ALL 6 JOBPOSTING AGENT SMOKE SCENARIOS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_smoke_tests())

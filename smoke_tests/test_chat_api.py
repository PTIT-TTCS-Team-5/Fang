import asyncio
import os

import httpx

# Lay URL tu bien moi truong hoac dung mac dinh
FANG_API_URL = os.getenv("FANG_API_URL", "http://localhost:8000/v2")

# ID cung dung de test (dam bao DB da chay reset_and_seed_db.py)
TEST_JOB_APP_ID = 40
TEST_HR_ID = 22


async def run_e2e_chat_test():
    print(f"\nBat dau Smoke Test E2E Chat API tai {FANG_API_URL}\n")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # --- BUOC 1: Lay danh sach hoi thoai cu ---
        print("1. Dang kiem tra API danh sach hoi thoai...")
        resp = await client.get(
            f"{FANG_API_URL}/chat/conversations",
            params={"hrId": TEST_HR_ID, "jobAppId": TEST_JOB_APP_ID},
        )
        if resp.status_code != 200:
            print(f"  LOI: API danh sach hoi thoai that bai ({resp.status_code})")
            print(resp.text)
            return

        initial_conv_count = len(resp.json())
        print(f"  Thanh cong. Hien co {initial_conv_count} hoi thoai.")

        # --- BUOC 2: Gui cau hoi dau tien ---
        print("\n2. Gui cau hoi #1 (Tao hoi thoai moi) voi modelMode: auto-lite...")
        payload_1 = {
            "jobAppId": TEST_JOB_APP_ID,
            "hrId": TEST_HR_ID,
            "prompt": "Chao ban, hay tom tat ngan gon quy trinh tuyen dung cua cong ty.",
            "modelMode": "auto-lite",
        }

        resp_1 = await client.post(f"{FANG_API_URL}/chat/query", json=payload_1)
        if resp_1.status_code != 200:
            print(f"  LOI: API Chat Query #1 that bai ({resp_1.status_code})")
            print(resp_1.text)
            return

        data_1 = resp_1.json()
        conv_id = data_1.get("conversationId")
        model_used = data_1.get("model")
        print(f"  Thanh cong! Da tao Conversation ID: {conv_id}")
        print(f"  Model phan hoi: {model_used}")
        print(f"  Tra loi: {data_1.get('response')[:100]}...")

        if not conv_id:
            print("  LOI: Khong nhan duoc conversationId")
            return

        # --- BUOC 3: Gui cau hoi thu 2 ---
        print("\n3. Gui cau hoi #2 (Tiep tuc hoi thoai) vao cung Conversation ID...")
        payload_2 = {
            "jobAppId": TEST_JOB_APP_ID,
            "hrId": TEST_HR_ID,
            "prompt": "Tuyet voi. Ban co the nhac lai cau hoi dau tien cua toi la gi khong?",
            "conversationId": conv_id,
            "modelMode": "auto-lite",
        }

        resp_2 = await client.post(f"{FANG_API_URL}/chat/query", json=payload_2)
        if resp_2.status_code != 200:
            print(f"  LOI: API Chat Query #2 that bai ({resp_2.status_code})")
            print(resp_2.text)
            return

        data_2 = resp_2.json()
        print(
            f"  Thanh cong! Cung Conversation ID: {data_2.get('conversationId') == conv_id}"
        )
        print(f"  Tra loi: {data_2.get('response')[:100]}...")

        # --- BUOC 4: Kiem tra danh sach tin nhan ---
        print(f"\n4. Dang lay danh sach tin nhan cho Conversation {conv_id}...")
        resp_msgs = await client.get(
            f"{FANG_API_URL}/chat/conversations/{conv_id}/messages"
        )
        if resp_msgs.status_code != 200:
            print(f"  LOI: API lay tin nhan that bai ({resp_msgs.status_code})")
            print(resp_msgs.text)
            return

        messages = resp_msgs.json()
        print(f"  Thanh cong. Co {len(messages)} tin nhan trong hoi thoai.")
        for i, m in enumerate(messages):
            role = m.get("role", "").upper()
            content = m.get("content", "")[:50].replace("\n", " ")
            print(f"  [{i+1}] {role}: {content}...")

    print("\n  Toan bo Smoke Test E2E Chat API da vuot qua!")


if __name__ == "__main__":
    asyncio.run(run_e2e_chat_test())

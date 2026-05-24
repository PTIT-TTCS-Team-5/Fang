import os
import re

from playwright.sync_api import Playwright, sync_playwright


def read_keys_from_file(file_path):
    """
    Ham ho tro doc danh sach API Key tu file text.
    Loai bo cac ky tu thua, dong trong, va dau gach dau dong '- '.
    """
    keys = []
    if not os.path.exists(file_path):
        print(f"[ERROR] File khong ton tai tai: {file_path}")
        return keys

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Loai bo dau gach dau dong '- ' neu co
            if line.startswith("- "):
                line = line[2:].strip()
            if line:
                keys.append(line)
    return keys


def run(playwright: Playwright) -> None:
    # 1. Cau hinh cac thong so tuy chinh o day
    txt_file_path = r"C:\Users\os\Desktop\cur_prj\Fang\9router_keys.txt"
    start_index = (
        1  # <--- BAN CO THE TUY CHINH SO THU TU BAT DAU O DAY (y bat dau tu may)
    )

    # Doc danh sach key tu file
    keys = read_keys_from_file(txt_file_path)
    print(f"[INFO] Da tim thay {len(keys)} API keys trong file.")
    if not keys:
        print("[WARNING] Khong co key nao de thuc hien test. Dung chuong trinh.")
        return
    # Khoi dong trinh duyet
    browser = playwright.chromium.launch(headless=False, slow_mo=1000)
    context = browser.new_context()
    page = context.new_page()

    # 2. Quy trinh dang nhap va di den nha cung cap
    print("[INFO] Dang truy cap dashboard 9router...")
    page.goto("http://localhost:20128/login")
    page.get_by_role("textbox", name="Enter password").fill("hungklv123")
    page.get_by_role("button", name="Login").click()

    print("[INFO] Dang di den nha cung cap Providers...")
    page.get_by_role("link", name="dns Providers").click()
    # 💡 GIAI QUYET BUG SELECTOR DONG (Gemini Gemini XX Connected):
    # Thay vi dung text cung "Gemini Gemini 12 Connected", ta su dung bieu thuc chinh quy (Regular Expression)
    # re.compile(r"Gemini Gemini \d+ Connected") se khop voi bat ky con so nao (12, 13, 14, v.v.)
    print("[INFO] Click vao nha cung cap Gemini...")
    page.get_by_role("link", name=re.compile(r"Gemini Gemini \d+ Connected")).click()

    # 3. Vong lap tu dong hoa them hang loat API Key
    for idx, key in enumerate(keys, start=start_index):
        key_name = f"TEMP_x{idx}"
        print(f"[PROCESS] Dang add key thu {idx}: Name={key_name}, Key={key[:10]}...")

        # Click vao nut "Add"
        page.get_by_role("button", name="add Add", exact=True).click()

        # Dien Production Key Name (TEMP_x1, TEMP_x2, ...)
        page.get_by_role("textbox", name="Production Key").fill(key_name)

        # Dien Password input (chinh la API Key tu file)
        page.locator('input[type="password"]').fill(key)

        # Click "Save"
        page.get_by_role("button", name="Save").click()

        # Doi 1 giay cho he thong cap nhat truoc khi add key tiep theo
        page.wait_for_timeout(1000)
        print(f"[SUCCESS] Da luu thanh cong key: {key_name}")

    print("[FINISHED] Da hoan tat them tat ca API key hang loat!")

    # Dong trinh duyet
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)

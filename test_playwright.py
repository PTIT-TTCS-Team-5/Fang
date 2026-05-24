from playwright.sync_api import sync_playwright


def run_test():
    with sync_playwright() as p:
        print("[INFO] Khoi dong trinh duyet Chromium...")
        # Su dung slow_mo de buoc di chuyen duoc cham lai giup de quan sat
        browser = p.chromium.launch(headless=False, slow_mo=1500)
        page = browser.new_page()

        # 1. Truy cap Google AI Studio
        print("[INFO] Dang truy cap Google AI Studio...")
        page.goto("https://aistudio.google.com/")

        # 2. Click vao nut "Get started"
        print("[INFO] Doi va click nut 'Get started'...")
        page.wait_for_selector("text=Get started")
        page.locator("text=Get started").first.click()

        # 3. Doi trang chuyen sang giao dien dang nhap Google
        print("[INFO] Doi giao dien dang nhap Google xuat hien...")
        # O nhap email thuong co type="email" hoac id="identifierId"
        page.wait_for_selector("input[type='email']")

        # 4. Dien Email vao o nhap lieu
        print("[INFO] Dang dien Email...")
        page.locator("input[type='email']").fill("SteffaneK2ZLHMedrano45098@hayate.us")

        # 5. Click nut "Next" de sang buoc mat khau
        print("[INFO] Click nut 'Next' sau khi dien email...")
        # Google dat ID cho nut nay la 'identifierNext'
        page.locator("#identifierNext").click()

        # 6. Doi o nhap mat khau xuat hien (input[type='password'])
        print("[INFO] Doi o nhap mat khau hien thi...")
        page.wait_for_selector("input[type='password']")

        # 7. Dien mat khau
        print("[INFO] Dang dien mat khau...")
        page.locator("input[type='password']").fill("Anhtai777")

        # 8. Click nut "Next" de dang nhap
        print("[INFO] Click nut 'Next' de hoan tat dang nhap...")
        # Google dat ID cho nut mat khau la 'passwordNext'
        page.locator("#passwordNext").click()

        # 9. Giu trinh duyet de quan sat xem Google phan hoi ra sao (Thanh cong hay bi Block!)
        print(
            "[INFO] Da gui request dang nhap. Giu trinh duyet trong 15 giay de ban theo doi ket qua..."
        )
        page.wait_for_timeout(15000)

        browser.close()
        print("[INFO] Da dong trinh duyet. Ket thuc test!")


if __name__ == "__main__":
    run_test()

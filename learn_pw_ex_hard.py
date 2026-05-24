import os
import re

from playwright.sync_api import Playwright, sync_playwright


def read_emails_from_file(file_path):
    """
    Doc danh sach email truong cap tu file learn_pw_mail.txt.
    """
    emails = []
    if not os.path.exists(file_path):
        print(f"[ERROR] File khong ton tai tai: {file_path}")
        return emails

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and "@" in line:
                # Loai bo cac ky tu du thua nhu '- ' neu co
                if line.startswith("- "):
                    line = line[2:].strip()
                emails.append(line)
    return emails


def write_result_to_file(file_path, results):
    """
    Ghi ket qua API key lay duoc vao file learn_pw_result.txt theo dung format.
    """
    with open(file_path, "w", encoding="utf-8") as f:
        for idx, key in enumerate(results, start=1):
            f.write(f"API_{idx}: {key}\n")
    print(f"[INFO] Da cap nhat ket qua vao file: {file_path}")


def process_email(playwright: Playwright, email: str, password: str) -> str:
    """
    Thuc hien chay tung email rieng biet trong mot Chromium Context co lap.
    Tra ve API Key lay duoc, hoac chuoi rong neu that bai.
    """
    # Tao user data dir rieng cho tung email de tranh xung dot phien (session isolation)
    email_slug = email.split("@")[0]
    user_data_dir = os.path.join(os.getcwd(), f"chrome_profile_{email_slug}")

    print(f"\n[START] Bat dau xu ly email: {email}")
    context = playwright.chromium.launch_persistent_context(
        user_data_dir,
        channel="chrome",  # Su dung Google Chrome thong mai thuc te de bypass bot detection
        headless=False,
        slow_mo=1000,
        args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
    )

    api_key = ""
    try:
        page = context.pages[0] if context.pages else context.new_page()

        # 1. Thu truy cap truc tiep vao api-keys de xem co auto-login san khong
        print(f"[{email}] Dang thu truy cap thang vao api-keys...")
        page.goto("https://aistudio.google.com/api-keys")
        page.wait_for_timeout(3000)  # Cho 3 giay de xem co redirect ve login khong

        current_url = page.url
        if "welcome" in current_url or "accounts.google" in current_url:
            print(
                f"[{email}] Chua dang nhap! Dang tien hanh luong dang nhap thu cong..."
            )

            # Neu dang o trang welcome, phai click "Get started"
            if "welcome" in current_url:
                print(f"[{email}] Click 'Get started'...")
                login_page = page
                try:
                    with context.expect_page(timeout=4000) as new_page_info:
                        page.get_by_role("navigation").get_by_role(
                            "link", name="Get started"
                        ).click()
                    login_page = new_page_info.value
                    print(f"[{email}] Phat hien va chuyen sang tab dang nhap moi.")
                except Exception:
                    print(f"[{email}] Khong co tab moi, tiep tuc tren tab hien tai.")
                    try:
                        page.get_by_role("navigation").get_by_role(
                            "link", name="Get started"
                        ).click(timeout=2000)
                    except Exception:
                        pass
                page = login_page
                page.wait_for_timeout(3000)

            # Thuc hien dang nhap
            if "accounts.google" in page.url:
                print(f"[{email}] Doi va dien email...")
                page.wait_for_selector("input[type='email']")
                page.locator("input[type='email']").fill(email)
                page.get_by_role(
                    "button", name=re.compile(r"Next|Tiếp theo", re.I)
                ).click()

                print(f"[{email}] Doi va dien mat khau...")
                page.wait_for_selector("input[type='password']")
                page.locator("input[type='password']").fill(password)
                page.get_by_role(
                    "button", name=re.compile(r"Next|Tiếp theo|Đăng nhập", re.I)
                ).click()

                page.wait_for_timeout(3000)

                # Check security prompts if any
                try:
                    if page.get_by_role(
                        "button", name=re.compile(r"Next|Tiếp theo", re.I)
                    ).is_visible():
                        page.get_by_role(
                            "button", name=re.compile(r"Next|Tiếp theo", re.I)
                        ).click()
                except Exception:
                    pass

            # Quay lai trang api-keys sau khi dang nhap
            print(f"[{email}] Di chuyen den trang api-keys sau khi dang nhap...")
            page.goto("https://aistudio.google.com/api-keys")
        else:
            print(
                f"[{email}] TUYET VOI! Da tu dong nhap san tu phien truoc. Bo qua form dang nhap!"
            )

        # --- THONG BAO DIEN DIEU KHOAN (EDU, Terms, Consent...) ---
        page.wait_for_timeout(4000)
        print(f"[{email}] Dang quet va xu ly cac thong bao dieu khoan (neu co)...")

        # 1. Click nut "Toi hieu" hoac "I understand"
        try:
            page.get_by_role(
                "button", name=re.compile(r"Tôi hiểu|I understand", re.I)
            ).click(timeout=3000)
            print(f"[{email}] Da click 'Toi hieu'/'I understand'")
        except Exception:
            pass

        # 2. Click nut "Skip"
        try:
            page.get_by_role("button", name=re.compile(r"Skip", re.I)).click(
                timeout=3000
            )
            print(f"[{email}] Da click 'Skip'")
        except Exception:
            pass

        # 3. Check tat ca cac checkbox dang hien thi
        try:
            checkboxes = page.get_by_role("checkbox").all()
            if checkboxes:
                print(f"[{email}] Tim thay {len(checkboxes)} checkbox(es) de dong y.")
                for cb in checkboxes:
                    try:
                        if cb.is_visible() and not cb.is_checked():
                            cb.click(timeout=2000, force=True)
                            print(f"[{email}] Da check/click checkbox thanh cong.")
                    except Exception as e_cb:
                        print(f"[{email}] Loi click checkbox: {e_cb}")
        except Exception as e_cbs:
            print(f"[{email}] Loi quet checkboxes bang role: {e_cbs}")

        # Quet bang selector mat-checkbox cho chac chan
        try:
            for selector in [
                "mat-checkbox",
                ".mat-checkbox",
                ".mdc-checkbox",
                "input[type='checkbox']",
            ]:
                for el in page.locator(selector).all():
                    try:
                        if el.is_visible():
                            el.click(timeout=2000, force=True)
                            print(f"[{email}] Da click selector: {selector}")
                    except Exception:
                        pass
        except Exception:
            pass

        # 4. Nut "Accept terms of service" hoac "Accept" hoac "Continue" hoac "Agree" hoac "Tôi đồng ý" hoac "Get started" hoac "I consent"
        for btn_name in [
            "Accept terms of service",
            "Accept",
            "Continue",
            "Agree",
            "Get started",
            "Tôi đồng ý",
            "Dong y",
            "I consent",
        ]:
            try:
                page.get_by_role("button", name=re.compile(btn_name, re.I)).click(
                    timeout=2000
                )
                print(f"[{email}] Da click button dong y: {btn_name}")
            except Exception:
                pass

        page.wait_for_timeout(2000)

        # --- QUY TRINH TAO PROJECT & GET API KEY ---
        print(f"[{email}] Bat dau quy trinh click tao Project...")
        page.wait_for_selector('[data-test-id="create-api-key-button"]', timeout=15000)
        page.locator('[data-test-id="create-api-key-button"]').click()
        page.wait_for_timeout(3000)

        # Khởi tạo cờ kiểm soát
        action_triggered = False

        # 1. Thử click nút "Create key" trực tiếp (nút thường xuất hiện trong dialog chọn Default Project)
        try:
            page.get_by_role("button", name=re.compile(r"^Create key$", re.I)).click(
                timeout=3000
            )
            print(f"[{email}] Da click nut 'Create key' truc tiep trong dialog.")
            action_triggered = True
        except Exception:
            pass

        # 2. Thử click nút "Create API key in new project" trực tiếp nếu xuất hiện lựa chọn
        if not action_triggered:
            try:
                page.get_by_role(
                    "button",
                    name=re.compile(r"new project|Create API key in new project", re.I),
                ).click(timeout=3000)
                print(f"[{email}] Da click tao trong new project.")
                action_triggered = True
            except Exception:
                pass

        # 3. Thử click nút "Create API key in existing project" trực tiếp
        if not action_triggered:
            try:
                page.get_by_role(
                    "button",
                    name=re.compile(
                        r"existing project|Create API key in existing project", re.I
                    ),
                ).click(timeout=3000)
                print(f"[{email}] Da click tao trong existing project da co san.")
                action_triggered = True
            except Exception:
                pass

        # 4. Fallback sang click mat-select dropdown và chọn "Create project" nếu không có nút trực tiếp nào
        if not action_triggered:
            print(
                f"[{email}] Khong click truc tiep nut tao duoc. Tien hanh lua chon fallback dropdown..."
            )
            try:
                # Click dropdown trigger
                try:
                    page.locator("mat-select").first.click(timeout=3000)
                except Exception:
                    page.locator("[role='combobox']").first.click(timeout=3000)
                page.wait_for_timeout(1000)

                # Chon option Create project
                try:
                    page.get_by_text("Create project").click(timeout=3000)
                except Exception:
                    page.locator("mat-option, [role='option']").has_text(
                        "Create project"
                    ).first.click(timeout=3000)

                # Dien ten va bam luu
                page.wait_for_selector(
                    "input[placeholder='Name your project']", timeout=5000
                )
                page.get_by_role("textbox", name="Name your project").click()
                page.get_by_role("textbox", name="Name your project").press(
                    "ControlOrMeta+a"
                )
                page.get_by_role("textbox", name="Name your project").fill("learn pw")
                page.get_by_role("button", name="Create project").click(timeout=3000)
                print(
                    f"[{email}] Da thuc hien quy trinh dropdown va tao project 'learn pw'."
                )
            except Exception as e_fallback:
                print(
                    f"[{email}] Quy trinh fallback dropdown cung gap loi: {e_fallback}"
                )

        # --- TRICH XUAT API KEY ---
        print(f"[{email}] Doi API Key duoc sinh ra...")
        try:
            page.wait_for_selector("input", timeout=25000)
        except Exception:
            pass

        page.wait_for_timeout(4000)

        # Danh sach cac key mac dinh/tinh cua he thong Google AI Studio can loai tru
        excluded_keys = {
            "AIzaSyDHAQL7kdN6lNBcBok1eNB8dG7wwo6E6io",
            "AIzaSyDdP816MREB3SkjZO04QXbjsigfcI0GWOs",
        }

        # Quet tat ca cac input
        for input_el in page.locator("input").all():
            try:
                val = input_el.input_value()
                if val and val.strip().startswith("AIzaSy"):
                    clean_val = val.strip()
                    if clean_val not in excluded_keys:
                        api_key = clean_val
                        print(f"[SUCCESS] Lay duoc API Key cho {email}: {api_key}")
                        break
            except Exception:
                pass

        # Neu van chua lay duoc, quet toan bo text cua trang (regex match)
        if not api_key:
            try:
                page_text = page.content()
                matches = re.findall(r"AIzaSy[A-Za-z0-9_\-]{33}", page_text)
                for match in matches:
                    if match not in excluded_keys:
                        api_key = match
                        print(
                            f"[SUCCESS] Lay duoc API Key tu page content cho {email}: {api_key}"
                        )
                        break
            except Exception:
                pass

    except Exception as e:
        print(f"[ERROR] That bai khi xu ly email {email}: {e}")

    finally:
        context.close()

    return api_key


def main():
    mail_file = r"c:\Users\os\Desktop\cur_prj\Fang\learn_pw_mail.txt"
    result_file = r"c:\Users\os\Desktop\cur_prj\Fang\learn_pw_result.txt"
    shared_password = "Anhtai777"

    # Doc email
    emails = read_emails_from_file(mail_file)
    print(f"[INFO] Da tai {len(emails)} emails tu file.")
    if not emails:
        print("[WARNING] Khong tim thay email nao hop le. Ket thuc.")
        return

    results = []

    with sync_playwright() as playwright:
        for email in emails:
            key = process_email(playwright, email, shared_password)
            if key:
                results.append(key)
            else:
                results.append("FAILED_TO_GET_KEY")

    # Ghi ket qua
    write_result_to_file(result_file, results)
    print("[FINISHED] Da hoan tat toan bo luong cong viec!")


if __name__ == "__main__":
    main()

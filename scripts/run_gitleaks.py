import os
import sys

# Fix Unicode output for Windows terminal
if sys.stdout.encoding.lower() != "utf-8":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    else:
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import json
import subprocess
from pathlib import Path

# Mã màu ANSI cho terminal
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

GITLEAKS_VERSION = "8.21.2"
GITLEAKS_URL = f"https://github.com/gitleaks/gitleaks/releases/download/v{GITLEAKS_VERSION}/gitleaks_{GITLEAKS_VERSION}_windows_x64.zip"


def download_gitleaks(project_root):
    """Tải và giải nén GitLeaks bằng PowerShell."""
    print(
        f"{YELLOW}>>> Không tìm thấy gitleaks.exe. Đang tải phiên bản v{GITLEAKS_VERSION}...{RESET}"
    )
    zip_path = project_root / "gitleaks.zip"

    ps_command = f"""
    $ProgressPreference = 'SilentlyContinue';
    Invoke-WebRequest -Uri "{GITLEAKS_URL}" -OutFile "{zip_path}";
    Expand-Archive -Path "{zip_path}" -DestinationPath "{project_root}" -Force;
    Remove-Item "{zip_path}";
    """

    try:
        subprocess.run(
            ["powershell", "-Command", ps_command], check=True, encoding="utf-8"
        )
        print(f"{GREEN}>>> Tải về và giải nén thành công!{RESET}")
    except subprocess.CalledProcessError as e:
        print(f"{RED}>>> Lỗi khi tải GitLeaks: {e}{RESET}")
        sys.exit(1)


def run_gitleaks():
    project_root = Path(__file__).resolve().parent.parent
    gitleaks_exe = project_root / "gitleaks.exe"
    report_file = project_root / "gitleaks_report.json"
    config_file = project_root / ".gitleaks.toml"

    print(
        f"{BLUE}{BOLD}=== FANG Security: Công cụ quét rò rỉ thông tin (GitLeaks) ==={RESET}"
    )

    # Kiểm tra và tải gitleaks.exe nếu chưa có
    if not gitleaks_exe.exists():
        download_gitleaks(project_root)

    if not gitleaks_exe.exists():
        print(f"{RED}>>> Lỗi: Không tìm thấy gitleaks.exe sau khi tải.{RESET}")
        return

    # Lệnh chạy quét (chế độ scan all files bằng --no-git)
    cmd = [
        str(gitleaks_exe),
        "detect",
        "--source=.",
        "--report-format=json",
        f"--report-path={report_file}",
        "--redact",
        "--verbose",
        "--no-git",  # Chế độ scan all (không chỉ các file trong git index)
    ]

    if config_file.exists():
        cmd.extend(["--config", str(config_file)])

    print(f"{BLUE}Đang bắt đầu quét toàn bộ mã nguồn (Full Log Mode)...{RESET}")
    print(f"{YELLOW}{'-'*70}{RESET}")

    import time

    start_time = time.time()

    try:
        # Chạy trực tiếp để hiện full log ra terminal
        # GitLeaks trả về exit code 1 nếu tìm thấy leak
        process = subprocess.run(cmd, cwd=str(project_root), encoding="utf-8")

        duration = time.time() - start_time
        print(f"{YELLOW}{'-'*70}{RESET}")
        print(f"{BLUE}Thời gian quét: {duration:.2f} giây{RESET}")

        if not report_file.exists():
            if process.returncode == 0:
                print(f"{GREEN}\u2714 Không phát hiện rò rỉ thông tin.{RESET}")
            else:
                print(f"{RED}>>> Quá trình quét có lỗi hoặc bị dừng giữa chừng.{RESET}")
            return

        with open(report_file, "r", encoding="utf-8") as f:
            leaks = json.load(f)

        if not leaks:
            print(f"{GREEN}\u2714 Không phát hiện rò rỉ thông tin.{RESET}")
        else:
            print(
                f"{RED}{BOLD}\u26a0 TỔNG KẾT: Phát hiện {len(leaks)} điểm rò rỉ thông tin!{RESET}"
            )
            print(
                f"{YELLOW}Hành động: Kiểm tra log phía trên để biết chi tiết từng vị trí.{RESET}"
            )

    except Exception as e:
        print(f"{RED}>>> Lỗi hệ thống: {e}{RESET}")
    finally:
        if report_file.exists():
            try:
                os.remove(report_file)
            except Exception:
                pass


if __name__ == "__main__":
    # Kích hoạt màu ANSI trên Windows
    if os.name == "nt":
        os.system("color")
    run_gitleaks()

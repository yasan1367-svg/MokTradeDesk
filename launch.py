import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = BASE_DIR / "backend"
FRONTEND_DIR = BASE_DIR / "frontend"

def get_venv_python():
    if sys.platform == "win32":
        venv_python = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
    else:
        venv_python = BACKEND_DIR / "venv" / "bin" / "python"
    
    if venv_python.exists():
        return str(venv_python)
    return sys.executable

def main():
    print("==========================================")
    print("🚀 در حال راه‌اندازی MokTradeDesk...")
    print("==========================================")

    # بررسی وجود پوشه‌ها
    if not BACKEND_DIR.exists():
        print(f"❌ پوشه بک‌اند در مسیر زیر پیدا نشد:\n{BACKEND_DIR}")
        return

    if not FRONTEND_DIR.exists():
        print(f"❌ پوشه فرانت‌اند در مسیر زیر پیدا نشد:\n{FRONTEND_DIR}")
        print("لطفاً مطمئن شوید پوشه frontend در کنار فایل launch.py قرار دارد.")
        return

    processes = []

    try:
        # ۱. اجرای بک‌اند
        python_bin = get_venv_python()
        print("📦 در حال اجرای بک‌اند...")
        
        backend_cmd = [
            python_bin, "-m", "uvicorn", "app.main:app",
            "--reload", "--host", "127.0.0.1", "--port", "8000"
        ]
        
        backend_process = subprocess.Popen(
            backend_cmd,
            cwd=str(BACKEND_DIR)
        )
        processes.append(backend_process)
        print("✅ سرویس بک‌اند روی http://127.0.0.1:8000 راه‌اندازی شد.")

        time.sleep(2)

        # ۲. اجرای فرانت‌اند
        print("🎨 در حال اجرای فرانت‌اند...")
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        
        frontend_process = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=str(FRONTEND_DIR),
            shell=(sys.platform == "win32")
        )
        processes.append(frontend_process)
        print("✅ سرویس فرانت‌اند شروع به کار کرد.")

        time.sleep(3)

        # ۳. باز کردن مرورگر
        print("🌐 در حال باز کردن مرورگر...")
        webbrowser.open("http://localhost:5173")

        print("\n✨ تمامی سرویس‌ها با موفقیت فعال شدند!")
        print("💡 برای متوقف کردن سیستم، کلیدهای CTRL+C را فشار دهید.\n")

        for p in processes:
            p.wait()

    except KeyboardInterrupt:
        print("\n🛑 در حال متوقف کردن تمام سرویس‌ها...")
        for p in processes:
            try:
                p.terminate()
            except Exception:
                pass
        print("👋 تمام سرویس‌ها متوقف شدند.")

if __name__ == "__main__":
    main()
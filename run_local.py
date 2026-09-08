import os
import sys
import time
import socket
import subprocess
import threading
import urllib.request
import webbrowser
from pathlib import Path

# Force UTF-8 encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
PYTHON_EXE = str(BASE_DIR / ".venv" / "Scripts" / "python.exe")
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = sys.executable

processes = {}


def get_local_ip() -> str:
    """ទាញយក Local IP Address (LAN/Wi-Fi) របស់កុំព្យូទ័រនេះ"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def cleanup():
    print("\n🛑 កំពុងបិទដំណើរការ Local Server ទាំងអស់ (Shutting down services)...")
    for name, p in list(processes.items()):
        try:
            p.terminate()
        except Exception:
            pass
    time.sleep(1)
    for name, p in list(processes.items()):
        try:
            p.kill()
        except Exception:
            pass
    print("✅ បានបិទរួចរាល់។")


def wait_for_web(port=8000, timeout=12):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/login")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    try:
        local_ip = get_local_ip()
        port = 8000

        print("=" * 65)
        print("  🚀 ចាប់ផ្តើមដំណើរការប្រព័ន្ធ SM Inventory ក្នុង LOCAL SERVER")
        print("=" * 65)

        # 1. Start Web Dashboard
        print("▶️ [1/2] កំពុងដំណើរការ Local Web Dashboard (FastAPI / Uvicorn)...")
        web_proc = subprocess.Popen(
            [PYTHON_EXE, "-m", "uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", str(port)],
            cwd=str(BASE_DIR)
        )
        processes["web_app"] = web_proc

        if not wait_for_web(port, timeout=10):
            print("⚠️ Web Dashboard កំពុងរៀបចំ...")
        else:
            print(f"✅ Web Dashboard ដំណើរការជោគជ័យលើ Local Server!")

        # 2. Start Telegram Bot
        print("▶️ [2/2] កំពុងដំណើរការ Telegram Bot (main.py)...")
        bot_proc = subprocess.Popen(
            [PYTHON_EXE, "main.py"],
            cwd=str(BASE_DIR)
        )
        processes["telegram_bot"] = bot_proc

        local_url = f"http://localhost:{port}/login"
        lan_url = f"http://{local_ip}:{port}/login"

        print("\n" + "=" * 65)
        print("  🎉 LOCAL SERVER ដំណើរការបានជោគជ័យ ១០០% (ONLINE)")
        print("=" * 65)
        print(f"  💻 លើកុំព្យូទ័រនេះ (Localhost)  : {local_url}")
        print(f"  📱 ឧបករណ៍ផ្សេងលើ Wi-Fi (LAN) : {lan_url}")
        print(f"  🤖 Telegram Bot                : ដំណើរការរួចរាល់")
        print("=" * 65)
        print("  🔑 គណនី Admin ដំបូង           : Username: admin | Password: admin123")
        print("  💡 ចុច Ctrl + C ក្នុងផ្ទាំងនេះ ដើម្បីបិទដំណើរការប្រព័ន្ធ។\n")

        # Automatically open browser to localhost
        try:
            webbrowser.open(local_url)
        except Exception:
            pass

        # Monitor running processes
        while True:
            time.sleep(2)
            for name, proc in list(processes.items()):
                code = proc.poll()
                if code is not None:
                    print(f"⚠️ សេវាកម្ម '{name}' បានឈប់ដំណើរការ (Exit code: {code})")
                    return

    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()

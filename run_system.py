import os
import sys
import time
import re
import subprocess
import threading
import urllib.request
import webbrowser
from pathlib import Path

# Force UTF-8 stdout on Windows
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

# ---- Hidden mode (គ្មានផ្ទាំង CMD) ----
# ដំណើរការតាម pythonw.exe ឬ START_*_HIDDEN.vbs -> កូនដំណើរការទាំងអស់លាក់ផ្ទាំង និងសរសេរ log ទៅ logs/
HIDDEN_MODE = (
    os.environ.get("SM_HIDDEN") == "1"
    or os.path.basename(sys.executable).lower() == "pythonw.exe"
)
LOG_DIR = BASE_DIR / "logs"
PID_FILE = BASE_DIR / ".sm_pids"


def child_kwargs(log_name: str) -> dict:
    """Popen kwargs៖ ក្នុង Hidden mode លាក់ console របស់កូនដំណើរការ និងបញ្ជូន output ទៅ log file"""
    kw = {}
    if HIDDEN_MODE:
        LOG_DIR.mkdir(exist_ok=True)
        log_f = open(LOG_DIR / f"{log_name}.log", "a", encoding="utf-8", errors="replace")
        kw["stdout"] = log_f
        kw["stderr"] = subprocess.STDOUT
        kw["stdin"] = subprocess.DEVNULL
        if sys.platform == "win32":
            kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return kw


def write_pid_file():
    """រក្សាទុក PID ទាំងអស់ ដើម្បីឱ្យ STOP_SYSTEM.bat បិទបាន"""
    try:
        pids = [str(os.getpid())] + [str(p.pid) for p in processes.values()]
        PID_FILE.write_text("\n".join(pids), encoding="utf-8")
    except Exception:
        pass


def remove_pid_file():
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception:
        pass

CLOUDFLARED_EXE = str(BASE_DIR / "cloudflared.exe")
TUNNEL_FILE = BASE_DIR / "tunnel_url.txt"

processes = {}

def cleanup():
    print("\n🛑 កំពុងបិទដំណើរការប្រព័ន្ធទាំងអស់ (Shutting down services)...")
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
    remove_pid_file()
    print("✅ បានបិទរួចរាល់។")

def wait_for_web(port=8000, timeout=15):
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

def start_cloudflared_and_get_url():
    if not os.path.exists(CLOUDFLARED_EXE):
        print(f"⚠️ រកមិនឃើញ {CLOUDFLARED_EXE}")
        return None

    cmd = [CLOUDFLARED_EXE, "tunnel", "--url", "http://127.0.0.1:8000"]
    cf_kw = {}
    if HIDDEN_MODE and sys.platform == "win32":
        cf_kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        **cf_kw
    )
    processes["cloudflared"] = proc
    write_pid_file()

    tunnel_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    start_time = time.time()
    while time.time() - start_time < 20:
        line = proc.stdout.readline()
        if not line and proc.poll() is not None:
            break
        if line:
            match = url_pattern.search(line)
            if match:
                tunnel_url = match.group(0)
                break

    def drain_output():
        try:
            for _ in proc.stdout:
                pass
        except Exception:
            pass

    threading.Thread(target=drain_output, daemon=True).start()
    return tunnel_url

def main():
    try:
        print("=" * 65)
        print("  🚀 ចាប់ផ្តើមដំណើរការប្រព័ន្ធ SM Telegram Bot & Web Dashboard")
        print("=" * 65)

        # 1. Start Web App
        print("▶️ [1/3] កំពុងដំណើរការ Web Dashboard (FastAPI / Uvicorn)...")
        web_proc = subprocess.Popen(
            [PYTHON_EXE, "-m", "uvicorn", "web_app:app", "--host", "0.0.0.0", "--port", "8000"],
            cwd=str(BASE_DIR),
            **child_kwargs("web")
        )
        processes["web_app"] = web_proc
        write_pid_file()

        if not wait_for_web(8000, timeout=12):
            print("⚠️ Web Dashboard កំពុងរៀបចំ...")
        else:
            print("✅ Web Dashboard ដំណើរការជោគជ័យលើ http://localhost:8000")

        # 2. Start Cloudflare Tunnel
        print("▶️ [2/3] កំពុងបង្កើត Cloudflare Public Tunnel (Internet Access)...")
        tunnel_url = start_cloudflared_and_get_url()

        if tunnel_url:
            print(f"✅ Cloudflare Tunnel ភ្ជាប់ជោគជ័យ!")
            try:
                TUNNEL_FILE.write_text(tunnel_url, encoding="utf-8")
            except Exception:
                pass
        else:
            print("⚠️ មិនទាន់ទទួលបាន Cloudflare Tunnel URL ទេ (ប្រើ Localhost ជំនួស)")
            tunnel_url = "http://localhost:8000"

        # 3. Start Telegram Bot
        print("▶️ [3/3] កំពុងដំណើរការ Telegram Bot (main.py)...")
        bot_proc = subprocess.Popen(
            [PYTHON_EXE, "main.py"],
            cwd=str(BASE_DIR),
            **child_kwargs("bot")
        )
        processes["telegram_bot"] = bot_proc
        write_pid_file()

        # Success Banner
        login_url = f"{tunnel_url}/login"
        local_url = "http://localhost:8000/login"

        print("\n" + "=" * 65)
        print("  🎉 ប្រព័ន្ធដំណើរការបានជោគជ័យ ១០០%! (ALL SERVICES ONLINE)")
        print("=" * 65)
        print(f"  🌐 Internet Link (ទូរសព្ទ/ក្រៅផ្ទះ) : {login_url}")
        print(f"  💻 Localhost Link (កុំព្យូទ័រនេះ)    : {local_url}")
        print(f"  🤖 Telegram Bot                     : ដំណើរការរួចរាល់")
        print("=" * 65)
        print("  💡 ចុច Ctrl + C ក្នុងផ្ទាំងនេះ ប្រសិនបើចង់បិទប្រព័ន្ធទាំងមូល។\n")

        # Automatically open the new link in browser
        try:
            webbrowser.open(login_url)
        except Exception:
            pass

        # Monitor processes
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

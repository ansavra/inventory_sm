import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

# Admin user IDs parsed into a set of integers
_admin_raw = os.getenv("ADMIN_USER_IDS", "").strip()
ADMIN_IDS = set()
if _admin_raw:
    for uid in _admin_raw.split(","):
        uid = uid.strip()
        if uid.isdigit():
            ADMIN_IDS.add(int(uid))

DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "inventory.db"))

# Telegram Group ឬ Channel ID សម្រាប់ទទួលការជូនដំណឹង (ឧ. -100xxxx ឬ @channel)
ALERT_CHAT_ID = os.getenv("TELEGRAM_ALERT_CHAT_ID", "").strip()


def get_dashboard_url() -> str:
    """ទាញយក URL សកម្មបច្ចុប្បន្នរបស់ Web Dashboard (Cloudflare ឬ Local)"""
    tunnel_file = BASE_DIR / "tunnel_url.txt"
    if tunnel_file.exists():
        try:
            url = tunnel_file.read_text(encoding="utf-8").strip()
            if url:
                return url
        except Exception:
            pass
    return os.getenv("CLOUDFLARE_URL", "http://localhost:8000")

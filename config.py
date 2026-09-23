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

# Postgres / Supabase — បើកំណត់ DATABASE_URL ប្រព័ន្ធនឹងប្រើ Supabase ជំនួស SQLite
# ឧ. postgresql://postgres.xxxx:PASSWORD@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Schema ក្នុង Postgres (ដាក់ដាច់ពីតារាងផ្សេងក្នុង Supabase project ដដែល)
DB_SCHEMA = os.getenv("DB_SCHEMA", "sm").strip() or "sm"

# តំបន់ម៉ោងសម្រាប់កត់ត្រាកាលបរិច្ឆេទ
APP_TZ = os.getenv("APP_TZ", "Asia/Phnom_Penh").strip() or "Asia/Phnom_Penh"

# លេខសម្ងាត់សម្រាប់ Telegram Webhook (path secret)
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()


def _prepare_database_path() -> None:
    """
    រៀបចំផ្លូវ Database សម្រាប់ Persistent Disk (ឧ. Render: DATABASE_PATH=/data/inventory.db)
    - បង្កើត folder បើមិនទាន់មាន
    - បើ Database លើ disk មិនទាន់មាន តែមាន inventory.db ក្នុង repo -> ចម្លងជា seed លើកដំបូង
    """
    import shutil
    db_path = Path(DATABASE_PATH)
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        return
    seed = BASE_DIR / "inventory.db"
    if not db_path.exists() and seed.exists() and seed.resolve() != db_path.resolve():
        try:
            shutil.copy2(seed, db_path)
            print(f"📦 Seeded database from repo to {db_path}")
        except Exception as e:
            print(f"⚠️ Could not seed database: {e}")


_prepare_database_path()

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

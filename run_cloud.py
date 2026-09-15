import os
import sys
import subprocess
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def main():
    # Cloud mode -> Bot ត្រូវបានបើកជានិច្ច (ប្រើដោយ /api/system/status ក្នុង web_app.py)
    os.environ["SM_MODE"] = "cloud"
    port = int(os.getenv("PORT", "8000"))
    print("=" * 60)
    print(f"🚀 Starting SM Telegram Bot & Inventory Web on Cloud (Port: {port})")
    print("=" * 60)

    # 1. Initialize Database
    try:
        import database as db
        db.init_db()
        print("✅ Database initialized successfully.")
    except Exception as e:
        print(f"⚠️ Database initialization warning: {e}")

    # 2. Start Telegram Bot process
    print("🤖 Starting Telegram Bot in background...")
    bot_proc = subprocess.Popen(
        [sys.executable, str(BASE_DIR / "main.py")],
        cwd=str(BASE_DIR)
    )

    # 3. Start Web Dashboard via Uvicorn
    print(f"🌐 Starting Web Dashboard on 0.0.0.0:{port}...")
    import uvicorn
    try:
        uvicorn.run("web_app:app", host="0.0.0.0", port=port, log_level="info")
    finally:
        print("\n🛑 Shutting down Cloud services...")
        bot_proc.terminate()
        try:
            bot_proc.wait(timeout=3)
        except Exception:
            bot_proc.kill()
        print("✅ All services stopped.")

if __name__ == "__main__":
    main()

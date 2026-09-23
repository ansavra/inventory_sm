"""
រៀបចំ Supabase (Setup / Migration Tool)
=======================================
ប្រើសម្រាប់៖
  1. បង្កើតតារាងទាំងអស់ក្នុង Supabase (បើមិនទាន់មាន)
  2. ផ្ទេរទិន្នន័យពីឯកសារ SQLite ចាស់ទៅ Supabase (ស្រេចចិត្ត)
  3. ពិនិត្យមើលថាការភ្ជាប់ដំណើរការ

របៀបប្រើ (ក្នុង Terminal):
    .venv\\Scripts\\python.exe setup_supabase.py                    # បង្កើតតារាង + ពិនិត្យ
    .venv\\Scripts\\python.exe setup_supabase.py --from inventory.db  # ផ្ទេរទិន្នន័យចូលផង

ត្រូវកំណត់ DATABASE_URL ក្នុងឯកសារ .env ជាមុនសិន។
"""
import argparse
import sqlite3
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent

import config          # noqa: E402
import db_core         # noqa: E402
import database as db  # noqa: E402

TABLES = ["users", "products", "product_batches", "transactions",
          "web_sessions", "app_settings", "bot_state"]

# តារាង -> columns ដែលត្រូវផ្ទេរ (តម្រៀបតាមលំដាប់ Foreign Key)
COPY_PLAN = [
    ("users", ["user_id", "username", "full_name", "role", "is_active", "password_hash", "created_at"]),
    ("products", ["id", "code", "name", "category", "unit", "cost_price", "sell_price",
                  "quantity", "min_quantity", "location", "created_at", "updated_at"]),
    ("product_batches", ["id", "product_id", "batch_no", "expiry_date", "quantity",
                         "created_at", "updated_at"]),
    ("transactions", ["id", "product_id", "type", "quantity", "unit_price", "total_price",
                      "reference", "performed_by", "batch_id", "expiry_date", "batch_no", "created_at"]),
    ("app_settings", ["key", "value", "updated_at"]),
]


def counts() -> dict:
    out = {}
    with db_core.get_connection() as conn:
        cur = conn.cursor()
        for t in TABLES:
            try:
                cur.execute(f"SELECT COUNT(*) AS n FROM {t}")
                row = cur.fetchone()
                out[t] = row["n"] if isinstance(row, dict) else row[0]
            except Exception as e:
                out[t] = f"ERR: {e}"
    return out


def copy_from_sqlite(sqlite_path: str) -> None:
    """ផ្ទេរទិន្នន័យពី SQLite ទៅ Postgres (រំលងជួរដែលមានស្រាប់)"""
    src_file = Path(sqlite_path)
    if not src_file.is_absolute():
        src_file = BASE_DIR / src_file
    if not src_file.exists():
        print(f"❌ រកមិនឃើញឯកសារ {src_file}")
        return

    src = sqlite3.connect(str(src_file))
    src.row_factory = sqlite3.Row
    src_tables = {r["name"] for r in src.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}

    print(f"\n📦 កំពុងផ្ទេរទិន្នន័យពី {src_file.name} ...")
    with db_core.get_connection() as conn:
        cur = conn.cursor()
        for table, cols in COPY_PLAN:
            if table not in src_tables:
                print(f"   ⏭️  {table}: មិនមានក្នុងឯកសារចាស់ — រំលង")
                continue

            avail = {r[1] for r in src.execute(f"PRAGMA table_info({table})")}
            use_cols = [c for c in cols if c in avail]
            rows = src.execute(f"SELECT {', '.join(use_cols)} FROM {table}").fetchall()
            if not rows:
                print(f"   ⏭️  {table}: គ្មានទិន្នន័យ")
                continue

            placeholders = ", ".join("?" * len(use_cols))
            conflict_col = {"users": "user_id", "app_settings": "key"}.get(table, "id")
            sql = (f"INSERT INTO {table} ({', '.join(use_cols)}) VALUES ({placeholders}) "
                   f"ON CONFLICT ({conflict_col}) DO NOTHING")
            ok = 0
            for r in rows:
                try:
                    cur.execute(sql, tuple(r[c] for c in use_cols))
                    ok += 1
                except Exception as e:
                    print(f"      ⚠️ {table}: មានជួរខុស — {e}")
            conn.commit()
            print(f"   ✅ {table}: ផ្ទេរ {ok}/{len(rows)} ជួរ")

        # កែ sequence ឱ្យត្រូវនឹង id ធំបំផុត (បើមិនធ្វើ ការបញ្ចូលថ្មីនឹង error)
        if db_core.IS_PG:
            for table in ("products", "product_batches", "transactions"):
                cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{config.DB_SCHEMA}.{table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table}), 1), true) AS v"
                )
            conn.commit()
            print("   🔧 កែ sequence រួចរាល់")
    src.close()


def main():
    ap = argparse.ArgumentParser(description="រៀបចំ Supabase សម្រាប់ SM Inventory")
    ap.add_argument("--from", dest="src", help="ឯកសារ SQLite ដែលត្រូវផ្ទេរទិន្នន័យចេញ (ឧ. inventory.db)")
    args = ap.parse_args()

    print("=" * 62)
    print("  🗄️  SM Inventory — រៀបចំ Database")
    print("=" * 62)
    print(f"  Backend : {db_core.backend_name()}")
    if db_core.IS_PG:
        safe = config.DATABASE_URL
        if "@" in safe:
            safe = safe.split("@", 1)[0].rsplit(":", 1)[0] + ":****@" + safe.split("@", 1)[1]
        print(f"  URL     : {safe}")
        print(f"  Schema  : {config.DB_SCHEMA}")
    else:
        print("  ⚠️  DATABASE_URL មិនទាន់កំណត់ — កំពុងប្រើ SQLite ក្នុងម៉ាស៊ីន")
        print("     សូមបន្ថែម DATABASE_URL=... ក្នុងឯកសារ .env ដើម្បីប្រើ Supabase")
    print("=" * 62)

    print("\n▶️  កំពុងបង្កើត/ពិនិត្យតារាង ...")
    db.init_db()
    print("✅ តារាងរួចរាល់")

    if args.src:
        copy_from_sqlite(args.src)

    print("\n📊 ចំនួនជួរក្នុងតារាងនីមួយៗ៖")
    for t, n in counts().items():
        print(f"   • {t:<16} {n}")
    print("\n🎉 រួចរាល់!")


if __name__ == "__main__":
    main()

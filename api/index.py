"""
Vercel Serverless Entry Point
=============================
Vercel នឹងហៅឯកសារនេះសម្រាប់គ្រប់ Request ទាំងអស់។
ទិន្នន័យត្រូវរក្សាក្នុង Supabase (កំណត់ DATABASE_URL ក្នុង Vercel Environment Variables)។
"""
import os
import sys
from pathlib import Path

# បន្ថែម folder មេចូល sys.path ដើម្បីឱ្យ import module របស់គម្រោងបាន
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("SM_MODE", "cloud")

from web_app import app  # noqa: E402  (ASGI app សម្រាប់ Vercel)

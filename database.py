import sqlite3
import datetime
from typing import Optional, List, Dict, Any, Tuple
from config import DATABASE_PATH, ADMIN_IDS


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """បង្កើតតារាងចាំបាច់ក្នុង Database ប្រសិនបើមិនទាន់មាន"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # តារាងអ្នកប្រើប្រាស់ (Users)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                role TEXT NOT NULL DEFAULT 'staff',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # តារាងទំនិញ (Products)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category TEXT DEFAULT 'ទូទៅ',
                unit TEXT DEFAULT 'ឯកតា',
                cost_price REAL DEFAULT 0.0,
                sell_price REAL DEFAULT 0.0,
                quantity INTEGER NOT NULL DEFAULT 0,
                min_quantity INTEGER NOT NULL DEFAULT 5,
                location TEXT DEFAULT 'ឃ្លាំងធំ',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # បង្កើត Index សម្រាប់ស្វែងរកលឿន
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_code ON products(code);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);")

        # តារាងប្រតិបត្តិការ នាំចូល-នាំចេញ (Transactions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('IN', 'OUT')),
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                unit_price REAL DEFAULT 0.0,
                total_price REAL DEFAULT 0.0,
                reference TEXT,
                performed_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tx_created ON transactions(created_at);")

        # តារាងឡូតិ៍ / ថ្ងៃផុតកំណត់ (Product Batches) - ទំនិញ ១ អាចមានថ្ងៃផុតកំណត់ច្រើន
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                expiry_date TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(product_id, expiry_date),
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_batches_product ON product_batches(product_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_batches_expiry ON product_batches(expiry_date);")

        # បន្ថែម column batch_id / expiry_date លើ transactions (សម្រាប់ DB ចាស់)
        cursor.execute("PRAGMA table_info(transactions);")
        tx_columns = [row['name'] for row in cursor.fetchall()]
        if 'batch_id' not in tx_columns:
            cursor.execute("ALTER TABLE transactions ADD COLUMN batch_id INTEGER;")
        if 'expiry_date' not in tx_columns:
            cursor.execute("ALTER TABLE transactions ADD COLUMN expiry_date TEXT;")

        # ពិនិត្យបន្ថែម password_hash column លើ users
        cursor.execute("PRAGMA table_info(users);")
        columns = [row['name'] for row in cursor.fetchall()]
        if 'password_hash' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT DEFAULT '';")

        # បញ្ចូល Admin ដំបូងពី Config
        for admin_id in ADMIN_IDS:
            cursor.execute("""
                INSERT INTO users (user_id, username, full_name, role)
                VALUES (?, 'admin', 'System Admin', 'admin')
                ON CONFLICT(user_id) DO UPDATE SET role = 'admin';
            """, (admin_id,))

        # បញ្ចូល Default Web Admin ប្រសិនបើមិនទាន់មាន
        cursor.execute("SELECT * FROM users WHERE username = 'admin';")
        admin_web = cursor.fetchone()
        from auth import hash_password
        default_pwd_hash = hash_password("admin123")

        if not admin_web:
            cursor.execute("""
                INSERT INTO users (user_id, username, full_name, role, password_hash)
                VALUES (1, 'admin', 'Administrator', 'admin', ?);
            """, (default_pwd_hash,))
        elif not admin_web['password_hash']:
            cursor.execute("""
                UPDATE users SET password_hash = ? WHERE username = 'admin';
            """, (default_pwd_hash,))

        conn.commit()


# ==========================================
# ការគ្រប់គ្រងអ្នកប្រើប្រាស់ (User Management)
# ==========================================

def create_web_user(username: str, password: str, full_name: str, role: str = 'staff') -> Tuple[bool, str, Optional[int]]:
    """បង្កើតគណនី Web ថ្មីសម្រាប់បុគ្គលិក ឬ Admin"""
    from auth import hash_password
    username = username.strip().lower()
    full_name = full_name.strip()
    if not username or not password:
        return False, "សូមបំពេញ Username និង Password ឱ្យបានត្រឹមត្រូវ!", None

    pwd_hash = hash_password(password)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False, f"Username '{username}' មានក្នុងប្រព័ន្ធរួចហើយ!", None

        # បង្កើត user_id ថ្មី (យក MAX(user_id) + 1)
        cursor.execute("SELECT COALESCE(MAX(user_id), 1000) as max_id FROM users;")
        next_id = cursor.fetchone()['max_id'] + 1

        cursor.execute("""
            INSERT INTO users (user_id, username, full_name, role, password_hash)
            VALUES (?, ?, ?, ?, ?);
        """, (next_id, username, full_name, role, pwd_hash))
        conn.commit()
        return True, "បង្កើតគណនីជោគជ័យ!", next_id


def verify_user_credentials(username: str, password: str) -> Optional[Dict[str, Any]]:
    """ផ្ទៀងផ្ទាត់ Username និង Password ពេល Login"""
    from auth import verify_password
    username = username.strip().lower()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(username) = ? AND is_active = 1", (username,))
        row = cursor.fetchone()
        if not row:
            return None
        user_dict = dict(row)
        stored_hash = user_dict.get('password_hash') or ''
        if verify_password(stored_hash, password):
            return user_dict
    return None


def list_web_users() -> List[Dict[str, Any]]:
    """បញ្ជីគណនីទាំងអស់សម្រាប់ Admin គ្រប់គ្រង"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, full_name, role, is_active, created_at FROM users ORDER BY user_id ASC")
        return [dict(row) for row in cursor.fetchall()]


def delete_user_by_id(user_id: int) -> Tuple[bool, str]:
    """លុបគណនីអ្នកប្រើប្រាស់ (មិនអនុញ្ញាតឱ្យលុប admin មេ)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        u = cursor.fetchone()
        if not u:
            return False, "រកមិនឃើញគណនីនេះទេ!"
        if u['username'] == 'admin':
            return False, "មិនអាចលុបគណនី Admin មេបានទេ!"

        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        return True, f"បានលុបគណនី '{u['username']}' ដោយជោគជ័យ!"


def register_or_update_user(user_id: int, username: str, full_name: str) -> Dict[str, Any]:
    role = 'admin' if user_id in ADMIN_IDS else 'staff'
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()

        if existing:
            # ប្រសិនបើមានរួច រក្សាតួនាទីចាស់ (លើកលែងតែក្នុង ADMIN_IDS)
            user_role = 'admin' if user_id in ADMIN_IDS else existing['role']
            cursor.execute("""
                UPDATE users SET username = ?, full_name = ?, role = ?
                WHERE user_id = ?;
            """, (username, full_name, user_role, user_id))
        else:
            cursor.execute("""
                INSERT INTO users (user_id, username, full_name, role)
                VALUES (?, ?, ?, ?);
            """, (user_id, username, full_name, role))
        conn.commit()

    return get_user(user_id)


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def is_admin(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    u = get_user(user_id)
    return bool(u and u.get('role') == 'admin')


def list_users() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]


# ==========================================
# ការគ្រប់គ្រងទំនិញ (Products Management)
# ==========================================

def add_product(
    code: str,
    name: str,
    category: str = 'ទូទៅ',
    unit: str = 'ឯកតា',
    cost_price: float = 0.0,
    sell_price: float = 0.0,
    quantity: int = 0,
    min_quantity: int = 5,
    location: str = 'ឃ្លាំងធំ'
) -> Tuple[bool, str, Optional[int]]:
    """បន្ថែមទំនិញថ្មីចូលប្រព័ន្ធ"""
    code = code.strip()
    name = name.strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO products (code, name, category, unit, cost_price, sell_price, quantity, min_quantity, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (code, name, category, unit, cost_price, sell_price, quantity, min_quantity, location))
            product_id = cursor.lastrowid
            conn.commit()
            return True, "ជោគជ័យ", product_id
        except sqlite3.IntegrityError:
            return False, f"កូដទំនិញ '{code}' មានរួចហើយក្នុងប្រព័ន្ធ!", None


def get_product_by_code(code: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE code = ?", (code.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def search_products(keyword: str, limit: int = 15) -> List[Dict[str, Any]]:
    """ស្វែងរកតាមលេខកូដ ឬឈ្មោះទំនិញ"""
    term = f"%{keyword.strip()}%"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM products
            WHERE code LIKE ? OR name LIKE ? OR category LIKE ?
            ORDER BY name ASC
            LIMIT ?;
        """, (term, term, term, limit))
        return [dict(row) for row in cursor.fetchall()]


def list_all_products(limit: int = 50) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products ORDER BY name ASC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_low_stock_products() -> List[Dict[str, Any]]:
    """ទាញយកបញ្ជីទំនិញដែលនៅសល់តិចជាង ឬស្មើ min_quantity"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM products
            WHERE quantity <= min_quantity
            ORDER BY quantity ASC;
        """)
        return [dict(row) for row in cursor.fetchall()]


# ==========================================
# ប្រតិបត្តិការស្តុក (Stock In / Stock Out)
# ==========================================

def normalize_expiry_date(value: Optional[Any]) -> Optional[str]:
    """បម្លែងថ្ងៃផុតកំណត់ទៅជាទម្រង់ YYYY-MM-DD (ទទួល YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, YYYY/MM/DD)"""
    if value is None:
        return None
    # datetime object ពី Excel
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime('%Y-%m-%d')
    text = str(value).strip()
    if not text or text.lower() in ('-', 'none', 'null', 'n/a'):
        return None
    if len(text) > 10 and text[10:11] in (' ', 'T'):
        text = text[:10]
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%d.%m.%Y', '%m/%d/%Y'):
        try:
            return datetime.datetime.strptime(text, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    raise ValueError(f"ទម្រង់ថ្ងៃផុតកំណត់ '{text}' មិនត្រឹមត្រូវ (សូមប្រើ YYYY-MM-DD)")


def _upsert_batch(cursor: sqlite3.Cursor, product_id: int, expiry_date: str, quantity: int) -> int:
    """បន្ថែមចំនួនចូលឡូតិ៍ដែលមានថ្ងៃផុតកំណត់ដូចគ្នា ឬបង្កើតឡូតិ៍ថ្មី; ត្រឡប់ batch_id"""
    cursor.execute(
        "SELECT id FROM product_batches WHERE product_id = ? AND expiry_date = ?",
        (product_id, expiry_date)
    )
    row = cursor.fetchone()
    if row:
        cursor.execute("""
            UPDATE product_batches
            SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """, (quantity, row['id']))
        return row['id']
    cursor.execute("""
        INSERT INTO product_batches (product_id, expiry_date, quantity)
        VALUES (?, ?, ?);
    """, (product_id, expiry_date, quantity))
    return cursor.lastrowid


def _deduct_from_batches(
    cursor: sqlite3.Cursor,
    product_id: int,
    quantity: int,
    batch_id: Optional[int] = None
) -> Tuple[bool, str, List[Tuple[int, str, int]]]:
    """
    កាត់ចំនួនចេញពីឡូតិ៍។
    - batch_id ជាក់លាក់៖ កាត់ចេញពីឡូតិ៍នោះតែម្តង (ត្រូវមានចំនួនគ្រប់)
    - គ្មាន batch_id៖ FEFO (First-Expire-First-Out) កាត់ពីឡូតិ៍ដែលផុតកំណត់មុនគេជាមុន
    ត្រឡប់ list នៃ (batch_id, expiry_date, qty_deducted)
    """
    deducted: List[Tuple[int, str, int]] = []
    if batch_id is not None:
        cursor.execute(
            "SELECT * FROM product_batches WHERE id = ? AND product_id = ?",
            (batch_id, product_id)
        )
        b = cursor.fetchone()
        if not b:
            return False, "រកមិនឃើញឡូតិ៍ (Batch) នេះទេ!", []
        if b['quantity'] < quantity:
            return False, f"ឡូតិ៍ផុតកំណត់ {b['expiry_date']} នៅសល់តែ {b['quantity']} ប៉ុណ្ណោះ!", []
        cursor.execute("""
            UPDATE product_batches SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;
        """, (quantity, batch_id))
        deducted.append((b['id'], b['expiry_date'], quantity))
        return True, "", deducted

    remaining = quantity
    cursor.execute("""
        SELECT * FROM product_batches
        WHERE product_id = ? AND quantity > 0
        ORDER BY expiry_date ASC, id ASC;
    """, (product_id,))
    for b in cursor.fetchall():
        if remaining <= 0:
            break
        take = min(b['quantity'], remaining)
        cursor.execute("""
            UPDATE product_batches SET quantity = quantity - ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;
        """, (take, b['id']))
        deducted.append((b['id'], b['expiry_date'], take))
        remaining -= take
    # ចំនួនដែលនៅសល់ (remaining > 0) គឺជាស្តុកដែលមិនមានថ្ងៃផុតកំណត់
    return True, "", deducted


def record_stock_in(
    product_id: int,
    quantity: int,
    unit_price: float,
    reference: str,
    user_id: int,
    expiry_date: Optional[str] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """នាំចូលទំនិញ (Stock In) - អាចភ្ជាប់ថ្ងៃផុតកំណត់ (បង្កើតជាឡូតិ៍)"""
    if quantity <= 0:
        return False, "ចំនួននាំចូលត្រូវតែធំជាង ០!", None

    try:
        expiry_date = normalize_expiry_date(expiry_date)
    except ValueError as e:
        return False, str(e), None

    total_price = round(quantity * unit_price, 2)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if not product:
            return False, "រកមិនឃើញទំនិញនេះទេ!", None

        new_qty = product['quantity'] + quantity

        # កែសម្រួលចំនួនស្តុក និងតម្លៃទិញចូលជាមធ្យម ឬតម្លៃទិញចុងក្រោយ
        cursor.execute("""
            UPDATE products
            SET quantity = ?,
                cost_price = CASE WHEN ? > 0 THEN ? ELSE cost_price END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """, (new_qty, unit_price, unit_price, product_id))

        batch_id = None
        if expiry_date:
            batch_id = _upsert_batch(cursor, product_id, expiry_date, quantity)

        # កត់ត្រាចូល transactions
        cursor.execute("""
            INSERT INTO transactions (product_id, type, quantity, unit_price, total_price, reference, performed_by, batch_id, expiry_date)
            VALUES (?, 'IN', ?, ?, ?, ?, ?, ?, ?);
        """, (product_id, quantity, unit_price, total_price, reference, user_id, batch_id, expiry_date))

        conn.commit()

        # ទាញយកទិន្នន័យទំនិញដែលបានកែប្រែ
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        updated_prod = dict(cursor.fetchone())
        updated_prod['expiry_date'] = expiry_date
        return True, "នាំចូលទំនិញជោគជ័យ!", updated_prod


def record_stock_out(
    product_id: int,
    quantity: int,
    unit_price: float,
    reference: str,
    user_id: int,
    batch_id: Optional[int] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """នាំចេញ ឬកាត់ស្តុកទំនិញ (Stock Out) - កាត់ពីឡូតិ៍ដែលផុតកំណត់មុន (FEFO) ឬឡូតិ៍ជាក់លាក់"""
    if quantity <= 0:
        return False, "ចំនួននាំចេញត្រូវតែធំជាង ០!", None

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if not product:
            return False, "រកមិនឃើញទំនិញនេះទេ!", None

        curr_qty = product['quantity']
        if curr_qty < quantity:
            return False, f"ស្តុកមិនគ្រប់គ្រាន់ទេ! (នៅសល់តែ {curr_qty} {product['unit']})", None

        ok, err, deducted = _deduct_from_batches(cursor, product_id, quantity, batch_id)
        if not ok:
            conn.rollback()
            return False, err, None

        new_qty = curr_qty - quantity
        price = unit_price if unit_price > 0 else product['sell_price']
        total_price = round(quantity * price, 2)

        # កាត់ស្តុក
        cursor.execute("""
            UPDATE products
            SET quantity = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """, (new_qty, product_id))

        # កត់ត្រាចូល transactions (១ ជួរក្នុង ១ ឡូតិ៍ ដើម្បីតាមដានថ្ងៃផុតកំណត់បានច្បាស់)
        tracked = sum(q for _, _, q in deducted)
        rows = [(b_id, exp, q) for b_id, exp, q in deducted]
        if quantity - tracked > 0:
            rows.append((None, None, quantity - tracked))
        for b_id, exp, q in rows:
            cursor.execute("""
                INSERT INTO transactions (product_id, type, quantity, unit_price, total_price, reference, performed_by, batch_id, expiry_date)
                VALUES (?, 'OUT', ?, ?, ?, ?, ?, ?, ?);
            """, (product_id, q, price, round(q * price, 2), reference, user_id, b_id, exp))

        conn.commit()

        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        updated_prod = dict(cursor.fetchone())
        updated_prod['batches_deducted'] = [
            {"batch_id": b_id, "expiry_date": exp, "quantity": q} for b_id, exp, q in deducted
        ]
        return True, "កាត់ស្តុកជោគជ័យ!", updated_prod


# ==========================================
# របាយការណ៍ និងសង្ខេប (Reports & Summaries)
# ==========================================

def get_daily_summary(target_date: Optional[str] = None) -> Dict[str, Any]:
    """
    ទាញយករបាយការណ៍សង្ខេបប្រចាំថ្ងៃ
    target_date: 'YYYY-MM-DD' (ប្រសិនបើ None គឺយកថ្ងៃនេះ)
    """
    if not target_date:
        target_date = datetime.date.today().isoformat()

    with get_connection() as conn:
        cursor = conn.cursor()

        # សរុបនាំចូល
        cursor.execute("""
            SELECT COUNT(*) as tx_count,
                   COALESCE(SUM(quantity), 0) as total_qty,
                   COALESCE(SUM(total_price), 0) as total_amount
            FROM transactions
            WHERE type = 'IN' AND DATE(created_at) = DATE(?);
        """, (target_date,))
        in_row = cursor.fetchone()

        # សរុបនាំចេញ
        cursor.execute("""
            SELECT COUNT(*) as tx_count,
                   COALESCE(SUM(quantity), 0) as total_qty,
                   COALESCE(SUM(total_price), 0) as total_amount
            FROM transactions
            WHERE type = 'OUT' AND DATE(created_at) = DATE(?);
        """, (target_date,))
        out_row = cursor.fetchone()

        # ចំនួនទំនិញសរុប និងទំនិញជិតអស់
        cursor.execute("SELECT COUNT(*) as total_prods FROM products;")
        total_prods = cursor.fetchone()['total_prods']

        cursor.execute("SELECT COUNT(*) as low_count FROM products WHERE quantity <= min_quantity;")
        low_count = cursor.fetchone()['low_count']

        return {
            "date": target_date,
            "stock_in": {
                "transactions": in_row['tx_count'],
                "quantity": in_row['total_qty'],
                "amount": in_row['total_amount']
            },
            "stock_out": {
                "transactions": out_row['tx_count'],
                "quantity": out_row['total_qty'],
                "amount": out_row['total_amount']
            },
            "total_products": total_prods,
            "low_stock_count": low_count
        }


def get_recent_transactions(limit: int = 10) -> List[Dict[str, Any]]:
    return get_transactions(limit=limit)


def get_transactions(
    limit: int = 50,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tx_type: Optional[str] = None,
    search: Optional[str] = None,
    product_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    ប្រវត្តិប្រតិបត្តិការ ជាមួយតម្រង (Filter)៖
    - date_from / date_to : 'YYYY-MM-DD' (រួមបញ្ចូលថ្ងៃទាំងពីរ)
    - tx_type            : 'IN' ឬ 'OUT'
    - search             : ឈ្មោះ ឬកូដទំនិញ
    """
    where = []
    params: List[Any] = []
    if date_from:
        where.append("DATE(t.created_at) >= DATE(?)")
        params.append(date_from)
    if date_to:
        where.append("DATE(t.created_at) <= DATE(?)")
        params.append(date_to)
    if tx_type in ('IN', 'OUT'):
        where.append("t.type = ?")
        params.append(tx_type)
    if search:
        term = f"%{search.strip()}%"
        where.append("(p.name LIKE ? OR p.code LIKE ? OR t.reference LIKE ?)")
        params.extend([term, term, term])
    if product_id:
        where.append("t.product_id = ?")
        params.append(product_id)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT t.*, p.name as product_name, p.code as product_code, p.unit as product_unit,
                   u.full_name as user_name
            FROM transactions t
            JOIN products p ON t.product_id = p.id
            LEFT JOIN users u ON t.performed_by = u.user_id
            {where_sql}
            ORDER BY t.created_at DESC, t.id DESC
            LIMIT ?;
        """, params)
        return [dict(row) for row in cursor.fetchall()]


def get_transactions_summary(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tx_type: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """សរុបចំនួន និងទឹកប្រាក់ នាំចូល/នាំចេញ តាមតម្រងដូចគ្នានឹង get_transactions"""
    where = []
    params: List[Any] = []
    if date_from:
        where.append("DATE(t.created_at) >= DATE(?)")
        params.append(date_from)
    if date_to:
        where.append("DATE(t.created_at) <= DATE(?)")
        params.append(date_to)
    if tx_type in ('IN', 'OUT'):
        where.append("t.type = ?")
        params.append(tx_type)
    if search:
        term = f"%{search.strip()}%"
        where.append("(p.name LIKE ? OR p.code LIKE ? OR t.reference LIKE ?)")
        params.extend([term, term, term])
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT t.type,
                   COUNT(*) as tx_count,
                   COALESCE(SUM(t.quantity), 0) as total_qty,
                   COALESCE(SUM(t.total_price), 0) as total_amount
            FROM transactions t
            JOIN products p ON t.product_id = p.id
            {where_sql}
            GROUP BY t.type;
        """, params)
        result = {
            "IN": {"transactions": 0, "quantity": 0, "amount": 0.0},
            "OUT": {"transactions": 0, "quantity": 0, "amount": 0.0}
        }
        for row in cursor.fetchall():
            result[row['type']] = {
                "transactions": row['tx_count'],
                "quantity": row['total_qty'],
                "amount": round(row['total_amount'], 2)
            }
        return result


def get_transaction_calendar(year: int, month: int) -> Dict[str, Dict[str, int]]:
    """ចំនួននាំចូល/នាំចេញ ក្នុងថ្ងៃនីមួយៗនៃខែ សម្រាប់បង្ហាញលើប្រតិទិន"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DATE(created_at) as day, type,
                   COUNT(*) as tx_count, COALESCE(SUM(quantity), 0) as total_qty
            FROM transactions
            WHERE strftime('%Y', created_at) = ? AND strftime('%m', created_at) = ?
            GROUP BY day, type
            ORDER BY day ASC;
        """, (f"{year:04d}", f"{month:02d}"))
        days: Dict[str, Dict[str, int]] = {}
        for row in cursor.fetchall():
            d = days.setdefault(row['day'], {"in_qty": 0, "out_qty": 0, "in_count": 0, "out_count": 0})
            if row['type'] == 'IN':
                d['in_qty'] += row['total_qty']
                d['in_count'] += row['tx_count']
            else:
                d['out_qty'] += row['total_qty']
                d['out_count'] += row['tx_count']
        return days


# ==========================================
# ការកែប្រែ និងលុបទំនិញ (Edit & Delete Operations)
# ==========================================

def update_product(
    product_id: int,
    name: Optional[str] = None,
    category: Optional[str] = None,
    unit: Optional[str] = None,
    cost_price: Optional[float] = None,
    sell_price: Optional[float] = None,
    min_quantity: Optional[int] = None,
    location: Optional[str] = None
) -> Tuple[bool, str]:
    """កែប្រែព័ត៌មានទំនិញ"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        prod = cursor.fetchone()
        if not prod:
            return False, "រកមិនឃើញទំនិញនេះទេ!"

        new_name = name.strip() if name is not None else prod['name']
        new_cat = category.strip() if category is not None else prod['category']
        new_unit = unit.strip() if unit is not None else prod['unit']
        new_cost = cost_price if cost_price is not None else prod['cost_price']
        new_sell = sell_price if sell_price is not None else prod['sell_price']
        new_min = min_quantity if min_quantity is not None else prod['min_quantity']
        new_loc = location.strip() if location is not None else prod['location']

        cursor.execute("""
            UPDATE products
            SET name = ?, category = ?, unit = ?, cost_price = ?, sell_price = ?,
                min_quantity = ?, location = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """, (new_name, new_cat, new_unit, new_cost, new_sell, new_min, new_loc, product_id))
        conn.commit()
        return True, "កែប្រែព័ត៌មានទំនិញបានជោគជ័យ!"


def adjust_product_quantity(product_id: int, new_quantity: int, reason: str, user_id: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """កែសម្រួលចំនួនស្តុកជាក់ស្តែង (Adjust / Correct Stock)"""
    if new_quantity < 0:
        return False, "ចំនួនស្តុកមិនអាចអវិជ្ជមានបានទេ!", None

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        prod = cursor.fetchone()
        if not prod:
            return False, "រកមិនឃើញទំនិញនេះទេ!", None

        old_qty = prod['quantity']
        diff = new_quantity - old_qty
        if diff == 0:
            return True, "ចំនួនស្តុកនៅដដែល!", dict(prod)

        cursor.execute("""
            UPDATE products
            SET quantity = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """, (new_quantity, product_id))

        # បើកាត់ថយ ត្រូវកាត់ចេញពីឡូតិ៍ផុតកំណត់ដែរ (FEFO)
        if diff < 0:
            _deduct_from_batches(cursor, product_id, abs(diff))

        # កត់ត្រាជា Transaction កែតម្រូវ
        tx_type = 'IN' if diff > 0 else 'OUT'
        cursor.execute("""
            INSERT INTO transactions (product_id, type, quantity, unit_price, total_price, reference, performed_by)
            VALUES (?, ?, ?, 0.0, 0.0, ?, ?);
        """, (product_id, tx_type, abs(diff), f"កែតម្រូវស្តុក ({old_qty} ទៅ {new_quantity}): {reason}", user_id))

        conn.commit()

        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        updated = dict(cursor.fetchone())
        return True, "កែតម្រូវចំនួនស្តុកជោគជ័យ!", updated


def delete_product(product_id: int) -> Tuple[bool, str]:
    """លុបទំនិញចេញពីប្រព័ន្ធ"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        prod = cursor.fetchone()
        if not prod:
            return False, "រកមិនឃើញទំនិញនេះទេ!"

        name = prod['name']
        cursor.execute("DELETE FROM products WHERE id = ?;", (product_id,))
        conn.commit()
        return True, f"បានលុបទំនិញ '{name}' ដោយជោគជ័យ!"



# ==========================================
# ឡូតិ៍ និងថ្ងៃផុតកំណត់ (Batches & Expiry)
# ==========================================

def _expiry_status(expiry_date: Optional[str], warn_days: int = 30) -> Tuple[str, Optional[int]]:
    """ត្រឡប់ ('expired'|'soon'|'ok'|'none', days_left)"""
    if not expiry_date:
        return 'none', None
    try:
        exp = datetime.date.fromisoformat(expiry_date)
    except ValueError:
        return 'none', None
    days_left = (exp - datetime.date.today()).days
    if days_left < 0:
        return 'expired', days_left
    if days_left <= warn_days:
        return 'soon', days_left
    return 'ok', days_left


def get_product_batches(product_id: int, include_empty: bool = False) -> List[Dict[str, Any]]:
    """បញ្ជីឡូតិ៍ (ថ្ងៃផុតកំណត់) ទាំងអស់របស់ទំនិញមួយ តម្រៀបតាមថ្ងៃផុតកំណត់"""
    with get_connection() as conn:
        cursor = conn.cursor()
        sql = "SELECT * FROM product_batches WHERE product_id = ?"
        if not include_empty:
            sql += " AND quantity > 0"
        sql += " ORDER BY expiry_date ASC, id ASC;"
        cursor.execute(sql, (product_id,))
        batches = []
        for row in cursor.fetchall():
            b = dict(row)
            b['status'], b['days_left'] = _expiry_status(b['expiry_date'])
            batches.append(b)
        return batches


def attach_expiry_info(products: List[Dict[str, Any]], warn_days: int = 30) -> List[Dict[str, Any]]:
    """បន្ថែមព័ត៌មានផុតកំណត់ (nearest_expiry, expired_qty, expiring_qty, batches) លើបញ្ជីទំនិញ"""
    if not products:
        return products
    ids = [p['id'] for p in products]
    by_id: Dict[int, Dict[str, Any]] = {}
    for p in products:
        p['batches'] = []
        p['nearest_expiry'] = None
        p['expired_qty'] = 0
        p['expiring_qty'] = 0
        p['tracked_qty'] = 0
        p['expiry_status'] = 'none'
        p['days_left'] = None
        by_id[p['id']] = p

    with get_connection() as conn:
        cursor = conn.cursor()
        # SQLite មានកំណត់ចំនួន params ~999 ដូច្នេះបែងចែកជាបាច់
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            marks = ",".join("?" * len(chunk))
            cursor.execute(f"""
                SELECT * FROM product_batches
                WHERE product_id IN ({marks}) AND quantity > 0
                ORDER BY expiry_date ASC, id ASC;
            """, chunk)
            for row in cursor.fetchall():
                b = dict(row)
                b['status'], b['days_left'] = _expiry_status(b['expiry_date'], warn_days)
                p = by_id[b['product_id']]
                p['batches'].append(b)
                p['tracked_qty'] += b['quantity']
                if b['status'] == 'expired':
                    p['expired_qty'] += b['quantity']
                elif b['status'] == 'soon':
                    p['expiring_qty'] += b['quantity']
                if p['nearest_expiry'] is None:
                    p['nearest_expiry'] = b['expiry_date']
                    p['expiry_status'] = b['status']
                    p['days_left'] = b['days_left']
    return products


def list_expiry_batches(
    days: int = 30,
    status: str = 'all',
    search: Optional[str] = None,
    limit: int = 500
) -> List[Dict[str, Any]]:
    """
    បញ្ជីឡូតិ៍តាមស្ថានភាពផុតកំណត់៖
    status = 'expired' | 'soon' (ក្នុងរយៈពេល `days` ថ្ងៃ) | 'ok' | 'all'
    """
    today = datetime.date.today()
    limit_date = (today + datetime.timedelta(days=days)).isoformat()
    where = ["b.quantity > 0"]
    params: List[Any] = []
    if status == 'expired':
        where.append("DATE(b.expiry_date) < DATE(?)")
        params.append(today.isoformat())
    elif status == 'soon':
        where.append("DATE(b.expiry_date) >= DATE(?) AND DATE(b.expiry_date) <= DATE(?)")
        params.extend([today.isoformat(), limit_date])
    elif status == 'ok':
        where.append("DATE(b.expiry_date) > DATE(?)")
        params.append(limit_date)
    elif status == 'alert':
        where.append("DATE(b.expiry_date) <= DATE(?)")
        params.append(limit_date)
    if search:
        term = f"%{search.strip()}%"
        where.append("(p.name LIKE ? OR p.code LIKE ?)")
        params.extend([term, term])
    params.append(limit)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT b.*, p.code as product_code, p.name as product_name, p.unit as product_unit,
                   p.category as product_category, p.location as product_location
            FROM product_batches b
            JOIN products p ON b.product_id = p.id
            WHERE {" AND ".join(where)}
            ORDER BY b.expiry_date ASC, p.name ASC
            LIMIT ?;
        """, params)
        result = []
        for row in cursor.fetchall():
            b = dict(row)
            b['status'], b['days_left'] = _expiry_status(b['expiry_date'], days)
            result.append(b)
        return result


def get_expiry_summary(days: int = 30) -> Dict[str, Any]:
    """សង្ខេបចំនួនឡូតិ៍/ចំនួនទំនិញ ដែលផុតកំណត់ និងជិតផុតកំណត់"""
    today = datetime.date.today().isoformat()
    limit_date = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as batches, COALESCE(SUM(quantity), 0) as qty,
                   COUNT(DISTINCT product_id) as products
            FROM product_batches
            WHERE quantity > 0 AND DATE(expiry_date) < DATE(?);
        """, (today,))
        expired = dict(cursor.fetchone())
        cursor.execute("""
            SELECT COUNT(*) as batches, COALESCE(SUM(quantity), 0) as qty,
                   COUNT(DISTINCT product_id) as products
            FROM product_batches
            WHERE quantity > 0 AND DATE(expiry_date) >= DATE(?) AND DATE(expiry_date) <= DATE(?);
        """, (today, limit_date))
        soon = dict(cursor.fetchone())
        return {"days": days, "expired": expired, "expiring_soon": soon}


def get_expiry_calendar(year: int, month: int) -> Dict[str, Dict[str, Any]]:
    """ចំនួនឡូតិ៍ដែលផុតកំណត់ក្នុងថ្ងៃនីមួយៗ សម្រាប់បង្ហាញលើប្រតិទិន"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.expiry_date as day, COUNT(*) as batches, COALESCE(SUM(b.quantity), 0) as qty,
                   GROUP_CONCAT(p.name, ', ') as names
            FROM product_batches b
            JOIN products p ON b.product_id = p.id
            WHERE b.quantity > 0
              AND strftime('%Y', b.expiry_date) = ? AND strftime('%m', b.expiry_date) = ?
            GROUP BY b.expiry_date
            ORDER BY b.expiry_date ASC;
        """, (f"{year:04d}", f"{month:02d}"))
        return {row['day']: dict(row) for row in cursor.fetchall()}


def update_batch(batch_id: int, expiry_date: Optional[str] = None, quantity: Optional[int] = None,
                 user_id: Optional[int] = None) -> Tuple[bool, str]:
    """កែប្រែថ្ងៃផុតកំណត់ ឬចំនួនរបស់ឡូតិ៍ (ការកែចំនួន នឹងកែស្តុកសរុបរបស់ទំនិញដែរ)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM product_batches WHERE id = ?", (batch_id,))
        b = cursor.fetchone()
        if not b:
            return False, "រកមិនឃើញឡូតិ៍នេះទេ!"

        if expiry_date is not None:
            try:
                new_exp = normalize_expiry_date(expiry_date)
            except ValueError as e:
                return False, str(e)
            if not new_exp:
                return False, "ថ្ងៃផុតកំណត់មិនអាចទទេបានទេ!"
            if new_exp != b['expiry_date']:
                # បើមានឡូតិ៍ថ្ងៃដូចគ្នាស្រាប់ ត្រូវបញ្ចូលគ្នា
                cursor.execute(
                    "SELECT id FROM product_batches WHERE product_id = ? AND expiry_date = ? AND id != ?",
                    (b['product_id'], new_exp, batch_id)
                )
                dup = cursor.fetchone()
                if dup:
                    cursor.execute(
                        "UPDATE product_batches SET quantity = quantity + ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (b['quantity'], dup['id'])
                    )
                    cursor.execute("UPDATE transactions SET batch_id = ?, expiry_date = ? WHERE batch_id = ?",
                                   (dup['id'], new_exp, batch_id))
                    cursor.execute("DELETE FROM product_batches WHERE id = ?", (batch_id,))
                    conn.commit()
                    return True, f"បានបញ្ចូលឡូតិ៍ចូលគ្នាជាមួយថ្ងៃ {new_exp}!"
                cursor.execute(
                    "UPDATE product_batches SET expiry_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (new_exp, batch_id)
                )
                cursor.execute("UPDATE transactions SET expiry_date = ? WHERE batch_id = ?", (new_exp, batch_id))

        if quantity is not None:
            if quantity < 0:
                return False, "ចំនួនមិនអាចអវិជ្ជមានបានទេ!"
            diff = quantity - b['quantity']
            if diff != 0:
                cursor.execute(
                    "UPDATE product_batches SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (quantity, batch_id)
                )
                cursor.execute(
                    "UPDATE products SET quantity = MAX(0, quantity + ?), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (diff, b['product_id'])
                )
                tx_type = 'IN' if diff > 0 else 'OUT'
                cursor.execute("""
                    INSERT INTO transactions (product_id, type, quantity, unit_price, total_price, reference, performed_by, batch_id, expiry_date)
                    VALUES (?, ?, ?, 0.0, 0.0, ?, ?, ?, ?);
                """, (b['product_id'], tx_type, abs(diff),
                      f"កែតម្រូវឡូតិ៍ ({b['quantity']} ទៅ {quantity})", user_id or 0, batch_id, b['expiry_date']))

        conn.commit()
        return True, "បានកែប្រែឡូតិ៍ជោគជ័យ!"


def delete_batch(batch_id: int, user_id: Optional[int] = None, reason: str = "លុបឡូតិ៍ (ផុតកំណត់/ខូច)") -> Tuple[bool, str]:
    """លុបឡូតិ៍ (ឧ. ទំនិញផុតកំណត់បោះចោល) - កាត់ស្តុកសរុបរបស់ទំនិញតាមចំនួនឡូតិ៍"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM product_batches WHERE id = ?", (batch_id,))
        b = cursor.fetchone()
        if not b:
            return False, "រកមិនឃើញឡូតិ៍នេះទេ!"
        qty = b['quantity']
        if qty > 0:
            cursor.execute(
                "UPDATE products SET quantity = MAX(0, quantity - ?), updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (qty, b['product_id'])
            )
            cursor.execute("""
                INSERT INTO transactions (product_id, type, quantity, unit_price, total_price, reference, performed_by, batch_id, expiry_date)
                VALUES (?, 'OUT', ?, 0.0, 0.0, ?, ?, NULL, ?);
            """, (b['product_id'], qty, reason, user_id or 0, b['expiry_date']))
        cursor.execute("UPDATE transactions SET batch_id = NULL WHERE batch_id = ?", (batch_id,))
        cursor.execute("DELETE FROM product_batches WHERE id = ?", (batch_id,))
        conn.commit()
        return True, f"បានលុបឡូតិ៍ផុតកំណត់ {b['expiry_date']} (-{qty}) ជោគជ័យ!"


# ==========================================
# នាំចូលទិន្នន័យជាបាច់ (Bulk Import)
# ==========================================

IMPORT_COLUMNS = [
    ("code", ["code", "sku", "barcode", "កូដ", "កូដទំនិញ", "លេខកូដ"]),
    ("name", ["name", "product", "product_name", "ឈ្មោះ", "ឈ្មោះទំនិញ"]),
    ("category", ["category", "cat", "group", "ប្រភេទ"]),
    ("unit", ["unit", "uom", "ខ្នាត", "ឯកតា"]),
    ("cost_price", ["cost_price", "cost", "buy_price", "តម្លៃដើម", "តម្លៃទិញ"]),
    ("sell_price", ["sell_price", "sell", "price", "sale_price", "តម្លៃលក់"]),
    ("quantity", ["quantity", "qty", "stock", "ចំនួន", "ចំនួនស្តុក"]),
    ("min_quantity", ["min_quantity", "min_qty", "min", "reorder", "កម្រិតជូនដំណឹង"]),
    ("location", ["location", "loc", "shelf", "ទីតាំង"]),
    ("expiry_date", ["expiry_date", "expiry", "expire", "exp", "expiration", "best_before", "ផុតកំណត់", "ថ្ងៃផុតកំណត់"]),
    ("reference", ["reference", "ref", "note", "supplier", "កំណត់ចំណាំ", "អ្នកផ្គត់ផ្គង់"]),
]


def _norm_header(h: Any) -> str:
    return str(h or '').strip().lower().replace(' ', '_').replace('-', '_')


def map_import_headers(headers: List[Any]) -> Dict[int, str]:
    """ផ្គូផ្គងឈ្មោះ column ក្នុងឯកសារ ទៅនឹង field ក្នុងប្រព័ន្ធ (ត្រឡប់ {column_index: field})"""
    mapping: Dict[int, str] = {}
    used = set()
    for idx, h in enumerate(headers):
        key = _norm_header(h)
        if not key:
            continue
        # អនុញ្ញាតឱ្យ header មានទម្រង់ "code (កូដ)" -> យកតែផ្នែកមុនវង់ក្រចក
        base = key.split('(')[0].strip('_ ')
        for field, aliases in IMPORT_COLUMNS:
            if field in used:
                continue
            norm_aliases = [_norm_header(a) for a in aliases]
            if key in norm_aliases or base in norm_aliases or any(key.startswith(a + '_') for a in norm_aliases):
                mapping[idx] = field
                used.add(field)
                break
    return mapping


def _to_float(v: Any, default: float = 0.0) -> float:
    if v is None or str(v).strip() == '':
        return default
    return float(str(v).replace('$', '').replace(',', '').strip())


def _to_int(v: Any, default: int = 0) -> int:
    if v is None or str(v).strip() == '':
        return default
    return int(float(str(v).replace(',', '').strip()))


def import_products_rows(
    rows: List[Dict[str, Any]],
    user_id: int,
    update_existing: bool = True,
    reference: str = "នាំចូលទិន្នន័យពីឯកសារ (Import)"
) -> Dict[str, Any]:
    """
    នាំចូលទិន្នន័យទំនិញជាបាច់។ ជួរនីមួយៗមាន field: code, name, category, unit, cost_price,
    sell_price, quantity, min_quantity, location, expiry_date, reference
    - កូដថ្មី      -> បង្កើតទំនិញ + ស្តុកដំបូង (ជាមួយថ្ងៃផុតកំណត់បើមាន)
    - កូដមានស្រាប់ -> កែព័ត៌មាន (បើ update_existing) + បន្ថែមស្តុក/ឡូតិ៍ថ្មីបើ quantity > 0
    ទំនិញតែ ១ អាចមានច្រើនជួរ ដែលមានថ្ងៃផុតកំណត់ខុសគ្នា = ឡូតិ៍ច្រើន
    """
    summary = {"total": len(rows), "created": 0, "updated": 0, "stock_added": 0, "batches": 0,
               "skipped": 0, "errors": []}

    for i, r in enumerate(rows, start=2):  # ជួរទី ១ ជា header
        code = str(r.get('code') or '').strip()
        name = str(r.get('name') or '').strip()
        try:
            if not code:
                raise ValueError("ខ្វះកូដទំនិញ (code)")
            qty = _to_int(r.get('quantity'), 0)
            if qty < 0:
                raise ValueError("ចំនួន (quantity) មិនអាចអវិជ្ជមាន")
            expiry = normalize_expiry_date(r.get('expiry_date'))
            cost = _to_float(r.get('cost_price'), 0.0)
            sell = _to_float(r.get('sell_price'), 0.0)
            row_ref = str(r.get('reference') or '').strip() or reference

            existing = get_product_by_code(code)
            if existing:
                if update_existing:
                    update_product(
                        product_id=existing['id'],
                        name=name or None,
                        category=(str(r.get('category')).strip() if r.get('category') else None),
                        unit=(str(r.get('unit')).strip() if r.get('unit') else None),
                        cost_price=cost if r.get('cost_price') not in (None, '') else None,
                        sell_price=sell if r.get('sell_price') not in (None, '') else None,
                        min_quantity=_to_int(r.get('min_quantity')) if r.get('min_quantity') not in (None, '') else None,
                        location=(str(r.get('location')).strip() if r.get('location') else None),
                    )
                    summary['updated'] += 1
                else:
                    summary['skipped'] += 1
                product_id = existing['id']
            else:
                if not name:
                    raise ValueError("ខ្វះឈ្មោះទំនិញ (name) សម្រាប់កូដថ្មី")
                ok, msg, product_id = add_product(
                    code=code, name=name,
                    category=str(r.get('category') or 'ទូទៅ').strip() or 'ទូទៅ',
                    unit=str(r.get('unit') or 'ឯកតា').strip() or 'ឯកតា',
                    cost_price=cost, sell_price=sell, quantity=0,
                    min_quantity=_to_int(r.get('min_quantity'), 5),
                    location=str(r.get('location') or 'ឃ្លាំងធំ').strip() or 'ឃ្លាំងធំ'
                )
                if not ok:
                    raise ValueError(msg)
                summary['created'] += 1

            if qty > 0 and product_id:
                ok, msg, _ = record_stock_in(
                    product_id=product_id, quantity=qty, unit_price=cost,
                    reference=row_ref, user_id=user_id, expiry_date=expiry
                )
                if not ok:
                    raise ValueError(msg)
                summary['stock_added'] += qty
                if expiry:
                    summary['batches'] += 1
        except Exception as e:
            summary['errors'].append({"row": i, "code": code, "error": str(e)})

    summary['success'] = summary['total'] - len(summary['errors'])
    return summary


def generate_import_sample_rows() -> List[List[Any]]:
    """ទិន្នន័យគំរូសម្រាប់ឯកសារ Import (ទំនិញ ១ អាចមានច្រើនជួរ = ថ្ងៃផុតកំណត់ច្រើន)"""
    today = datetime.date.today()
    d = lambda days: (today + datetime.timedelta(days=days)).isoformat()
    headers = ["code", "name", "category", "unit", "cost_price", "sell_price",
               "quantity", "min_quantity", "location", "expiry_date", "reference"]
    rows = [
        ["MED-001", "Paracetamol 500mg", "ថ្នាំពេទ្យ", "ប្រអប់", 1.20, 2.00, 50, 10, "ទូ A", d(90), "ក្រុមហ៊ុន A - Inv#1001"],
        ["MED-001", "Paracetamol 500mg", "ថ្នាំពេទ្យ", "ប្រអប់", 1.20, 2.00, 30, 10, "ទូ A", d(240), "ក្រុមហ៊ុន A - Inv#1002"],
        ["MED-001", "Paracetamol 500mg", "ថ្នាំពេទ្យ", "ប្រអប់", 1.20, 2.00, 20, 10, "ទូ A", d(400), "ក្រុមហ៊ុន A - Inv#1003"],
        ["DRK-010", "Coca-Cola 330ml", "ភេសជ្ជៈ", "កំប៉ុង", 0.35, 0.60, 120, 24, "ធ្នើរទី២", d(180), "ដឹកជញ្ជូនលើកទី១"],
        ["DRK-010", "Coca-Cola 330ml", "ភេសជ្ជៈ", "កំប៉ុង", 0.35, 0.60, 48, 24, "ធ្នើរទី២", d(15), "ស្តុកចាស់ ជិតផុតកំណត់"],
        ["EQP-200", "ដបទឹកកែវ 1L", "ឧបករណ៍", "ដប", 2.50, 4.00, 10, 3, "ឃ្លាំងធំ", "", "គ្មានថ្ងៃផុតកំណត់"],
    ]
    return [headers] + rows

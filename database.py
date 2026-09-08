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

def record_stock_in(
    product_id: int,
    quantity: int,
    unit_price: float,
    reference: str,
    user_id: int
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """នាំចូលទំនិញ (Stock In)"""
    if quantity <= 0:
        return False, "ចំនួននាំចូលត្រូវតែធំជាង ០!", None

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

        # កត់ត្រាចូល transactions
        cursor.execute("""
            INSERT INTO transactions (product_id, type, quantity, unit_price, total_price, reference, performed_by)
            VALUES (?, 'IN', ?, ?, ?, ?, ?);
        """, (product_id, quantity, unit_price, total_price, reference, user_id))

        conn.commit()

        # ទាញយកទិន្នន័យទំនិញដែលបានកែប្រែ
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        updated_prod = dict(cursor.fetchone())
        return True, "នាំចូលទំនិញជោគជ័យ!", updated_prod


def record_stock_out(
    product_id: int,
    quantity: int,
    unit_price: float,
    reference: str,
    user_id: int
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """នាំចេញ ឬកាត់ស្តុកទំនិញ (Stock Out)"""
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

        # កត់ត្រាចូល transactions
        cursor.execute("""
            INSERT INTO transactions (product_id, type, quantity, unit_price, total_price, reference, performed_by)
            VALUES (?, 'OUT', ?, ?, ?, ?, ?);
        """, (product_id, quantity, price, total_price, reference, user_id))

        conn.commit()

        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        updated_prod = dict(cursor.fetchone())
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
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, p.name as product_name, p.code as product_code, p.unit as product_unit,
                   u.full_name as user_name
            FROM transactions t
            JOIN products p ON t.product_id = p.id
            LEFT JOIN users u ON t.performed_by = u.user_id
            ORDER BY t.created_at DESC
            LIMIT ?;
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


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


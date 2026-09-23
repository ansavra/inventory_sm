import hashlib
import os
import secrets
import time
from typing import Optional, Dict, Any

SESSION_EXPIRY_SECONDS = 7 * 24 * 3600  # 7 days

# Session ត្រូវរក្សាក្នុង Database (មិនមែនក្នុង memory) ដើម្បីឱ្យដំណើរការលើ
# Vercel serverless ដែលរាល់ការហៅមួយៗអាចជា process ថ្មី។
_memory_sessions: Dict[str, Dict[str, Any]] = {}   # fallback ពេល DB មានបញ្ហា


def hash_password(password: str) -> str:
    """Hash password ដោយប្រើ PBKDF2-HMAC-SHA256 ជាមួយ Salt"""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return f"{salt}${key}"


def verify_password(stored_hash: str, password_attempt: str) -> bool:
    """ផ្ទៀងផ្ទាត់លេខសម្ងាត់"""
    if not stored_hash or '$' not in stored_hash:
        return False
    salt, key = stored_hash.split('$', 1)
    new_key = hashlib.pbkdf2_hmac(
        'sha256',
        password_attempt.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    return secrets.compare_digest(key, new_key)


def create_session(user: Dict[str, Any]) -> str:
    """បង្កើត Session Token ថ្មី និងរក្សាទុកក្នុង Database"""
    token = secrets.token_urlsafe(32)
    data = {
        "user_id": user["user_id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
        "expires_at": time.time() + SESSION_EXPIRY_SECONDS
    }
    _memory_sessions[token] = data
    try:
        from db_core import get_connection
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO web_sessions (token, user_id, username, full_name, role, expires_at)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (token, data["user_id"], data["username"], data["full_name"],
                  data["role"], data["expires_at"]))
            # សម្អាត Session ផុតកំណត់ចាស់ៗ
            cur.execute("DELETE FROM web_sessions WHERE expires_at < ?;", (time.time(),))
            conn.commit()
    except Exception:
        pass
    return token


def get_session(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """ទាញយក Session ប្រសិនបើតម្លៃនៅត្រឹមត្រូវ"""
    if not token:
        return None

    sess = _memory_sessions.get(token)
    if sess:
        if time.time() > sess["expires_at"]:
            _memory_sessions.pop(token, None)
            delete_session(token)
            return None
        return sess

    try:
        from db_core import get_connection
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM web_sessions WHERE token = ?", (token,))
            row = cur.fetchone()
            if not row:
                return None
            data = {
                "user_id": row["user_id"],
                "username": row["username"],
                "full_name": row["full_name"],
                "role": row["role"],
                "expires_at": float(row["expires_at"]),
            }
    except Exception:
        return None

    if time.time() > data["expires_at"]:
        delete_session(token)
        return None

    _memory_sessions[token] = data
    return data


def delete_session(token: Optional[str]):
    """លុប Session (Logout)"""
    if not token:
        return
    _memory_sessions.pop(token, None)
    try:
        from db_core import get_connection
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM web_sessions WHERE token = ?;", (token,))
            conn.commit()
    except Exception:
        pass

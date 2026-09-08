import hashlib
import os
import secrets
import time
from typing import Optional, Dict, Any

# Session storage: token -> {user_id, username, full_name, role, expires_at}
_active_sessions: Dict[str, Dict[str, Any]] = {}
SESSION_EXPIRY_SECONDS = 7 * 24 * 3600  # 7 days


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
    """បង្កើត Session Token ថ្មី"""
    token = secrets.token_urlsafe(32)
    _active_sessions[token] = {
        "user_id": user["user_id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
        "expires_at": time.time() + SESSION_EXPIRY_SECONDS
    }
    return token


def get_session(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """ទាញយក Session ប្រសិនបើតម្លៃនៅត្រឹមត្រូវ"""
    if not token or token not in _active_sessions:
        return None
    sess = _active_sessions[token]
    if time.time() > sess["expires_at"]:
        del _active_sessions[token]
        return None
    return sess


def delete_session(token: Optional[str]):
    """លុប Session (Logout)"""
    if token and token in _active_sessions:
        del _active_sessions[token]

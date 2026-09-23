"""
Telegram Bot សម្រាប់ Webhook (Serverless)
==========================================
លើ Vercel គ្មាន process រត់ជាប់ទេ — រាល់សារពី Telegram ជាការហៅថ្មីមួយ។
ដូច្នេះ៖
  • ស្ថានភាពសន្ទនា (ConversationHandler) ត្រូវរក្សាក្នុង Database តាម `DBPersistence`
  • Application ត្រូវបង្កើត និង initialize ម្តងក្នុងមួយ cold start (cache ក្នុង global)
"""
import asyncio
import json
import logging
from typing import Any, Dict, Optional, Tuple

from telegram import Update
from telegram.ext import BasePersistence, PersistenceInput

import config
import db_core

logger = logging.getLogger(__name__)

_SCOPE_USER = "user_data"
_SCOPE_CHAT = "chat_data"
_SCOPE_BOT = "bot_data"
_SCOPE_CONV = "conversations"


# ==========================================
# រក្សាស្ថានភាព Bot ក្នុង Database
# ==========================================

def _load(scope: str) -> Dict[str, Any]:
    """អានទិន្នន័យទាំងអស់ក្នុង scope មួយ -> {key: value}"""
    try:
        with db_core.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT key, value FROM bot_state WHERE scope = ?", (scope,))
            out = {}
            for row in cur.fetchall():
                try:
                    out[row["key"]] = json.loads(row["value"]) if row["value"] else {}
                except (ValueError, TypeError):
                    out[row["key"]] = {}
            return out
    except Exception as e:
        logger.warning(f"bot_state load({scope}) បរាជ័យ: {e}")
        return {}


def _save(scope: str, key: str, value: Any) -> None:
    try:
        with db_core.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO bot_state (scope, key, value, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(scope, key) DO UPDATE
                    SET value = excluded.value, updated_at = excluded.updated_at;
            """, (scope, key, json.dumps(value, ensure_ascii=False, default=str)))
            conn.commit()
    except Exception as e:
        logger.warning(f"bot_state save({scope}/{key}) បរាជ័យ: {e}")


def _delete(scope: str, key: str) -> None:
    try:
        with db_core.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM bot_state WHERE scope = ? AND key = ?", (scope, key))
            conn.commit()
    except Exception as e:
        logger.warning(f"bot_state delete({scope}/{key}) បរាជ័យ: {e}")


def _conv_key_to_str(key: Tuple) -> str:
    return "|".join(str(k) for k in key)


def _conv_key_from_str(text: str) -> Tuple:
    parts = []
    for p in text.split("|"):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(p)
    return tuple(parts)


class DBPersistence(BasePersistence):
    """រក្សា user_data / chat_data / bot_data / conversations ក្នុង Database"""

    def __init__(self):
        super().__init__(store_data=PersistenceInput(
            bot_data=True, chat_data=True, user_data=True, callback_data=False
        ), update_interval=60)

    # ---------- user_data ----------
    async def get_user_data(self) -> Dict[int, Dict]:
        return {int(k): v for k, v in _load(_SCOPE_USER).items() if str(k).lstrip("-").isdigit()}

    async def update_user_data(self, user_id: int, data: Dict) -> None:
        _save(_SCOPE_USER, str(user_id), data)

    async def drop_user_data(self, user_id: int) -> None:
        _delete(_SCOPE_USER, str(user_id))

    async def refresh_user_data(self, user_id: int, user_data: Dict) -> None:
        return None

    # ---------- chat_data ----------
    async def get_chat_data(self) -> Dict[int, Dict]:
        return {int(k): v for k, v in _load(_SCOPE_CHAT).items() if str(k).lstrip("-").isdigit()}

    async def update_chat_data(self, chat_id: int, data: Dict) -> None:
        _save(_SCOPE_CHAT, str(chat_id), data)

    async def drop_chat_data(self, chat_id: int) -> None:
        _delete(_SCOPE_CHAT, str(chat_id))

    async def refresh_chat_data(self, chat_id: int, chat_data: Dict) -> None:
        return None

    # ---------- bot_data ----------
    async def get_bot_data(self) -> Dict:
        return _load(_SCOPE_BOT).get("bot", {})

    async def update_bot_data(self, data: Dict) -> None:
        _save(_SCOPE_BOT, "bot", data)

    async def refresh_bot_data(self, bot_data: Dict) -> None:
        return None

    # ---------- callback_data (មិនប្រើ) ----------
    async def get_callback_data(self):
        return None

    async def update_callback_data(self, data) -> None:
        return None

    # ---------- conversations ----------
    async def get_conversations(self, name: str) -> Dict:
        raw = _load(_SCOPE_CONV).get(name, {})
        return {_conv_key_from_str(k): v for k, v in raw.items()}

    async def update_conversation(self, name: str, key: Tuple, new_state: Optional[object]) -> None:
        raw = _load(_SCOPE_CONV).get(name, {})
        skey = _conv_key_to_str(key)
        if new_state is None:
            raw.pop(skey, None)
        else:
            raw[skey] = new_state
        _save(_SCOPE_CONV, name, raw)

    async def flush(self) -> None:
        return None


# ==========================================
# Application (cache ក្នុងមួយ cold start)
# ==========================================

_application = None
_init_lock = asyncio.Lock()


async def get_application():
    """បង្កើត និង initialize Application (តែម្តងក្នុងមួយ instance)"""
    global _application
    if _application is not None:
        return _application

    async with _init_lock:
        if _application is not None:
            return _application
        import main  # ចុះឈ្មោះ handler ទាំងអស់ពី main.py
        app = main.build_application(persistence=DBPersistence())
        await app.initialize()
        _application = app
        return _application


async def process_update(payload: Dict[str, Any]) -> None:
    """ដំណើរការ Update មួយពី Telegram Webhook"""
    app = await get_application()
    update = Update.de_json(payload, app.bot)
    if update is None:
        return
    await app.process_update(update)
    # សរសេរស្ថានភាពចូល Database ភ្លាម (serverless អាចបិទភ្លាមក្រោយឆ្លើយតប)
    try:
        await app.update_persistence()
    except Exception as e:
        logger.warning(f"update_persistence បរាជ័យ: {e}")


def webhook_path() -> str:
    """ផ្លូវ Webhook (មានលេខសម្ងាត់ដើម្បីកុំឱ្យអ្នកដទៃហៅបាន)"""
    return f"/api/telegram/webhook/{config.TELEGRAM_WEBHOOK_SECRET}"

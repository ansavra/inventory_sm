import os
import json
import logging
import threading
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Set

import config

logger = logging.getLogger(__name__)


def _get_target_chat_ids() -> Set[str]:
    """ទាញយក Chat IDs ទាំងអស់ដែលត្រូវទទួលបានការជូនដំណឹង (Admin IDs & Alert Group/Channel)"""
    targets = set()

    # 1. Alert Group ឬ Channel ID ពី .env (ឧ. -100xxxx ឬ @channel_name)
    alert_chat_id = getattr(config, "ALERT_CHAT_ID", "").strip()
    if alert_chat_id:
        targets.add(alert_chat_id)

    # 2. Telegram IDs របស់អ្នកគ្រប់គ្រង (Admin IDs) ទាំងអស់
    for admin_id in config.ADMIN_IDS:
        targets.add(str(admin_id))

    return targets


def _send_telegram_message_async(text: str, parse_mode: str = "Markdown"):
    """ផ្ញើសារតាម Telegram ទៅកាន់ Admins/Groups ដោយប្រើ Background Thread (មិនបង្កការរំខាន ឬយឺតដល់ប្រព័ន្ធ)"""
    bot_token = config.BOT_TOKEN
    if not bot_token:
        logger.debug("Telegram Bot Token មិនទាន់បានកំណត់ មិនអាចផ្ញើការជូនដំណឹងបានទេ។")
        return

    targets = _get_target_chat_ids()
    if not targets:
        logger.debug("មិនមាន Chat ID ឬ Admin ID សម្រាប់ទទួលការជូនដំណឹងទេ។")
        return

    def worker():
        api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        for chat_id in targets:
            try:
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode
                }
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    api_url,
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    pass
            except Exception as e:
                logger.warning(f"បរាជ័យក្នុងការផ្ញើ Alert ទៅកាន់ Chat ID {chat_id}: {e}")

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


def alert_low_stock(product: Dict[str, Any], current_qty: int, min_qty: int):
    """ការជូនដំណឹងបន្ទាន់៖ ទំនិញជិតអស់ពីស្តុក (Low Stock Alert)"""
    name = product.get("name", "ទំនិញ")
    code = product.get("code", "N/A")
    unit = product.get("unit", "ឯកតា")
    location = product.get("location", "ឃ្លាំងធំ")

    text = (
        "🚨 **ការជូនដំណឹងបន្ទាន់៖ ទំនិញជិតអស់ពីស្តុក!**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 **ទំនិញ ៖** {name}\n"
        f"🏷️ **លេខកូដ (SKU) ៖** `{code}`\n"
        f"⚠️ **ស្តុកនៅសល់ជាក់ស្តែង ៖** `{current_qty} {unit}`\n"
        f"🎯 **កម្រិតសុវត្ថិភាពកំណត់ ៖** `{min_qty} {unit}`\n"
        f"📍 **ទីតាំងឃ្លាំង ៖** {location}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *សូមមេត្តារៀបចំបញ្ជាទិញចូលស្តុកបន្ថែមជាបន្ទាន់!*"
    )
    _send_telegram_message_async(text)


def alert_stock_out(
    product: Dict[str, Any],
    quantity: int,
    unit_price: float,
    total_price: float,
    remaining_stock: int,
    performed_by: str,
    reference: str = ""
):
    """ការជូនដំណឹង៖ នាំចេញ/លក់ទំនិញ (Stock Out / Sale Alert)"""
    name = product.get("name", "ទំនិញ")
    code = product.get("code", "N/A")
    unit = product.get("unit", "ឯកតា")
    min_qty = product.get("min_quantity", 5)

    ref_str = reference if reference and reference != "-" else "លក់ចេញទូទៅ"

    text = (
        "📤 **ការជូនដំណឹង៖ មានការនាំចេញ/លក់ទំនិញ**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 **ទំនិញ ៖** {name} (`{code}`)\n"
        f"➖ **ចំនួនដកចេញ ៖** -{quantity} {unit}\n"
        f"💵 **តម្លៃលក់រាយ ៖** ${unit_price:.2f} / {unit}\n"
        f"💰 **ចំណូលសរុប ៖** **${total_price:.2f}**\n"
        f"📊 **ស្តុកនៅសល់ ៖** `{remaining_stock} {unit}`\n"
        f"👤 **អ្នកកត់ត្រា ៖** {performed_by}\n"
        f"🔖 **វិក្កយបត្រ/មូលហេតុ ៖** {ref_str}\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    _send_telegram_message_async(text)

    # ប្រសិនបើស្តុកធ្លាក់ចុះដល់ ឬក្រោម Low Stock Alert ផ្ញើការព្រមានបន្ថែមភ្លាមៗ
    if remaining_stock <= min_qty:
        alert_low_stock(product, remaining_stock, min_qty)


def alert_stock_in(
    product: Dict[str, Any],
    quantity: int,
    cost_price: float,
    total_price: float,
    new_stock: int,
    performed_by: str,
    reference: str = ""
):
    """ការជូនដំណឹង៖ នាំចូលទំនិញថ្មី (Stock In Alert)"""
    name = product.get("name", "ទំនិញ")
    code = product.get("code", "N/A")
    unit = product.get("unit", "ឯកតា")

    ref_str = reference if reference and reference != "-" else "ទិញចូលស្តុក"

    text = (
        "📥 **ការជូនដំណឹង៖ បាននាំចូលទំនិញថ្មី**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 **ទំនិញ ៖** {name} (`{code}`)\n"
        f"➕ **ចំនួននាំចូល ៖** +{quantity} {unit}\n"
        f"💵 **តម្លៃដើម ៖** ${cost_price:.2f} / {unit}\n"
        f"💰 **តម្លៃដើមសរុប ៖** **${total_price:.2f}**\n"
        f"📊 **ស្តុកសរុបបច្ចុប្បន្ន ៖** `{new_stock} {unit}`\n"
        f"👤 **អ្នកកត់ត្រា ៖** {performed_by}\n"
        f"🏢 **អ្នកផ្គត់ផ្គង់/វិក្កយបត្រ ៖** {ref_str}\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    _send_telegram_message_async(text)


def send_system_alert(title: str, message: str):
    """ផ្ញើសារជូនដំណឹងប្រព័ន្ធទូទៅ"""
    text = (
        f"🔔 **{title}**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{message}\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    _send_telegram_message_async(text)

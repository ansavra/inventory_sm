import os
import json
import logging
import threading
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# URL Webhook ពី Google Apps Script
# អាចកំណត់ក្នុង .env: GOOGLE_SHEET_WEBHOOK_URL="https://script.google.com/macros/s/.../exec"
WEBHOOK_URL = os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "").strip()


def set_webhook_url(url: str):
    """កំណត់ ឬផ្លាស់ប្តូរ Webhook URL (រក្សាក្នុង Database ដើម្បីឱ្យនៅគង់វង្សលើ serverless)"""
    global WEBHOOK_URL
    WEBHOOK_URL = url.strip()
    try:
        import db_core
        db_core.set_setting("google_sheet_webhook_url", WEBHOOK_URL)
    except Exception as e:
        logger.warning(f"មិនអាចរក្សា Google Sheet Webhook URL ក្នុង Database: {e}")


def get_webhook_url() -> str:
    """អាន Webhook URL ពី Database មុន (បើគ្មាន ប្រើតម្លៃពី .env)"""
    global WEBHOOK_URL
    try:
        import db_core
        stored = db_core.get_setting("google_sheet_webhook_url", "")
        if stored:
            WEBHOOK_URL = stored
    except Exception:
        pass
    return WEBHOOK_URL


def _send_payload_async(payload: Dict[str, Any]):
    """បញ្ជូនទិន្នន័យទៅ Google Sheets ដោយប្រើ Threading (មិនធ្វើឱ្យ Bot ឬ Web យឺតឡើយ)"""
    def worker():
        url = get_webhook_url()
        if not url:
            return

        try:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_text = resp.read().decode("utf-8")
                logger.info(f"Google Sheet sync success: {resp_text[:100]}")
        except Exception as e:
            logger.warning(f"Google Sheet sync error (អាចមកពី Webhook URL មិនទាន់ត្រឹមត្រូវ): {e}")

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


def sync_transaction(
    tx_type: str,
    product_code: str,
    product_name: str,
    quantity: int,
    unit: str,
    unit_price: float,
    total_price: float,
    reference: str,
    performed_by: str,
    stock_remaining: int
):
    """បញ្ជូនប្រតិបត្តិការ នាំចូល ឬ នាំចេញ ទៅ Google Sheets ដោយស្វ័យប្រវត្តិ"""
    if not get_webhook_url():
        return

    payload = {
        "action": "transaction",
        "type": "នាំចូល (IN)" if tx_type == "IN" else "នាំចេញ (OUT)",
        "product_code": product_code,
        "product_name": product_name,
        "quantity": quantity,
        "unit": unit,
        "unit_price": unit_price,
        "total_price": total_price,
        "reference": reference or "-",
        "performed_by": performed_by or "System",
        "stock_remaining": stock_remaining
    }
    _send_payload_async(payload)


def sync_product(
    code: str,
    name: str,
    category: str,
    unit: str,
    cost_price: float,
    sell_price: float,
    quantity: int,
    location: str
):
    """បញ្ជូនទំនិញថ្មីទៅ Sheet ទំនិញ"""
    if not get_webhook_url():
        return

    payload = {
        "action": "product",
        "code": code,
        "name": name,
        "category": category,
        "unit": unit,
        "cost_price": cost_price,
        "sell_price": sell_price,
        "quantity": quantity,
        "location": location
    }
    _send_payload_async(payload)


def test_connection(webhook_url: str) -> bool:
    """តេស្តមើលថាតើ Google Sheet Webhook ដំណើរការឬអត់"""
    if not webhook_url:
        return False
    try:
        data = json.dumps({"action": "ping"}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 302)
    except Exception as e:
        logger.error(f"Google Sheet ping failed: {e}")
        return False

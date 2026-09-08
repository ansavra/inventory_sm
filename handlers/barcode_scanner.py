import io
import logging
from telegram import Update
from telegram.ext import ContextTypes
from PIL import Image

import database as db
import keyboards as kb
from handlers.inventory import format_product_card

logger = logging.getLogger(__name__)

# Check if pyzbar is available
try:
    from pyzbar.pyzbar import decode as zbar_decode
    PYZBAR_AVAILABLE = True
except Exception as e:
    PYZBAR_AVAILABLE = False
    logger.info(f"pyzbar not available, will use OpenCV: {e}")

# Check if OpenCV is available
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except Exception as e:
    OPENCV_AVAILABLE = False
    logger.info(f"OpenCV not available: {e}")


def decode_image_code(image_bytes_io) -> tuple[str, str]:
    """
    ព្យាយាម decode barcode / QR code ពីរូបភាព
    ត្រឡប់មកវិញ (code_str, code_type) ឬ ("", "")
    """
    image_bytes_io.seek(0)
    # 1. សាកល្បងជាមួយ PyZBar ជាមុនសិន
    if PYZBAR_AVAILABLE:
        try:
            image = Image.open(image_bytes_io)
            decoded_objects = zbar_decode(image)
            if decoded_objects:
                return (
                    decoded_objects[0].data.decode("utf-8").strip(),
                    decoded_objects[0].type
                )
        except Exception as e:
            logger.debug(f"Pyzbar decoding failed: {e}")

    # 2. បើមិនទាន់ឃើញ ឬគ្មាន PyZBar សាកល្បងជាមួយ OpenCV QRCodeDetector
    if OPENCV_AVAILABLE:
        try:
            image_bytes_io.seek(0)
            file_bytes = np.asarray(bytearray(image_bytes_io.read()), dtype=np.uint8)
            img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            if img is not None:
                detector = cv2.QRCodeDetector()
                data, bbox, _ = detector.detectAndDecode(img)
                if data:
                    return data.strip(), "QRCODE"
        except Exception as e:
            logger.debug(f"OpenCV decoding failed: {e}")

    return "", ""


async def photo_barcode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ទទួលយករូបថត និងស្កេនរក Barcode / QR Code"""
    if not update.message.photo:
        return

    if not PYZBAR_AVAILABLE and not OPENCV_AVAILABLE:
        await update.message.reply_text(
            "⚠️ ប្រព័ន្ធមិនទាន់អាចស្កេនរូបភាពបានទេ!\n"
            "👉 សូមវាយលេខកូដ Barcode ដោយផ្ទាល់ជាអក្សរជំនួសវិញ។"
        )
        return

    status_msg = await update.message.reply_text("⏳ កំពុងស្កេនពិនិត្យ Barcode / QR Code ពីរូបថត...")

    # ទាញយករូបថតទំហំធំបំផុត
    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    image_bytes = io.BytesIO()
    await photo_file.download_to_memory(image_bytes)

    try:
        code, code_type = decode_image_code(image_bytes)

        if not code:
            await status_msg.edit_text(
                "❌ រកមិនឃើញ Barcode ឬ QR Code ក្នុងរូបថតនេះទេ!\n"
                "💡 សូមព្យាយាមថតឱ្យកាន់តែច្បាស់ និងជិត ឬវាយលេខកូដដោយដៃ។"
            )
            return

        user_id = update.effective_user.id
        is_admin = db.is_admin(user_id)

        product = db.get_product_by_code(code)

        if product:
            card = format_product_card(product, is_admin)
            await status_msg.edit_text(
                f"📷 **ស្កេនជោគជ័យ!** (ប្រភេទ៖ {code_type})\n\n{card}",
                reply_markup=kb.get_product_action_keyboard(product['id'], is_admin),
                parse_mode="Markdown"
            )
        else:
            await status_msg.edit_text(
                f"📷 **ស្កេនបានកូដ៖** `{code}` ({code_type})\n\n"
                f"⚠️ មិនទាន់មានទំនិញដែលមានលេខកូដនេះក្នុងស្តុកនៅឡើយទេ។\n"
                f"👉 អ្នកអាចចុច **'➕ បន្ថែមទំនិញថ្មី'** ហើយប្រើប្រាស់លេខកូដនេះបាន!",
                parse_mode="Markdown"
            )

    except Exception as ex:
        logger.error(f"Error scanning barcode: {ex}", exc_info=True)
        await status_msg.edit_text(
            f"❌ មានបញ្ហាក្នុងការស្កេនរូបថត៖ {str(ex)}\n"
            "សូមសាកល្បងវាយលេខកូដដោយផ្ទាល់។"
        )

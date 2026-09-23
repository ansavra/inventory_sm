import logging
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

import config
import database as db
import keyboards as kb

# Handlers
from handlers.common import start_command, help_command, cancel_conversation, web_dashboard_info_handler
from handlers.inventory import (
    check_inventory_handler,
    edit_delete_menu_handler,
    product_view_callback,
    low_stock_handler,
    search_start,
    search_perform,
    SEARCH_WAITING,
    format_product_card
)
from handlers.stock_in import (
    stock_in_start,
    stock_in_product_selected,
    stock_in_quantity_received,
    stock_in_price_received,
    stock_in_finish,
    stock_in_from_callback,
    stock_in_expiry_received,
    stock_in_batch_received,
    IN_SELECT_PRODUCT,
    IN_QUANTITY,
    IN_PRICE,
    IN_EXPIRY,
    IN_BATCH,
    IN_REFERENCE
)
from handlers.stock_out import (
    stock_out_start,
    stock_out_product_selected,
    stock_out_quantity_received,
    stock_out_price_received,
    stock_out_finish,
    stock_out_from_callback,
    OUT_SELECT_PRODUCT,
    OUT_QUANTITY,
    OUT_PRICE,
    OUT_REFERENCE
)
from handlers.product_mgmt import (
    add_product_start,
    add_product_code_received,
    add_product_name_received,
    add_product_category_received,
    add_product_unit_received,
    add_product_cost_received,
    add_product_sell_received,
    add_product_qty_received,
    add_product_min_qty_received,
    add_product_finish,
    PROD_CODE,
    PROD_NAME,
    PROD_CATEGORY,
    PROD_UNIT,
    PROD_COST_PRICE,
    PROD_SELL_PRICE,
    PROD_QTY,
    PROD_MIN_QTY,
    PROD_LOCATION
)
from handlers.reports import reports_menu_handler, reports_callback_handler
from handlers.barcode_scanner import photo_barcode_handler
from handlers.admin import admin_users_handler
from handlers.product_edit import (
    edit_product_menu_callback,
    edit_field_chosen_callback,
    edit_value_received,
    delete_confirm_callback,
    delete_execute_callback,
    EDIT_SELECT_ACTION,
    EDIT_VALUE
)

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """កត់ត្រាកំហុសស្វ័យប្រវត្តិ និងផ្ញើសារប្រាប់អ្នកប្រើប្រាស់បើចាំបាច់"""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ មានបញ្ហាបច្ចេកទេសមួយបានកើតឡើង! សូមព្យាយាមម្តងទៀត។"
            )
        except Exception:
            pass


async def generic_refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback សម្រាប់ប៊ូតុង Refresh ទិន្នន័យទំនិញ"""
    query = update.callback_query
    await query.answer("កំពុងផ្ទុកទិន្នន័យថ្មី...")
    data = query.data
    if data.startswith("act_refresh:"):
        pid = int(data.split(":")[1])
        prod = db.get_product_by_id(pid)
        if prod:
            is_admin = db.is_admin(update.effective_user.id)
            card = format_product_card(prod, is_admin)
            try:
                await query.edit_message_text(
                    card,
                    reply_markup=kb.get_product_action_keyboard(pid, is_admin),
                    parse_mode="Markdown"
                )
            except Exception:
                pass


def build_application(persistence=None):
    """បង្កើត Telegram Application និងចុះឈ្មោះ Handler ទាំងអស់
    (ប្រើរួមគ្នាទាំង Polling ក្នុង local និង Webhook លើ Vercel)"""
    builder = ApplicationBuilder().token(config.BOT_TOKEN)
    if persistence is not None:
        builder = builder.persistence(persistence)
    app = builder.build()

    # ពេលមាន persistence (Webhook/serverless) ត្រូវរក្សាស្ថានភាពសន្ទនាក្នុង Database
    _persist = persistence is not None


    # Cancel filter (ប៊ូតុងបោះបង់ ឬបញ្ជា /cancel)
    cancel_filter = filters.Regex("^❌ បោះបង់$") | filters.Regex(r"^/cancel")

    # ==========================================
    # Conversation Handlers
    # ==========================================

    # A. បន្ថែមទំនិញថ្មី (Add Product)
    add_product_conv = ConversationHandler(
        name="add_product_conv",
        persistent=_persist,
        entry_points=[
            MessageHandler(filters.Regex("^➕ បន្ថែមទំនិញថ្មី$"), add_product_start),
            CommandHandler("addproduct", add_product_start)
        ],
        states={
            PROD_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, add_product_code_received)
            ],
            PROD_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, add_product_name_received)
            ],
            PROD_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, add_product_category_received)
            ],
            PROD_UNIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, add_product_unit_received)
            ],
            PROD_COST_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, add_product_cost_received)
            ],
            PROD_SELL_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, add_product_sell_received)
            ],
            PROD_QTY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, add_product_qty_received)
            ],
            PROD_MIN_QTY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, add_product_min_qty_received)
            ],
            PROD_LOCATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, add_product_finish)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ បោះបង់$"), cancel_conversation),
            CommandHandler("cancel", cancel_conversation)
        ]
    )

    # B. នាំចូលទំនិញ (Stock In)
    stock_in_conv = ConversationHandler(
        name="stock_in_conv",
        persistent=_persist,
        entry_points=[
            MessageHandler(filters.Regex("^📥 នាំចូលទំនិញ$"), stock_in_start),
            CommandHandler("stockin", stock_in_start),
            CallbackQueryHandler(stock_in_from_callback, pattern=r"^act_in:\d+$")
        ],
        states={
            IN_SELECT_PRODUCT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, stock_in_product_selected)
            ],
            IN_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, stock_in_quantity_received)
            ],
            IN_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, stock_in_price_received)
            ],
            IN_EXPIRY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, stock_in_expiry_received)
            ],
            IN_BATCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, stock_in_batch_received)
            ],
            IN_REFERENCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, stock_in_finish)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ បោះបង់$"), cancel_conversation),
            CommandHandler("cancel", cancel_conversation)
        ]
    )

    # C. នាំចេញ/កាត់ស្តុក (Stock Out)
    stock_out_conv = ConversationHandler(
        name="stock_out_conv",
        persistent=_persist,
        entry_points=[
            MessageHandler(filters.Regex("^📤 នាំចេញ/លក់$"), stock_out_start),
            CommandHandler("stockout", stock_out_start),
            CallbackQueryHandler(stock_out_from_callback, pattern=r"^act_out:\d+$")
        ],
        states={
            OUT_SELECT_PRODUCT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, stock_out_product_selected)
            ],
            OUT_QUANTITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, stock_out_quantity_received)
            ],
            OUT_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, stock_out_price_received)
            ],
            OUT_REFERENCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, stock_out_finish)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ បោះបង់$"), cancel_conversation),
            CommandHandler("cancel", cancel_conversation)
        ]
    )

    # D. ស្វែងរកទំនិញ (Search Product)
    search_conv = ConversationHandler(
        name="search_conv",
        persistent=_persist,
        entry_points=[
            MessageHandler(filters.Regex("^🔍 ស្វែងរកទំនិញ$"), search_start),
            CommandHandler("search", search_start)
        ],
        states={
            SEARCH_WAITING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, search_perform)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ បោះបង់$"), cancel_conversation),
            CommandHandler("cancel", cancel_conversation)
        ]
    )

    # E. កែប្រែទំនិញ (Edit Product)
    edit_product_conv = ConversationHandler(
        name="edit_product_conv",
        persistent=_persist,
        entry_points=[
            CallbackQueryHandler(edit_product_menu_callback, pattern=r"^act_edit:\d+$")
        ],
        states={
            EDIT_SELECT_ACTION: [
                CallbackQueryHandler(edit_field_chosen_callback, pattern=r"^ed_")
            ],
            EDIT_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~cancel_filter, edit_value_received)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ បោះបង់$"), cancel_conversation),
            CommandHandler("cancel", cancel_conversation),
            CallbackQueryHandler(generic_refresh_callback, pattern=r"^act_refresh:")
        ]
    )

    # ចុះឈ្មោះ Conversations
    app.add_handler(add_product_conv)
    app.add_handler(stock_in_conv)
    app.add_handler(stock_out_conv)
    app.add_handler(search_conv)
    app.add_handler(edit_product_conv)

    # ==========================================
    # Standard Commands & Button Handlers
    # ==========================================
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))

    # Menu Buttons
    app.add_handler(MessageHandler(filters.Regex("^📦 ពិនិត្យស្តុក$"), check_inventory_handler))
    app.add_handler(MessageHandler(filters.Regex("^✏️ កែប្រែ / លុបទំនិញ$"), edit_delete_menu_handler))
    app.add_handler(MessageHandler(filters.Regex("^⚠️ ទំនិញជិតអស់$"), low_stock_handler))
    app.add_handler(MessageHandler(filters.Regex("^📊 របាយការណ៍$"), reports_menu_handler))
    app.add_handler(MessageHandler(filters.Regex("^🌐 ចូលមើលលើ Web$"), web_dashboard_info_handler))
    app.add_handler(MessageHandler(filters.Regex("^⚙️ គ្រប់គ្រងអ្នកប្រើប្រាស់$"), admin_users_handler))
    app.add_handler(MessageHandler(filters.Regex("^ℹ️ ជំនួយ / ព័ត៌មាន$"), help_command))

    # Barcode/QR Scanning from photo
    app.add_handler(MessageHandler(filters.PHOTO, photo_barcode_handler))

    # Callbacks
    app.add_handler(CallbackQueryHandler(reports_callback_handler, pattern=r"^rep_"))
    app.add_handler(CallbackQueryHandler(product_view_callback, pattern=r"^act_view:\d+$"))
    app.add_handler(CallbackQueryHandler(delete_confirm_callback, pattern=r"^act_del_confirm:\d+$"))
    app.add_handler(CallbackQueryHandler(delete_execute_callback, pattern=r"^act_del_yes:\d+$"))
    app.add_handler(CallbackQueryHandler(generic_refresh_callback, pattern=r"^act_refresh:"))

    # Error Handler
    app.add_error_handler(error_handler)

    return app


def main():
    print("==================================================")
    print("🚀 កំពុងចាប់ផ្តើម Telegram Inventory Bot...")
    print("==================================================")

    # 1. ពិនិត្យ Token
    if not config.BOT_TOKEN or config.BOT_TOKEN == "your_telegram_bot_token_here":
        print("\n❌ កំហុស៖ មិនទាន់ឃើញ TELEGRAM_BOT_TOKEN ក្នុងឯកសារ .env ឡើយ!")
        print("👉 សូមបង្កើតឯកសារ .env (ចម្លងពី .env.example) រួចដាក់ Token របស់ Bot របស់អ្នក។\n")
        print("ឧទាហរណ៍ក្នុងឯកសារ .env:")
        print("TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ")
        print("ADMIN_USER_IDS=123456789\n")
        sys.exit(1)

    # 2. បង្កើត SQLite Database
    print("📦 កំពុងរៀបចំ Database (inventory.db)...")
    db.init_db()
    print("✅ Database រួចរាល់!")

    app = build_application()


    print("🤖 Bot កំពុងដំណើរការ... (ចុច Ctrl + C ដើម្បីបញ្ឈប់)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

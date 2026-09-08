from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import database as db
import keyboards as kb
from handlers.inventory import format_product_card

(
    PROD_CODE,
    PROD_NAME,
    PROD_CATEGORY,
    PROD_UNIT,
    PROD_COST_PRICE,
    PROD_SELL_PRICE,
    PROD_QTY,
    PROD_MIN_QTY,
    PROD_LOCATION
) = range(9)


async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ចាប់ផ្តើមបន្ថែមទំនិញថ្មី"""
    context.user_data.clear()
    await update.message.reply_text(
        "➕ **បង្កើតទំនិញថ្មីក្នុងប្រព័ន្ធ (Add Product)**\n\n"
        "👉 សូមបញ្ចូល **លេខកូដទំនិញ (SKU ឬ Barcode)** ៖\n"
        "(ឧទាហរណ៍៖ `8850123456789` ឬ `PROD-001`)\n\n"
        "*(អ្នកក៏អាចថតរូប Barcode ផ្ញើចូលដើម្បីយកកូដដោយស្វ័យប្រវត្តិបានដែរ)*",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return PROD_CODE


async def add_product_code_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    existing = db.get_product_by_code(code)
    if existing:
        await update.message.reply_text(
            f"⚠️ កូដទំនិញ `{code}` មានក្នុងប្រព័ន្ធរួចហើយ ({existing['name']})!\n"
            f"សូមបញ្ចូលលេខកូដថ្មី ឬចុច '❌ បោះបង់'៖",
            reply_markup=kb.get_cancel_keyboard(),
            parse_mode="Markdown"
        )
        return PROD_CODE

    context.user_data['p_code'] = code
    await update.message.reply_text(
        "👉 សូមបញ្ចូល **ឈ្មោះទំនិញ** ៖\n(ឧទាហរណ៍៖ `Coca Cola កំប៉ុង 330ml`)",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return PROD_NAME


async def add_product_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data['p_name'] = name

    await update.message.reply_text(
        "👉 សូមបញ្ចូល **ប្រភេទ/ក្រុមទំនិញ (Category)** ៖\n"
        "(ឧទាហរណ៍៖ `ភេសជ្ជៈ`, `សម្ភារៈប្រើប្រាស់` ឬវាយ `-` សម្រាប់ 'ទូទៅ') ៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return PROD_CATEGORY


async def add_product_category_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cat = update.message.text.strip()
    context.user_data['p_cat'] = "ទូទៅ" if cat == "-" else cat

    await update.message.reply_text(
        "👉 សូមបញ្ចូល **ខ្នាតទំនិញ (Unit)** ៖\n"
        "(ឧទាហរណ៍៖ `កំប៉ុង`, `ដប`, `ប្រអប់`, `កញ្ចប់`, `គីឡូ`) ៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return PROD_UNIT


async def add_product_unit_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    unit = update.message.text.strip()
    context.user_data['p_unit'] = unit

    await update.message.reply_text(
        f"💵 សូមបញ្ចូល **តម្លៃដើម/ទិញចូល (Cost Price)** ក្នុង ១{unit} ($) ៖\n"
        "(ឧទាហរណ៍៖ `0.50` ឬវាយ `0` បើមិនទាន់កំណត់) ៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return PROD_COST_PRICE


async def add_product_cost_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        cost = float(text)
        if cost < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ តម្លៃមិនត្រឹមត្រូវ! សូមបញ្ចូលជាលេខ ឧ. 0.50 ៖",
            reply_markup=kb.get_cancel_keyboard()
        )
        return PROD_COST_PRICE

    context.user_data['p_cost'] = cost
    unit = context.user_data['p_unit']

    await update.message.reply_text(
        f"🏷️ សូមបញ្ចូល **តម្លៃលក់ (Selling Price)** ក្នុង ១{unit} ($) ៖\n"
        "(ឧទាហរណ៍៖ `0.75` ឬវាយ `0`) ៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return PROD_SELL_PRICE


async def add_product_sell_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        sell = float(text)
        if sell < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ តម្លៃមិនត្រឹមត្រូវ! សូមបញ្ចូលជាលេខ ឧ. 0.75 ៖",
            reply_markup=kb.get_cancel_keyboard()
        )
        return PROD_SELL_PRICE

    context.user_data['p_sell'] = sell
    unit = context.user_data['p_unit']

    await update.message.reply_text(
        f"📊 សូមបញ្ចូល **ចំនួនស្តុកដំបូង (Initial Quantity)** គិតជា {unit} ៖\n"
        "(ឧទាហរណ៍៖ `24` ឬវាយ `0` ប្រសិនបើមិនទាន់មានក្នុងស្តុក) ៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return PROD_QTY


async def add_product_qty_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit() or int(text) < 0:
        await update.message.reply_text(
            "⚠️ សូមបញ្ចូលជាចំនួនលេខ (0 ឬធំជាង) ៖",
            reply_markup=kb.get_cancel_keyboard()
        )
        return PROD_QTY

    context.user_data['p_qty'] = int(text)
    unit = context.user_data['p_unit']

    await update.message.reply_text(
        f"⚠️ សូមបញ្ចូល **កម្រិតកំណត់ជូនដំណឹងជិតអស់ (Min Stock / Reorder Point)** ៖\n"
        f"(ឧ. នៅសល់តិចជាង `5` {unit} នឹងផ្ញើសារប្រាប់ ឬវាយ `-` សម្រាប់ 5) ៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return PROD_MIN_QTY


async def add_product_min_qty_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "-":
        min_qty = 5
    elif text.isdigit() and int(text) >= 0:
        min_qty = int(text)
    else:
        await update.message.reply_text(
            "⚠️ សូមបញ្ចូលជាលេខវិជ្ជមាន ឬវាយ '-' ៖",
            reply_markup=kb.get_cancel_keyboard()
        )
        return PROD_MIN_QTY

    context.user_data['p_min_qty'] = min_qty

    await update.message.reply_text(
        "📍 សូមបញ្ចូល **ទីតាំងទុកដាក់ក្នុងឃ្លាំង (Location)** ៖\n"
        "(ឧទាហរណ៍៖ `ធ្នើរ A-01`, `ទូកញ្ចក់ជាន់ទី២` ឬវាយ `-` សម្រាប់ 'ឃ្លាំងធំ') ៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return PROD_LOCATION


async def add_product_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loc = update.message.text.strip()
    location = "ឃ្លាំងធំ" if loc == "-" else loc

    user_id = update.effective_user.id
    is_admin = db.is_admin(user_id)

    code = context.user_data['p_code']
    name = context.user_data['p_name']
    cat = context.user_data['p_cat']
    unit = context.user_data['p_unit']
    cost = context.user_data['p_cost']
    sell = context.user_data['p_sell']
    qty = context.user_data['p_qty']
    min_qty = context.user_data['p_min_qty']

    success, msg, prod_id = db.add_product(
        code=code,
        name=name,
        category=cat,
        unit=unit,
        cost_price=cost,
        sell_price=sell,
        quantity=qty,
        min_quantity=min_qty,
        location=location
    )

    if success and prod_id:
        # Sync ទៅកាន់ Google Sheets ប្រសិនបើបានភ្ជាប់
        try:
            import google_sheets_sync
            google_sheets_sync.sync_product(
                code=code,
                name=name,
                category=cat,
                unit=unit,
                cost_price=cost,
                sell_price=sell,
                quantity=qty,
                location=location
            )
        except Exception:
            pass

        # ប្រសិនបើមានចំនួនដំបូងធំជាង ០ កត់ត្រាជា Transaction នាំចូលដំបូង
        if qty > 0:
            db.record_stock_in(
                product_id=prod_id,
                quantity=qty,
                unit_price=cost,
                reference="ស្តុកដំបូងពេលបង្កើតទំនិញ",
                user_id=user_id
            )
            try:
                import google_sheets_sync
                user_info = db.get_user_by_id(user_id)
                u_name = user_info.get('full_name', 'Telegram User') if user_info else 'Telegram User'
                google_sheets_sync.sync_transaction(
                    tx_type="IN",
                    product_code=code,
                    product_name=name,
                    quantity=qty,
                    unit=unit,
                    unit_price=cost,
                    total_price=round(cost * qty, 2),
                    reference="ស្តុកដំបូងពេលបង្កើតទំនិញ",
                    performed_by=u_name,
                    stock_remaining=qty
                )
            except Exception:
                pass

        product = db.get_product_by_id(prod_id)
        card = format_product_card(product, is_admin)

        await update.message.reply_text(
            f"🎉 **បង្កើតទំនិញថ្មីបានជោគជ័យ!**\n\n{card}",
            reply_markup=kb.get_product_action_keyboard(prod_id, is_admin),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ បរាជ័យ៖ {msg}")

    context.user_data.clear()
    await update.message.reply_text(
        "តើអ្នកចង់ធ្វើអ្វីបន្តទៀត?",
        reply_markup=kb.get_main_menu_keyboard(is_admin)
    )
    return ConversationHandler.END

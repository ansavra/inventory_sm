from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import database as db
import keyboards as kb

IN_SELECT_PRODUCT, IN_QUANTITY, IN_PRICE, IN_EXPIRY, IN_REFERENCE = range(5)


async def stock_in_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ចាប់ផ្តើមដំណើរការនាំចូលទំនិញ"""
    context.user_data.clear()
    await update.message.reply_text(
        "📥 **នាំចូលទំនិញ (Stock In)**\n\n"
        "សូមវាយ **លេខកូដ (Barcode/SKU)** ឬ **ឈ្មោះទំនិញ** ដែលត្រូវនាំចូល៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return IN_SELECT_PRODUCT


async def stock_in_product_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ទទួលយកឈ្មោះ ឬលេខកូដទំនិញ"""
    query = update.message.text.strip()
    products = db.search_products(query, limit=5)

    if not products:
        await update.message.reply_text(
            f"❌ រកមិនឃើញទំនិញ '{query}' ទេ!\n"
            "សូមពិនិត្យលេខកូដ ឬឈ្មោះឡើងវិញ ឬចុច '❌ បោះបង់'៖",
            reply_markup=kb.get_cancel_keyboard()
        )
        return IN_SELECT_PRODUCT

    # ប្រសិនបើមានច្រើន ឱ្យជ្រើសរើស
    product = products[0]
    context.user_data['stock_in_product_id'] = product['id']
    context.user_data['stock_in_product_name'] = product['name']
    context.user_data['stock_in_product_unit'] = product['unit']

    await update.message.reply_text(
        f"✅ បានជ្រើសរើស៖ **{product['name']}** (កូដ: `{product['code']}`)\n"
        f"📊 ចំនួនបច្ចុប្បន្នក្នុងស្តុក៖ **{product['quantity']} {product['unit']}**\n\n"
        f"👉 សូមបញ្ចូល **ចំនួនដែលត្រូវនាំចូល** (ឧ. 10, 50, 100)៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return IN_QUANTITY


async def stock_in_quantity_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ទទួលចំនួននាំចូល"""
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text(
            "⚠️ សូមបញ្ចូលជាចំនួនលេខវិជ្ជមាន (ធំជាង ០) ឧទាហរណ៍៖ 10, 25 ៖",
            reply_markup=kb.get_cancel_keyboard()
        )
        return IN_QUANTITY

    qty = int(text)
    context.user_data['stock_in_qty'] = qty

    await update.message.reply_text(
        f"💵 សូមបញ្ចូល **តម្លៃទិញចូលក្នុង ១{context.user_data.get('stock_in_product_unit', 'ឯកតា')}** ($)\n"
        f"(ឧទាហរណ៍៖ `1.50` ឬវាយ `0` ប្រសិនបើមិនចង់កត់ត្រាតម្លៃ) ៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return IN_PRICE


async def stock_in_price_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ទទួលតម្លៃទិញចូល"""
    text = update.message.text.strip()
    try:
        price = float(text)
        if price < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ តម្លៃមិនត្រឹមត្រូវ! សូមបញ្ចូលជាលេខ ឧទាហរណ៍៖ 2.5 ឬ 0 ៖",
            reply_markup=kb.get_cancel_keyboard()
        )
        return IN_PRICE

    context.user_data['stock_in_price'] = price

    # បង្ហាញឡូតិ៍ដែលមានស្រាប់ ដើម្បីងាយស្រួលជ្រើសរើស
    batches = db.get_product_batches(context.user_data['stock_in_product_id'])
    batch_text = ""
    if batches:
        batch_text = "\n📋 ឡូតិ៍ដែលមានស្រាប់៖\n" + "\n".join(
            f"  • `{b['expiry_date']}` — សល់ {b['quantity']}" for b in batches[:8]
        ) + "\n"

    await update.message.reply_text(
        "⏰ សូមបញ្ចូល **ថ្ងៃផុតកំណត់ (Expiry Date)** របស់ទំនិញដែលនាំចូលលើកនេះ៖\n"
        "(ទម្រង់៖ `2026-12-31` ឬ `31/12/2026` — ឬវាយ `-` បើគ្មានថ្ងៃផុតកំណត់)\n"
        f"{batch_text}"
        "💡 ទំនិញ ១ អាចមានថ្ងៃផុតកំណត់ច្រើន៖ ថ្ងៃថ្មី = ឡូតិ៍ថ្មី, ថ្ងៃដូចឡូតិ៍ស្រាប់ = បូកបញ្ចូលគ្នា។",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return IN_EXPIRY


async def stock_in_expiry_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ទទួលថ្ងៃផុតកំណត់ (ឬ - បើគ្មាន)"""
    text = update.message.text.strip()
    try:
        expiry = db.normalize_expiry_date(text)
    except ValueError:
        await update.message.reply_text(
            "⚠️ ទម្រង់ថ្ងៃមិនត្រឹមត្រូវ! សូមវាយជា `2026-12-31` ឬ `31/12/2026` ឬ `-` បើគ្មាន៖",
            reply_markup=kb.get_cancel_keyboard(),
            parse_mode="Markdown"
        )
        return IN_EXPIRY

    context.user_data['stock_in_expiry'] = expiry

    await update.message.reply_text(
        "📝 សូមបញ្ចូល **ប្រភពផ្គត់ផ្គង់ / លេខវិក្កយបត្រ / កំណត់ចំណាំ** ៖\n"
        "(ឧទាហរណ៍៖ `អ្នកផ្គត់ផ្គង់ A - វិក្កយបត្រ #1049` ឬវាយ `-` បើគ្មាន) ៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return IN_REFERENCE


async def stock_in_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """បញ្ចប់ការនាំចូល និងកត់ត្រាចូល Database"""
    ref = update.message.text.strip()
    if ref == "-":
        ref = "នាំចូលទូទៅ"

    user_id = update.effective_user.id
    is_admin = db.is_admin(user_id)
    product_id = context.user_data['stock_in_product_id']
    qty = context.user_data['stock_in_qty']
    price = context.user_data['stock_in_price']
    expiry = context.user_data.get('stock_in_expiry')

    success, message, updated_prod = db.record_stock_in(
        product_id=product_id,
        quantity=qty,
        unit_price=price,
        reference=ref,
        user_id=user_id,
        expiry_date=expiry
    )

    if success and updated_prod:
        import google_sheets_sync
        import notifier
        total = qty * price
        performer = update.effective_user.full_name or "Telegram User"
        google_sheets_sync.sync_transaction(
            tx_type="IN",
            product_code=updated_prod.get("code", ""),
            product_name=updated_prod.get("name", ""),
            quantity=qty,
            unit=updated_prod.get("unit", "ឯកតា"),
            unit_price=price,
            total_price=total,
            reference=ref,
            performed_by=performer,
            stock_remaining=updated_prod.get("quantity", 0)
        )
        # ផ្ញើការជូនដំណឹង Real-time ទៅកាន់ Admin និង Alert Group
        notifier.alert_stock_in(
            product=updated_prod,
            quantity=qty,
            cost_price=price,
            total_price=total,
            new_stock=updated_prod.get("quantity", 0),
            performed_by=performer,
            reference=ref
        )
        result_text = (
            f"🎉 **នាំចូលទំនិញជោគជ័យ!**\n\n"
            f"📦 ទំនិញ៖ **{updated_prod['name']}**\n"
            f"📥 ចំនួនបន្ថែម៖ +{qty} {updated_prod['unit']}\n"
            f"📊 ស្តុកថ្មីសរុប៖ **{updated_prod['quantity']} {updated_prod['unit']}**\n"
            f"⏰ ថ្ងៃផុតកំណត់៖ {expiry or 'គ្មាន'}\n"
            f"💵 តម្លៃក្នុងមួយឯកតា៖ ${price:.2f}\n"
            f"💰 ចំណាយសរុប៖ ${total:.2f}\n"
            f"🔖 កំណត់ចំណាំ៖ {ref}\n"
            f"👤 អ្នកបញ្ចូល៖ {update.effective_user.full_name}"
        )
    else:
        result_text = f"❌ បរាជ័យ៖ {message}"

    context.user_data.clear()
    await update.message.reply_text(
        result_text,
        reply_markup=kb.get_main_menu_keyboard(is_admin),
        parse_mode="Markdown"
    )
    return ConversationHandler.END


# Helper សម្រាប់ Callback ពេលចុចប៊ូតុង [📥 នាំចូល] លើ Card ទំនិញ
async def stock_in_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split(":")[1])
    product = db.get_product_by_id(product_id)
    if not product:
        await query.edit_message_text("❌ រកមិនឃើញទំនិញនេះទៀតទេ!")
        return ConversationHandler.END

    context.user_data['stock_in_product_id'] = product['id']
    context.user_data['stock_in_product_name'] = product['name']
    context.user_data['stock_in_product_unit'] = product['unit']

    await query.message.reply_text(
        f"📥 **នាំចូលទំនិញ៖ {product['name']}** (កូដ: `{product['code']}`)\n"
        f"📊 ចំនួនបច្ចុប្បន្ន៖ **{product['quantity']} {product['unit']}**\n\n"
        f"👉 សូមបញ្ចូល **ចំនួនដែលត្រូវនាំចូល** (ឧ. 10, 50, 100)៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return IN_QUANTITY

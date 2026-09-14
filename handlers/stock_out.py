from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import database as db
import keyboards as kb

OUT_SELECT_PRODUCT, OUT_QUANTITY, OUT_PRICE, OUT_REFERENCE = range(4)


async def stock_out_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ចាប់ផ្តើមដំណើរការនាំចេញ/កាត់ស្តុក"""
    context.user_data.clear()
    await update.message.reply_text(
        "📤 **នាំចេញ / កាត់ស្តុកទំនិញ (Stock Out)**\n\n"
        "សូមវាយ **លេខកូដ (Barcode/SKU)** ឬ **ឈ្មោះទំនិញ** ដែលត្រូវកាត់ស្តុក៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return OUT_SELECT_PRODUCT


async def stock_out_product_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ទទួលយកឈ្មោះ ឬលេខកូដទំនិញ"""
    query = update.message.text.strip()
    products = db.search_products(query, limit=5)

    if not products:
        await update.message.reply_text(
            f"❌ រកមិនឃើញទំនិញ '{query}' ទេ!\n"
            "សូមពិនិត្យឡើងវិញ ឬចុច '❌ បោះបង់'៖",
            reply_markup=kb.get_cancel_keyboard()
        )
        return OUT_SELECT_PRODUCT

    product = products[0]

    if product['quantity'] <= 0:
        await update.message.reply_text(
            f"🚫 ទំនិញ **{product['name']}** អស់ពីស្តុកហើយ (សល់ 0 {product['unit']})! មិនអាចកាត់ស្តុកបានទេ។",
            reply_markup=kb.get_main_menu_keyboard(db.is_admin(update.effective_user.id)),
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    context.user_data['stock_out_product_id'] = product['id']
    context.user_data['stock_out_product_name'] = product['name']
    context.user_data['stock_out_product_unit'] = product['unit']
    context.user_data['stock_out_curr_qty'] = product['quantity']
    context.user_data['stock_out_default_sell_price'] = product['sell_price']

    await update.message.reply_text(
        f"✅ បានជ្រើសរើស៖ **{product['name']}**\n"
        f"📊 ចំនួននៅសល់ក្នុងស្តុក៖ **{product['quantity']} {product['unit']}**\n\n"
        f"👉 សូមបញ្ចូល **ចំនួនដែលត្រូវដកចេញ/លក់** ៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return OUT_QUANTITY


async def stock_out_quantity_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ទទួលចំនួនកាត់ស្តុក និងផ្ទៀងផ្ទាត់ថាមិនលើសស្តុកដែលមាន"""
    text = update.message.text.strip()
    curr_qty = context.user_data.get('stock_out_curr_qty', 0)
    unit = context.user_data.get('stock_out_product_unit', 'ឯកតា')

    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text(
            "⚠️ សូមបញ្ចូលជាចំនួនលេខវិជ្ជមាន (ធំជាង ០)៖",
            reply_markup=kb.get_cancel_keyboard()
        )
        return OUT_QUANTITY

    qty = int(text)
    if qty > curr_qty:
        await update.message.reply_text(
            f"🚫 **ស្តុកមិនគ្រប់គ្រាន់ទេ!**\n"
            f"អ្នកចង់ដក៖ {qty} {unit}\n"
            f"ស្តុកជាក់ស្តែងនៅសល់តែ៖ **{curr_qty} {unit}** ប៉ុណ្ណោះ!\n\n"
            f"សូមបញ្ចូលចំនួនម្តងទៀតឱ្យតិចជាង ឬស្មើ {curr_qty}៖",
            reply_markup=kb.get_cancel_keyboard(),
            parse_mode="Markdown"
        )
        return OUT_QUANTITY

    context.user_data['stock_out_qty'] = qty
    default_price = context.user_data.get('stock_out_default_sell_price', 0.0)

    await update.message.reply_text(
        f"💵 តម្លៃលក់ក្នុងមួយ {unit}៖\n"
        f"(តម្លៃកំណត់ទុក៖ ${default_price:.2f})\n\n"
        f"👉 វាយតម្លៃជាក់ស្តែង (ឧ. `3.00`) ឬវាយ `-` ដើម្បីប្រើតម្លៃដើម (${default_price:.2f})៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return OUT_PRICE


async def stock_out_price_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ទទួលតម្លៃលក់"""
    text = update.message.text.strip()
    default_price = context.user_data.get('stock_out_default_sell_price', 0.0)

    if text == "-":
        price = default_price
    else:
        try:
            price = float(text)
            if price < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text(
                "⚠️ តម្លៃមិនត្រឹមត្រូវ! សូមបញ្ចូលជាលេខ (ឧ. 2.5) ឬវាយ '-' ៖",
                reply_markup=kb.get_cancel_keyboard()
            )
            return OUT_PRICE

    context.user_data['stock_out_price'] = price

    await update.message.reply_text(
        "📝 សូមបញ្ចូល **មូលហេតុ / អតិថិជន / លេខវិក្កយបត្រ** ៖\n"
        "(ឧទាហរណ៍៖ `លក់ជូនអតិថិជន A - វិក្កយបត្រ #205` ឬ `ខូចខាត` ឬវាយ `-` បើគ្មាន) ៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return OUT_REFERENCE


async def stock_out_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """កាត់ស្តុកជាក់ស្តែង និងផ្ញើសារជូនដំណឹង"""
    ref = update.message.text.strip()
    if ref == "-":
        ref = "លក់ចេញទូទៅ"

    user_id = update.effective_user.id
    is_admin = db.is_admin(user_id)
    product_id = context.user_data['stock_out_product_id']
    qty = context.user_data['stock_out_qty']
    price = context.user_data['stock_out_price']

    success, message, updated_prod = db.record_stock_out(
        product_id=product_id,
        quantity=qty,
        unit_price=price,
        reference=ref,
        user_id=user_id
    )

    if success and updated_prod:
        import google_sheets_sync
        import notifier
        total = qty * price
        performer = update.effective_user.full_name or "Telegram User"
        google_sheets_sync.sync_transaction(
            tx_type="OUT",
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
        notifier.alert_stock_out(
            product=updated_prod,
            quantity=qty,
            unit_price=price,
            total_price=total,
            remaining_stock=updated_prod.get("quantity", 0),
            performed_by=performer,
            reference=ref
        )
        result_text = (
            f"✅ **កាត់ស្តុកជោគជ័យ!**\n\n"
            f"📦 ទំនិញ៖ **{updated_prod['name']}**\n"
            f"📤 ចំនួនដកចេញ៖ -{qty} {updated_prod['unit']}\n"
            f"📊 ស្តុកនៅសល់ជាក់ស្តែង៖ **{updated_prod['quantity']} {updated_prod['unit']}**\n"
            + ("⏰ ដកចេញពីឡូតិ៍ (ផុតកំណត់មុន ចេញមុន)៖ " + ", ".join(
                f"{('`' + d['batch_no'] + '` ') if d.get('batch_no') else ''}`{d['expiry_date']}` ×{d['quantity']}" for d in updated_prod.get('batches_deducted', [])
            ) + "\n" if updated_prod.get('batches_deducted') else "")
            + f"💵 តម្លៃលក់៖ ${price:.2f}\n"
            f"💰 ចំណូលសរុប៖ ${total:.2f}\n"
            f"🔖 មូលហេតុ/វិក្កយបត្រ៖ {ref}\n"
            f"👤 អ្នកកាត់ស្តុក៖ {update.effective_user.full_name}"
        )

        # ពិនិត្យ Low Stock Alert ស្វ័យប្រវត្តិ
        if updated_prod['quantity'] <= updated_prod['min_quantity']:
            result_text += (
                f"\n\n🚨 **ការជូនដំណឹងបន្ទាន់ (Low Stock Alert)!**\n"
                f"ទំនិញ **{updated_prod['name']}** នៅសល់តែ **{updated_prod['quantity']} {updated_prod['unit']}** ប៉ុណ្ណោះ!\n"
                f"កម្រិតសុវត្ថិភាពកំណត់៖ {updated_prod['min_quantity']} {updated_prod['unit']}។ សូមរៀបចំទិញបន្ថែម!"
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


# Helper សម្រាប់ Callback ពេលចុចប៊ូតុង [📤 នាំចេញ] លើ Card ទំនិញ
async def stock_out_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split(":")[1])
    product = db.get_product_by_id(product_id)
    if not product:
        await query.edit_message_text("❌ រកមិនឃើញទំនិញនេះទៀតទេ!")
        return ConversationHandler.END

    if product['quantity'] <= 0:
        await query.message.reply_text(
            f"🚫 ទំនិញ **{product['name']}** អស់ពីស្តុកហើយ (សល់ 0 {product['unit']})!",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    context.user_data['stock_out_product_id'] = product['id']
    context.user_data['stock_out_product_name'] = product['name']
    context.user_data['stock_out_product_unit'] = product['unit']
    context.user_data['stock_out_curr_qty'] = product['quantity']
    context.user_data['stock_out_default_sell_price'] = product['sell_price']

    await query.message.reply_text(
        f"📤 **កាត់ស្តុកទំនិញ៖ {product['name']}**\n"
        f"📊 ស្តុកនៅសល់៖ **{product['quantity']} {product['unit']}**\n\n"
        f"👉 សូមបញ្ចូល **ចំនួនដែលត្រូវដកចេញ/លក់** ៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return OUT_QUANTITY

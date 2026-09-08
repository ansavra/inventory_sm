from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import database as db
import keyboards as kb
from handlers.inventory import format_product_card

EDIT_SELECT_ACTION, EDIT_VALUE = range(2)


def get_edit_options_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Menu ជម្រើសកែប្រែ"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 កែតម្រូវចំនួនស្តុក (Quantity)", callback_data=f"ed_qty:{product_id}")
        ],
        [
            InlineKeyboardButton("🏷️ កែឈ្មោះទំនិញ (Name)", callback_data=f"ed_name:{product_id}"),
            InlineKeyboardButton("💵 កែតម្លៃលក់ (Price)", callback_data=f"ed_price:{product_id}")
        ],
        [
            InlineKeyboardButton("⚠️ កែកម្រិតប្រកាសអាសន្ន (Min Qty)", callback_data=f"ed_min:{product_id}"),
            InlineKeyboardButton("📍 កែទីតាំង (Location)", callback_data=f"ed_loc:{product_id}")
        ],
        [
            InlineKeyboardButton("🔙 ត្រឡប់ក្រោយ", callback_data=f"act_refresh:{product_id}")
        ]
    ])


async def edit_product_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """បង្ហាញ Menu ជម្រើសកែប្រែ"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split(":")[1])
    product = db.get_product_by_id(product_id)
    if not product:
        await query.edit_message_text("❌ រកមិនឃើញទំនិញនេះទេ!")
        return ConversationHandler.END

    text = (
        f"✏️ **កែប្រែព័ត៌មានទំនិញ៖ {product['name']}**\n\n"
        f"🔹 ចំនួនក្នុងស្តុកបច្ចុប្បន្ន៖ **{product['quantity']} {product['unit']}**\n"
        f"🔹 តម្លៃលក់៖ **${product['sell_price']:.2f}**\n"
        f"🔹 កម្រិតជូនដំណឹង៖ {product['min_quantity']} {product['unit']}\n"
        f"🔹 ទីតាំង៖ {product['location']}\n\n"
        f"👉 សូមជ្រើសរើសផ្នែកដែលបងចង់កែសម្រួល៖"
    )

    await query.edit_message_text(
        text,
        reply_markup=get_edit_options_keyboard(product_id),
        parse_mode="Markdown"
    )
    return EDIT_SELECT_ACTION


async def edit_field_chosen_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ពេលចុចជ្រើសរើស Field ដែលត្រូវកែ"""
    query = update.callback_query
    await query.answer()
    data = query.data  # e.g., "ed_qty:12"
    action, pid_str = data.split(":")
    product_id = int(pid_str)

    product = db.get_product_by_id(product_id)
    if not product:
        await query.edit_message_text("❌ រកមិនឃើញទំនិញនេះទេ!")
        return ConversationHandler.END

    context.user_data['edit_product_id'] = product_id
    context.user_data['edit_field'] = action

    prompts = {
        "ed_qty": f"📊 សូមបញ្ចូល **ចំនួនស្តុកជាក់ស្តែងថ្មី** សម្រាប់ '{product['name']}' (ចំនួនបច្ចុប្បន្ន: {product['quantity']}) ៖",
        "ed_name": f"🏷️ សូមបញ្ចូល **ឈ្មោះទំនិញថ្មី** (ឈ្មោះចាស់: {product['name']}) ៖",
        "ed_price": f"💵 សូមបញ្ចូល **តម្លៃលក់ថ្មី ($)** (តម្លៃចាស់: ${product['sell_price']:.2f}) ៖",
        "ed_min": f"⚠️ សូមបញ្ចូល **កម្រិតជូនដំណឹងថ្មី** (ចាស់: {product['min_quantity']}) ៖",
        "ed_loc": f"📍 សូមបញ្ចូល **ទីតាំងទុកដាក់ថ្មី** (ចាស់: {product['location']}) ៖",
    }

    prompt_text = prompts.get(action, "សូមបញ្ចូលព័ត៌មានថ្មី៖")

    await query.message.reply_text(
        prompt_text,
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return EDIT_VALUE


async def edit_value_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ទទួលតម្លៃថ្មី និងរក្សាទុកចូល Database"""
    text = update.message.text.strip()
    field = context.user_data.get('edit_field')
    product_id = context.user_data.get('edit_product_id')
    user_id = update.effective_user.id
    is_admin = db.is_admin(user_id)

    if not product_id:
        return ConversationHandler.END

    if field == "ed_qty":
        if not text.isdigit() or int(text) < 0:
            await update.message.reply_text("⚠️ សូមបញ្ចូលជាចំនួនលេខវិជ្ជមាន (0 ឬធំជាង)៖")
            return EDIT_VALUE
        new_qty = int(text)
        success, msg, prod = db.adjust_product_quantity(
            product_id=product_id,
            new_quantity=new_qty,
            reason="កែសម្រួលដោយ Admin/Staff តាម Telegram",
            user_id=user_id
        )

    elif field == "ed_name":
        success, msg = db.update_product(product_id, name=text)

    elif field == "ed_price":
        try:
            val = float(text)
            if val < 0:
                raise ValueError
            success, msg = db.update_product(product_id, sell_price=val)
        except ValueError:
            await update.message.reply_text("⚠️ តម្លៃមិនត្រឹមត្រូវ! សូមបញ្ចូលជាលេខ ឧ. 1.50 ៖")
            return EDIT_VALUE

    elif field == "ed_min":
        if not text.isdigit() or int(text) < 0:
            await update.message.reply_text("⚠️ សូមបញ្ចូលជាចំនួនលេខវិជ្ជមាន៖")
            return EDIT_VALUE
        success, msg = db.update_product(product_id, min_quantity=int(text))

    elif field == "ed_loc":
        success, msg = db.update_product(product_id, location=text)
    else:
        success, msg = False, "Unknown action"

    if success:
        updated_prod = db.get_product_by_id(product_id)
        card = format_product_card(updated_prod, is_admin)
        await update.message.reply_text(
            f"✅ **កែប្រែទិន្នន័យបានជោគជ័យ!**\n\n{card}",
            reply_markup=kb.get_product_action_keyboard(product_id, is_admin),
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


# ==========================================
# ការលុបទំនិញ (Delete Product Handlers)
# ==========================================

async def delete_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """សួរការបញ្ជាក់មុនពេលលុប"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split(":")[1])
    product = db.get_product_by_id(product_id)
    if not product:
        await query.edit_message_text("❌ រកមិនឃើញទំនិញនេះទេ!")
        return

    text = (
        f"⚠️ **ការបញ្ជាក់ការលុបទំនិញ**\n\n"
        f"តើបងពិតជាចង់លុបទំនិញ **'{product['name']}'** (កូដ: `{product['code']}`) មែនទេ?\n"
        f"*(រាល់ប្រវត្តិប្រតិបត្តិការរបស់ទំនិញនេះនឹងត្រូវបានលុបចេញពីប្រព័ន្ធ)*"
    )
    await query.edit_message_text(
        text,
        reply_markup=kb.get_delete_confirmation_keyboard(product_id),
        parse_mode="Markdown"
    )


async def delete_execute_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """អនុវត្តការលុបទំនិញជាក់ស្តែង"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        await query.message.reply_text("⛔ មានតែ Admin ទើបមានសិទ្ធិលុបទំនិញបាន!")
        return

    product_id = int(query.data.split(":")[1])
    success, msg = db.delete_product(product_id)

    if success:
        await query.edit_message_text(f"🗑️ {msg}")
    else:
        await query.edit_message_text(f"❌ {msg}")

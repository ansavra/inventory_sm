from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import database as db
import keyboards as kb

SEARCH_WAITING = 1


def format_product_card(p: dict, is_admin: bool = False) -> str:
    """រៀបចំទម្រង់ព័ត៌មានទំនិញឱ្យស្អាត"""
    is_low = p['quantity'] <= p['min_quantity']
    status_icon = "⚠️ **ជិតអស់ពីស្តុក!**" if is_low else "✅ **គ្រប់គ្រាន់**"

    lines = [
        f"📦 **{p['name']}**",
        f"🔹 លេខកូដ (SKU/Barcode)៖ `{p['code']}`",
        f"🔹 ប្រភេទ៖ {p['category']}",
        f"🔹 ចំនួនក្នុងស្តុក៖ **{p['quantity']} {p['unit']}**",
        f"🔹 កម្រិតកំណត់ទាបបំផុត៖ {p['min_quantity']} {p['unit']}",
        f"🔹 ទីតាំងទុកដាក់៖ {p['location']}",
        f"🔹 តម្លៃលក់៖ **${p['sell_price']:.2f}**",
        f"🔹 ស្ថានភាពស្តុក៖ {status_icon}"
    ]

    # បង្ហាញតម្លៃដើមសម្រាប់តែ Admin ប៉ុណ្ណោះ (ការពារការសម្ងាត់ហិរញ្ញវត្ថុ)
    if is_admin:
        lines.append(f"🔒 តម្លៃដើម (Admin only)៖ ${p['cost_price']:.2f}")

    return "\n".join(lines)


async def check_inventory_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ពិនិត្យស្តុកទំនិញទាំងអស់ និងបង្ហាញប៊ូតុងចុចមើលលម្អិត"""
    user_id = update.effective_user.id
    is_admin = db.is_admin(user_id)
    products = db.list_all_products(limit=30)

    if not products:
        await update.message.reply_text(
            "📭 **បច្ចុប្បន្នមិនទាន់មានទំនិញក្នុងស្តុកនៅឡើយទេ!**\n\n"
            "👉 សូមចុចប៊ូតុង **'➕ បន្ថែមទំនិញថ្មី'** នៅលើ Keyboard ខាងក្រោមដើម្បីចាប់ផ្តើមបញ្ចូលទំនិញដំបូង។",
            parse_mode="Markdown"
        )
        return

    text = f"📋 **បញ្ជីទំនិញក្នុងស្តុក (សរុប៖ {len(products)} មុខ)**\n\n"
    keyboard = []
    for i, p in enumerate(products, start=1):
        low_flag = " ⚠️" if p['quantity'] <= p['min_quantity'] else ""
        text += f"{i}. `{p['code']}` - **{p['name']}** ៖ {p['quantity']} {p['unit']}{low_flag}\n"
        keyboard.append([
            kb.InlineKeyboardButton(f"🔍 មើល/កែប្រែ៖ {p['name']}", callback_data=f"act_view:{p['id']}")
        ])

    text += "\n👇 *ចុចលើប៊ូតុងទំនិញខាងក្រោមដើម្បី នាំចូល, នាំចេញ, កែប្រែ ឬលុប៖*"
    reply_markup = kb.InlineKeyboardMarkup(keyboard) if keyboard else None
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def edit_delete_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu កែប្រែ ឬលុបទំនិញ"""
    products = db.list_all_products(limit=30)

    if not products:
        await update.message.reply_text(
            "📭 **មិនទាន់មានទំនិញក្នុងប្រព័ន្ធនៅឡើយទេ!**\n\n"
            "👉 សូមចុចប៊ូតុង **'➕ បន្ថែមទំនិញថ្មី'** ដើម្បីបញ្ចូលទំនិញជាមុនសិន។\n"
            "នៅពេលបងបញ្ចូលទំនិញរួច មុខងារ **[✏️ កែប្រែ]** និង **[🗑️ លុប]** នឹងបង្ហាញឡើងសម្រាប់ទំនិញនោះភ្លាមៗ!",
            parse_mode="Markdown"
        )
        return

    keyboard = []
    for p in products:
        keyboard.append([
            kb.InlineKeyboardButton(f"✏️ កែប្រែ/លុប៖ {p['name']}", callback_data=f"act_view:{p['id']}")
        ])

    await update.message.reply_text(
        "✏️ **ជ្រើសរើសទំនិញដែលបងចង់កែប្រែ ឬលុប៖**",
        reply_markup=kb.InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def product_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback ពេលចុចមើលទំនិញមួយ ដើម្បីបង្ហាញប៊ូតុង នាំចូល, នាំចេញ, កែប្រែ, លុប"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split(":")[1])
    product = db.get_product_by_id(product_id)
    if not product:
        await query.message.reply_text("❌ រកមិនឃើញទំនិញនេះទៀតទេ!")
        return

    is_admin = db.is_admin(update.effective_user.id)
    card = format_product_card(product, is_admin)
    await query.message.reply_text(
        card,
        reply_markup=kb.get_product_action_keyboard(product_id, is_admin),
        parse_mode="Markdown"
    )



async def low_stock_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """បង្ហាញបញ្ជីទំនិញជិតអស់ពីស្តុក (Low stock alert)"""
    low_products = db.get_low_stock_products()

    if not low_products:
        await update.message.reply_text(
            "🎉 **អស្ចារ្យណាស់!** គ្មានទំនិញណាមួយជិតអស់ពីស្តុកឡើយ (ស្តុកទាំងអស់ស្ថិតក្នុងកម្រិតសុវត្ថិភាព)។",
            parse_mode="Markdown"
        )
        return

    msg = f"⚠️ **ការជូនដំណឹង៖ ទំនិញជិតអស់ពីស្តុក ({len(low_products)} មុខ)**\n\n"
    for i, p in enumerate(low_products, start=1):
        msg += (
            f"{i}. `{p['code']}` - **{p['name']}**\n"
            f"   👉 នៅសល់៖ **{p['quantity']} {p['unit']}** (កម្រិតកំណត់៖ {p['min_quantity']})\n"
        )
    msg += "\n🔔 *សូមរៀបចំទិញនាំចូលបន្ថែម (Reorder) ឱ្យបានទាន់ពេលវេលា!*"
    await update.message.reply_text(msg, parse_mode="Markdown")


# ==========================================
# ការស្វែងរកទំនិញ (Search Product Flow)
# ==========================================

async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ចាប់ផ្តើមស្វែងរកទំនិញ"""
    await update.message.reply_text(
        "🔍 **ស្វែងរកទំនិញក្នុងស្តុក**\n\n"
        "សូមវាយ **ឈ្មោះទំនិញ** ឬ **លេខកូដ (Barcode/SKU)** ដែលអ្នកចង់ស្វែងរក៖",
        reply_markup=kb.get_cancel_keyboard(),
        parse_mode="Markdown"
    )
    return SEARCH_WAITING


async def search_perform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """អនុវត្តការស្វែងរក"""
    query = update.message.text.strip()
    user_id = update.effective_user.id
    is_admin = db.is_admin(user_id)

    results = db.search_products(query, limit=10)

    if not results:
        await update.message.reply_text(
            f"❌ រកមិនឃើញទំនិញដែលត្រូវនឹងពាក្យ '{query}' ទេ!\n"
            "សូមសាកល្បងស្វែងរកម្តងទៀត ឬចុច '❌ បោះបង់'៖",
            reply_markup=kb.get_cancel_keyboard()
        )
        return SEARCH_WAITING

    # បើឃើញចំ ១គត់ បង្ហាញព័ត៌មានលម្អិត និងប៊ូតុងសកម្មភាពភ្លាមៗ
    if len(results) == 1:
        p = results[0]
        card = format_product_card(p, is_admin)
        await update.message.reply_text(
            card,
            reply_markup=kb.get_product_action_keyboard(p['id'], is_admin),
            parse_mode="Markdown"
        )
        await update.message.reply_text(
            "✅ ស្វែងរកបានជោគជ័យ!",
            reply_markup=kb.get_main_menu_keyboard(is_admin)
        )
        return ConversationHandler.END

    # បើឃើញច្រើន បង្ហាញបញ្ជី
    text = f"🔎 **លទ្ធផលស្វែងរកសម្រាប់ '{query}' (សរុប {len(results)})៖**\n\n"
    for i, p in enumerate(results, start=1):
        text += f"{i}. `{p['code']}` - **{p['name']}** ({p['quantity']} {p['unit']})\n"
    text += "\n💡 *អ្នកអាចវាយលេខកូដជាក់លាក់ដើម្បីមើលព័ត៌មានលម្អិត និងប៊ូតុងសកម្មភាព។*"

    await update.message.reply_text(
        text,
        reply_markup=kb.get_main_menu_keyboard(is_admin),
        parse_mode="Markdown"
    )
    return ConversationHandler.END

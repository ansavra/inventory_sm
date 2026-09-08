from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import config
import database as db
import keyboards as kb


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """បញ្ជា /start ស្វាគមន៍ និងចុះឈ្មោះអ្នកប្រើប្រាស់"""
    user = update.effective_user
    if not user:
        return

    # ចុះឈ្មោះ ឬ Update ព័ត៌មានអ្នកប្រើប្រាស់ក្នុង DB
    user_data = db.register_or_update_user(
        user_id=user.id,
        username=user.username or "",
        full_name=user.full_name or user.first_name or "User"
    )

    is_admin = (user_data.get('role') == 'admin')
    role_khmer = "👑 អ្នកគ្រប់គ្រង (Admin)" if is_admin else "👷 បុគ្គលិក (Staff)"

    welcome_text = (
        f"👋 សួស្តី **{user.full_name}**!\n\n"
        f"សូមស្វាគមន៍មកកាន់ **ប្រព័ន្ធគ្រប់គ្រងស្តុកទំនិញ (Inventory Management Bot)**\n"
        f"🏷️ តួនាទីរបស់អ្នក៖ {role_khmer}\n"
        f"🆔 Telegram ID: `{user.id}`\n\n"
        f"សូមជ្រើសរើសមុខងារពី Menu ខាងក្រោមដើម្បីចាប់ផ្តើម៖"
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=kb.get_main_menu_keyboard(is_admin),
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """បញ្ជា /help ឬប៊ូតុង ព័ត៌មាន/ជំនួយ"""
    help_text = (
        "📖 **សៀវភៅណែនាំអំពីការប្រើប្រាស់ប្រព័ន្ធ**\n\n"
        "1. **📦 ពិនិត្យស្តុក** ៖ មើលបញ្ជីទំនិញទាំងអស់ក្នុងឃ្លាំង និងចំនួននៅសល់។\n"
        "2. **📥 នាំចូលទំនិញ** ៖ កត់ត្រាទំនិញទិញចូលស្តុកថ្មី រួមជាមួយតម្លៃ និងអ្នកផ្គត់ផ្គង់។\n"
        "3. **📤 នាំចេញ/លក់** ៖ កាត់ស្តុកពេលលក់ចេញ ផ្ទេរ ឬខូចខាត (ការពារមិនឱ្យស្តុកធ្លាក់អវិជ្ជមាន)។\n"
        "4. **➕ បន្ថែមទំនិញថ្មី** ៖ បង្កើតទំនិញថ្មីដោយបញ្ចូលកូដ (SKU/Barcode) ឈ្មោះ តម្លៃ និងកម្រិតប្រកាសអាសន្ន។\n"
        "5. **⚠️ ទំនិញជិតអស់** ៖ ពិនិត្យបញ្ជីទំនិញដែលនៅសល់តិចជាងកម្រិតកំណត់ (Reorder Level)។\n"
        "6. **📊 របាយការណ៍** ៖ មើលសង្ខេបប្រតិបត្តិការប្រចាំថ្ងៃ និងប្រវត្តិការចេញចូល។\n"
        "7. **📷 ស្កេន Barcode/QR** ៖ គ្រាន់តែថតរូប Barcode ឬ QR code លើទំនិញរួចផ្ញើចូល Bot វានឹងស្វែងរកទំនិញជូនភ្លាមៗ!\n\n"
        "💡 *ចំណាំ* ៖ រាល់ពេលស្ថិតក្នុងទម្រង់បំពេញព័ត៌មាន អ្នកអាចចុច **'❌ បោះបង់'** ដើម្បីត្រឡប់មកកាន់ Menu ដើមវិញ។"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """លុបចោលប្រតិបត្តិការដែលកំពុងដំណើរការ ហើយត្រឡប់ទៅ Menu ដើម"""
    context.user_data.clear()
    user_id = update.effective_user.id
    is_admin = db.is_admin(user_id)
    await update.message.reply_text(
        "❌ ប្រតិបត្តិការត្រូវបានបោះបង់!",
        reply_markup=kb.get_main_menu_keyboard(is_admin)
    )
    return ConversationHandler.END


async def web_dashboard_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ផ្តល់ Link ចូលទៅកាន់ Web Dashboard លើ Internet"""
    internet_url = config.get_dashboard_url()

    text = (
        "🌐 **ផ្ទាំង Web Dashboard គ្រប់គ្រងស្តុកលើ Internet**\n\n"
        "ឥឡូវនេះ បងអាចបើកមើលពីទីណាក៏បានតាមទូរសព្ទដៃ (4G/5G/Wi-Fi) ឬកុំព្យូទ័រ៖\n\n"
        f"🌍 **តំណភ្ជាប់ Internet (Global Online) ៖**\n"
        f"👉 [ចុចត្រង់នេះដើម្បីបើកមើល]({internet_url})\n"
        f"`{internet_url}`\n\n"
        "💻 **លើកុំព្យូទ័រផ្ទាល់ ៖** [http://localhost:8000](http://localhost:8000)\n\n"
        "*(ទិន្នន័យទាំងអស់ភ្ជាប់ជាមួយ Telegram Bot នេះដោយស្វ័យប្រវត្តិ!)*"
    )

    inline_kb = kb.InlineKeyboardMarkup([
        [kb.InlineKeyboardButton("🌐 បើក Web Dashboard ឥឡូវនេះ", url=internet_url)]
    ])

    await update.message.reply_text(text, reply_markup=inline_kb, parse_mode="Markdown")



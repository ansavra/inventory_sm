from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard(is_admin_user: bool = False) -> ReplyKeyboardMarkup:
    """Menu មេផ្ញើតាមរយៈ Keyboard Buttons លើអេក្រង់"""
    buttons = [
        ["📦 ពិនិត្យស្តុក", "⚠️ ទំនិញជិតអស់"],
        ["📥 នាំចូលទំនិញ", "📤 នាំចេញ/លក់"],
        ["➕ បន្ថែមទំនិញថ្មី", "✏️ កែប្រែ / លុបទំនិញ"],
        ["📊 របាយការណ៍", "🔍 ស្វែងរកទំនិញ"],
        ["🌐 ចូលមើលលើ Web", "ℹ️ ជំនួយ / ព័ត៌មាន"]
    ]
    if is_admin_user:
        buttons.append(["⚙️ គ្រប់គ្រងអ្នកប្រើប្រាស់"])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """ប៊ូតុងបោះបង់ ឬត្រឡប់ក្រោយ"""
    return ReplyKeyboardMarkup([["❌ បោះបង់"]], resize_keyboard=True, one_time_keyboard=True)


def get_product_action_keyboard(product_id: int, is_admin: bool = False) -> InlineKeyboardMarkup:
    """ប៊ូតុងសកម្មភាពរហ័សលើទំនិញមួយ (Inline Buttons)"""
    keyboard = [
        [
            InlineKeyboardButton("📥 នាំចូល", callback_data=f"act_in:{product_id}"),
            InlineKeyboardButton("📤 នាំចេញ", callback_data=f"act_out:{product_id}")
        ],
        [
            InlineKeyboardButton("✏️ កែប្រែស្តុក/ព័ត៌មាន", callback_data=f"act_edit:{product_id}"),
            InlineKeyboardButton("🔄 ផ្ទុកឡើងវិញ", callback_data=f"act_refresh:{product_id}")
        ]
    ]
    if is_admin:
        keyboard.append([
            InlineKeyboardButton("🗑️ លុបទំនិញនេះ", callback_data=f"act_del_confirm:{product_id}")
        ])
    return InlineKeyboardMarkup(keyboard)


def get_delete_confirmation_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """ប៊ូតុងបញ្ជាក់ការលុបទំនិញ"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚠️ បាទ/ចាស ប្រាកដជាលុប", callback_data=f"act_del_yes:{product_id}"),
            InlineKeyboardButton("❌ ទេ កុំលុប", callback_data=f"act_refresh:{product_id}")
        ]
    ])



def get_report_options_keyboard() -> InlineKeyboardMarkup:
    """ប៊ូតុងជម្រើសរបាយការណ៍"""
    keyboard = [
        [
            InlineKeyboardButton("📅 របាយការណ៍ថ្ងៃនេះ", callback_data="rep_today"),
            InlineKeyboardButton("📜 ប្រវត្តិប្រតិបត្តិការ", callback_data="rep_history")
        ],
        [
            InlineKeyboardButton("⚠️ បញ្ជីទំនិញជិតអស់", callback_data="rep_low")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

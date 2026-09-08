from telegram import Update
from telegram.ext import ContextTypes
import database as db


async def admin_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """គ្រប់គ្រងអ្នកប្រើប្រាស់ និងបុគ្គលិក (Admin Only)"""
    user_id = update.effective_user.id
    if not db.is_admin(user_id):
        await update.message.reply_text("⛔ អ្នកគ្មានសិទ្ធិចូលមើលទំព័រនេះទេ (Admin Only)!")
        return

    users = db.list_users()
    if not users:
        await update.message.reply_text("📭 មិនទាន់មានអ្នកប្រើប្រាស់ផ្សេងទៀតទេ។")
        return

    text = f"👥 **បញ្ជីអ្នកប្រើប្រាស់ក្នុងប្រព័ន្ធ (សរុប {len(users)} នាក់)៖**\n\n"
    for i, u in enumerate(users, start=1):
        role_label = "👑 Admin" if u['role'] == 'admin' else "👷 Staff"
        username_str = f"@{u['username']}" if u['username'] else "គ្មាន Username"
        text += (
            f"{i}. **{u['full_name']}** ({username_str})\n"
            f"   🆔 ID: `{u['user_id']}` | តួនាទី៖ {role_label}\n"
        )

    text += (
        "\n💡 *ចំណាំ* ៖ ដើម្បីកំណត់សិទ្ធិ Admin បន្ថែម អ្នកអាចបញ្ចូល Telegram User ID "
        "ចូលទៅក្នុងអថេរ `ADMIN_USER_IDS` ក្នុងឯកសារ `.env`។"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

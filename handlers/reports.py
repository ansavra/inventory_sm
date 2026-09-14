from telegram import Update
from telegram.ext import ContextTypes
import database as db
import keyboards as kb


async def reports_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """បង្ហាញ Menu ជម្រើសរបាយការណ៍"""
    text = (
        "📊 **ប្រព័ន្ធរបាយការណ៍ស្តុកទំនិញ (Inventory Reports)**\n\n"
        "សូមជ្រើសរើសប្រភេទរបាយការណ៍ដែលអ្នកចង់ពិនិត្យមើល៖"
    )
    await update.message.reply_text(
        text,
        reply_markup=kb.get_report_options_keyboard(),
        parse_mode="Markdown"
    )


async def reports_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """គ្រប់គ្រងការចុចប៊ូតុងលើ Menu របាយការណ៍"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    is_admin = db.is_admin(user_id)

    if data == "rep_today":
        summary = db.get_daily_summary()
        si = summary['stock_in']
        so = summary['stock_out']

        text = (
            f"📅 **របាយការណ៍សង្ខេបប្រចាំថ្ងៃ ({summary['date']})**\n\n"
            f"📥 **នាំចូលទំនិញ (Stock In)៖**\n"
            f"  • ប្រតិបត្តិការ៖ {si['transactions']} លើក\n"
            f"  • បរិមាណសរុប៖ {si['quantity']} ឯកតា\n"
        )
        if is_admin:
            text += f"  • ចំណាយសរុប៖ ${si['amount']:.2f}\n"

        text += (
            f"\n📤 **នាំចេញ / លក់ចេញ (Stock Out)៖**\n"
            f"  • ប្រតិបត្តិការ៖ {so['transactions']} លើក\n"
            f"  • បរិមាណសរុប៖ {so['quantity']} ឯកតា\n"
        )
        if is_admin:
            text += f"  • ចំណូលសរុប៖ ${so['amount']:.2f}\n"

        text += (
            f"\n🏷️ មុខទំនិញសរុបក្នុងប្រព័ន្ធ៖ {summary['total_products']} មុខ\n"
            f"⚠️ ទំនិញជិតអស់ពីស្តុក៖ {summary['low_stock_count']} មុខ\n"
        )

        await query.message.reply_text(text, parse_mode="Markdown")

    elif data == "rep_history":
        txs = db.get_recent_transactions(limit=10)
        if not txs:
            await query.message.reply_text("📭 មិនទាន់មានប្រវត្តិប្រតិបត្តិការនៅឡើយទេ។")
            return

        text = "📜 **ប្រវត្តិប្រតិបត្តិការចុងក្រោយ (១០ លើក)**\n\n"
        for t in txs:
            icon = "📥 នាំចូល" if t['type'] == 'IN' else "📤 នាំចេញ"
            sign = "+" if t['type'] == 'IN' else "-"
            # Format date substring
            dt = t['created_at'][:16] if t.get('created_at') else ""
            user_name = t.get('user_name') or f"ID:{t['performed_by']}"

            text += (
                f"{icon} **{t['product_name']}** ({sign}{t['quantity']} {t['product_unit']})\n"
                f"   ⏰ {dt} | ដោយ៖ {user_name}\n"
                f"   🔖 {t['reference'] or '-'}\n\n"
            )
        await query.message.reply_text(text, parse_mode="Markdown")

    elif data == "rep_low":
        lows = db.get_low_stock_products()
        if not lows:
            await query.message.reply_text("🎉 គ្មានទំនិញណាមួយជិតអស់ពីស្តុកឡើយ!")
            return

        text = f"⚠️ **បញ្ជីទំនិញជិតអស់ ({len(lows)} មុខ)**\n\n"
        for i, p in enumerate(lows, start=1):
            text += f"{i}. `{p['code']}` - **{p['name']}** ៖ សល់ **{p['quantity']}** (កំណត់៖ {p['min_quantity']})\n"
        await query.message.reply_text(text, parse_mode="Markdown")

    elif data == "rep_expiry":
        days = 30
        summary = db.get_expiry_summary(days=days)
        batches = db.list_expiry_batches(days=days, status='alert', limit=30)
        if not batches:
            await query.message.reply_text(f"🎉 គ្មានទំនិញណាផុតកំណត់ ឬជិតផុតកំណត់ក្នុង {days} ថ្ងៃខាងមុខឡើយ!")
            return

        text = (
            f"⏰ **ទំនិញផុតកំណត់ / ជិតផុតកំណត់ ({days} ថ្ងៃ)**\n"
            f"🔴 ផុតកំណត់ហើយ៖ {summary['expired']['batches']} ឡូតិ៍ ({summary['expired']['qty']} ឯកតា)\n"
            f"🟠 ជិតផុតកំណត់៖ {summary['expiring_soon']['batches']} ឡូតិ៍ ({summary['expiring_soon']['qty']} ឯកតា)\n\n"
        )
        for b in batches:
            if b['status'] == 'expired':
                tag = f"🔴 ផុត {abs(b['days_left'])} ថ្ងៃហើយ"
            else:
                tag = f"🟠 នៅ {b['days_left']} ថ្ងៃទៀត"
            text += (
                f"• **{b['product_name']}** (`{b['product_code']}`)\n"
                f"   {('🏷️ ' + b['batch_no'] + ' | ') if b.get('batch_no') else ''}⏰ {b['expiry_date']} — {tag} — សល់ **{b['quantity']} {b['product_unit']}**\n"
            )
        await query.message.reply_text(text, parse_mode="Markdown")

from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from features import FEATURES, CATEGORIES
from ui import main_menu, category_menu, permission_menu, feature_permission_menu

def register_callback_handlers(app):
    @app.on_callback_query()
    async def callbacks(_, q: CallbackQuery):
        uid = q.from_user.id
        role = await app.db.get_role(uid)
        chat_id = q.message.chat.id

        if q.data == "home":
            if role != "owner" and not await app.db.permission(chat_id, "dashboard", role):
                return
            await q.message.edit_text("🤖 <b>UBot</b>\n\nPilih menu:", reply_markup=main_menu())
            return

        if q.data == "perm:menu":
            if role != "owner":
                return
            await q.message.edit_text(
                "⚙️ <b>Permission Manager</b>\n\nSemua fitur default <b>Owner Only</b>.",
                reply_markup=permission_menu()
            )
            return

        if q.data.startswith("cat:"):
            if role != "owner" and not await app.db.permission(chat_id, "dashboard", role):
                return
            try:
                title = list(CATEGORIES)[int(q.data.split(":", 1)[1])]
            except Exception:
                return
            visible = [f for f in CATEGORIES[title]
                       if role == "owner" or await app.db.permission(chat_id, f, role)]
            if not visible:
                return
            await q.message.edit_text(
                f"<b>{title}</b>",
                reply_markup=category_menu(title, visible)
            )
            return

        if q.data.startswith("pfeat:"):
            if role != "owner":
                return
            feature = q.data.split(":", 1)[1]
            if feature not in FEATURES:
                return
            await q.message.edit_text(
                f"⚙️ <b>{FEATURES[feature][0]}</b>\n\nPilih akses:",
                reply_markup=feature_permission_menu(
                    feature,
                    await app.db.permission(chat_id, feature, "admin"),
                    await app.db.permission(chat_id, feature, "member")
                )
            )
            return

        if q.data.startswith("toggle:"):
            if role != "owner":
                return
            _, feature, target_role = q.data.split(":")
            if feature not in FEATURES or target_role not in ("admin", "member"):
                return
            current = await app.db.permission(chat_id, feature, target_role)
            await app.db.set_permission(chat_id, feature, target_role, not current)
            await q.answer("Permission diperbarui.")
            await q.message.edit_reply_markup(
                feature_permission_menu(
                    feature,
                    await app.db.permission(chat_id, feature, "admin"),
                    await app.db.permission(chat_id, feature, "member")
                )
            )
            return

        if q.data == "pay:settings":
            if role != "owner":
                return
            await q.message.edit_text(
                "💳 <b>Payment Settings</b>\n\n"
                "Gunakan <code>.setpay</code> untuk mengatur data pembayaran.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Kembali", callback_data="home")]
                ])
            )
            return

        if q.data.startswith("feat:"):
            feature = q.data.split(":", 1)[1]
            if feature not in FEATURES:
                return
            if role != "owner" and not await app.db.permission(chat_id, feature, role):
                return
            await q.answer("Fitur dapat digunakan.")

from pyrogram import filters


def register_message_handlers(app):
    @app.on_message(filters.text)
    async def messages(_, message):
        if not message.from_user:
            return
        # Ignore all command-like messages here; command handlers decide permission.
        if message.text.startswith("."):
            return

        # Auto-reply is silent unless explicitly allowed.
        role = await app.db.get_role(message.from_user.id)
        feature = "autoreply"
        if role == "owner":
            allowed = True
        else:
            allowed = await app.db.permission(message.chat.id, feature, role)

        if not allowed:
            return

        response = await app.db.find_autoreply(message.chat.id, message.text)
        if response:
            await message.reply_text(response)

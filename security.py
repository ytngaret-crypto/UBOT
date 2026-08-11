from features import COMMAND_FEATURES

async def is_allowed(app, message, feature):
    uid = message.from_user.id if message.from_user else 0
    role = await app.db.get_role(uid)

    if role == "owner":
        return True
    if role not in ("admin", "member"):
        return False

    scope = message.chat.id if message.chat else uid
    return await app.db.permission(scope, feature, role)

async def command_is_allowed(app, message, command):
    feature = COMMAND_FEATURES.get(command.lower())
    return bool(feature and await is_allowed(app, message, feature))

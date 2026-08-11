from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from features import FEATURES, CATEGORIES

def main_menu():
    rows = []
    for i, title in enumerate(CATEGORIES):
        rows.append([InlineKeyboardButton(title, callback_data=f"cat:{i}")])
    rows.append([
        InlineKeyboardButton("⚙️ Permission", callback_data="perm:menu"),
        InlineKeyboardButton("💳 Payment", callback_data="pay:settings"),
    ])
    return InlineKeyboardMarkup(rows)

def category_menu(title, visible_features=None):
    features = CATEGORIES.get(title, [])
    if visible_features is not None:
        features = [f for f in features if f in visible_features]
    rows = [[InlineKeyboardButton(FEATURES[f][0], callback_data=f"feat:{f}")] for f in features]
    rows.append([InlineKeyboardButton("⬅️ Kembali", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def permission_menu():
    rows = [[InlineKeyboardButton(label[:34], callback_data=f"pfeat:{f}")]
            for f, (label, _) in FEATURES.items()]
    rows.append([InlineKeyboardButton("⬅️ Kembali", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def feature_permission_menu(feature, admin_allowed, member_allowed):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"Admin {'✅' if admin_allowed else '❌'}",
                                 callback_data=f"toggle:{feature}:admin"),
            InlineKeyboardButton(f"Member {'✅' if member_allowed else '❌'}",
                                 callback_data=f"toggle:{feature}:member")
        ],
        [InlineKeyboardButton("⬅️ Permission", callback_data="perm:menu")]
    ])

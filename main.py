import os
import re
import json
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.errors import FloodWait

# ============================================================
# KONFIGURASI
# ============================================================

API_ID = 12345678
API_HASH = "ISI_API_HASH_KAMU"
SESSION_NAME = "autoclick_monitor"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
GROUPS_FILE = os.path.join(BASE_DIR, "groups.json")
NOTIF_FILE = os.path.join(BASE_DIR, "notifications.json")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")

LINK_PATTERN = re.compile(
    r"https?://t\.me/([A-Za-z0-9_]+)\?"
    r"(?:start|startapp)=([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)

# ============================================================
# FILE HELPERS
# ============================================================

def ensure_file(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def save_json(path, data):
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temp, path)


ensure_file(CONFIG_FILE, {
    "enabled": True,
    "trigger": 1,
    "delay": 0,
})

ensure_file(GROUPS_FILE, [])
ensure_file(NOTIF_FILE, [])
ensure_file(HISTORY_FILE, [])

config = load_json(CONFIG_FILE, {
    "enabled": True,
    "trigger": 1,
    "delay": 0,
})
groups = load_json(GROUPS_FILE, [])
notifications = load_json(NOTIF_FILE, [])
history = load_json(HISTORY_FILE, [])

if not isinstance(groups, list):
    groups = []
if not isinstance(notifications, list):
    notifications = []
if not isinstance(history, list):
    history = []

# ============================================================
# CLIENT
# ============================================================

app = Client(
    SESSION_NAME,
    api_id=API_ID,
    api_hash=API_HASH,
)

processed = set()

# ============================================================
# UTILITIES
# ============================================================

def is_owner(message):
    return bool(message.from_user and message.outgoing)


def is_target(chat_id):
    return str(chat_id) in {str(x) for x in groups}


def add_history(status, username, parameter, source):
    history.append({
        "status": status,
        "bot": username,
        "parameter": parameter,
        "source": str(source),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    if len(history) > 500:
        del history[:-500]

    save_json(HISTORY_FILE, history)


async def send_notification(text):
    failed = []

    for chat_id in list(notifications):
        try:
            await app.send_message(int(chat_id), text)
        except FloodWait as exc:
            print(f"[NOTIF] FloodWait {exc.value}s untuk {chat_id}")
        except Exception as exc:
            print(f"[NOTIF ERROR] {chat_id}: {exc}")
            failed.append(chat_id)

    return failed


async def resolve_chat_id(value):
    value = str(value).strip()

    if value.startswith("@"):
        chat = await app.get_chat(value)
        return chat.id

    return int(value)


# ============================================================
# LINK MONITOR
# ============================================================

@app.on_message(filters.text | filters.caption)
async def monitor_link(client, message):
    if not config.get("enabled", True):
        return

    if not message.chat or not is_target(message.chat.id):
        return

    text = message.text or message.caption or ""
    match = LINK_PATTERN.search(text)

    if not match:
        return

    username = match.group(1)
    parameter = match.group(2)

    unique_id = f"{message.chat.id}:{username.lower()}:{parameter}"
    if unique_id in processed:
        return

    processed.add(unique_id)

    if len(processed) > 5000:
        for item in list(processed)[:1000]:
            processed.discard(item)

    source_name = (
        message.chat.title
        or (f"@{message.chat.username}" if message.chat.username else None)
        or str(message.chat.id)
    )

    print(
        f"[LINK] @{username} | {parameter} | {source_name}"
    )

    add_history(
        "TERDETEKSI",
        username,
        parameter,
        source_name,
    )

    await send_notification(
        "🔗 LINK TERDETEKSI\n\n"
        f"🤖 Bot: @{username}\n"
        f"🔑 Parameter: {parameter}\n"
        f"📍 Sumber: {source_name}\n"
        f"🕐 {datetime.now().strftime('%H:%M:%S')}\n\n"
        "⚠️ Link terdeteksi. Silakan lanjutkan secara manual."
    )


# ============================================================
# /ID
# ============================================================

@app.on_message(filters.command("id") & filters.me)
async def command_id(client, message):
    chat = message.chat
    username = f"@{chat.username}" if chat.username else "-"

    await message.reply_text(
        "🆔 CHAT INFO\n\n"
        f"Nama: {chat.title or '-'}\n"
        f"ID: `{chat.id}`\n"
        f"Tipe: {chat.type}\n"
        f"Username: {username}"
    )


# ============================================================
# /ADDGRUP
# ============================================================

@app.on_message(filters.command("addgrup") & filters.me)
async def add_group(client, message):
    if len(message.command) < 2:
        await message.reply_text(
            "Gunakan:\n/addgrup @username\n/addgrup -100123456789"
        )
        return

    try:
        chat_id = await resolve_chat_id(message.command[1])

        # Validasi chat benar-benar bisa diakses.
        await client.get_chat(chat_id)

        if str(chat_id) in {str(x) for x in groups}:
            await message.reply_text("⚠️ Grup/channel sudah ada.")
            return

        groups.append(chat_id)
        save_json(GROUPS_FILE, groups)

        await message.reply_text(
            f"✅ Berhasil ditambahkan.\nID: `{chat_id}`"
        )

    except (ValueError, TypeError):
        await message.reply_text("❌ ID chat tidak valid.")
    except Exception as exc:
        await message.reply_text(f"❌ Gagal: {exc}")


# ============================================================
# /DELGRUP
# ============================================================

@app.on_message(filters.command("delgrup") & filters.me)
async def delete_group(client, message):
    if len(message.command) < 2:
        await message.reply_text(
            "Gunakan:\n/delgrup @username\n/delgrup -100123456789"
        )
        return

    try:
        chat_id = await resolve_chat_id(message.command[1])
        old_len = len(groups)

        groups[:] = [
            item for item in groups
            if str(item) != str(chat_id)
        ]
        save_json(GROUPS_FILE, groups)

        if len(groups) < old_len:
            await message.reply_text("✅ Berhasil dihapus.")
        else:
            await message.reply_text("⚠️ Tidak ditemukan.")

    except (ValueError, TypeError):
        await message.reply_text("❌ ID chat tidak valid.")
    except Exception as exc:
        await message.reply_text(f"❌ Gagal: {exc}")


# ============================================================
# /DELGRUPALL
# ============================================================

@app.on_message(filters.command("delgrupall") & filters.me)
async def delete_all_groups(client, message):
    groups.clear()
    save_json(GROUPS_FILE, groups)
    await message.reply_text("🗑️ Semua grup/channel pantauan dihapus.")


# ============================================================
# /LISTGRUP
# ============================================================

@app.on_message(filters.command("listgrup") & filters.me)
async def list_groups(client, message):
    if not groups:
        await message.reply_text("📭 Belum ada grup/channel pantauan.")
        return

    lines = ["📡 DAFTAR PANTAUAN\n"]

    for index, chat_id in enumerate(groups, 1):
        try:
            chat = await client.get_chat(int(chat_id))
            name = (
                chat.title
                or (f"@{chat.username}" if chat.username else None)
                or str(chat_id)
            )
        except Exception:
            name = "Tidak dapat diakses"

        lines.append(f"{index}. {name}\n   ID: `{chat_id}`")

    lines.append(f"\nTotal: {len(groups)}")
    await message.reply_text("\n".join(lines))


# ============================================================
# /ADDNOTIF
# ============================================================

@app.on_message(filters.command("addnotif") & filters.me)
async def add_notification(client, message):
    if len(message.command) < 2:
        await message.reply_text(
            "Gunakan:\n/addnotif ID_CHAT\n\n"
            "Contoh:\n/addnotif 123456789"
        )
        return

    try:
        chat_id = await resolve_chat_id(message.command[1])
        await client.get_chat(chat_id)

        if str(chat_id) in {str(x) for x in notifications}:
            await message.reply_text("⚠️ Tujuan sudah ada.")
            return

        notifications.append(chat_id)
        save_json(NOTIF_FILE, notifications)

        await message.reply_text(
            f"✅ Tujuan notifikasi ditambahkan.\nID: `{chat_id}`"
        )

    except (ValueError, TypeError):
        await message.reply_text("❌ ID chat tidak valid.")
    except Exception as exc:
        await message.reply_text(f"❌ Gagal: {exc}")


# ============================================================
# /DELNOTIF
# ============================================================

@app.on_message(filters.command("delnotif") & filters.me)
async def delete_notification(client, message):
    if len(message.command) < 2:
        await message.reply_text("Gunakan:\n/delnotif ID_CHAT")
        return

    try:
        chat_id = await resolve_chat_id(message.command[1])

        notifications[:] = [
            item for item in notifications
            if str(item) != str(chat_id)
        ]
        save_json(NOTIF_FILE, notifications)

        await message.reply_text("✅ Tujuan notifikasi dihapus.")

    except (ValueError, TypeError):
        await message.reply_text("❌ ID chat tidak valid.")
    except Exception as exc:
        await message.reply_text(f"❌ Gagal: {exc}")


# ============================================================
# /DELNOTIFALL
# ============================================================

@app.on_message(filters.command("delnotifall") & filters.me)
async def delete_all_notifications(client, message):
    notifications.clear()
    save_json(NOTIF_FILE, notifications)
    await message.reply_text("🗑️ Semua tujuan notifikasi dihapus.")


# ============================================================
# /LISTNOTIF
# ============================================================

@app.on_message(filters.command("listnotif") & filters.me)
async def list_notifications(client, message):
    if not notifications:
        await message.reply_text("📭 Belum ada tujuan notifikasi.")
        return

    lines = ["🔔 TUJUAN NOTIFIKASI\n"]

    for index, chat_id in enumerate(notifications, 1):
        try:
            chat = await client.get_chat(int(chat_id))
            name = (
                chat.title
                or (f"@{chat.username}" if chat.username else None)
                or str(chat_id)
            )
        except Exception:
            name = "Tidak dapat diakses"

        lines.append(f"{index}. {name}\n   ID: `{chat_id}`")

    await message.reply_text("\n".join(lines))


# ============================================================
# /SETNOTIF
# ============================================================

@app.on_message(filters.command("setnotif") & filters.me)
async def set_notification(client, message):
    await message.reply_text(
        "🔔 Tujuan notifikasi saat ini diatur dengan ID chat.\n\n"
        "Tambahkan:\n"
        "/addnotif ID_CHAT\n\n"
        "Hapus satu:\n"
        "/delnotif ID_CHAT\n\n"
        "Lihat semua:\n"
        "/listnotif"
    )


# ============================================================
# /TESTNOTIF
# ============================================================

@app.on_message(filters.command("testnotif") & filters.me)
async def test_notification(client, message):
    if not notifications:
        await message.reply_text(
            "⚠️ Belum ada tujuan notifikasi.\n"
            "Gunakan /addnotif ID_CHAT"
        )
        return

    await send_notification(
        "🧪 TEST NOTIFIKASI\n\n"
        "Sistem notifikasi aktif.\n"
        f"Waktu: {datetime.now().strftime('%H:%M:%S')}"
    )

    await message.reply_text("✅ Test notifikasi dikirim.")


# ============================================================
# /START
# ============================================================

@app.on_message(filters.command("start") & filters.me)
async def start_monitor(client, message):
    config["enabled"] = True
    save_json(CONFIG_FILE, config)
    await message.reply_text("🟢 Monitoring AKTIF.")


# ============================================================
# /STOP
# ============================================================

@app.on_message(filters.command("stop") & filters.me)
async def stop_monitor(client, message):
    config["enabled"] = False
    save_json(CONFIG_FILE, config)
    await message.reply_text("🔴 Monitoring DIMATIKAN.")


# ============================================================
# /STATUS
# ============================================================

@app.on_message(filters.command("status") & filters.me)
async def status(client, message):
    state = "🟢 AKTIF" if config.get("enabled", True) else "🔴 NONAKTIF"

    await message.reply_text(
        "⚡ UBOT STATUS\n\n"
        f"Monitoring : {state}\n"
        f"Pantauan   : {len(groups)}\n"
        f"Notifikasi : {len(notifications)}\n"
        f"Riwayat    : {len(history)}"
    )


# ============================================================
# /HISTORY
# ============================================================

@app.on_message(filters.command("history") & filters.me)
async def show_history(client, message):
    if not history:
        await message.reply_text("📭 Belum ada riwayat.")
        return

    lines = ["📜 RIWAYAT TERAKHIR\n"]

    for item in reversed(history[-10:]):
        lines.append(
            f"🔗 {item['status']}\n"
            f"🤖 @{item['bot']}\n"
            f"📍 {item['source']}\n"
            f"🕐 {item['time']}\n"
        )

    await message.reply_text("\n".join(lines))


# ============================================================
# /RESETSTATS
# ============================================================

@app.on_message(filters.command("resetstats") & filters.me)
async def reset_stats(client, message):
    history.clear()
    save_json(HISTORY_FILE, history)
    await message.reply_text("🗑️ Riwayat berhasil dihapus.")


# ============================================================
# /HELP
# ============================================================

@app.on_message(filters.command("help") & filters.me)
async def help_command(client, message):
    await message.reply_text(
        "⚡ AUTO CLICK MONITOR\n\n"
        "MONITORING\n"
        "/start - aktifkan\n"
        "/stop - matikan\n"
        "/status - status\n"
        "/id - ID chat\n\n"
        "GRUP / CHANNEL\n"
        "/addgrup @username atau ID\n"
        "/delgrup @username atau ID\n"
        "/delgrupall\n"
        "/listgrup\n\n"
        "NOTIFIKASI\n"
        "/addnotif ID_CHAT\n"
        "/delnotif ID_CHAT\n"
        "/delnotifall\n"
        "/listnotif\n"
        "/setnotif\n"
        "/testnotif\n\n"
        "RIWAYAT\n"
        "/history\n"
        "/resetstats\n\n"
        "Link Telegram yang sesuai akan otomatis\n"
        "dideteksi hanya dari target pantauan."
    )


# ============================================================
# RUN
# ============================================================

print("=" * 55)
print("       AUTO CLICK MONITOR USERBOT")
print("=" * 55)
print(f"Monitoring : {config.get('enabled', True)}")
print(f"Target     : {len(groups)}")
print(f"Notifikasi : {len(notifications)}")
print("=" * 55)

app.run()

import os
import re
import random
import asyncio
import aiohttp
from pyrogram import Client, filters

# ==========================================
# ⚙️ KONFIGURASI UTAMA (DARI RAILWAY VARIABLES)
# ==========================================
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

# Nama file database lokal untuk menyimpan list USERNAME grup di server Railway
DB_FILE = "usernames.txt"

# Regex untuk mendeteksi tautan HTTP/HTTPS secara universal
LINK_REGEX = r"(https?://[^\s]+)"

# Sidik jari Browser HP/PC populer (Anti-Bot & User-Agent Rotation)
USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Status Awal: Bot otomatis AKTIF saat server Railway menyala
BOT_STATUS = True

# ==========================================
# 📂 FUNGSI UTILITAS DATABASE USERNAME LOKAL
# ==========================================
def load_target_usernames():
    """Membaca daftar username grup dari file usernames.txt"""
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r") as f:
        # Menyimpan dalam format huruf kecil semua agar pencocokan tidak sensitif (case-insensitive)
        return [line.strip().lower().replace("@", "") for line in f if line.strip()]

def save_target_usernames(usernames_list):
    """Menyimpan daftar username grup ke file usernames.txt"""
    with open(DB_FILE, "w") as f:
        for uname in usernames_list:
            f.write(f"{uname}\n")

# ==========================================
# 🤖 INGERENSI UBOT (PENYAMARAN TELEGRAM DESKTOP)
# ==========================================
app = Client(
    name="ubot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    device_model="Telegram Desktop",
    system_version="Windows 11",
    app_version="5.1.7"
)

# ==========================================
# 🎮 FITUR PERINTAH KONTROL (HANYA AKUN ANDA)
# ==========================================

# 🟢 Mengaktifkan Bot (.uboton)
@app.on_message(filters.command("uboton", prefixes=["/", "."]) & filters.me)
async def turn_on_bot(client, message):
    global BOT_STATUS
    if BOT_STATUS:
        await message.edit_text("⚠️ **Userbot sudah dalam posisi AKTIF.**")
    else:
        BOT_STATUS = True
        await message.edit_text("🟢 **Userbot BERHASIL DIAKTIFKAN!**")

# 🔴 Menonaktifkan Bot (.ubotoff)
@app.on_message(filters.command("ubotoff", prefixes=["/", "."]) & filters.me)
async def turn_off_bot(client, message):
    global BOT_STATUS
    if not BOT_STATUS:
        await message.edit_text("⚠️ **Userbot memang sedang NONAKTIF.**")
    else:
        BOT_STATUS = False
        await message.edit_text("🔴 **Userbot BERHASIL DINONAKTIFKAN!**")

# ➕ Mendaftarkan Username ke Pantauan (.addgrup)
@app.on_message(filters.command("addgrup", prefixes=["/", "."]) & filters.me)
async def add_group_username(client, message):
    # Cek apakah chat saat ini memiliki username (grup/channel publik)
    if not message.chat.username:
        await message.edit_text("⚠️ **Grup/Channel ini bersifat PRIVAT (Tidak punya username)!** Gunakan skrip versi ID untuk grup privat.")
        return

    username = message.chat.username.lower()
    current_usernames = load_target_usernames()
    
    if username in current_usernames:
        await message.edit_text(f"⚠️ **Username @{username} sudah terdaftar dalam daftar pantauan.**")
    else:
        current_usernames.append(username)
        save_target_usernames(current_usernames)
        await message.edit_text(f"➕ **Berhasil menambahkan target!**\nNama: `{message.chat.title}`\nUsername: `@{username}`")

# ➖ Menghapus Username dari Pantauan (.delgrup)
@app.on_message(filters.command("delgrup", prefixes=["/", "."]) & filters.me)
async def delete_group_username(client, message):
    if not message.chat.username:
        await message.edit_text("⚠️ **Grup/Channel ini tidak memiliki username.**")
        return

    username = message.chat.username.lower()
    current_usernames = load_target_usernames()
    
    if username not in current_usernames:
        await message.edit_text(f"⚠️ **Username @{username} tidak ada dalam daftar pantauan.**")
    else:
        current_usernames.remove(username)
        save_target_usernames(current_usernames)
        await message.edit_text(f"➖ **Berhasil menghapus target!**\nUsername: `@{username}`")

# 📋 Melihat List Semua Username Terpantau (.listgrup)
@app.on_message(filters.command("listgrup", prefixes=["/", "."]) & filters.me)
async def list_usernames(client, message):
    current_usernames = load_target_usernames()
    if not current_usernames:
        await message.edit_text("📋 **Daftar Pantauan Kosong.**\nBot memantau *SEMUA* grup/channel secara default.")
        return
        
    text = "📋 **Daftar Username Terpantau:**\n"
    for idx, uname in enumerate(current_usernames, 1):
        text += f"{idx}. `@{uname}`\n"
    await message.edit_text(text)

# ==========================================
# 🕵️ CORE SYSTEM: PEMANTAUAN DI LATAR BELAKANG (SILENT MODE)
# ==========================================
@app.on_message((filters.group | filters.channel) & filters.text)
async def auto_click_handler(client, message):
    global BOT_STATUS
    
    # Proteksi 1: Cek status on/off bot
    if not BOT_STATUS:
        return

    # Proteksi 2: Abaikan pesan jika dikirim oleh Bot lain
    if message.from_user and message.from_user.is_bot:
        return

    # Proteksi 3: Filter Whitelist Username Dinamis
    target_usernames = load_target_usernames()
    if target_usernames:
        # Jika grup/channel tidak punya username, atau username-nya tidak ada di database -> abaikan
        if not message.chat.username or (message.chat.username.lower() not in target_usernames):
            return

    # Ekstraksi tautan menggunakan regex
    links = re.findall(LINK_REGEX, message.text)
    for link in links:
        # Laporan senyap hanya ke log internal server Railway
        chat_title = message.chat.title or "Channel"
        print(f"[➔] Menemukan tautan di @{message.chat.username} [{chat_title}]: {link}")
        
        # Eksekusi klik di background
        asyncio.create_task(click_link(link))

async def click_link(url):
    # Proteksi 4: Jeda acak (human delay)
    delay = random.uniform(0.5, 2.5)
    await asyncio.sleep(delay)

    # Proteksi 5: Manipulasi Header browser
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://t.me",
        "Connection": "keep-alive"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10, allow_redirects=True) as response:
                print(f"[✓] Diakses otomatis (jeda {delay:.2f}s) | Status: {response.status} | URL: {url}")
    except Exception as e:
        print(f"[✗] Gagal mengakses tautan {url} | Error: {e}")

if __name__ == "__main__":
    print("[*] Userbot Railway (Username Version) berhasil dijalankan...")
    app.run()

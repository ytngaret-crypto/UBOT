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

# Nama file database lokal untuk menyimpan list ID grup di server Railway
DB_FILE = "groups.txt"

# Regex untuk mendeteksi tautan HTTP/HTTPS secara universal
LINK_REGEX = r"(https?://[^\s]+)"

# Sidik jari Browser HP/PC populer (Anti-Bot & User-Agent Rotation)
USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Status Awal: Bot otomatis AKTIF saat server Railway menyala
BOT_STATUS = True

# ==========================================
# 📂 FUNGSI UTILITAS DATABASE GRUP LOKAL
# ==========================================
def load_target_groups():
    """Membaca daftar ID grup dari file groups.txt"""
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r") as f:
        return [int(line.strip()) for line in f if line.strip()]

def save_target_groups(groups_list):
    """Menyimpan daftar ID grup ke file groups.txt"""
    with open(DB_FILE, "w") as f:
        for gid in groups_list:
            f.write(f"{gid}\n")

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

# ➕ Mendaftarkan Grup ke Pantauan (.addgrup)
@app.on_message(filters.command("addgrup", prefixes=["/", "."]) & filters.me)
async def add_group_id(client, message):
    chat_id = message.chat.id
    current_groups = load_target_groups()
    
    if chat_id in current_groups:
        await message.edit_text("⚠️ **Grup ini sudah terdaftar dalam daftar pantauan.**")
    else:
        current_groups.append(chat_id)
        save_target_groups(current_groups)
        await message.edit_text(f"➕ **Berhasil menambahkan grup!**\nNama: `{message.chat.title}`\nID: `{chat_id}`")

# ➖ Menghapus Grup dari Pantauan (.delgrup)
@app.on_message(filters.command("delgrup", prefixes=["/", "."]) & filters.me)
async def delete_group_id(client, message):
    chat_id = message.chat.id
    current_groups = load_target_groups()
    
    if chat_id not in current_groups:
        await message.edit_text("⚠️ **Grup ini tidak ada dalam daftar pantauan.**")
    else:
        current_groups.remove(chat_id)
        save_target_groups(current_groups)
        await message.edit_text(f"➖ **Berhasil menghapus grup!**\nNama: `{message.chat.title}`")

# 📋 Melihat List Semua Grup Terpantau (.listgrup)
@app.on_message(filters.command("listgrup", prefixes=["/", "."]) & filters.me)
async def list_groups(client, message):
    current_groups = load_target_groups()
    if not current_groups:
        await message.edit_text("📋 **Daftar Pantauan Kosong.**\nBot memantau *SEMUA* grup secara default.")
        return
        
    text = "📋 **Daftar Grup Terpantau:**\n"
    for idx, gid in enumerate(current_groups, 1):
        text += f"{idx}. `{gid}`\n"
    await message.edit_text(text)

# ==========================================
# 🕵️ CORE SYSTEM: PEMANTAUAN DI LATAR BELAKANG (SILENT MODE)
# ==========================================
@app.on_message(filters.group & filters.text)
async def auto_click_handler(client, message):
    global BOT_STATUS
    
    # Proteksi 1: Cek status on/off bot
    if not BOT_STATUS:
        return

    # Proteksi 2: Abaikan pesan jika dikirim oleh Bot lain di grup
    if message.from_user and message.from_user.is_bot:
        return

    # Proteksi 3: Filter Whitelist Grup Dinamis
    target_groups = load_target_groups()
    if target_groups and (message.chat.id not in target_groups):
        return

    # Ekstraksi tautan menggunakan regex
    links = re.findall(LINK_REGEX, message.text)
    for link in links:
        # Laporan senyap hanya dikirim ke LOG INTERNAL server Railway Anda
        print(f"[➔] Menemukan tautan di grup [{message.chat.title}]: {link}")
        
        # Eksekusi klik di background agar ubot tetap responsif
        asyncio.create_task(click_link(link))

async def click_link(url):
    # Proteksi 4: Jeda acak (human delay) agar dikira diklik manual oleh jari manusia
    delay = random.uniform(0.5, 2.5)
    await asyncio.sleep(delay)

    # Proteksi 5: Manipulasi Header agar server web membaca request dari Browser HP/PC
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://t.me", # Rekam jejak rujukan seolah berasal langsung dari aplikasi Telegram
        "Connection": "keep-alive"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10, allow_redirects=True) as response:
                # Log sukses internal server (tidak akan terkirim ke chat grup)
                print(f"[✓] Diakses otomatis (jeda {delay:.2f}s) | Status: {response.status} | URL: {url}")
    except Exception as e:
        print(f"[✗] Gagal mengakses tautan {url} | Error: {e}")

if __name__ == "__main__":
    print("[*] Userbot Railway versi terbaru berhasil dijalankan...")
    app.run()

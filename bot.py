import os
import re
import random
import asyncio
import aiohttp
from pyrogram import Client, filters

# Mengambil kredensial dari Environment Variables Railway
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

# Mengambil daftar ID Grup dari Railway (Contoh format di Railway: -10012345,-10067890)
# Jika dikosongkan, ubot akan memantau SEMUA grup secara default
TARGET_GROUPS_RAW = os.environ.get("TARGET_GROUPS", "")
TARGET_GROUPS = [int(x.strip()) for x in TARGET_GROUPS_RAW.split(",") if x.strip()]

# Regex fleksibel untuk mendeteksi tautan HTTP/HTTPS
LINK_REGEX = r"(https?://[^\s]+)"

# Daftar User-Agent browser populer untuk memalsukan identitas request (Anti-Bot)
USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Inisialisasi Ubot
app = Client(
    name="ubot_session",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING
)

# Filter Proteksi: Hanya grup, hanya teks, dan abaikan jika pengirimnya adalah Akun Bot Telegram
@app.on_message(filters.group & filters.text)
async def auto_click_handler(client, message):
    # 🛡️ PROTEKSI 1: Abaikan pesan jika dikirim oleh bot lain di grup
    if message.from_user and message.from_user.is_bot:
        return

    # 🎯 FITUR PILIH GRUP: Jika whitelist diisi, cek apakah chat ID terdaftar
    if TARGET_GROUPS and (message.chat.id not in TARGET_GROUPS):
        return

    links = re.findall(LINK_REGEX, message.text)
    
    for link in links:
        print(f"[➔] Menemukan tautan di grup [{message.chat.title}]: {link}")
        # Jalankan fungsi klik secara background agar ubot tidak lag/beku
        asyncio.create_task(click_link(link))

async def click_link(url):
    # 🛡️ PROTEKSI 2: Jeda acak (Human-like delay) antara 0.5 hingga 2.5 detik
    # Ini mencegah sistem keamanan tautan mendeteksi respons instan robotik yang tidak wajar
    delay = random.uniform(0.5, 2.5)
    await asyncio.sleep(delay)

    # 🛡️ PROTEKSI 3: Rotasi User-Agent dan Header acak agar dikira diklik manusia lewat HP/PC
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://t.me", # Seolah-olah dialihkan langsung dari aplikasi Telegram resmi
        "Connection": "keep-alive"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10, allow_redirects=True) as response:
                print(f"[✓] Diakses setelah jeda {delay:.2f}s | Status: {response.status} | URL: {url}")
    except Exception as e:
        print(f"[✗] Gagal mengakses tautan | Error: {e}")

if name == "main":
    print("[*] Userbot Railway aktif dengan proteksi anti-bot...")
    if TARGET_GROUPS:
        print(f"[*] Memantau {len(TARGET_GROUPS)} grup spesifik: {TARGET_GROUPS}")
    else:
        print("[*] Memantau SEMUA grup (Variabel TARGET_GROUPS kosong).")
    app.run()
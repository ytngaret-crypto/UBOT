import os
import re
import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatAction
from pyrogram.errors import RPCError
from pyrogram import idle

# ========================================================
# 1. KONFIGURASI KREDENSIAL (PRODUKSI & VALIDASI AMAN)
# ========================================================
API_ID_ENV = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
STRING_SESSION = os.environ.get("STRING_SESSION")

# Validasi awal sebelum bot di-start untuk mencegah EOFError di Railway
if not API_ID_ENV or not API_HASH or not STRING_SESSION:
    print("[ERROR FATAL] Variabel ENV tidak lengkap di Railway!")
    print(f"-> API_ID ditemukan: {bool(API_ID_ENV)}")
    print(f"-> API_HASH ditemukan: {bool(API_HASH)}")
    print(f"-> STRING_SESSION ditemukan: {bool(STRING_SESSION)}")
    print("[SYSTEM] Mematikan aplikasi secara aman untuk menghindari perulangan crash.")
    exit(1)

API_ID = int(API_ID_ENV)

# Inisialisasi Ubot menggunakan String Session agar login permanen di Cloud
app = Client(
    name="my_ubot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    session_string=STRING_SESSION.strip()
)

# Pola Regex untuk mendeteksi link Telegram Bot dengan parameter start
BOT_LINK_PATTERN = r"(?:https?:\/\/)?(?:t\.me|telegram\.me)\/([A-Za-z0-9_]+bot)\?start=([A-Za-z0-9_\-]+)"

# Database Lokal (Disimpan di RAM Server Railway)
monitored_groups = set()     # Menyimpan ID grup yang dipantau (Kosong = Pantau Semua)
clicked_links = set()        # Menyimpan token Daget yang sudah diklik (Anti-Duplikasi)
is_bot_active = True         # Status Sakelar Utama Ubot

# Pengaturan Jeda Klik Default (Dapat diubah lewat Telegram)
MIN_DELAY = 1.0  
MAX_DELAY = 2.5  


# ========================================================
# 2. FITUR KONTROL VIA PRIVATE CHAT / SAVED MESSAGES
# ========================================================

@app.on_message(filters.command("ubot", prefixes=".") & filters.me)
async def toggle_ubot_status(client: Client, message: Message):
    """Sakelar On/Off Ubot. Contoh: .ubot on / .ubot off"""
    global is_bot_active
    if len(message.command) < 2:
        status_str = "AKTIF" if is_bot_active else "NONAKTIF"
        return await message.reply_text(f"ℹ️ Status ubot saat ini: **{status_str}**.\nJeda aktif: `{MIN_DELAY}` - `{MAX_DELAY}` detik.")
    
    action = message.command.lower()
    if action == "on":
        is_bot_active = True
        await message.reply_text("✅ **Ubot Aktif!** Deteksi otomatis & Mode Stealth berjalan.")
    elif action == "off":
        is_bot_active = False
        await message.reply_text("⏸️ **Ubot Dinonaktifkan!** Pemindaian link dihentikan sementara.")
    else:
        await message.reply_text("❌ Perintah salah. Gunakan `.ubot on` atau `.ubot off`.")


@app.on_message(filters.command("setdelay", prefixes=".") & filters.me)
async def set_click_delay(client: Client, message: Message):
    """Mengatur jeda waktu klik secara dinamis. Contoh: .setdelay 0.5 1.8"""
    global MIN_DELAY, MAX_DELAY
    if len(message.command) < 3:
        return await message.reply_text(
            f"ℹ️ Jeda saat ini: `{MIN_DELAY}` sampai `{MAX_DELAY}` detik.\n"
            f"Gunakan format: `.setdelay [minimal] [maksimal]`\n"
            f"Contoh: `.setdelay 0.8 2.0`"
        )
    
    try:
        new_min = float(message.command)
        new_max = float(message.command)
        
        if new_min > new_max:
            return await message.reply_text("❌ Nilai minimal tidak boleh lebih besar dari nilai maksimal!")
            
        MIN_DELAY = new_min
        MAX_DELAY = new_max
        await message.reply_text(f"⚡ **Jeda Klik Berhasil Diubah!**\nUbot akan menahan klik secara acak antara `{MIN_DELAY}` hingga `{MAX_DELAY}` detik.")
    except (ValueError, IndexError):
        await message.reply_text("❌ Input salah! Harus berupa angka numerik/desimal. Contoh: `.setdelay 1.5 3.0`")


@app.on_message(filters.command("idgrup", prefixes=".") & filters.me)
async def get_all_ids_and_channels(client: Client, message: Message):
    """Melihat daftar ID grup & channel secara silent tanpa kirim chat ke grup luar"""
    text_groups = "👥 **Daftar ID Grup Anda:**\n\n"
    text_channels = "\n📢 **Daftar ID Channel Anda:**\n\n"
    
    try:
        async for dialog in client.get_dialogs():
            if not dialog.chat:
                continue
            chat_type = dialog.chat.type.value
            if chat_type in ["group", "supergroup"]:
                text_groups += f"• `{dialog.chat.id}` - **{dialog.chat.title}**\n"
            elif chat_type == "channel":
                text_channels += f"• `{dialog.chat.id}` - **{dialog.chat.title}**\n"
                
        full_report = text_groups + text_channels
        
        if len(full_report) > 4096:
            for chunk in [full_report[i:i+4096] for i in range(0, len(full_report), 4096)]:
                await message.reply_text(chunk)
        else:
            await message.reply_text(full_report)
    except Exception as e:
        await message.reply_text(f"❌ Gagal mengambil data ID: {e}")


@app.on_message(filters.command("addgrup", prefixes=".") & filters.me)
async def add_group_to_whitelist(client: Client, message: Message):
    """Mendaftarkan grup khusus untuk dipantau. Contoh: .addgrup -100123456789"""
    if len(message.command) < 2: 
        return await message.reply_text("❌ Format salah. Contoh: `.addgrup -100123456789`")
    try:
        group_id = int(message.command)
        monitored_groups.add(group_id)
        await message.reply_text(f"✅ ID `{group_id}` berhasil dimasukkan ke daftar pantau khusus.")
    except (ValueError, IndexError):
        await message.reply_text("❌ ID grup harus berupa angka numerik yang valid.")


@app.on_message(filters.command("delgrup", prefixes=".") & filters.me)
async def delete_group_from_whitelist(client: Client, message: Message):
    """Menghapus grup dari daftar pantau. Contoh: .delgrup -100123456789"""
    if len(message.command) < 2: 
        return await message.reply_text("❌ Format salah. Contoh: `.delgrup -100123456789`")
    try:
        group_id = int(message.command)
        if group_id in monitored_groups:
            monitored_groups.remove(group_id)
            await message.reply_text(f"🗑️ ID `{group_id}` berhasil dihapus dari daftar pantau.")
        else:
            await message.reply_text("❌ ID grup tersebut tidak ada di dalam daftar pantau.")
    except (ValueError, IndexError):
        await message.reply_text("❌ ID grup harus berupa angka.")


@app.on_message(filters.command("listgrup", prefixes=".") & filters.me)
async def list_monitored_groups(client: Client, message: Message):
    """Melihat daftar grup yang dikunci untuk dipantau"""
    if not monitored_groups:
        return await message.reply_text("ℹ️ Daftar kosong. Ubot memantau **seluruh grup** Anda secara default.")
    
    text = "**📌 Grup Yang Dikunci Untuk Dipantau:**\n\n"
    for g_id in monitored_groups:
        try:
            chat = await client.get_chat(g_id)
            text += f"• `{g_id}` - **{chat.title}**\n"
        except Exception:
            text += f"• `{g_id}` - *(Grup Tidak Aktif/Keluar)*\n"
    await message.reply_text(text)


# ========================================================
# 3. CORE STEALTH ENGINE: DETEKSI, ANTI-BOT, & KLAIM SILENT
# ========================================================

@app.on_message(filters.group & ~filters.me)
async def auto_claim_daget(client: Client, message: Message):
    if not is_bot_active:
        return
        
    if monitored_groups and message.chat.id not in monitored_groups:
        return
        
    if not message.text:
        return

    # Pemindaian teks link portal bot menggunakan regex yang divalidasi
    match = re.search(BOT_LINK_PATTERN, message.text, re.IGNORECASE)
    
    if match:
        bot_username = match.group(1)      
        start_parameter = match.group(2)   

        # 🛑 PROTEKSI 1: SISTEM ANTI-DUPLIKASI KLIKS
        if start_parameter in clicked_links:
            return

        # Mengunci token ke memory agar tidak terklik ulang oleh spammer di grup
        clicked_links.add(start_parameter)

        # 🕵️‍♂️ PROTEKSI 2: JEDA MANUSIA ACAK (HUMAN-DELAY SIMULATION)
        sleep_time = random.uniform(MIN_DELAY, MAX_DELAY)
        print(f"[STEALTH LOG] Link Baru Terdeteksi: {start_parameter}. Menahan tindakan {sleep_time:.2f} detik...")
        await asyncio.sleep(sleep_time)

        try:
            # 🕵️‍♂️ PROTEKSI 3: BACA RIWAYAT (READ CHAT HISTORY)
            await client.read_chat_history(chat_id=message.chat.id, max_id=message.id)

            # 🕵️‍♂️ PROTEKSI 4: SIMULASI AKSI MENGETIK (TYPING ACTION MASKING)
            await client.send_chat_action(chat_id=bot_username, action=ChatAction.TYPING)
            await asyncio.sleep(0.3)

            # Eksekusi Tembak API Utama (Auto-Click Instan tanpa memunculkan chat di UI)
            from pyrogram.raw import functions
            peer = await client.resolve_peer(bot_username)
            await client.invoke(
                functions.messages.StartBot(
                    bot=peer,
                    peer=peer,
                    random_id=random.randint(1, 999999),
                    start_param=start_parameter
                )
            )
            print(f"[STEALTH SUCCESS] Eksekusi klaim berhasil dikirim untuk token: {start_parameter}")
            
        except RPCError as rpc_err:
            print(f"[STEALTH TELEGRAM ERROR] Gagal di tingkat server Telegram: {rpc_err}")
        except Exception as e:
            print(f"[STEALTH SYSTEM ERROR] Gagal mengeksekusi tautan: {e}")


# ========================================================
# 4. MANAJEMEN LOOP ASINKRON (STANDARISASI PYTHON 3.13)
# ========================================================
async def main():

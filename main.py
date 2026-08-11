import os
import re
import asyncio
import random
from pyrogram import Client, filters
from pyrogram.types import Message

# ========================================================
# 1. KONFIGURASI KREDENSIAL (OTOMATIS DARI RAILWAY VARIABLES)
# ========================================================
API_ID = int(os.environ.get("API_ID", 1234567)) 
API_HASH = os.environ.get("API_HASH", "your_api_hash_here")
STRING_SESSION = os.environ.get("STRING_SESSION")

# Inisialisasi Ubot menggunakan String Session agar login permanen di Cloud
app = Client("my_ubot", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION)

# Pola Regex Baru (Hanya mendeteksi bot @SukaClaimDagetBot)
BOT_LINK_PATTERN = r"(?:https?:\/\/)?(?:t\.me|telegram\.me)\/(claimdanakaget)\?start=([A-Za-z0-9_\-]+)"


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
    
    action = message.command[1].lower()
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
        new_min = float(message.command[1])
        new_max = float(message.command[2])
        
        if new_min > new_max:
            return await message.reply_text("❌ Nilai minimal tidak boleh lebih besar dari nilai maksimal!")
            
        MIN_DELAY = new_min
        MAX_DELAY = new_max
        await message.reply_text(f"⚡ **Jeda Klik Berhasil Diubah!**\nUbot akan menahan klik secara acak antara `{MIN_DELAY}` hingga `{MAX_DELAY}` detik.")
    except ValueError:
        await message.reply_text("❌ Input harus berupa angka atau desimal menggunakan titik (contoh: 1.5).")


@app.on_message(filters.command("idgrup", prefixes=".") & filters.me)
async def get_all_ids_and_channels(client: Client, message: Message):
    """Melihat daftar ID grup & channel secara silent tanpa kirim chat ke grup luar"""
    text_groups = "👥 **Daftar ID Grup Anda:**\n\n"
    text_channels = "\n📢 **Daftar ID Channel Anda:**\n\n"
    
    async for dialog in client.get_dialogs():
        chat_type = dialog.chat.type.value
        if chat_type in ["group", "supergroup"]:
            text_groups += f"• `{dialog.chat.id}` - **{dialog.chat.title}**\n"
        elif chat_type == "channel":
            text_channels += f"• `{dialog.chat.id}` - **{dialog.chat.title}**\n"
            
    full_report = text_groups + text_channels
    
    # Antisipasi jika teks terlalu panjang melebihi limit Telegram (4096 karakter)
    if len(full_report) > 4096:
        for chunk in [full_report[i:i+4096] for i in range(0, len(full_report), 4096)]:
            await message.reply_text(chunk)
    else:
        await message.reply_text(full_report)


@app.on_message(filters.command("addgrup", prefixes=".") & filters.me)
async def add_group_to_whitelist(client: Client, message: Message):
    """Mendaftarkan grup khusus untuk dipantau. Contoh: .addgrup -100123456789"""
    if len(message.command) < 2: 
        return await message.reply_text("❌ Format salah. Contoh: `.addgrup -100123456789`")
    try:
        group_id = int(message.command[1])
        monitored_groups.add(group_id)
        await message.reply_text(f"✅ ID `{group_id}` berhasil dimasukkan ke daftar pantau khusus.")
    except ValueError:
        await message.reply_text("❌ ID grup harus berupa angka numerik.")


@app.on_message(filters.command("delgrup", prefixes=".") & filters.me)
async def delete_group_from_whitelist(client: Client, message: Message):
    """Menghapus grup dari daftar pantau. Contoh: .delgrup -100123456789"""
    if len(message.command) < 2: 
        return await message.reply_text("❌ Format salah. Contoh: `.delgrup -100123456789`")
    try:
        group_id = int(message.command[1])
        if group_id in monitored_groups:
            monitored_groups.remove(group_id)
            await message.reply_text(f"🗑️ ID `{group_id}` berhasil dihapus dari daftar pantau.")
        else:
            await message.reply_text("❌ ID grup tersebut tidak ada di dalam daftar pantau.")
    except ValueError:
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
            text += f"• `{g_id}` - (Gagal memuat nama)\n"
    await message.reply_text(text)


# ========================================================
# 3. CORE STEALTH ENGINE: DETEKSI, ANTI-BOT, & KLAIM SILENT
# ========================================================

@app.on_message(filters.group & ~filters.me)
async def auto_claim_daget(client: Client, message: Message):
    # Validasi sakelar ubot
    if not is_bot_active:
        return
        
    # Validasi daftar pantau khusus (jika di-set)
    if monitored_groups and message.chat.id not in monitored_groups:
        return
        
    if not message.text:
        return

    # Pemindaian teks link portal bot
    match = re.search(BOT_LINK_PATTERN, message.text, re.IGNORECASE)
    
    if match:
        bot_username = match.group(1)      
        start_parameter = match.group(2)   # Token unik link (misal: DAGET_N26811km503)

        # 🛑 PROTEKSI 1: SISTEM ANTI-DUPLIKASI KLIKS
        if start_parameter in clicked_links:
            return

        # Mengunci token ke memory agar tidak terklik ulang oleh spammer di grup
        clicked_links.add(start_parameter)

        # 🕵️‍♂️ PROTEKSI 2: JEDA MANUSIA ACAK (HUMAN-DELAY SIMULATION)
        # Menghindar dari deteksi log bot owner yang mem-banned akun dengan klik < 0.5 detik konstan
        sleep_time = random.uniform(MIN_DELAY, MAX_DELAY)
        print(f"[STEALTH LOG] Link Baru Terdeteksi. Menahan tindakan {sleep_time:.2f} detik agar natural...")
        await asyncio.sleep(sleep_time)

        try:
            # 🕵️‍♂️ PROTEKSI 3: BACA RIWAYAT (READ CHAT HISTORY)
            # Menandai pesan di grup sebagai 'Read' (Centang Dua) sebelum melakukan klik.
            # Akun asli pasti membaca pesan grup dulu, ubot ilegal biasanya melewatkan proses ini.
            await client.read_chat_history(chat_id=message.chat.id, max_id=message.id)

            # 🕵️‍♂️ PROTEKSI 4: SIMULASI AKSI MENGETIK (TYPING ACTION MASKING)
# Mengirimkan status typing super singkat ke target bot seakan kita sedang membuka chatnya
from pyrogram.enums import ChatAction

await client.send_chat_action(bot_username, ChatAction.TYPING)
await asyncio.sleep(0.5) # Jeda singkat simulasi mengetik

            # Eksekusi Tembak API Utama (Klik /Start Bot Senyap)
            # Seluruh proses ini 100% silent, tidak mengirim logs apa pun ke grup chat Anda.
            await client.start_bot(bot_username, start_parameter)
            print(f"[STEALTH SUCCESS] Eksekusi klaim berhasil dikirim untuk token: {start_parameter}")
            
        except Exception as e:
            # Logs hanya muncul di konsol internal Railway Anda, rahasia dari Telegram
            print(f"[STEALTH ERROR] Gagal mengeksekusi tautan: {e}")


if __name__ == "__main__":
    print("[SYSTEM] ==============================================")
    print("[SYSTEM] Ubot Dana Kaget Premium (Super Protect) Aktif!")
    print("[SYSTEM] Berjalan senyap di latar belakang...")
    print("[SYSTEM] ==============================================")
    app.run()
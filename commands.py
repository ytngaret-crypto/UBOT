import asyncio
import io
import random
from datetime import datetime, timezone

from pyrogram import filters
from pyrogram.types import Message

from features import FEATURES
from security import command_allowed
from ui import main_menu, category_menu, permission_menu


def register_handlers(app):
    @app.on_message(filters.me & filters.command("menu", prefixes="."))
    async def menu(_, message):
        await message.reply_text("🤖 <b>UBot</b>\n\nPilih fitur:", reply_markup=main_menu())

    @app.on_message(filters.me & filters.command("help", prefixes="."))
    async def help_me(_, message):
        await message.reply_text(
            "🤖 <b>UBot</b>\n\n"
            "Semua command menggunakan prefix <code>.</code>\n"
            "Buka <code>.menu</code> untuk menu fitur."
        )

    @app.on_message(filters.command("menu", prefixes="."))
    async def menu_all(_, message):
        # Unauthorized .menu is silent except owner/admin; menu itself can be enabled if desired.
        role = await app.db.get_role(message.from_user.id)
        if role == "member":
            if not await app.db.permission(message.chat.id, "dashboard", "member"):
                return
        elif role == "admin":
            if not await app.db.permission(message.chat.id, "dashboard", "admin"):
                return
        await message.reply_text("🤖 <b>UBot</b>\n\nPilih fitur:", reply_markup=main_menu())

    @app.on_message(filters.command("pay", prefixes="."))
    async def pay(_, message):
        if not await command_allowed(app, message, "pay"):
            return
        p = await app.db.get_payment(app.cfg.owner_id)
        if not p:
            return
        text = "💳 <b>PEMBAYARAN</b>\n\n"
        if p["bank"] and p["account_number"]:
            text += f"🏦 <b>Bank:</b> {p['bank']}\n💳 <b>No. Rek:</b> {p['account_number']}\n"
        if p["account_name"]:
            text += f"👤 <b>A/N:</b> {p['account_name']}\n"
        if p["ewallet"] and p["ewallet_number"]:
            text += f"📱 <b>{p['ewallet']}:</b> {p['ewallet_number']}\n"
        if p["description"]:
            text += f"\n📝 {p['description']}"
        if p["qris_file_id"]:
            await message.reply_photo(p["qris_file_id"], caption=text)
        else:
            await message.reply_text(text)

    @app.on_message(filters.command("song", prefixes="."))
    async def song(_, message):
        if not await command_allowed(app, message, "song"):
            return
        q = message.text.split(maxsplit=1)
        if len(q) < 2:
            return
        await message.reply_text(f"🎵 <b>Mencari:</b> {q[1]}\n\n"
                                "Pencarian audio memerlukan sumber/API musik yang dikonfigurasi.")

    @app.on_message(filters.command("movie", prefixes="."))
    async def movie(_, message):
        if not await command_allowed(app, message, "movie"):
            return
        q = message.text.split(maxsplit=1)
        if len(q) < 2:
            return
        if not app.cfg.tmdb_api_key:
            return await message.reply_text("TMDB API belum dikonfigurasi oleh Owner.")
        import aiohttp
        async with aiohttp.ClientSession() as s:
            async with s.get(
                "https://api.themoviedb.org/3/search/multi",
                params={"api_key": app.cfg.tmdb_api_key, "query": q[1], "language": "id-ID"}
            ) as r:
                data = await r.json()
        results = data.get("results", [])
        if not results:
            return
        x = results[0]
        title = x.get("title") or x.get("name") or q[1]
        overview = x.get("overview") or "-"
        year = (x.get("release_date") or x.get("first_air_date") or "")[:4] or "-"
        await message.reply_text(f"🎬 <b>{title}</b>\n📅 {year}\n\n{overview[:700]}")

    @app.on_message(filters.command("random", prefixes="."))
    async def random_cmd(_, message):
        if not await command_allowed(app, message, "random"):
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            return
        choices = [x.strip() for x in args[1].split("|") if x.strip()]
        if not choices:
            return
        await message.reply_text(f"🎲 {random.choice(choices)}")

    @app.on_message(filters.command("qr", prefixes="."))
    async def qr(_, message):
        if not await command_allowed(app, message, "qr"):
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            return
        try:
            import qrcode
            img = qrcode.make(args[1])
            bio = io.BytesIO()
            bio.name = "qrcode.png"
            img.save(bio, "PNG")
            bio.seek(0)
            await message.reply_photo(bio)
        except Exception:
            return

    @app.on_message(filters.command("texttools", prefixes="."))
    async def texttools(_, message):
        if not await command_allowed(app, message, "texttools"):
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            return
        txt = args[1]
        await message.reply_text(
            f"🔤 <b>Text Tools</b>\n"
            f"Karakter: {len(txt)}\n"
            f"Kata: {len(txt.split())}\n"
            f"UPPER: {txt.upper()}\n"
            f"lower: {txt.lower()}"
        )

    @app.on_message(filters.command("game", prefixes="."))
    async def game(_, message):
        if not await command_allowed(app, message, "game"):
            return
        await message.reply_text(
            "🎮 <b>Game Center</b>\n\n"
            "Mini-game dasar siap dikembangkan dari menu Game."
        )

    @app.on_message(filters.command("quiz", prefixes="."))
    async def quiz(_, message):
        if not await command_allowed(app, message, "quiz"):
            return
        topic = message.text.split(maxsplit=1)
        topic = topic[1] if len(topic) > 1 else "pengetahuan umum"
        await message.reply_text(
            f"🧩 <b>Quiz Generator</b>\nTopik: {topic}\n\n"
            "Generator AI dapat diaktifkan setelah API AI dikonfigurasi."
        )

    @app.on_message(filters.command("autoreply", prefixes="."))
    async def autoreply(_, message):
        if not await command_allowed(app, message, "autoreply"):
            return
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            return await message.reply_text("Format: <code>.autoreply keyword balasan</code>")
        await app.db.add_autoreply(message.chat.id, args[1], args[2])
        await message.reply_text("✅ Auto-reply disimpan.")

    @app.on_message(filters.command("delreply", prefixes="."))
    async def delreply(_, message):
        if not await command_allowed(app, message, "reply"):
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            return
        await app.db.del_autoreply(message.chat.id, args[1])
        await message.reply_text("✅ Auto-reply dihapus.")

    @app.on_message(filters.command("listreply", prefixes="."))
    async def listreply(_, message):
        if not await command_allowed(app, message, "reply"):
            return
        rows = await app.db.list_autoreplies(message.chat.id)
        if not rows:
            return await message.reply_text("Belum ada auto-reply.")
        text = "📋 <b>Auto-reply</b>\n\n" + "\n".join(
            f"• <code>{r['keyword']}</code> → {r['response'][:80]}" for r in rows
        )
        await message.reply_text(text)

    @app.on_message(filters.command("setpay", prefixes="."))
    async def setpay(_, message):
        role = await app.db.get_role(message.from_user.id)
        if role != "owner":
            return
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            return await message.reply_text(
                "Format:\n<code>.setpay bank BCA</code>\n"
                "<code>.setpay rekening 123</code>\n"
                "<code>.setpay nama SETYAA</code>\n"
                "<code>.setpay ewallet DANA</code>\n"
                "<code>.setpay ewallet_no 0812...</code>\n"
                "<code>.setpay desc teks</code>"
            )
        key, value = args[1], args[2]
        mapping = {
            "bank": "bank",
            "rekening": "account_number",
            "nama": "account_name",
            "ewallet": "ewallet",
            "ewallet_no": "ewallet_number",
            "desc": "description",
        }
        if key not in mapping:
            return
        await app.db.set_payment(app.cfg.owner_id, **{mapping[key]: value})
        await message.reply_text("✅ Payment setting diperbarui.")

    @app.on_message(filters.command("setadmin", prefixes="."))
    async def setadmin(_, message):
        if await app.db.get_role(message.from_user.id) != "owner":
            return
        target = message.reply_to_message.from_user.id if message.reply_to_message else None
        if not target:
            args = message.text.split(maxsplit=1)
            if len(args) < 2 or not args[1].isdigit():
                return
            target = int(args[1])
        await app.db.set_role(target, "admin")
        await message.reply_text("✅ User dijadikan Admin.")

    @app.on_message(filters.command("allow", prefixes="."))
    async def allow(_, message):
        if await app.db.get_role(message.from_user.id) != "owner":
            return
        args = message.text.split()
        if len(args) < 3 or args[1] not in FEATURES:
            return
        role = args[2].lower()
        if role not in ("admin", "member"):
            return
        scope = message.chat.id
        await app.db.set_permission(scope, args[1], role, True)
        await message.reply_text(f"✅ {args[1]} → {role} diizinkan.")

    @app.on_message(filters.command("deny", prefixes="."))
    async def deny(_, message):
        if await app.db.get_role(message.from_user.id) != "owner":
            return
        args = message.text.split()
        if len(args) < 3 or args[1] not in FEATURES:
            return
        role = args[2].lower()
        if role not in ("admin", "member"):
            return
        await app.db.set_permission(message.chat.id, args[1], role, False)
        await message.reply_text(f"🔒 {args[1]} → {role} dinonaktifkan.")

    # Basic group moderation: reply OR @username/id.
    @app.on_message(filters.command(["ban", "unban", "mute", "unmute"], prefixes=".") & filters.group)
    async def moderation(_, message):
        cmd = message.command[0].lower()
        if not await command_allowed(app, message, cmd):
            return
        target = None
        if message.reply_to_message and message.reply_to_message.from_user:
            target = message.reply_to_message.from_user
        elif len(message.command) >= 2:
            token = message.command[1]
            try:
                target = await app.get_users(token)
            except Exception:
                return
        if not target:
            return
        try:
            from pyrogram.types import ChatPermissions
            if cmd == "ban":
                await app.ban_chat_member(message.chat.id, target.id)
            elif cmd == "unban":
                await app.unban_chat_member(message.chat.id, target.id)
            elif cmd == "mute":
                await app.restrict_chat_member(message.chat.id, target.id, ChatPermissions())
            elif cmd == "unmute":
                await app.restrict_chat_member(
                    message.chat.id, target.id,
                    ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                                    can_send_other_messages=True, can_add_web_page_previews=True)
                )
        except Exception:
            return

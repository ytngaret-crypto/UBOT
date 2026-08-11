import io, random, re
from pyrogram import filters
from pyrogram.types import ChatPermissions
from security import command_is_allowed

def register_full_feature_handlers(app):
    @app.on_message(filters.command("qr", prefixes="."))
    async def qr(_, m):
        if not await command_is_allowed(app,m,"qr"): return
        args=m.text.split(maxsplit=1)
        if len(args)<2:return
        try:
            import qrcode
            b=io.BytesIO(); b.name="qr.png"
            qrcode.make(args[1]).save(b,"PNG"); b.seek(0)
            await m.reply_photo(b)
        except Exception: return

    @app.on_message(filters.command("random", prefixes="."))
    async def rnd(_,m):
        if not await command_is_allowed(app,m,"random"): return
        a=m.text.split(maxsplit=1)
        if len(a)<2:return
        items=[x.strip() for x in a[1].split("|") if x.strip()]
        if items: await m.reply_text("🎲 "+random.choice(items))

    @app.on_message(filters.command("texttools", prefixes="."))
    async def texttools(_,m):
        if not await command_is_allowed(app,m,"texttools"): return
        a=m.text.split(maxsplit=1)
        if len(a)<2:return
        t=a[1]
        await m.reply_text(f"🔤 <b>Text Tools</b>\nKata: {len(t.split())}\nKarakter: {len(t)}\n\n{t.upper()}")

    @app.on_message(filters.command("quiz", prefixes="."))
    async def quiz(_,m):
        if not await command_is_allowed(app,m,"quiz"): return
        topic=m.text.split(maxsplit=1)
        topic=topic[1] if len(topic)>1 else "pengetahuan umum"
        await m.reply_text(f"🧩 <b>Quiz</b>\nTopik: {topic}\n\nFitur quiz engine siap dikembangkan.")

    @app.on_message(filters.command("game", prefixes="."))
    async def game(_,m):
        if not await command_is_allowed(app,m,"game"): return
        await m.reply_text("🎮 <b>Game Center</b>\n\nGame aktif.")

    @app.on_message(filters.command("song", prefixes="."))
    async def song(_,m):
        if not await command_is_allowed(app,m,"song"): return
        a=m.text.split(maxsplit=1)
        if len(a)<2:return
        await m.reply_text(f"🎵 <b>{a[1]}</b>\n\nSong search provider belum dikonfigurasi.")

    @app.on_message(filters.command("movie", prefixes="."))
    async def movie(_,m):
        if not await command_is_allowed(app,m,"movie"): return
        a=m.text.split(maxsplit=1)
        if len(a)<2:return
        key=getattr(app.cfg,"tmdb_api_key","")
        if not key:return
        try:
            import aiohttp
            async with aiohttp.ClientSession() as s:
                async with s.get("https://api.themoviedb.org/3/search/multi",
                    params={"api_key":key,"query":a[1],"language":"id-ID"}) as r:
                    d=await r.json()
            x=(d.get("results") or [None])[0]
            if not x:return
            title=x.get("title") or x.get("name") or a[1]
            await m.reply_text(f"🎬 <b>{title}</b>\n\n{x.get('overview') or '-'}")
        except: return

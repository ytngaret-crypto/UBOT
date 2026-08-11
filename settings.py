from pyrogram import filters
from feature_defaults import DEFAULT_SETTINGS

def register_settings_handlers(app):
    async def owner(m):
        return bool(m.from_user and await app.db.get_role(m.from_user.id)=="owner")

    @app.on_message(filters.command("settings", prefixes="."))
    async def settings(_,m):
        if not await owner(m): return
        a=m.text.split()
        if len(a)==1:
            await m.reply_text("⚙️ <b>Settings</b>\n\n"+"\n".join(f"• <code>{x}</code>" for x in DEFAULT_SETTINGS))
            return
        f=a[1].lower()
        if f not in DEFAULT_SETTINGS:return
        d=dict(DEFAULT_SETTINGS[f]); d.update(await app.settings.all(m.chat.id,f))
        await m.reply_text(f"⚙️ <b>{f}</b>\n\n"+"\n".join(f"• <code>{k}</code> = <code>{v}</code>" for k,v in d.items()))

    @app.on_message(filters.command("set", prefixes="."))
    async def setv(_,m):
        if not await owner(m):return
        a=m.text.split(maxsplit=3)
        if len(a)<4:return
        f,k,v=a[1].lower(),a[2].lower(),a[3]
        if f not in DEFAULT_SETTINGS or k not in DEFAULT_SETTINGS[f]:return
        if v.lower() in ("on","true","yes"): val=True
        elif v.lower() in ("off","false","no"): val=False
        else:
            try: val=int(v)
            except: val=v
        await app.settings.set(m.chat.id,f,k,val)
        await m.reply_text(f"✅ <code>{f}.{k}</code> = <code>{val}</code>")

    for command, value in (("on",True),("off",False)):
        @app.on_message(filters.command(command, prefixes="."))
        async def toggle(_,m, value=value):
            if not await owner(m):return
            a=m.text.split()
            if len(a)!=2 or a[1].lower() not in DEFAULT_SETTINGS:return
            await app.settings.set(m.chat.id,a[1].lower(),"enabled",value)
            await m.reply_text(("✅ " if value else "🔒 ")+f"<b>{a[1]}</b> {'aktif' if value else 'nonaktif'}.")

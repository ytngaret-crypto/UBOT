from settings_store import SettingsStore
from handlers.settings import register_settings_handlers
import asyncio
import logging
import os

from pyrogram import Client, idle
from pyrogram.enums import ParseMode

from config import Config
from database import Database
from handlers.commands import register_handlers
from handlers.callbacks import register_callback_handlers
from handlers.message import register_message_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("UBot")


async def main():
    cfg = Config.from_env()
    db = Database(cfg.db_path)
    await db.init()

    if not cfg.api_id or not cfg.api_hash:
        raise RuntimeError("API_ID/API_HASH belum diisi di environment.")
    if not cfg.session_string:
        raise RuntimeError("SESSION_STRING belum diisi di environment.")
    if not cfg.owner_id:
        raise RuntimeError("OWNER_ID belum diisi di environment.")

    app = Client(

settings = SettingsStore(getattr(cfg, 'db_path', 'ubot.db'))
app.settings = settings
register_settings_handlers(app)
        "ubot",
        api_id=cfg.api_id,
        api_hash=cfg.api_hash,
        session_string=cfg.session_string,
        parse_mode=ParseMode.HTML,
        workdir=cfg.workdir,
        sleep_threshold=30,
    )

    app.cfg = cfg
    app.db = db

    await db.ensure_owner(cfg.owner_id)

    register_handlers(app)
    register_callback_handlers(app)
    register_message_handlers(app)

    log.info("Starting UBot...")
    await app.start()
    me = await app.get_me()
    log.info("Logged in as %s (%s)", me.first_name, me.id)

    await idle()
    await app.stop()
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())

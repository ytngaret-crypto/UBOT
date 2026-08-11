import json, sqlite3, asyncio

class SettingsStore:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init()

    def _conn(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init(self):
        with self._conn() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS feature_settings(
                chat_id INTEGER, feature TEXT, setting TEXT, value TEXT,
                PRIMARY KEY(chat_id,feature,setting))""")

    async def set(self, chat_id, feature, setting, value):
        def work():
            with self._conn() as c:
                c.execute("""INSERT INTO feature_settings VALUES(?,?,?,?)
                    ON CONFLICT(chat_id,feature,setting)
                    DO UPDATE SET value=excluded.value""",
                          (chat_id, feature, setting, json.dumps(value, ensure_ascii=False)))
        await asyncio.to_thread(work)

    async def get(self, chat_id, feature, setting, default=None):
        def work():
            with self._conn() as c:
                r=c.execute("""SELECT value FROM feature_settings
                    WHERE chat_id=? AND feature=? AND setting=?""",
                    (chat_id,feature,setting)).fetchone()
                return r
        r=await asyncio.to_thread(work)
        if not r: return default
        try: return json.loads(r[0])
        except: return r[0]

    async def all(self, chat_id, feature):
        def work():
            with self._conn() as c:
                return c.execute("""SELECT setting,value FROM feature_settings
                    WHERE chat_id=? AND feature=?""",(chat_id,feature)).fetchall()
        rows=await asyncio.to_thread(work)
        out={}
        for k,v in rows:
            try: out[k]=json.loads(v)
            except: out[k]=v
        return out

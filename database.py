import json
import sqlite3
import asyncio
from typing import Optional


class Database:
    def __init__(self, path):
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = asyncio.Lock()

    async def init(self):
        async with self.lock:
            self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                role TEXT NOT NULL DEFAULT 'member',
                enabled INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS permissions (
                scope_id INTEGER NOT NULL,
                feature TEXT NOT NULL,
                role TEXT NOT NULL,
                allowed INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(scope_id, feature, role)
            );
            CREATE TABLE IF NOT EXISTS settings (
                scope_id INTEGER NOT NULL,
                feature TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                PRIMARY KEY(scope_id, feature, key)
            );
            CREATE TABLE IF NOT EXISTS autoreplies (
                scope_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                response TEXT NOT NULL,
                mode TEXT NOT NULL DEFAULT 'contains',
                PRIMARY KEY(scope_id, keyword)
            );
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS group_targets (
                owner_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                label TEXT,
                PRIMARY KEY(owner_id, chat_id)
            );
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                plan TEXT,
                expires_at TEXT
            );
            CREATE TABLE IF NOT EXISTS game_scores (
                scope_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                name TEXT,
                xp INTEGER NOT NULL DEFAULT 0,
                points INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(scope_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS payment (
                owner_id INTEGER PRIMARY KEY,
                qris_file_id TEXT,
                bank TEXT,
                account_number TEXT,
                account_name TEXT,
                ewallet TEXT,
                ewallet_number TEXT,
                description TEXT
            );
            """)
            self.conn.commit()

    async def close(self):
        async with self.lock:
            self.conn.close()

    async def execute(self, sql, params=()):
        async with self.lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur

    async def fetchone(self, sql, params=()):
        async with self.lock:
            return self.conn.execute(sql, params).fetchone()

    async def fetchall(self, sql, params=()):
        async with self.lock:
            return self.conn.execute(sql, params).fetchall()

    async def ensure_owner(self, owner_id):
        await self.execute(
            "INSERT OR REPLACE INTO users(user_id, role, enabled) VALUES (?, 'owner', 1)",
            (owner_id,)
        )

    async def get_role(self, user_id):
        row = await self.fetchone("SELECT role FROM users WHERE user_id=?", (user_id,))
        return row["role"] if row else "member"

    async def set_role(self, user_id, role):
        await self.execute(
            "INSERT INTO users(user_id, role) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET role=excluded.role",
            (user_id, role)
        )

    async def set_permission(self, scope_id, feature, role, allowed):
        await self.execute(
            "INSERT INTO permissions(scope_id, feature, role, allowed) VALUES (?,?,?,?) "
            "ON CONFLICT(scope_id,feature,role) DO UPDATE SET allowed=excluded.allowed",
            (scope_id, feature, role, int(allowed))
        )

    async def permission(self, scope_id, feature, role):
        row = await self.fetchone(
            "SELECT allowed FROM permissions WHERE scope_id=? AND feature=? AND role=?",
            (scope_id, feature, role)
        )
        return bool(row["allowed"]) if row else False

    async def set_setting(self, scope_id, feature, key, value):
        await self.execute(
            "INSERT INTO settings(scope_id,feature,key,value) VALUES (?,?,?,?) "
            "ON CONFLICT(scope_id,feature,key) DO UPDATE SET value=excluded.value",
            (scope_id, feature, key, str(value))
        )

    async def get_setting(self, scope_id, feature, key, default=None):
        row = await self.fetchone(
            "SELECT value FROM settings WHERE scope_id=? AND feature=? AND key=?",
            (scope_id, feature, key)
        )
        return row["value"] if row else default

    async def list_settings(self, scope_id, feature):
        rows = await self.fetchall(
            "SELECT key,value FROM settings WHERE scope_id=? AND feature=?",
            (scope_id, feature)
        )
        return {r["key"]: r["value"] for r in rows}

    async def add_autoreply(self, scope_id, keyword, response, mode="contains"):
        await self.execute(
            "INSERT INTO autoreplies(scope_id,keyword,response,mode) VALUES (?,?,?,?) "
            "ON CONFLICT(scope_id,keyword) DO UPDATE SET response=excluded.response, mode=excluded.mode",
            (scope_id, keyword.lower(), response, mode)
        )

    async def del_autoreply(self, scope_id, keyword):
        await self.execute(
            "DELETE FROM autoreplies WHERE scope_id=? AND keyword=?",
            (scope_id, keyword.lower())
        )

    async def list_autoreplies(self, scope_id):
        return await self.fetchall(
            "SELECT keyword,response,mode FROM autoreplies WHERE scope_id=? ORDER BY keyword",
            (scope_id,)
        )

    async def find_autoreply(self, scope_id, text):
        rows = await self.fetchall(
            "SELECT keyword,response,mode FROM autoreplies WHERE scope_id=?",
            (scope_id,)
        )
        low = text.lower()
        for r in rows:
            if r["mode"] == "exact" and low.strip() == r["keyword"]:
                return r["response"]
            if r["mode"] == "contains" and r["keyword"] in low:
                return r["response"]
        return None

    async def set_payment(self, owner_id, **kwargs):
        fields = [
            "qris_file_id","bank","account_number","account_name",
            "ewallet","ewallet_number","description"
        ]
        current = await self.fetchone("SELECT * FROM payment WHERE owner_id=?", (owner_id,))
        data = {f: (current[f] if current else None) for f in fields}
        for f in fields:
            if f in kwargs and kwargs[f] is not None:
                data[f] = kwargs[f]
        await self.execute(
            "INSERT INTO payment(owner_id," + ",".join(fields) + ") VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT(owner_id) DO UPDATE SET " +
            ",".join(f"{f}=excluded.{f}" for f in fields),
            (owner_id, *[data[f] for f in fields])
        )

    async def get_payment(self, owner_id):
        return await self.fetchone("SELECT * FROM payment WHERE owner_id=?", (owner_id,))

    async def add_target(self, owner_id, chat_id, label=""):
        await self.execute(
            "INSERT OR REPLACE INTO group_targets(owner_id,chat_id,label) VALUES (?,?,?)",
            (owner_id, chat_id, label)
        )

    async def del_target(self, owner_id, chat_id):
        await self.execute(
            "DELETE FROM group_targets WHERE owner_id=? AND chat_id=?",
            (owner_id, chat_id)
        )

    async def targets(self, owner_id):
        return await self.fetchall(
            "SELECT chat_id,label FROM group_targets WHERE owner_id=? ORDER BY chat_id",
            (owner_id,)
        )

    async def score_add(self, scope_id, user_id, name, points=0, xp=0):
        await self.execute(
            "INSERT INTO game_scores(scope_id,user_id,name,xp,points) VALUES (?,?,?,?,?) "
            "ON CONFLICT(scope_id,user_id) DO UPDATE SET "
            "name=excluded.name, xp=xp+excluded.xp, points=points+excluded.points",
            (scope_id, user_id, name, xp, points)
        )

    async def leaderboard(self, scope_id, limit=10):
        return await self.fetchall(
            "SELECT user_id,name,xp,points FROM game_scores WHERE scope_id=? "
            "ORDER BY points DESC, xp DESC LIMIT ?",
            (scope_id, limit)
        )

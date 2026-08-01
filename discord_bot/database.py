from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id INTEGER PRIMARY KEY,
    timezone TEXT NOT NULL DEFAULT 'Asia/Seoul',
    welcome_channel_id INTEGER,
    welcome_message TEXT NOT NULL DEFAULT '환영합니다, {user}! **{server}**에 오신 것을 환영합니다.',
    leave_channel_id INTEGER,
    leave_message TEXT NOT NULL DEFAULT '**{username}**님이 서버를 떠났습니다.',
    autorole_id INTEGER,
    log_channel_id INTEGER,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scheduled_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    creator_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    mention_type TEXT NOT NULL DEFAULT 'none',
    mention_id INTEGER,
    schedule_kind TEXT NOT NULL,
    interval_seconds INTEGER,
    local_time TEXT,
    weekday INTEGER,
    timezone TEXT NOT NULL,
    next_run_at TEXT NOT NULL,
    last_run_at TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    failure_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scheduled_due
ON scheduled_messages(enabled, next_run_at);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    due_at TEXT NOT NULL,
    sent INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reminders_due
ON reminders(sent, due_at);

CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    moderator_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_warnings_user
ON warnings(guild_id, user_id);


CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    course TEXT NOT NULL,
    title TEXT NOT NULL,
    due_at TEXT NOT NULL,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_assignments_user_due
ON assignments(user_id, guild_id, status, due_at);

CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    course TEXT NOT NULL,
    title TEXT NOT NULL,
    exam_at TEXT NOT NULL,
    location TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_exams_user_date
ON exams(user_id, guild_id, exam_at);

CREATE TABLE IF NOT EXISTS timetable_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    course TEXT NOT NULL,
    weekday INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    location TEXT,
    professor TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_timetable_user_day
ON timetable_entries(user_id, guild_id, weekday, start_time);

CREATE TABLE IF NOT EXISTS ai_usage (
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    usage_date TEXT NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(user_id, guild_id, usage_date)
);
"""


class Database:
    """Small async wrapper around SQLite using one connection per operation."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._write_lock = asyncio.Lock()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=15000")
        return connection

    async def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        def _init() -> None:
            with self._connect() as connection:
                connection.executescript(SCHEMA)

        await asyncio.to_thread(_init)

    async def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        async with self._write_lock:
            return await asyncio.to_thread(self._execute_sync, sql, params)

    def _execute_sync(self, sql: str, params: Sequence[Any]) -> int:
        with self._connect() as connection:
            cursor = connection.execute(sql, params)
            connection.commit()
            return int(cursor.lastrowid)

    async def executemany(self, sql: str, params: Iterable[Sequence[Any]]) -> None:
        values = list(params)
        async with self._write_lock:
            await asyncio.to_thread(self._executemany_sync, sql, values)

    def _executemany_sync(self, sql: str, params: list[Sequence[Any]]) -> None:
        with self._connect() as connection:
            connection.executemany(sql, params)
            connection.commit()

    async def fetch_one(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
        return await asyncio.to_thread(self._fetch_one_sync, sql, params)

    def _fetch_one_sync(self, sql: str, params: Sequence[Any]) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute(sql, params).fetchone()

    async def fetch_all(self, sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
        return await asyncio.to_thread(self._fetch_all_sync, sql, params)

    def _fetch_all_sync(self, sql: str, params: Sequence[Any]) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return list(connection.execute(sql, params).fetchall())

    async def ensure_guild(self, guild_id: int) -> None:
        await self.execute(
            "INSERT OR IGNORE INTO guild_settings(guild_id) VALUES (?)",
            (guild_id,),
        )

    async def guild_timezone(self, guild_id: int) -> str:
        await self.ensure_guild(guild_id)
        row = await self.fetch_one(
            "SELECT timezone FROM guild_settings WHERE guild_id = ?", (guild_id,)
        )
        return str(row["timezone"]) if row else "Asia/Seoul"

    async def consume_ai_quota(
        self,
        *,
        user_id: int,
        guild_id: int,
        usage_date: str,
        limit: int,
    ) -> tuple[bool, int]:
        async with self._write_lock:
            return await asyncio.to_thread(
                self._consume_ai_quota_sync,
                user_id,
                guild_id,
                usage_date,
                limit,
            )

    def _consume_ai_quota_sync(
        self,
        user_id: int,
        guild_id: int,
        usage_date: str,
        limit: int,
    ) -> tuple[bool, int]:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT request_count FROM ai_usage
                WHERE user_id = ? AND guild_id = ? AND usage_date = ?
                """,
                (user_id, guild_id, usage_date),
            ).fetchone()
            current = int(row["request_count"]) if row else 0
            if limit > 0 and current >= limit:
                connection.rollback()
                return False, current
            new_count = current + 1
            connection.execute(
                """
                INSERT INTO ai_usage(user_id, guild_id, usage_date, request_count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id, usage_date)
                DO UPDATE SET request_count = excluded.request_count
                """,
                (user_id, guild_id, usage_date, new_count),
            )
            connection.commit()
            return True, new_count

    async def refund_ai_quota(
        self,
        *,
        user_id: int,
        guild_id: int,
        usage_date: str,
    ) -> None:
        await self.execute(
            """
            UPDATE ai_usage
            SET request_count = CASE WHEN request_count > 0 THEN request_count - 1 ELSE 0 END
            WHERE user_id = ? AND guild_id = ? AND usage_date = ?
            """,
            (user_id, guild_id, usage_date),
        )

    async def ai_usage_count(
        self,
        *,
        user_id: int,
        guild_id: int,
        usage_date: str,
    ) -> int:
        row = await self.fetch_one(
            """
            SELECT request_count FROM ai_usage
            WHERE user_id = ? AND guild_id = ? AND usage_date = ?
            """,
            (user_id, guild_id, usage_date),
        )
        return int(row["request_count"]) if row else 0


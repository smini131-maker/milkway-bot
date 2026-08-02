from __future__ import annotations

import asyncio
import re
import sqlite3
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import asyncpg


SQLITE_SCHEMA = """
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

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT PRIMARY KEY,
    timezone TEXT NOT NULL DEFAULT 'Asia/Seoul',
    welcome_channel_id BIGINT,
    welcome_message TEXT NOT NULL DEFAULT '환영합니다, {user}! **{server}**에 오신 것을 환영합니다.',
    leave_channel_id BIGINT,
    leave_message TEXT NOT NULL DEFAULT '**{username}**님이 서버를 떠났습니다.',
    autorole_id BIGINT,
    log_channel_id BIGINT,
    updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::TEXT)
);

CREATE TABLE IF NOT EXISTS scheduled_messages (
    id BIGSERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    creator_id BIGINT NOT NULL,
    message TEXT NOT NULL,
    mention_type TEXT NOT NULL DEFAULT 'none',
    mention_id BIGINT,
    schedule_kind TEXT NOT NULL,
    interval_seconds BIGINT,
    local_time TEXT,
    weekday INTEGER,
    timezone TEXT NOT NULL,
    next_run_at TEXT NOT NULL,
    last_run_at TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    failure_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::TEXT)
);

CREATE INDEX IF NOT EXISTS idx_scheduled_due
ON scheduled_messages(enabled, next_run_at);

CREATE TABLE IF NOT EXISTS reminders (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message TEXT NOT NULL,
    due_at TEXT NOT NULL,
    sent INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::TEXT)
);

CREATE INDEX IF NOT EXISTS idx_reminders_due
ON reminders(sent, due_at);

CREATE TABLE IF NOT EXISTS warnings (
    id BIGSERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    moderator_id BIGINT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::TEXT)
);

CREATE INDEX IF NOT EXISTS idx_warnings_user
ON warnings(guild_id, user_id);

CREATE TABLE IF NOT EXISTS assignments (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    course TEXT NOT NULL,
    title TEXT NOT NULL,
    due_at TEXT NOT NULL,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::TEXT),
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_assignments_user_due
ON assignments(user_id, guild_id, status, due_at);

CREATE TABLE IF NOT EXISTS exams (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    course TEXT NOT NULL,
    title TEXT NOT NULL,
    exam_at TEXT NOT NULL,
    location TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::TEXT)
);

CREATE INDEX IF NOT EXISTS idx_exams_user_date
ON exams(user_id, guild_id, exam_at);

CREATE TABLE IF NOT EXISTS timetable_entries (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    course TEXT NOT NULL,
    weekday INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    location TEXT,
    professor TEXT,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::TEXT)
);

CREATE INDEX IF NOT EXISTS idx_timetable_user_day
ON timetable_entries(user_id, guild_id, weekday, start_time);

CREATE TABLE IF NOT EXISTS ai_usage (
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    usage_date TEXT NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(user_id, guild_id, usage_date)
);
"""

_ID_TABLES = {
    "scheduled_messages",
    "reminders",
    "warnings",
    "assignments",
    "exams",
    "timetable_entries",
}
_INSERT_TABLE_RE = re.compile(r"^\s*INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE)


def _postgres_placeholders(sql: str) -> str:
    index = 0

    def replacement(_: re.Match[str]) -> str:
        nonlocal index
        index += 1
        return f"${index}"

    converted = re.sub(r"\?", replacement, sql)
    return re.sub(
        r"CURRENT_TIMESTAMP(?!\s*::)",
        "(CURRENT_TIMESTAMP::TEXT)",
        converted,
        flags=re.IGNORECASE,
    )


def _insert_table(sql: str) -> str | None:
    match = _INSERT_TABLE_RE.match(sql)
    return match.group(1).lower() if match else None


class Database:
    """Async database wrapper using SQLite locally or PostgreSQL when DATABASE_URL is set."""

    def __init__(self, path: Path, url: str | None = None) -> None:
        self.path = path
        self.url = (url or "").strip() or None
        self._write_lock = asyncio.Lock()
        self._pool: asyncpg.Pool | None = None

    @property
    def backend(self) -> str:
        return "postgresql" if self.url else "sqlite"

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=15000")
        return connection

    async def initialize(self) -> None:
        if self.url:
            self._pool = await asyncpg.create_pool(
                dsn=self.url,
                min_size=1,
                max_size=3,
                command_timeout=30,
            )
            async with self._pool.acquire() as connection:
                for statement in POSTGRES_SCHEMA.split(";"):
                    cleaned = statement.strip()
                    if cleaned:
                        await connection.execute(cleaned)
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)

        def _init() -> None:
            with self._connect() as connection:
                connection.executescript(SQLITE_SCHEMA)

        await asyncio.to_thread(_init)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("PostgreSQL 연결 풀이 초기화되지 않았습니다.")
        return self._pool

    async def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        if self.url:
            async with self._write_lock:
                pool = self._require_pool()
                async with pool.acquire() as connection:
                    query = _postgres_placeholders(sql).strip().rstrip(";")
                    table = _insert_table(query)
                    if table in _ID_TABLES and "RETURNING" not in query.upper():
                        row = await connection.fetchrow(f"{query} RETURNING id", *params)
                        return int(row["id"]) if row else 0
                    await connection.execute(query, *params)
                    return 0

        async with self._write_lock:
            return await asyncio.to_thread(self._execute_sync, sql, params)

    def _execute_sync(self, sql: str, params: Sequence[Any]) -> int:
        with self._connect() as connection:
            cursor = connection.execute(sql, params)
            connection.commit()
            return int(cursor.lastrowid)

    async def executemany(self, sql: str, params: Iterable[Sequence[Any]]) -> None:
        values = list(params)
        if not values:
            return
        if self.url:
            async with self._write_lock:
                pool = self._require_pool()
                async with pool.acquire() as connection:
                    await connection.executemany(_postgres_placeholders(sql), values)
            return

        async with self._write_lock:
            await asyncio.to_thread(self._executemany_sync, sql, values)

    def _executemany_sync(self, sql: str, params: list[Sequence[Any]]) -> None:
        with self._connect() as connection:
            connection.executemany(sql, params)
            connection.commit()

    async def fetch_one(self, sql: str, params: Sequence[Any] = ()) -> Any | None:
        if self.url:
            pool = self._require_pool()
            async with pool.acquire() as connection:
                return await connection.fetchrow(_postgres_placeholders(sql), *params)
        return await asyncio.to_thread(self._fetch_one_sync, sql, params)

    def _fetch_one_sync(self, sql: str, params: Sequence[Any]) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute(sql, params).fetchone()

    async def fetch_all(self, sql: str, params: Sequence[Any] = ()) -> list[Any]:
        if self.url:
            pool = self._require_pool()
            async with pool.acquire() as connection:
                return list(await connection.fetch(_postgres_placeholders(sql), *params))
        return await asyncio.to_thread(self._fetch_all_sync, sql, params)

    def _fetch_all_sync(self, sql: str, params: Sequence[Any]) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return list(connection.execute(sql, params).fetchall())

    async def ensure_guild(self, guild_id: int) -> None:
        await self.execute(
            """
            INSERT INTO guild_settings(guild_id) VALUES (?)
            ON CONFLICT(guild_id) DO NOTHING
            """,
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
        if self.url:
            async with self._write_lock:
                pool = self._require_pool()
                async with pool.acquire() as connection:
                    async with connection.transaction():
                        row = await connection.fetchrow(
                            """
                            SELECT request_count FROM ai_usage
                            WHERE user_id = $1 AND guild_id = $2 AND usage_date = $3
                            FOR UPDATE
                            """,
                            user_id,
                            guild_id,
                            usage_date,
                        )
                        current = int(row["request_count"]) if row else 0
                        if limit > 0 and current >= limit:
                            return False, current
                        new_count = current + 1
                        await connection.execute(
                            """
                            INSERT INTO ai_usage(user_id, guild_id, usage_date, request_count)
                            VALUES ($1, $2, $3, $4)
                            ON CONFLICT(user_id, guild_id, usage_date)
                            DO UPDATE SET request_count = EXCLUDED.request_count
                            """,
                            user_id,
                            guild_id,
                            usage_date,
                            new_count,
                        )
                        return True, new_count

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

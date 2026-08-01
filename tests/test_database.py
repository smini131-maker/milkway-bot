import asyncio
from pathlib import Path

from discord_bot.database import Database


def test_database_initialization_and_guild_defaults(tmp_path: Path) -> None:
    async def scenario() -> None:
        db = Database(tmp_path / "bot.db")
        await db.initialize()
        await db.ensure_guild(123)
        assert await db.guild_timezone(123) == "Asia/Seoul"
        await db.execute(
            "UPDATE guild_settings SET timezone = ? WHERE guild_id = ?",
            ("UTC", 123),
        )
        assert await db.guild_timezone(123) == "UTC"

    asyncio.run(scenario())


def test_database_insert_and_fetch(tmp_path: Path) -> None:
    async def scenario() -> None:
        db = Database(tmp_path / "bot.db")
        await db.initialize()
        reminder_id = await db.execute(
            """
            INSERT INTO reminders(user_id, guild_id, channel_id, message, due_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (1, 2, 3, "test", "2026-08-01T00:00:00+00:00"),
        )
        row = await db.fetch_one("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
        assert row is not None
        assert row["message"] == "test"

    asyncio.run(scenario())


def test_ai_quota_is_atomic_and_refundable(tmp_path: Path) -> None:
    async def scenario() -> None:
        db = Database(tmp_path / "bot.db")
        await db.initialize()
        allowed, used = await db.consume_ai_quota(
            user_id=1, guild_id=2, usage_date="2026-08-01", limit=2
        )
        assert allowed is True and used == 1
        allowed, used = await db.consume_ai_quota(
            user_id=1, guild_id=2, usage_date="2026-08-01", limit=2
        )
        assert allowed is True and used == 2
        allowed, used = await db.consume_ai_quota(
            user_id=1, guild_id=2, usage_date="2026-08-01", limit=2
        )
        assert allowed is False and used == 2
        await db.refund_ai_quota(user_id=1, guild_id=2, usage_date="2026-08-01")
        assert await db.ai_usage_count(
            user_id=1, guild_id=2, usage_date="2026-08-01"
        ) == 1

    asyncio.run(scenario())


def test_ai_quota_zero_is_unlimited_and_counted(tmp_path: Path) -> None:
    async def scenario() -> None:
        db = Database(tmp_path / "bot.db")
        await db.initialize()
        for expected in range(1, 4):
            allowed, used = await db.consume_ai_quota(
                user_id=5, guild_id=6, usage_date="2026-08-01", limit=0
            )
            assert allowed is True
            assert used == expected

    asyncio.run(scenario())


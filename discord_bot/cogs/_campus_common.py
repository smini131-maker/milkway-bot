from __future__ import annotations

import discord
from discord.ext import commands

from discord_bot.utils.timeparse import parse_duration, to_iso, utc_now

_WEEKDAY_LABELS = ("월", "화", "수", "목", "금", "토", "일")


def _clean(value: str, *, label: str, maximum: int) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label}을(를) 입력하세요.")
    if len(cleaned) > maximum:
        raise ValueError(f"{label}은(는) {maximum}자 이하로 입력하세요.")
    return cleaned


async def _guild_timezone(bot: commands.Bot, guild_id: int) -> str:
    return await bot.db.guild_timezone(guild_id)


async def _optional_reminder(
    bot: commands.Bot,
    interaction: discord.Interaction,
    *,
    due_at,
    remind_before: str | None,
    message: str,
) -> int | None:
    if not remind_before:
        return None
    delta = parse_duration(remind_before)
    reminder_at = due_at - delta
    if reminder_at <= utc_now():
        raise ValueError("미리 알림 시각이 이미 지났습니다. 더 짧은 시간을 입력하세요.")
    return await bot.db.execute(
        """
        INSERT INTO reminders(user_id, guild_id, channel_id, message, due_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            interaction.user.id,
            interaction.guild_id,
            interaction.channel_id,
            message[:1700],
            to_iso(reminder_at),
        ),
    )

from __future__ import annotations

from datetime import timedelta  # noqa: F401
from typing import Literal  # noqa: F401

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.cogs._campus_common import (  # noqa: F401
    _WEEKDAY_LABELS,
    _clean,
    _guild_timezone,
    _optional_reminder,
)
from discord_bot.utils.academic import (  # noqa: F401
    calculate_gpa,
    required_future_gpa,
    split_teams,
)
from discord_bot.utils.timeparse import (  # noqa: F401
    from_iso,
    get_timezone,
    parse_clock,
    parse_duration,
    parse_local_datetime,
    parse_weekday,
    to_iso,
    utc_now,
)

class TimetableCog(
    commands.GroupCog,
    group_name="timetable",
    group_description="개인 시간표를 관리합니다.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage
        return True

    @app_commands.command(name="add", description="시간표에 강의를 추가합니다.")
    @app_commands.describe(weekday="월~일", start="HH:MM", end="HH:MM")
    async def add(
        self,
        interaction: discord.Interaction,
        course: str,
        weekday: str,
        start: str,
        end: str,
        location: str | None = None,
        professor: str | None = None,
    ) -> None:
        day = parse_weekday(weekday)
        start_hm = parse_clock(start)
        end_hm = parse_clock(end)
        start_norm = f"{start_hm[0]:02d}:{start_hm[1]:02d}"
        end_norm = f"{end_hm[0]:02d}:{end_hm[1]:02d}"
        if end_norm <= start_norm:
            raise ValueError("종료 시각은 시작 시각보다 늦어야 합니다.")
        course = _clean(course, label="과목명", maximum=80)
        overlap = await self.bot.db.fetch_one(
            """
            SELECT id, course FROM timetable_entries
            WHERE user_id = ? AND guild_id = ? AND weekday = ?
              AND start_time < ? AND end_time > ?
            LIMIT 1
            """,
            (interaction.user.id, interaction.guild_id, day, end_norm, start_norm),
        )
        if overlap:
            raise ValueError(f"기존 강의 `#{overlap['id']} {overlap['course']}`와 시간이 겹칩니다.")
        entry_id = await self.bot.db.execute(
            """
            INSERT INTO timetable_entries(
                user_id, guild_id, course, weekday, start_time, end_time, location, professor
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.user.id,
                interaction.guild_id,
                course,
                day,
                start_norm,
                end_norm,
                location.strip()[:120] if location and location.strip() else None,
                professor.strip()[:80] if professor and professor.strip() else None,
            ),
        )
        await interaction.response.send_message(
            f"강의 `#{entry_id}` 추가: **{course}** · {_WEEKDAY_LABELS[day]} {start_norm}~{end_norm}",
            ephemeral=True,
        )

    async def _show(self, interaction: discord.Interaction, weekday: int | None) -> None:
        where = "AND weekday = ?" if weekday is not None else ""
        params = (
            (interaction.user.id, interaction.guild_id, weekday)
            if weekday is not None
            else (interaction.user.id, interaction.guild_id)
        )
        rows = await self.bot.db.fetch_all(
            f"""
            SELECT * FROM timetable_entries
            WHERE user_id = ? AND guild_id = ? {where}
            ORDER BY weekday ASC, start_time ASC
            """,
            params,
        )
        if not rows:
            await interaction.response.send_message("등록된 강의가 없습니다.", ephemeral=True)
            return
        grouped: dict[int, list[str]] = {}
        for row in rows:
            detail = f"`#{row['id']}` {row['start_time']}~{row['end_time']} **{row['course']}**"
            if row["location"]:
                detail += f" · {row['location']}"
            if row["professor"]:
                detail += f" · {row['professor']} 교수"
            grouped.setdefault(int(row["weekday"]), []).append(detail)
        embed = discord.Embed(title="🗓️ 내 시간표", color=discord.Color.blue())
        for day, entries in grouped.items():
            embed.add_field(
                name=f"{_WEEKDAY_LABELS[day]}요일",
                value="\n".join(entries)[:1024],
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="today", description="오늘 시간표를 확인합니다.")
    async def today(self, interaction: discord.Interaction) -> None:
        timezone_name = await _guild_timezone(self.bot, interaction.guild_id)
        weekday = utc_now().astimezone(get_timezone(timezone_name)).weekday()
        await self._show(interaction, weekday)

    @app_commands.command(name="week", description="주간 시간표를 확인합니다.")
    async def week(self, interaction: discord.Interaction) -> None:
        await self._show(interaction, None)

    @app_commands.command(name="delete", description="시간표에서 강의를 삭제합니다.")
    async def delete(self, interaction: discord.Interaction, entry_id: int) -> None:
        row = await self.bot.db.fetch_one(
            "SELECT id FROM timetable_entries WHERE id = ? AND user_id = ? AND guild_id = ?",
            (entry_id, interaction.user.id, interaction.guild_id),
        )
        if row is None:
            raise ValueError("내 시간표에서 해당 번호를 찾지 못했습니다.")
        await self.bot.db.execute("DELETE FROM timetable_entries WHERE id = ?", (entry_id,))
        await interaction.response.send_message(f"강의 `#{entry_id}`을 삭제했습니다.", ephemeral=True)

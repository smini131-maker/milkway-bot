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

class AttendanceCog(
    commands.GroupCog,
    group_name="attendance",
    group_description="과목별 출석을 간단히 기록합니다.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage
        return True

    @app_commands.command(name="record", description="출석·지각·결석을 한 건 기록합니다.")
    async def record(
        self,
        interaction: discord.Interaction,
        course: str,
        status: Literal["출석", "지각", "결석"],
    ) -> None:
        course = _clean(course, label="과목명", maximum=80)
        column = {"출석": "attended", "지각": "late", "결석": "absent"}[status]
        await self.bot.db.execute(
            f"""
            INSERT INTO attendance_records(user_id, guild_id, course, {column})
            VALUES (?, ?, ?, 1)
            ON CONFLICT(user_id, guild_id, course)
            DO UPDATE SET {column} = {column} + 1, updated_at = CURRENT_TIMESTAMP
            """,
            (interaction.user.id, interaction.guild_id, course),
        )
        await interaction.response.send_message(f"**{course}**에 `{status}` 1회를 기록했습니다.", ephemeral=True)

    @app_commands.command(name="status", description="과목별 출석 현황을 확인합니다.")
    async def status(self, interaction: discord.Interaction, course: str | None = None) -> None:
        if course:
            rows = await self.bot.db.fetch_all(
                """
                SELECT * FROM attendance_records
                WHERE user_id = ? AND guild_id = ? AND course = ?
                """,
                (interaction.user.id, interaction.guild_id, course.strip()),
            )
        else:
            rows = await self.bot.db.fetch_all(
                """
                SELECT * FROM attendance_records
                WHERE user_id = ? AND guild_id = ? ORDER BY course
                """,
                (interaction.user.id, interaction.guild_id),
            )
        if not rows:
            await interaction.response.send_message("출석 기록이 없습니다.", ephemeral=True)
            return
        lines = []
        for row in rows:
            total = int(row["attended"]) + int(row["late"]) + int(row["absent"])
            absence_rate = (int(row["absent"]) / total * 100) if total else 0
            lines.append(
                f"**{row['course']}** · 출석 {row['attended']} / 지각 {row['late']} / 결석 {row['absent']} "
                f"(결석률 {absence_rate:.1f}%)"
            )
        await interaction.response.send_message(
            embed=discord.Embed(
                title="📋 출석 현황",
                description="\n".join(lines)[:4000],
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )

    @app_commands.command(name="reset", description="한 과목의 출석 기록을 초기화합니다.")
    async def reset(self, interaction: discord.Interaction, course: str) -> None:
        row = await self.bot.db.fetch_one(
            """
            SELECT course FROM attendance_records
            WHERE user_id = ? AND guild_id = ? AND course = ?
            """,
            (interaction.user.id, interaction.guild_id, course.strip()),
        )
        if row is None:
            raise ValueError("해당 과목의 출석 기록이 없습니다.")
        await self.bot.db.execute(
            "DELETE FROM attendance_records WHERE user_id = ? AND guild_id = ? AND course = ?",
            (interaction.user.id, interaction.guild_id, course.strip()),
        )
        await interaction.response.send_message(f"**{course.strip()}** 출석 기록을 초기화했습니다.", ephemeral=True)

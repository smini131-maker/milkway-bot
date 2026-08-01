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

class ExamCog(
    commands.GroupCog,
    group_name="exam",
    group_description="시험 일정을 관리합니다.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage
        return True

    @app_commands.command(name="add", description="시험 일정을 등록합니다.")
    @app_commands.describe(
        when="YYYY-MM-DD HH:MM",
        remind_before="미리 알림: 1h, 1d, 1w",
    )
    async def add(
        self,
        interaction: discord.Interaction,
        course: str,
        title: str,
        when: str,
        location: str | None = None,
        notes: str | None = None,
        remind_before: str | None = "1d",
    ) -> None:
        timezone_name = await _guild_timezone(self.bot, interaction.guild_id)
        exam_at = parse_local_datetime(when, timezone_name)
        if exam_at <= utc_now().astimezone(exam_at.tzinfo):
            raise ValueError("시험 시각은 현재보다 미래여야 합니다.")
        course = _clean(course, label="과목명", maximum=80)
        title = _clean(title, label="시험명", maximum=150)
        location = location.strip()[:120] if location and location.strip() else None
        notes = notes.strip()[:1000] if notes and notes.strip() else None
        if remind_before:
            reminder_at = exam_at - parse_duration(remind_before)
            if reminder_at <= utc_now():
                raise ValueError("미리 알림 시각이 이미 지났습니다. 더 짧은 시간을 입력하세요.")
        exam_id = await self.bot.db.execute(
            """
            INSERT INTO exams(user_id, guild_id, channel_id, course, title, exam_at, location, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.user.id,
                interaction.guild_id,
                interaction.channel_id,
                course,
                title,
                to_iso(exam_at),
                location,
                notes,
            ),
        )
        reminder_id = await _optional_reminder(
            self.bot,
            interaction,
            due_at=exam_at,
            remind_before=remind_before,
            message=f"🧪 시험 임박 · {course} — {title}\n시험: <t:{int(exam_at.timestamp())}:F>",
        )
        reminder_text = f" · 리마인더 `#{reminder_id}`" if reminder_id else ""
        await interaction.response.send_message(
            f"시험 `#{exam_id}` 등록 완료{reminder_text}\n"
            f"**{course} — {title}** · <t:{int(exam_at.timestamp())}:F>",
            ephemeral=True,
        )

    @app_commands.command(name="list", description="다가오는 시험을 확인합니다.")
    async def list_exams(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.fetch_all(
            """
            SELECT * FROM exams
            WHERE user_id = ? AND guild_id = ? AND exam_at >= ?
            ORDER BY exam_at ASC LIMIT 25
            """,
            (interaction.user.id, interaction.guild_id, to_iso(utc_now())),
        )
        if not rows:
            await interaction.response.send_message("다가오는 시험이 없습니다.", ephemeral=True)
            return
        lines = []
        for row in rows:
            exam_at = from_iso(row["exam_at"])
            location = f" · {row['location']}" if row["location"] else ""
            lines.append(
                f"🧪 `#{row['id']}` **{row['course']} — {row['title']}**{location}\n"
                f"　<t:{int(exam_at.timestamp())}:F> · <t:{int(exam_at.timestamp())}:R>"
            )
        embed = discord.Embed(
            title="다가오는 시험",
            description="\n\n".join(lines)[:4000],
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="delete", description="시험 일정을 삭제합니다.")
    async def delete(self, interaction: discord.Interaction, exam_id: int) -> None:
        row = await self.bot.db.fetch_one(
            "SELECT id FROM exams WHERE id = ? AND user_id = ? AND guild_id = ?",
            (exam_id, interaction.user.id, interaction.guild_id),
        )
        if row is None:
            raise ValueError("내 시험 목록에서 해당 번호를 찾지 못했습니다.")
        await self.bot.db.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
        await interaction.response.send_message(f"시험 `#{exam_id}`을 삭제했습니다.", ephemeral=True)

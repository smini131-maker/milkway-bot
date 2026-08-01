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

class AssignmentCog(
    commands.GroupCog,
    group_name="assignment",
    group_description="개인 과제와 제출 기한을 관리합니다.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage
        return True

    @app_commands.command(name="add", description="과제와 제출 기한을 등록합니다.")
    @app_commands.describe(
        course="과목명",
        title="과제명",
        due="YYYY-MM-DD HH:MM",
        notes="메모 또는 제출 방식",
        remind_before="미리 알림: 30m, 1d, 1w",
    )
    async def add(
        self,
        interaction: discord.Interaction,
        course: str,
        title: str,
        due: str,
        notes: str | None = None,
        remind_before: str | None = "1d",
    ) -> None:
        timezone_name = await _guild_timezone(self.bot, interaction.guild_id)
        due_at = parse_local_datetime(due, timezone_name)
        if due_at <= utc_now().astimezone(due_at.tzinfo):
            raise ValueError("제출 기한은 현재보다 미래여야 합니다.")
        course = _clean(course, label="과목명", maximum=80)
        title = _clean(title, label="과제명", maximum=150)
        notes = notes.strip()[:1000] if notes and notes.strip() else None
        if remind_before:
            reminder_at = due_at - parse_duration(remind_before)
            if reminder_at <= utc_now():
                raise ValueError("미리 알림 시각이 이미 지났습니다. 더 짧은 시간을 입력하세요.")

        assignment_id = await self.bot.db.execute(
            """
            INSERT INTO assignments(user_id, guild_id, channel_id, course, title, due_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.user.id,
                interaction.guild_id,
                interaction.channel_id,
                course,
                title,
                to_iso(due_at),
                notes,
            ),
        )
        reminder_id = await _optional_reminder(
            self.bot,
            interaction,
            due_at=due_at,
            remind_before=remind_before,
            message=f"📚 과제 마감 임박 · {course} — {title}\n마감: <t:{int(due_at.timestamp())}:F>",
        )
        reminder_text = f" · 리마인더 `#{reminder_id}`" if reminder_id else ""
        await interaction.response.send_message(
            f"과제 `#{assignment_id}` 등록 완료{reminder_text}\n"
            f"**{course} — {title}** · <t:{int(due_at.timestamp())}:F>",
            ephemeral=True,
        )

    @app_commands.command(name="list", description="내 과제 목록을 마감순으로 확인합니다.")
    async def list_assignments(
        self,
        interaction: discord.Interaction,
        include_completed: bool = False,
    ) -> None:
        status_sql = "" if include_completed else "AND status = 'pending'"
        rows = await self.bot.db.fetch_all(
            f"""
            SELECT * FROM assignments
            WHERE user_id = ? AND guild_id = ? {status_sql}
            ORDER BY CASE status WHEN 'pending' THEN 0 ELSE 1 END, due_at ASC
            LIMIT 30
            """,
            (interaction.user.id, interaction.guild_id),
        )
        if not rows:
            await interaction.response.send_message("등록된 과제가 없습니다.", ephemeral=True)
            return
        lines: list[str] = []
        for row in rows:
            due_at = from_iso(row["due_at"])
            icon = "✅" if row["status"] == "completed" else ("🚨" if due_at < utc_now() else "📝")
            lines.append(
                f"{icon} `#{row['id']}` **{row['course']}** · {row['title']}\n"
                f"　<t:{int(due_at.timestamp())}:F> · <t:{int(due_at.timestamp())}:R>"
            )
        embed = discord.Embed(
            title="📚 내 과제",
            description="\n\n".join(lines)[:4000],
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _owned(self, interaction: discord.Interaction, assignment_id: int):
        row = await self.bot.db.fetch_one(
            "SELECT * FROM assignments WHERE id = ? AND user_id = ? AND guild_id = ?",
            (assignment_id, interaction.user.id, interaction.guild_id),
        )
        if row is None:
            raise ValueError("내 과제 목록에서 해당 번호를 찾지 못했습니다.")
        return row

    @app_commands.command(name="done", description="과제를 완료 처리합니다.")
    async def done(self, interaction: discord.Interaction, assignment_id: int) -> None:
        await self._owned(interaction, assignment_id)
        await self.bot.db.execute(
            """
            UPDATE assignments
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (assignment_id,),
        )
        await interaction.response.send_message(
            f"과제 `#{assignment_id}`을 완료 처리했습니다. 🎉", ephemeral=True
        )

    @app_commands.command(name="reopen", description="완료한 과제를 다시 진행 중으로 돌립니다.")
    async def reopen(self, interaction: discord.Interaction, assignment_id: int) -> None:
        await self._owned(interaction, assignment_id)
        await self.bot.db.execute(
            "UPDATE assignments SET status = 'pending', completed_at = NULL WHERE id = ?",
            (assignment_id,),
        )
        await interaction.response.send_message(
            f"과제 `#{assignment_id}`을 다시 진행 중으로 변경했습니다.", ephemeral=True
        )

    @app_commands.command(name="delete", description="과제를 삭제합니다.")
    async def delete(self, interaction: discord.Interaction, assignment_id: int) -> None:
        await self._owned(interaction, assignment_id)
        await self.bot.db.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))
        await interaction.response.send_message(
            f"과제 `#{assignment_id}`을 삭제했습니다.", ephemeral=True
        )

    @app_commands.command(name="clear_completed", description="완료한 과제를 모두 정리합니다.")
    async def clear_completed(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.fetch_all(
            "SELECT id FROM assignments WHERE user_id = ? AND guild_id = ? AND status = 'completed'",
            (interaction.user.id, interaction.guild_id),
        )
        if not rows:
            await interaction.response.send_message("정리할 완료 과제가 없습니다.", ephemeral=True)
            return
        await self.bot.db.execute(
            "DELETE FROM assignments WHERE user_id = ? AND guild_id = ? AND status = 'completed'",
            (interaction.user.id, interaction.guild_id),
        )
        await interaction.response.send_message(
            f"완료 과제 {len(rows)}개를 정리했습니다.", ephemeral=True
        )

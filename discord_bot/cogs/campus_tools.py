from __future__ import annotations

from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.cogs._campus_common import _guild_timezone
from discord_bot.utils.academic import calculate_gpa
from discord_bot.utils.timeparse import from_iso, get_timezone, to_iso, utc_now


class CampusCog(
    commands.GroupCog,
    group_name="대학생",
    group_description="대학생활에 유용한 간단한 도구입니다.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage
        return True

    @app_commands.command(name="한눈에", description="오늘 강의와 가까운 과제·시험을 한 번에 확인합니다.")
    async def dashboard(self, interaction: discord.Interaction) -> None:
        timezone_name = await _guild_timezone(self.bot, interaction.guild_id)
        today = utc_now().astimezone(get_timezone(timezone_name)).weekday()
        classes = await self.bot.db.fetch_all(
            """
            SELECT * FROM timetable_entries
            WHERE user_id = ? AND guild_id = ? AND weekday = ?
            ORDER BY start_time LIMIT 10
            """,
            (interaction.user.id, interaction.guild_id, today),
        )
        assignments = await self.bot.db.fetch_all(
            """
            SELECT * FROM assignments
            WHERE user_id = ? AND guild_id = ? AND status = 'pending'
            ORDER BY due_at LIMIT 5
            """,
            (interaction.user.id, interaction.guild_id),
        )
        exams = await self.bot.db.fetch_all(
            """
            SELECT * FROM exams
            WHERE user_id = ? AND guild_id = ? AND exam_at >= ?
            ORDER BY exam_at LIMIT 5
            """,
            (interaction.user.id, interaction.guild_id, to_iso(utc_now())),
        )
        embed = discord.Embed(
            title=f"🎓 {interaction.user.display_name}의 대학생활",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow(),
        )
        class_lines = [
            f"{row['start_time']}~{row['end_time']} **{row['course']}**"
            + (f" · {row['location']}" if row["location"] else "")
            for row in classes
        ]
        assignment_lines = [
            f"`#{row['id']}` **{row['course']}** {row['title']} · <t:{int(from_iso(row['due_at']).timestamp())}:R>"
            for row in assignments
        ]
        exam_lines = [
            f"`#{row['id']}` **{row['course']}** {row['title']} · <t:{int(from_iso(row['exam_at']).timestamp())}:R>"
            for row in exams
        ]
        embed.add_field(name="오늘 강의", value="\n".join(class_lines) or "없음", inline=False)
        embed.add_field(name="가까운 과제", value="\n".join(assignment_lines) or "없음", inline=False)
        embed.add_field(name="다가오는 시험", value="\n".join(exam_lines) or "없음", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="학점", description="4.5 만점 기준 평균평점을 계산합니다.")
    @app_commands.rename(grades="성적")
    @app_commands.describe(grades="예: 자료구조=3:A+, 교양=2:B0, 영어=2:A0")
    async def gpa(self, interaction: discord.Interaction, grades: str) -> None:
        result = calculate_gpa(grades)
        lines = [
            f"{entry.name}: {entry.credits}학점 × {entry.grade}({entry.points})"
            for entry in result.entries
        ]
        embed = discord.Embed(
            title=f"📊 평균평점 {result.gpa} / 4.5",
            description="\n".join(lines)[:3500],
            color=discord.Color.teal(),
        )
        embed.add_field(name="총 이수학점", value=str(result.total_credits))
        embed.add_field(name="총 평점합", value=str(result.total_points))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="집중", description="포모도로 집중·휴식 알림을 등록합니다.")
    @app_commands.rename(focus_minutes="집중분", break_minutes="휴식분", cycles="횟수")
    async def pomodoro(
        self,
        interaction: discord.Interaction,
        focus_minutes: app_commands.Range[int, 10, 120] = 25,
        break_minutes: app_commands.Range[int, 1, 60] = 5,
        cycles: app_commands.Range[int, 1, 8] = 4,
    ) -> None:
        cursor = utc_now()
        reminder_ids: list[int] = []
        for cycle in range(1, cycles + 1):
            cursor += timedelta(minutes=focus_minutes)
            reminder_ids.append(
                await self.bot.db.execute(
                    """
                    INSERT INTO reminders(user_id, guild_id, channel_id, message, due_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        interaction.user.id,
                        interaction.guild_id,
                        interaction.channel_id,
                        f"🍅 집중 {cycle}/{cycles} 종료! "
                        + ("전체 세션 완료 🎉" if cycle == cycles else f"{break_minutes}분 쉬세요."),
                        to_iso(cursor),
                    ),
                )
            )
            if cycle < cycles:
                cursor += timedelta(minutes=break_minutes)
                reminder_ids.append(
                    await self.bot.db.execute(
                        """
                        INSERT INTO reminders(user_id, guild_id, channel_id, message, due_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            interaction.user.id,
                            interaction.guild_id,
                            interaction.channel_id,
                            f"📚 휴식 종료! 집중 {cycle + 1}/{cycles}을 시작하세요.",
                            to_iso(cursor),
                        ),
                    )
                )
        await interaction.response.send_message(
            f"🍅 {focus_minutes}분 집중 + {break_minutes}분 휴식 × {cycles}회 알림을 등록했습니다.\n"
            f"예상 종료: <t:{int(cursor.timestamp())}:F> · 알림 {len(reminder_ids)}개",
            ephemeral=True,
        )

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

class CampusCog(
    commands.GroupCog,
    group_name="campus",
    group_description="대학생활에 유용한 도구를 제공합니다.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage
        return True

    @app_commands.command(name="dashboard", description="오늘 강의와 가까운 과제·시험을 한 번에 확인합니다.")
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
            title=f"🎓 {interaction.user.display_name}의 대학생활 대시보드",
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

    @app_commands.command(name="gpa", description="4.5 만점 기준 가중 평균평점을 계산합니다.")
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

    @app_commands.command(name="target_gpa", description="목표 누적평점에 필요한 향후 평균을 계산합니다.")
    async def target_gpa(
        self,
        interaction: discord.Interaction,
        current_credits: float,
        current_gpa: float,
        future_credits: float,
        target_gpa: float,
    ) -> None:
        required = required_future_gpa(
            current_credits=current_credits,
            current_gpa=current_gpa,
            future_credits=future_credits,
            target_gpa=target_gpa,
        )
        if required > 4.5:
            message = f"필요 평균은 **{required} / 4.5**로, 설정한 학점 범위에서는 달성할 수 없습니다."
        elif required <= 0:
            message = "앞으로 F를 받지 않는 한 이미 목표 누적평점을 충족할 수 있는 범위입니다."
        else:
            message = f"앞으로 {future_credits:g}학점에서 평균 **{required} / 4.5** 이상이 필요합니다."
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="team", description="이름 목록을 무작위로 균형 있게 팀 편성합니다.")
    @app_commands.describe(members="쉼표, 줄바꿈 또는 | 로 구분", team_size="팀당 최대 인원")
    async def team(
        self,
        interaction: discord.Interaction,
        members: str,
        team_size: app_commands.Range[int, 1, 20] = 4,
    ) -> None:
        teams = split_teams(members, team_size)
        lines = [f"**{index}팀** · " + ", ".join(team) for index, team in enumerate(teams, start=1)]
        await interaction.response.send_message(
            embed=discord.Embed(
                title="👥 무작위 팀 편성",
                description="\n".join(lines)[:4000],
                color=discord.Color.random(),
            )
        )

    @app_commands.command(name="pomodoro", description="집중·휴식 사이클 알림을 등록합니다.")
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
                        f"🍅 포모도로 {cycle}/{cycles} 집중 종료! "
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
                            f"📚 휴식 종료! 포모도로 {cycle + 1}/{cycles} 집중을 시작하세요.",
                            to_iso(cursor),
                        ),
                    )
                )
        await interaction.response.send_message(
            f"🍅 {focus_minutes}분 집중 + {break_minutes}분 휴식 × {cycles}회 알림을 등록했습니다.\n"
            f"예상 종료: <t:{int(cursor.timestamp())}:F> · 리마인더 {len(reminder_ids)}개",
            ephemeral=True,
        )

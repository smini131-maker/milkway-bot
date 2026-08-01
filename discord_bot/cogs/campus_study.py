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

class StudyCog(
    commands.GroupCog,
    group_name="study",
    group_description="스터디와 팀원을 모집합니다.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage
        return True

    @app_commands.command(name="create", description="현재 채널에서 스터디를 모집합니다.")
    @app_commands.describe(meeting="선택: YYYY-MM-DD HH:MM")
    async def create(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        max_members: app_commands.Range[int, 2, 30] = 6,
        meeting: str | None = None,
    ) -> None:
        title = _clean(title, label="스터디 제목", maximum=100)
        description = _clean(description, label="설명", maximum=1000)
        meeting_at = None
        if meeting:
            timezone_name = await _guild_timezone(self.bot, interaction.guild_id)
            parsed = parse_local_datetime(meeting, timezone_name)
            if parsed <= utc_now().astimezone(parsed.tzinfo):
                raise ValueError("모임 시각은 현재보다 미래여야 합니다.")
            meeting_at = to_iso(parsed)
        study_id = await self.bot.db.execute(
            """
            INSERT INTO study_groups(
                guild_id, channel_id, creator_id, title, description, max_members, meeting_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.guild_id,
                interaction.channel_id,
                interaction.user.id,
                title,
                description,
                max_members,
                meeting_at,
            ),
        )
        await self.bot.db.execute(
            "INSERT INTO study_members(study_id, user_id) VALUES (?, ?)",
            (study_id, interaction.user.id),
        )
        meeting_text = (
            f"\n모임: <t:{int(from_iso(meeting_at).timestamp())}:F>" if meeting_at else ""
        )
        embed = discord.Embed(
            title=f"📖 스터디 모집 #{study_id} · {title}",
            description=description,
            color=discord.Color.purple(),
        )
        embed.add_field(name="모집", value=f"1/{max_members}명{meeting_text}", inline=False)
        embed.add_field(name="참가", value=f"`/study join study_id:{study_id}`", inline=False)
        embed.set_footer(text=f"개설자: {interaction.user}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="list", description="현재 서버의 모집 중인 스터디를 확인합니다.")
    async def list_groups(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.fetch_all(
            """
            SELECT g.*, COUNT(m.user_id) AS member_count
            FROM study_groups g
            LEFT JOIN study_members m ON m.study_id = g.id
            WHERE g.guild_id = ? AND g.status = 'open'
            GROUP BY g.id ORDER BY g.created_at DESC LIMIT 20
            """,
            (interaction.guild_id,),
        )
        if not rows:
            await interaction.response.send_message("모집 중인 스터디가 없습니다.", ephemeral=True)
            return
        lines = []
        for row in rows:
            meeting = ""
            if row["meeting_at"]:
                dt = from_iso(row["meeting_at"])
                meeting = f" · <t:{int(dt.timestamp())}:R>"
            lines.append(
                f"`#{row['id']}` **{row['title']}** · {row['member_count']}/{row['max_members']}명{meeting}\n"
                f"　{str(row['description'])[:120]}"
            )
        await interaction.response.send_message(
            embed=discord.Embed(
                title="📖 모집 중인 스터디",
                description="\n\n".join(lines)[:4000],
                color=discord.Color.purple(),
            )
        )

    @app_commands.command(name="join", description="스터디에 참가합니다.")
    async def join(self, interaction: discord.Interaction, study_id: int) -> None:
        success, message, count, maximum = await self.bot.db.join_study_group(
            study_id=study_id,
            guild_id=interaction.guild_id,
            user_id=interaction.user.id,
        )
        if not success:
            raise ValueError(message)
        await interaction.response.send_message(
            f"스터디 `#{study_id}`에 참가했습니다. ({count}/{maximum}명)"
        )

    @app_commands.command(name="leave", description="스터디에서 나갑니다.")
    async def leave(self, interaction: discord.Interaction, study_id: int) -> None:
        group = await self.bot.db.fetch_one(
            "SELECT * FROM study_groups WHERE id = ? AND guild_id = ?",
            (study_id, interaction.guild_id),
        )
        if group is None:
            raise ValueError("존재하지 않는 스터디입니다.")
        if int(group["creator_id"]) == interaction.user.id:
            raise ValueError("개설자는 나갈 수 없습니다. `/study close`로 마감하세요.")
        row = await self.bot.db.fetch_one(
            "SELECT 1 FROM study_members WHERE study_id = ? AND user_id = ?",
            (study_id, interaction.user.id),
        )
        if row is None:
            raise ValueError("참가 중인 스터디가 아닙니다.")
        await self.bot.db.execute(
            "DELETE FROM study_members WHERE study_id = ? AND user_id = ?",
            (study_id, interaction.user.id),
        )
        await interaction.response.send_message(f"스터디 `#{study_id}`에서 나갔습니다.")

    @app_commands.command(name="members", description="스터디 참가자를 확인합니다.")
    async def members(self, interaction: discord.Interaction, study_id: int) -> None:
        group = await self.bot.db.fetch_one(
            "SELECT * FROM study_groups WHERE id = ? AND guild_id = ?",
            (study_id, interaction.guild_id),
        )
        if group is None:
            raise ValueError("존재하지 않는 스터디입니다.")
        rows = await self.bot.db.fetch_all(
            "SELECT user_id FROM study_members WHERE study_id = ? ORDER BY joined_at",
            (study_id,),
        )
        mentions = [f"<@{row['user_id']}>" for row in rows]
        await interaction.response.send_message(
            f"**#{study_id} {group['title']}** 참가자 ({len(rows)}/{group['max_members']})\n"
            + " ".join(mentions),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="close", description="스터디 모집을 마감합니다.")
    async def close(self, interaction: discord.Interaction, study_id: int) -> None:
        group = await self.bot.db.fetch_one(
            "SELECT * FROM study_groups WHERE id = ? AND guild_id = ?",
            (study_id, interaction.guild_id),
        )
        if group is None:
            raise ValueError("존재하지 않는 스터디입니다.")
        can_manage = isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.manage_guild
        if int(group["creator_id"]) != interaction.user.id and not can_manage:
            raise app_commands.MissingPermissions(["manage_guild"])
        await self.bot.db.execute(
            "UPDATE study_groups SET status = 'closed' WHERE id = ?", (study_id,)
        )
        await interaction.response.send_message(f"스터디 `#{study_id}` 모집을 마감했습니다.")

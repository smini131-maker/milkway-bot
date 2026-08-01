from __future__ import annotations

from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.utils.timeparse import (
    get_timezone,
    next_daily,
    next_weekly,
    to_iso,
    utc_now,
)


def format_template(template: str, *, member: discord.Member) -> str:
    replacements = {
        "{user}": member.mention,
        "{username}": member.display_name,
        "{server}": member.guild.name,
        "{member_count}": str(member.guild.member_count or 0),
    }
    result = template
    for key, value in replacements.items():
        result = result.replace(key, value)
    return result[:1900]


class AutomationCog(
    commands.GroupCog,
    group_name="설정",
    group_description="서버 자동화 설정을 관리합니다.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            raise app_commands.NoPrivateMessage
        if not interaction.user.guild_permissions.manage_guild:
            raise app_commands.MissingPermissions(["manage_guild"])
        await self.bot.db.ensure_guild(interaction.guild_id)
        return True

    @app_commands.command(name="시간대", description="예약과 알림에 사용할 서버 시간대를 설정합니다.")
    @app_commands.rename(name="이름")
    @app_commands.describe(name="예: Asia/Seoul, Asia/Tokyo, UTC")
    async def timezone(self, interaction: discord.Interaction, name: str) -> None:
        get_timezone(name)
        now = utc_now()
        repeating_rows = await self.bot.db.fetch_all(
            """
            SELECT id, schedule_kind, local_time, weekday
            FROM scheduled_messages
            WHERE guild_id = ? AND schedule_kind IN ('daily', 'weekly')
            """,
            (interaction.guild_id,),
        )
        schedule_updates = []
        for row in repeating_rows:
            if row["schedule_kind"] == "daily":
                next_run = next_daily(str(row["local_time"]), name, now)
            else:
                next_run = next_weekly(
                    int(row["weekday"]), str(row["local_time"]), name, now
                )
            schedule_updates.append((name, to_iso(next_run), row["id"]))

        await self.bot.db.execute(
            "UPDATE guild_settings SET timezone = ?, updated_at = CURRENT_TIMESTAMP WHERE guild_id = ?",
            (name, interaction.guild_id),
        )
        await self.bot.db.execute(
            "UPDATE scheduled_messages SET timezone = ? WHERE guild_id = ?",
            (name, interaction.guild_id),
        )
        if schedule_updates:
            await self.bot.db.executemany(
                "UPDATE scheduled_messages SET timezone = ?, next_run_at = ? WHERE id = ?",
                schedule_updates,
            )
        await interaction.response.send_message(
            f"서버 시간대를 `{name}`으로 설정했습니다. 기존 일일·주간 예약도 새 시간대로 다시 계산했습니다.",
            ephemeral=True,
        )

    @app_commands.command(name="환영", description="신규 멤버 환영 메시지를 설정합니다.")
    @app_commands.rename(channel="채널", message="메시지")
    @app_commands.describe(
        channel="환영 메시지를 보낼 채널",
        message="사용 가능: {user}, {username}, {server}, {member_count}",
    )
    async def welcome(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str = "환영합니다, {user}! **{server}**에 오신 것을 환영합니다.",
    ) -> None:
        if not message.strip():
            raise ValueError("환영 메시지를 입력하세요.")
        await self.bot.db.execute(
            """
            UPDATE guild_settings
            SET welcome_channel_id = ?, welcome_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = ?
            """,
            (channel.id, message.strip()[:1900], interaction.guild_id),
        )
        await interaction.response.send_message(
            f"환영 메시지를 {channel.mention}에 설정했습니다.", ephemeral=True
        )

    @app_commands.command(name="퇴장", description="멤버 퇴장 메시지를 설정합니다.")
    @app_commands.rename(channel="채널", message="메시지")
    @app_commands.describe(
        channel="퇴장 메시지를 보낼 채널",
        message="사용 가능: {username}, {server}, {member_count}",
    )
    async def leave(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str = "**{username}**님이 서버를 떠났습니다.",
    ) -> None:
        if not message.strip():
            raise ValueError("퇴장 메시지를 입력하세요.")
        await self.bot.db.execute(
            """
            UPDATE guild_settings
            SET leave_channel_id = ?, leave_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = ?
            """,
            (channel.id, message.strip()[:1900], interaction.guild_id),
        )
        await interaction.response.send_message(
            f"퇴장 메시지를 {channel.mention}에 설정했습니다.", ephemeral=True
        )

    @app_commands.command(name="자동역할", description="신규 멤버에게 자동으로 부여할 역할을 설정합니다.")
    @app_commands.rename(role="역할")
    async def autorole(self, interaction: discord.Interaction, role: discord.Role) -> None:
        bot_member = interaction.guild.me
        if role.is_default() or role.managed:
            raise ValueError("@everyone 또는 외부 연동 역할은 자동 역할로 사용할 수 없습니다.")
        if bot_member and role >= bot_member.top_role:
            raise ValueError("봇의 최고 역할보다 낮은 역할을 선택하세요.")
        await self.bot.db.execute(
            "UPDATE guild_settings SET autorole_id = ?, updated_at = CURRENT_TIMESTAMP WHERE guild_id = ?",
            (role.id, interaction.guild_id),
        )
        await interaction.response.send_message(
            f"신규 멤버 자동 역할을 {role.mention}(으)로 설정했습니다.", ephemeral=True
        )

    @app_commands.command(name="로그", description="관리 및 메시지 변경 로그 채널을 설정합니다.")
    @app_commands.rename(channel="채널")
    async def log_channel(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        await self.bot.db.execute(
            "UPDATE guild_settings SET log_channel_id = ?, updated_at = CURRENT_TIMESTAMP WHERE guild_id = ?",
            (channel.id, interaction.guild_id),
        )
        await interaction.response.send_message(
            f"로그 채널을 {channel.mention}(으)로 설정했습니다.", ephemeral=True
        )

    @app_commands.command(name="끄기", description="선택한 자동화 기능을 끕니다.")
    @app_commands.rename(feature="기능")
    async def disable(
        self,
        interaction: discord.Interaction,
        feature: Literal["환영", "퇴장", "자동역할", "로그"],
    ) -> None:
        columns = {
            "환영": "welcome_channel_id",
            "퇴장": "leave_channel_id",
            "자동역할": "autorole_id",
            "로그": "log_channel_id",
        }
        column = columns[feature]
        await self.bot.db.execute(
            f"UPDATE guild_settings SET {column} = NULL, updated_at = CURRENT_TIMESTAMP WHERE guild_id = ?",
            (interaction.guild_id,),
        )
        await interaction.response.send_message(
            f"`{feature}` 기능을 껐습니다.", ephemeral=True
        )

    @app_commands.command(name="보기", description="현재 서버 자동화 설정을 확인합니다.")
    async def show(self, interaction: discord.Interaction) -> None:
        row = await self.bot.db.fetch_one(
            "SELECT * FROM guild_settings WHERE guild_id = ?", (interaction.guild_id,)
        )
        embed = discord.Embed(title="서버 자동화 설정", color=discord.Color.blurple())
        embed.add_field(name="시간대", value=f"`{row['timezone']}`", inline=False)
        embed.add_field(
            name="환영 채널",
            value=f"<#{row['welcome_channel_id']}>" if row["welcome_channel_id"] else "꺼짐",
        )
        embed.add_field(
            name="퇴장 채널",
            value=f"<#{row['leave_channel_id']}>" if row["leave_channel_id"] else "꺼짐",
        )
        embed.add_field(
            name="자동 역할",
            value=f"<@&{row['autorole_id']}>" if row["autorole_id"] else "꺼짐",
        )
        embed.add_field(
            name="로그 채널",
            value=f"<#{row['log_channel_id']}>" if row["log_channel_id"] else "꺼짐",
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    async def _settings(self, guild_id: int):
        await self.bot.db.ensure_guild(guild_id)
        return await self.bot.db.fetch_one(
            "SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        row = await self._settings(member.guild.id)
        if row["autorole_id"]:
            role = member.guild.get_role(int(row["autorole_id"]))
            if role:
                try:
                    await member.add_roles(role, reason="신규 멤버 자동 역할")
                except discord.DiscordException:
                    pass
        if row["welcome_channel_id"]:
            channel = member.guild.get_channel(int(row["welcome_channel_id"]))
            if isinstance(channel, discord.TextChannel):
                try:
                    await channel.send(
                        format_template(str(row["welcome_message"]), member=member),
                        allowed_mentions=discord.AllowedMentions(
                            everyone=False,
                            roles=False,
                            users=[member],
                        ),
                    )
                except discord.DiscordException:
                    pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        row = await self._settings(member.guild.id)
        if row["leave_channel_id"]:
            channel = member.guild.get_channel(int(row["leave_channel_id"]))
            if isinstance(channel, discord.TextChannel):
                try:
                    await channel.send(
                        format_template(str(row["leave_message"]), member=member),
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                except discord.DiscordException:
                    pass

    async def _message_log(self, guild: discord.Guild, embed: discord.Embed) -> None:
        row = await self._settings(guild.id)
        if not row["log_channel_id"]:
            return
        channel = guild.get_channel(int(row["log_channel_id"]))
        if isinstance(channel, discord.TextChannel):
            try:
                await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
            except discord.DiscordException:
                pass

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot or not message.content:
            return
        embed = discord.Embed(
            title="메시지 삭제",
            description=message.content[:3500],
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="작성자", value=f"{message.author} (`{message.author.id}`)")
        embed.add_field(name="채널", value=message.channel.mention)
        await self._message_log(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.guild is None or before.author.bot or before.content == after.content:
            return
        embed = discord.Embed(
            title="메시지 수정",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="작성자", value=f"{before.author} (`{before.author.id}`)", inline=False)
        embed.add_field(name="이전", value=(before.content or "(내용 없음)")[:1000], inline=False)
        embed.add_field(name="이후", value=(after.content or "(내용 없음)")[:1000], inline=False)
        embed.add_field(name="바로가기", value=f"[메시지 열기]({after.jump_url})", inline=False)
        await self._message_log(before.guild, embed)



async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutomationCog(bot))

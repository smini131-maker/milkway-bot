from __future__ import annotations

from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.utils.timeparse import human_duration, parse_duration


class ModerationCog(
    commands.GroupCog,
    group_name="관리",
    group_description="서버 관리 명령어입니다.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage
        return True

    @staticmethod
    def _check_target(interaction: discord.Interaction, member: discord.Member) -> None:
        if member.id == interaction.user.id:
            raise ValueError("자기 자신에게는 이 작업을 할 수 없습니다.")
        if interaction.guild and member.id == interaction.guild.owner_id:
            raise ValueError("서버 소유자에게는 이 작업을 할 수 없습니다.")
        if isinstance(interaction.user, discord.Member):
            if interaction.user.id != interaction.guild.owner_id and member.top_role >= interaction.user.top_role:
                raise ValueError("자신과 같거나 높은 역할의 사용자에게는 작업할 수 없습니다.")
        bot_member = interaction.guild.me if interaction.guild else None
        if bot_member and member.top_role >= bot_member.top_role:
            raise ValueError("봇의 역할보다 같거나 높은 사용자는 제재할 수 없습니다.")

    async def _log(self, guild: discord.Guild, title: str, description: str) -> None:
        row = await self.bot.db.fetch_one(
            "SELECT log_channel_id FROM guild_settings WHERE guild_id = ?", (guild.id,)
        )
        if row is None or not row["log_channel_id"]:
            return
        channel = guild.get_channel(int(row["log_channel_id"]))
        if not isinstance(channel, discord.TextChannel):
            return
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        try:
            await channel.send(embed=embed)
        except discord.DiscordException:
            pass

    @app_commands.command(name="삭제", description="최근 메시지를 일괄 삭제합니다.")
    @app_commands.rename(count="개수")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.bot_has_permissions(manage_messages=True, read_message_history=True)
    async def clear(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, 1, 100],
    ) -> None:
        if not isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
            raise ValueError("텍스트 채널에서만 사용할 수 있습니다.")
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=int(count))
        await interaction.followup.send(f"메시지 {len(deleted)}개를 삭제했습니다.", ephemeral=True)
        await self._log(
            interaction.guild,
            "메시지 정리",
            f"{interaction.user.mention}님이 {interaction.channel.mention}에서 {len(deleted)}개를 삭제했습니다.",
        )

    @app_commands.command(name="타임아웃", description="사용자를 일정 시간 타임아웃합니다.")
    @app_commands.rename(member="사용자", duration="시간", reason="사유")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    @app_commands.describe(duration="예: 10m, 2h, 1d", reason="사유")
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: str = "사유 없음",
    ) -> None:
        self._check_target(interaction, member)
        delta = parse_duration(duration)
        if delta > timedelta(days=28):
            raise ValueError("타임아웃은 최대 28일까지 설정할 수 있습니다.")
        until = discord.utils.utcnow() + delta
        await member.timeout(until, reason=f"{interaction.user}: {reason}")
        await interaction.response.send_message(
            f"{member.mention}님을 {human_duration(delta)} 동안 타임아웃했습니다. 사유: {reason}",
            ephemeral=True,
        )
        await self._log(
            interaction.guild,
            "타임아웃",
            f"대상: {member.mention}\n기간: {human_duration(delta)}\n담당: {interaction.user.mention}\n사유: {reason}",
        )

    @app_commands.command(name="타임아웃해제", description="사용자의 타임아웃을 해제합니다.")
    @app_commands.rename(member="사용자")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member) -> None:
        self._check_target(interaction, member)
        await member.timeout(None, reason=f"{interaction.user}: 타임아웃 해제")
        await interaction.response.send_message(
            f"{member.mention}님의 타임아웃을 해제했습니다.", ephemeral=True
        )
        await self._log(
            interaction.guild,
            "타임아웃 해제",
            f"대상: {member.mention}\n담당: {interaction.user.mention}",
        )

    @app_commands.command(name="추방", description="사용자를 서버에서 추방합니다.")
    @app_commands.rename(member="사용자", reason="사유")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.checks.bot_has_permissions(kick_members=True)
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "사유 없음",
    ) -> None:
        self._check_target(interaction, member)
        await member.kick(reason=f"{interaction.user}: {reason}")
        await interaction.response.send_message(
            f"{member}님을 추방했습니다. 사유: {reason}", ephemeral=True
        )
        await self._log(
            interaction.guild,
            "추방",
            f"대상: {member} (`{member.id}`)\n담당: {interaction.user.mention}\n사유: {reason}",
        )

    @app_commands.command(name="차단", description="사용자를 서버에서 차단합니다.")
    @app_commands.rename(member="사용자", reason="사유", delete_days="삭제일수")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "사유 없음",
        delete_days: app_commands.Range[int, 0, 7] = 0,
    ) -> None:
        self._check_target(interaction, member)
        await member.ban(
            reason=f"{interaction.user}: {reason}",
            delete_message_seconds=int(delete_days) * 86400,
        )
        await interaction.response.send_message(
            f"{member}님을 차단했습니다. 사유: {reason}", ephemeral=True
        )
        await self._log(
            interaction.guild,
            "차단",
            f"대상: {member} (`{member.id}`)\n담당: {interaction.user.mention}\n사유: {reason}",
        )

    @app_commands.command(name="차단해제", description="사용자 ID로 차단을 해제합니다.")
    @app_commands.rename(user_id="사용자아이디")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str) -> None:
        try:
            target_id = int(user_id)
        except ValueError as exc:
            raise ValueError("올바른 숫자 사용자 ID를 입력하세요.") from exc
        user = await self.bot.fetch_user(target_id)
        await interaction.guild.unban(user, reason=f"{interaction.user}: 차단 해제")
        await interaction.response.send_message(f"{user}님의 차단을 해제했습니다.", ephemeral=True)
        await self._log(
            interaction.guild,
            "차단 해제",
            f"대상: {user} (`{user.id}`)\n담당: {interaction.user.mention}",
        )

    @app_commands.command(name="슬로우", description="채널 슬로우모드를 설정합니다. 0은 해제입니다.")
    @app_commands.rename(seconds="초", channel="채널")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    async def slowmode(
        self,
        interaction: discord.Interaction,
        seconds: app_commands.Range[int, 0, 21600],
        channel: discord.TextChannel | None = None,
    ) -> None:
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            raise ValueError("텍스트 채널을 선택하세요.")
        await target.edit(slowmode_delay=int(seconds), reason=f"{interaction.user}: 슬로우모드")
        text = "해제" if seconds == 0 else f"{seconds}초로 설정"
        await interaction.response.send_message(
            f"{target.mention} 슬로우모드를 {text}했습니다.", ephemeral=True
        )

    @app_commands.command(name="경고", description="사용자에게 경고를 기록합니다.")
    @app_commands.rename(member="사용자", reason="사유")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str,
    ) -> None:
        self._check_target(interaction, member)
        cleaned_reason = reason.strip()[:1000]
        if not cleaned_reason:
            raise ValueError("경고 사유를 입력하세요.")
        warning_id = await self.bot.db.execute(
            """
            INSERT INTO warnings(guild_id, user_id, moderator_id, reason)
            VALUES (?, ?, ?, ?)
            """,
            (interaction.guild_id, member.id, interaction.user.id, cleaned_reason[:1000]),
        )
        try:
            await member.send(f"⚠️ **{interaction.guild.name} 경고**\n사유: {cleaned_reason}")
        except discord.DiscordException:
            pass
        await interaction.response.send_message(
            f"{member.mention}님에게 경고 `#{warning_id}`을 기록했습니다.", ephemeral=True
        )
        await self._log(
            interaction.guild,
            "경고",
            f"대상: {member.mention}\n담당: {interaction.user.mention}\n사유: {cleaned_reason}",
        )

    @app_commands.command(name="경고보기", description="사용자의 경고 기록을 확인합니다.")
    @app_commands.rename(member="사용자")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member) -> None:
        rows = await self.bot.db.fetch_all(
            """
            SELECT * FROM warnings
            WHERE guild_id = ? AND user_id = ?
            ORDER BY id DESC LIMIT 20
            """,
            (interaction.guild_id, member.id),
        )
        if not rows:
            await interaction.response.send_message(
                f"{member.mention}님의 경고 기록이 없습니다.", ephemeral=True
            )
            return
        lines = []
        for row in rows:
            reason_preview = str(row["reason"]).replace("\n", " ")[:220]
            lines.append(
                f"`#{row['id']}` <@{row['moderator_id']}> · {row['created_at']}\n{reason_preview}"
            )
        description = "\n\n".join(lines)
        if len(description) > 3900:
            description = description[:3897] + "..."
        embed = discord.Embed(
            title=f"{member} 경고 기록 ({len(rows)}개)",
            description=description,
            color=discord.Color.red(),
        )
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="경고삭제", description="사용자의 모든 경고 기록을 삭제합니다.")
    @app_commands.rename(member="사용자")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_warnings(
        self, interaction: discord.Interaction, member: discord.Member
    ) -> None:
        await self.bot.db.execute(
            "DELETE FROM warnings WHERE guild_id = ? AND user_id = ?",
            (interaction.guild_id, member.id),
        )
        await interaction.response.send_message(
            f"{member.mention}님의 경고 기록을 모두 삭제했습니다.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModerationCog(bot))

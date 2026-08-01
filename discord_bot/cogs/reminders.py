from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from discord_bot.utils.timeparse import (
    from_iso,
    parse_duration,
    parse_local_datetime,
    to_iso,
    utc_now,
)

LOGGER = logging.getLogger(__name__)


class ReminderCog(
    commands.GroupCog,
    group_name="알림",
    group_description="개인 알림을 등록하고 관리합니다.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.reminder_worker.start()

    async def cog_unload(self) -> None:
        self.reminder_worker.cancel()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage
        return True

    @staticmethod
    def _clean_message(message: str) -> str:
        cleaned = message.strip()
        if not cleaned:
            raise ValueError("알림 내용을 입력하세요.")
        if len(cleaned) > 1700:
            raise ValueError("알림는 1700자 이하로 입력하세요.")
        return cleaned

    @app_commands.command(name="후에", description="지금부터 일정 시간이 지난 뒤 알려줍니다.")
    @app_commands.rename(duration="시간", message="내용")
    @app_commands.describe(duration="예: 10m, 1h30m, 2d", message="알림 내용")
    async def remind_in(
        self,
        interaction: discord.Interaction,
        duration: str,
        message: str,
    ) -> None:
        delta = parse_duration(duration)
        if delta.total_seconds() > 365 * 86400:
            raise ValueError("알림는 최대 1년 뒤까지 설정할 수 있습니다.")
        due = utc_now() + delta
        reminder_id = await self.bot.db.execute(
            """
            INSERT INTO reminders(user_id, guild_id, channel_id, message, due_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                interaction.user.id,
                interaction.guild_id,
                interaction.channel_id,
                self._clean_message(message),
                to_iso(due),
            ),
        )
        await interaction.response.send_message(
            f"알림 `#{reminder_id}` 등록 완료: <t:{int(due.timestamp())}:F> (<t:{int(due.timestamp())}:R>)",
            ephemeral=True,
        )

    @app_commands.command(name="날짜", description="지정한 날짜와 시각에 알려줍니다.")
    @app_commands.rename(when="일시", message="내용")
    @app_commands.describe(when="YYYY-MM-DD HH:MM", message="알림 내용")
    async def remind_at(
        self,
        interaction: discord.Interaction,
        when: str,
        message: str,
    ) -> None:
        timezone_name = await self.bot.db.guild_timezone(interaction.guild_id)
        due = parse_local_datetime(when, timezone_name).astimezone(utc_now().tzinfo)
        if due <= utc_now():
            raise ValueError("현재보다 미래 시각을 입력하세요.")
        reminder_id = await self.bot.db.execute(
            """
            INSERT INTO reminders(user_id, guild_id, channel_id, message, due_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                interaction.user.id,
                interaction.guild_id,
                interaction.channel_id,
                self._clean_message(message),
                to_iso(due),
            ),
        )
        await interaction.response.send_message(
            f"알림 `#{reminder_id}` 등록 완료: <t:{int(due.timestamp())}:F> ({timezone_name})",
            ephemeral=True,
        )

    @app_commands.command(name="보기", description="내 알림 목록을 확인합니다.")
    async def list_reminders(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.fetch_all(
            """
            SELECT * FROM reminders
            WHERE user_id = ? AND guild_id = ? AND sent = 0
            ORDER BY due_at ASC
            LIMIT 25
            """,
            (interaction.user.id, interaction.guild_id),
        )
        if not rows:
            await interaction.response.send_message("등록된 알림가 없습니다.", ephemeral=True)
            return
        lines = []
        for row in rows:
            due = from_iso(row["due_at"])
            preview = str(row["message"]).replace("\n", " ")[:65]
            lines.append(f"`#{row['id']}` <t:{int(due.timestamp())}:R> · {preview}")
        embed = discord.Embed(
            title="내 알림",
            description="\n".join(lines),
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="삭제", description="내 알림을 삭제합니다.")
    @app_commands.rename(reminder_id="번호")
    async def cancel(self, interaction: discord.Interaction, reminder_id: int) -> None:
        row = await self.bot.db.fetch_one(
            """
            SELECT id FROM reminders
            WHERE id = ? AND user_id = ? AND guild_id = ? AND sent = 0
            """,
            (reminder_id, interaction.user.id, interaction.guild_id),
        )
        if row is None:
            raise ValueError("취소할 수 있는 알림를 찾지 못했습니다.")
        await self.bot.db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        await interaction.response.send_message(
            f"알림 `#{reminder_id}`을 취소했습니다.", ephemeral=True
        )

    async def _deliver(self, row) -> None:
        content = f"<@{row['user_id']}> ⏰ **알림**\n{row['message']}"
        allowed = discord.AllowedMentions(
            everyone=False,
            roles=False,
            users=[discord.Object(id=int(row["user_id"]))],
        )
        channel = self.bot.get_channel(int(row["channel_id"]))
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(int(row["channel_id"]))
            except discord.DiscordException:
                channel = None
        if isinstance(channel, (discord.TextChannel, discord.Thread)):
            try:
                await channel.send(content, allowed_mentions=allowed)
                return
            except discord.DiscordException:
                LOGGER.warning(
                    "알림 #%s 채널 전송 실패, DM으로 재시도", row["id"]
                )

        user = self.bot.get_user(int(row["user_id"])) or await self.bot.fetch_user(
            int(row["user_id"])
        )
        await user.send(f"⏰ **알림**\n{row['message']}")

    @tasks.loop(seconds=15)
    async def reminder_worker(self) -> None:
        now = utc_now()
        rows = await self.bot.db.fetch_all(
            """
            SELECT * FROM reminders
            WHERE sent = 0 AND due_at <= ?
            ORDER BY due_at ASC
            LIMIT 50
            """,
            (to_iso(now),),
        )
        for row in rows:
            try:
                await self._deliver(row)
                await self.bot.db.execute(
                    "UPDATE reminders SET sent = 1 WHERE id = ?", (row["id"],)
                )
            except Exception:
                failures = int(row["failure_count"]) + 1
                mark_sent = 1 if failures >= 5 else 0
                await self.bot.db.execute(
                    "UPDATE reminders SET failure_count = ?, sent = ? WHERE id = ?",
                    (failures, mark_sent, row["id"]),
                )
                LOGGER.exception("알림 #%s 전송 실패 (%s/5)", row["id"], failures)

    @reminder_worker.before_loop
    async def before_reminder_worker(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReminderCog(bot))

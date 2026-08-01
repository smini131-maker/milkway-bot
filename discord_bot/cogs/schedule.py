from __future__ import annotations

import logging
from datetime import timedelta
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands, tasks

from discord_bot.utils.mentions import (
    MentionSpec,
    ensure_mention_permissions,
    render_message,
    resolve_mention,
)
from discord_bot.utils.permissions import ensure_bot_channel_permissions
from discord_bot.utils.timeparse import (
    from_iso,
    next_daily,
    next_weekly,
    parse_local_datetime,
    parse_weekday,
    to_iso,
    utc_now,
)

LOGGER = logging.getLogger(__name__)
WEEKDAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]
KIND_NAMES = {"interval": "반복", "daily": "매일", "weekly": "매주", "once": "한번"}


class ScheduleCog(
    commands.GroupCog,
    group_name="예약",
    group_description="정해진 시각에 메시지를 자동 전송합니다.",
):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.scheduler.start()

    async def cog_unload(self) -> None:
        self.scheduler.cancel()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            raise app_commands.NoPrivateMessage
        if not interaction.user.guild_permissions.manage_guild:
            raise app_commands.MissingPermissions(["manage_guild"])
        return True

    @staticmethod
    def _validate_message(message: str) -> str:
        cleaned = message.strip()
        if not cleaned:
            raise ValueError("메시지를 입력하세요.")
        if len(cleaned) > 1850:
            raise ValueError("예약 메시지는 1850자 이하로 입력하세요.")
        return cleaned

    async def _insert_schedule(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str,
        mention: MentionSpec,
        kind: str,
        next_run_at: str,
        timezone_name: str,
        interval_seconds: int | None = None,
        local_time: str | None = None,
        weekday: int | None = None,
    ) -> int:
        return await self.bot.db.execute(
            """
            INSERT INTO scheduled_messages(
                guild_id, channel_id, creator_id, message, mention_type, mention_id,
                schedule_kind, interval_seconds, local_time, weekday, timezone, next_run_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                interaction.guild_id,
                channel.id,
                interaction.user.id,
                message,
                mention.kind,
                mention.target_id,
                kind,
                interval_seconds,
                local_time,
                weekday,
                timezone_name,
                next_run_at,
            ),
        )

    async def _prepare_mention(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        role: discord.Role | None,
        user: discord.Member | None,
        ping_everyone: bool,
        ping_here: bool,
    ) -> MentionSpec:
        ensure_bot_channel_permissions(interaction, channel)
        ensure_mention_permissions(
            interaction,
            channel,
            role=role,
            ping_everyone=ping_everyone,
            ping_here=ping_here,
        )
        return resolve_mention(role, user, ping_everyone, ping_here)

    @app_commands.command(name="간격", description="몇 분·시간·일마다 메시지를 반복 전송합니다.")
    @app_commands.rename(
        channel="채널",
        amount="숫자",
        unit="단위",
        message="메시지",
        role="역할",
        user="사용자",
        ping_everyone="전체멘션",
        ping_here="현재멘션",
    )
    async def interval(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        amount: app_commands.Range[int, 1, 10080],
        unit: Literal["분", "시간", "일"],
        message: str,
        role: discord.Role | None = None,
        user: discord.Member | None = None,
        ping_everyone: bool = False,
        ping_here: bool = False,
    ) -> None:
        multipliers = {"분": 60, "시간": 3600, "일": 86400}
        interval_seconds = int(amount) * multipliers[unit]
        cleaned = self._validate_message(message)
        mention = await self._prepare_mention(
            interaction, channel, role, user, ping_everyone, ping_here
        )
        timezone_name = await self.bot.db.guild_timezone(interaction.guild_id)
        next_run = utc_now() + timedelta(seconds=interval_seconds)
        schedule_id = await self._insert_schedule(
            interaction,
            channel,
            cleaned,
            mention,
            "interval",
            to_iso(next_run),
            timezone_name,
            interval_seconds=interval_seconds,
        )
        await interaction.response.send_message(
            f"예약 `#{schedule_id}` 생성 완료: {channel.mention}에 {amount}{unit}마다 전송합니다.",
            ephemeral=True,
        )

    @app_commands.command(name="매일", description="매일 같은 시각에 메시지를 전송합니다.")
    @app_commands.rename(
        channel="채널",
        time="시간",
        message="메시지",
        role="역할",
        user="사용자",
        ping_everyone="전체멘션",
        ping_here="현재멘션",
    )
    @app_commands.describe(time="예: 09:00")
    async def daily(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        time: str,
        message: str,
        role: discord.Role | None = None,
        user: discord.Member | None = None,
        ping_everyone: bool = False,
        ping_here: bool = False,
    ) -> None:
        cleaned = self._validate_message(message)
        mention = await self._prepare_mention(
            interaction, channel, role, user, ping_everyone, ping_here
        )
        timezone_name = await self.bot.db.guild_timezone(interaction.guild_id)
        next_run = next_daily(time, timezone_name)
        schedule_id = await self._insert_schedule(
            interaction,
            channel,
            cleaned,
            mention,
            "daily",
            to_iso(next_run),
            timezone_name,
            local_time=time.strip(),
        )
        await interaction.response.send_message(
            f"예약 `#{schedule_id}` 생성 완료: 매일 `{time}`에 전송합니다.",
            ephemeral=True,
        )

    @app_commands.command(name="매주", description="매주 같은 요일과 시각에 메시지를 전송합니다.")
    @app_commands.rename(
        channel="채널",
        weekday="요일",
        time="시간",
        message="메시지",
        role="역할",
        user="사용자",
        ping_everyone="전체멘션",
        ping_here="현재멘션",
    )
    @app_commands.describe(weekday="월~일", time="예: 09:00")
    async def weekly(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        weekday: str,
        time: str,
        message: str,
        role: discord.Role | None = None,
        user: discord.Member | None = None,
        ping_everyone: bool = False,
        ping_here: bool = False,
    ) -> None:
        weekday_number = parse_weekday(weekday)
        cleaned = self._validate_message(message)
        mention = await self._prepare_mention(
            interaction, channel, role, user, ping_everyone, ping_here
        )
        timezone_name = await self.bot.db.guild_timezone(interaction.guild_id)
        next_run = next_weekly(weekday_number, time, timezone_name)
        schedule_id = await self._insert_schedule(
            interaction,
            channel,
            cleaned,
            mention,
            "weekly",
            to_iso(next_run),
            timezone_name,
            local_time=time.strip(),
            weekday=weekday_number,
        )
        await interaction.response.send_message(
            f"예약 `#{schedule_id}` 생성 완료: 매주 {WEEKDAY_NAMES[weekday_number]}요일 `{time}`에 전송합니다.",
            ephemeral=True,
        )

    @app_commands.command(name="한번", description="지정한 날짜와 시각에 한 번 전송합니다.")
    @app_commands.rename(
        channel="채널",
        when="일시",
        message="메시지",
        role="역할",
        user="사용자",
        ping_everyone="전체멘션",
        ping_here="현재멘션",
    )
    @app_commands.describe(when="예: 2026-08-15 18:00")
    async def once(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        when: str,
        message: str,
        role: discord.Role | None = None,
        user: discord.Member | None = None,
        ping_everyone: bool = False,
        ping_here: bool = False,
    ) -> None:
        cleaned = self._validate_message(message)
        mention = await self._prepare_mention(
            interaction, channel, role, user, ping_everyone, ping_here
        )
        timezone_name = await self.bot.db.guild_timezone(interaction.guild_id)
        next_run = parse_local_datetime(when, timezone_name).astimezone(utc_now().tzinfo)
        if next_run <= utc_now():
            raise ValueError("현재보다 미래 시각을 입력하세요.")
        schedule_id = await self._insert_schedule(
            interaction,
            channel,
            cleaned,
            mention,
            "once",
            to_iso(next_run),
            timezone_name,
        )
        await interaction.response.send_message(
            f"예약 `#{schedule_id}` 생성 완료: <t:{int(next_run.timestamp())}:F>에 전송합니다.",
            ephemeral=True,
        )

    @app_commands.command(name="보기", description="현재 작동 중인 예약 목록을 확인합니다.")
    async def list_schedules(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.fetch_all(
            """
            SELECT * FROM scheduled_messages
            WHERE guild_id = ? AND enabled = 1
            ORDER BY next_run_at ASC
            LIMIT 25
            """,
            (interaction.guild_id,),
        )
        if not rows:
            await interaction.response.send_message("작동 중인 예약이 없습니다.", ephemeral=True)
            return

        lines = []
        for row in rows:
            timestamp = int(from_iso(row["next_run_at"]).timestamp())
            preview = str(row["message"]).replace("\n", " ")[:55]
            kind = KIND_NAMES.get(str(row["schedule_kind"]), str(row["schedule_kind"]))
            lines.append(
                f"`#{row['id']}` **{kind}** · <#{row['channel_id']}> · <t:{timestamp}:R>\n{preview}"
            )
        embed = discord.Embed(
            title="자동 전송 예약",
            description="\n\n".join(lines),
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _owned_row(self, interaction: discord.Interaction, schedule_id: int):
        row = await self.bot.db.fetch_one(
            "SELECT * FROM scheduled_messages WHERE id = ? AND guild_id = ?",
            (schedule_id, interaction.guild_id),
        )
        if row is None:
            raise ValueError("해당 예약을 찾을 수 없습니다.")
        return row

    @app_commands.command(name="삭제", description="예약을 삭제합니다.")
    @app_commands.rename(schedule_id="번호")
    async def delete(self, interaction: discord.Interaction, schedule_id: int) -> None:
        await self._owned_row(interaction, schedule_id)
        await self.bot.db.execute("DELETE FROM scheduled_messages WHERE id = ?", (schedule_id,))
        await interaction.response.send_message(f"예약 `#{schedule_id}`을 삭제했습니다.", ephemeral=True)

    async def _send_row(self, row) -> None:
        channel = self.bot.get_channel(int(row["channel_id"]))
        if channel is None:
            channel = await self.bot.fetch_channel(int(row["channel_id"]))
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            raise RuntimeError("메시지를 보낼 수 없는 채널입니다.")

        spec = MentionSpec(str(row["mention_type"]), row["mention_id"])
        content, allowed_mentions = render_message(str(row["message"]), spec)
        await channel.send(content, allowed_mentions=allowed_mentions)

    @tasks.loop(seconds=15)
    async def scheduler(self) -> None:
        now = utc_now()
        rows = await self.bot.db.fetch_all(
            """
            SELECT * FROM scheduled_messages
            WHERE enabled = 1 AND next_run_at <= ?
            ORDER BY next_run_at ASC
            LIMIT 50
            """,
            (to_iso(now),),
        )
        for row in rows:
            try:
                await self._send_row(row)
                kind = row["schedule_kind"]
                if kind == "once":
                    await self.bot.db.execute(
                        "UPDATE scheduled_messages SET enabled = 0, last_run_at = ?, failure_count = 0 WHERE id = ?",
                        (to_iso(now), row["id"]),
                    )
                    continue
                if kind == "interval":
                    due = from_iso(row["next_run_at"])
                    interval = timedelta(seconds=int(row["interval_seconds"]))
                    next_run = due + interval
                    while next_run <= now:
                        next_run += interval
                elif kind == "daily":
                    next_run = next_daily(row["local_time"], row["timezone"], now)
                else:
                    next_run = next_weekly(
                        int(row["weekday"]), row["local_time"], row["timezone"], now
                    )
                await self.bot.db.execute(
                    """
                    UPDATE scheduled_messages
                    SET next_run_at = ?, last_run_at = ?, failure_count = 0
                    WHERE id = ?
                    """,
                    (to_iso(next_run), to_iso(now), row["id"]),
                )
            except Exception:
                failures = int(row["failure_count"]) + 1
                enabled = 0 if failures >= 5 else 1
                await self.bot.db.execute(
                    "UPDATE scheduled_messages SET failure_count = ?, enabled = ? WHERE id = ?",
                    (failures, enabled, row["id"]),
                )
                LOGGER.exception("예약 #%s 전송 실패 (%s/5)", row["id"], failures)

    @scheduler.before_loop
    async def before_scheduler(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ScheduleCog(bot))

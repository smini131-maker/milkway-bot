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
    parse_clock,
    parse_duration,
    parse_local_datetime,
    parse_weekday,
    to_iso,
    utc_now,
)

LOGGER = logging.getLogger(__name__)
WEEKDAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]


class ScheduleCog(
    commands.GroupCog,
    group_name="schedule",
    group_description="주기·일일·주간·일회성 메시지를 관리합니다.",
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

    @app_commands.command(name="interval", description="일정 간격마다 메시지를 반복 전송합니다.")
    @app_commands.describe(
        channel="메시지를 보낼 채널",
        amount="반복 간격 숫자",
        unit="간격 단위",
        message="보낼 메시지",
        role="함께 맨션할 역할",
        user="함께 맨션할 사용자",
        ping_everyone="@everyone 맨션",
        ping_here="@here 맨션",
    )
    async def interval(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        amount: app_commands.Range[int, 1, 10080],
        unit: Literal["minutes", "hours", "days"],
        message: str,
        role: discord.Role | None = None,
        user: discord.Member | None = None,
        ping_everyone: bool = False,
        ping_here: bool = False,
    ) -> None:
        multipliers = {"minutes": 60, "hours": 3600, "days": 86400}
        interval_seconds = int(amount) * multipliers[unit]
        if interval_seconds < 60:
            raise ValueError("반복 간격은 최소 1분입니다.")

        cleaned = self._validate_message(message)
        ensure_bot_channel_permissions(interaction, channel)
        ensure_mention_permissions(
            interaction,
            channel,
            role=role,
            ping_everyone=ping_everyone,
            ping_here=ping_here,
        )
        mention = resolve_mention(role, user, ping_everyone, ping_here)
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
            f"예약 `#{schedule_id}` 생성 완료: {channel.mention}에 <t:{int(next_run.timestamp())}:R>부터 반복 전송합니다.",
            ephemeral=True,
        )

    @app_commands.command(name="daily", description="매일 정해진 시각에 메시지를 전송합니다.")
    @app_commands.describe(channel="메시지를 보낼 채널", time="HH:MM", message="보낼 메시지")
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
        ensure_bot_channel_permissions(interaction, channel)
        ensure_mention_permissions(
            interaction,
            channel,
            role=role,
            ping_everyone=ping_everyone,
            ping_here=ping_here,
        )
        mention = resolve_mention(role, user, ping_everyone, ping_here)
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
            local_time=time,
        )
        await interaction.response.send_message(
            f"예약 `#{schedule_id}` 생성 완료: 매일 `{time}` ({timezone_name}), 다음 실행 <t:{int(next_run.timestamp())}:F>",
            ephemeral=True,
        )

    @app_commands.command(name="weekly", description="매주 정해진 요일과 시각에 메시지를 전송합니다.")
    @app_commands.describe(weekday="요일: 월~일", time="HH:MM", message="보낼 메시지")
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
        ensure_bot_channel_permissions(interaction, channel)
        ensure_mention_permissions(
            interaction,
            channel,
            role=role,
            ping_everyone=ping_everyone,
            ping_here=ping_here,
        )
        mention = resolve_mention(role, user, ping_everyone, ping_here)
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
            local_time=time,
            weekday=weekday_number,
        )
        await interaction.response.send_message(
            f"예약 `#{schedule_id}` 생성 완료: 매주 {WEEKDAY_NAMES[weekday_number]}요일 `{time}`, 다음 실행 <t:{int(next_run.timestamp())}:F>",
            ephemeral=True,
        )

    @app_commands.command(name="once", description="지정한 날짜와 시각에 한 번 메시지를 전송합니다.")
    @app_commands.describe(when="YYYY-MM-DD HH:MM", message="보낼 메시지")
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
        ensure_bot_channel_permissions(interaction, channel)
        ensure_mention_permissions(
            interaction,
            channel,
            role=role,
            ping_everyone=ping_everyone,
            ping_here=ping_here,
        )
        mention = resolve_mention(role, user, ping_everyone, ping_here)
        timezone_name = await self.bot.db.guild_timezone(interaction.guild_id)
        local_datetime = parse_local_datetime(when, timezone_name)
        next_run = local_datetime.astimezone(utc_now().tzinfo)
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
            f"예약 `#{schedule_id}` 생성 완료: <t:{int(next_run.timestamp())}:F>에 한 번 전송합니다.",
            ephemeral=True,
        )

    @app_commands.command(name="list", description="이 서버의 예약 메시지 목록을 확인합니다.")
    async def list_schedules(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.fetch_all(
            """
            SELECT * FROM scheduled_messages
            WHERE guild_id = ?
            ORDER BY enabled DESC, next_run_at ASC
            LIMIT 25
            """,
            (interaction.guild_id,),
        )
        if not rows:
            await interaction.response.send_message("등록된 예약이 없습니다.", ephemeral=True)
            return

        lines = []
        for row in rows:
            state = "켜짐" if row["enabled"] else "꺼짐"
            timestamp = int(from_iso(row["next_run_at"]).timestamp())
            preview = str(row["message"]).replace("\n", " ")[:45]
            lines.append(
                f"`#{row['id']}` **{row['schedule_kind']}** · {state} · <#{row['channel_id']}> · <t:{timestamp}:R>\n{preview}"
            )
        embed = discord.Embed(title="예약 메시지", description="\n\n".join(lines), color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _owned_row(self, interaction: discord.Interaction, schedule_id: int):
        row = await self.bot.db.fetch_one(
            "SELECT * FROM scheduled_messages WHERE id = ? AND guild_id = ?",
            (schedule_id, interaction.guild_id),
        )
        if row is None:
            raise ValueError("해당 예약을 찾을 수 없습니다.")
        return row

    @app_commands.command(name="pause", description="예약을 일시 중지합니다.")
    async def pause(self, interaction: discord.Interaction, schedule_id: int) -> None:
        await self._owned_row(interaction, schedule_id)
        await self.bot.db.execute(
            "UPDATE scheduled_messages SET enabled = 0 WHERE id = ?", (schedule_id,)
        )
        await interaction.response.send_message(f"예약 `#{schedule_id}`을 중지했습니다.", ephemeral=True)

    @app_commands.command(name="resume", description="중지된 예약을 다시 시작합니다.")
    async def resume(self, interaction: discord.Interaction, schedule_id: int) -> None:
        row = await self._owned_row(interaction, schedule_id)
        now = utc_now()
        kind = row["schedule_kind"]
        if kind == "interval":
            next_run = now + timedelta(seconds=int(row["interval_seconds"]))
        elif kind == "daily":
            next_run = next_daily(row["local_time"], row["timezone"], now)
        elif kind == "weekly":
            next_run = next_weekly(int(row["weekday"]), row["local_time"], row["timezone"], now)
        else:
            old_run = from_iso(row["next_run_at"])
            if old_run <= now:
                raise ValueError("이미 지난 일회성 예약은 다시 시작할 수 없습니다.")
            next_run = old_run
        await self.bot.db.execute(
            "UPDATE scheduled_messages SET enabled = 1, failure_count = 0, next_run_at = ? WHERE id = ?",
            (to_iso(next_run), schedule_id),
        )
        await interaction.response.send_message(
            f"예약 `#{schedule_id}`을 다시 시작했습니다. 다음 실행 <t:{int(next_run.timestamp())}:R>",
            ephemeral=True,
        )

    @app_commands.command(name="edit", description="예약의 채널·메시지·맨션을 수정합니다.")
    async def edit(
        self,
        interaction: discord.Interaction,
        schedule_id: int,
        channel: discord.TextChannel | None = None,
        message: str | None = None,
        role: discord.Role | None = None,
        user: discord.Member | None = None,
        ping_everyone: bool = False,
        ping_here: bool = False,
        clear_mention: bool = False,
    ) -> None:
        row = await self._owned_row(interaction, schedule_id)
        mention_changed = any((role, user, ping_everyone, ping_here, clear_mention))
        if channel is None and message is None and not mention_changed:
            raise ValueError("변경할 채널, 메시지 또는 맨션을 입력하세요.")
        if clear_mention and any((role, user, ping_everyone, ping_here)):
            raise ValueError("맨션 지우기와 새 맨션 지정은 동시에 사용할 수 없습니다.")

        new_channel_id = channel.id if channel else int(row["channel_id"])
        new_message = self._validate_message(message) if message is not None else str(row["message"])
        if channel is not None:
            ensure_bot_channel_permissions(interaction, channel)
        if clear_mention:
            mention = MentionSpec()
        elif mention_changed:
            target_channel = channel or interaction.guild.get_channel(new_channel_id)
            if not isinstance(target_channel, discord.TextChannel):
                raise ValueError("예약 대상 텍스트 채널을 찾을 수 없습니다.")
            ensure_mention_permissions(
                interaction,
                target_channel,
                role=role,
                ping_everyone=ping_everyone,
                ping_here=ping_here,
            )
            mention = resolve_mention(role, user, ping_everyone, ping_here)
        else:
            mention = MentionSpec(str(row["mention_type"]), row["mention_id"])

        await self.bot.db.execute(
            """
            UPDATE scheduled_messages
            SET channel_id = ?, message = ?, mention_type = ?, mention_id = ?
            WHERE id = ?
            """,
            (new_channel_id, new_message, mention.kind, mention.target_id, schedule_id),
        )
        await interaction.response.send_message(
            f"예약 `#{schedule_id}`의 내용을 수정했습니다.", ephemeral=True
        )

    @app_commands.command(name="time", description="예약 종류에 맞는 새 실행 시각이나 간격을 설정합니다.")
    @app_commands.describe(
        value="간격 2h / 매일 09:00 / 매주 월 09:00 / 일회성 2026-08-15 18:00"
    )
    async def change_time(
        self, interaction: discord.Interaction, schedule_id: int, value: str
    ) -> None:
        row = await self._owned_row(interaction, schedule_id)
        kind = str(row["schedule_kind"])
        timezone_name = str(row["timezone"])
        now = utc_now()

        if kind == "interval":
            delta = parse_duration(value)
            seconds = int(delta.total_seconds())
            if seconds < 60:
                raise ValueError("반복 간격은 최소 1분입니다.")
            next_run = now + delta
            await self.bot.db.execute(
                "UPDATE scheduled_messages SET interval_seconds = ?, next_run_at = ?, enabled = 1, failure_count = 0 WHERE id = ?",
                (seconds, to_iso(next_run), schedule_id),
            )
        elif kind == "daily":
            parse_clock(value)
            next_run = next_daily(value, timezone_name, now)
            await self.bot.db.execute(
                "UPDATE scheduled_messages SET local_time = ?, next_run_at = ?, enabled = 1, failure_count = 0 WHERE id = ?",
                (value.strip(), to_iso(next_run), schedule_id),
            )
        elif kind == "weekly":
            parts = value.split(maxsplit=1)
            if len(parts) != 2:
                raise ValueError("주간 예약은 `월 09:00` 형식으로 입력하세요.")
            weekday = parse_weekday(parts[0])
            parse_clock(parts[1])
            next_run = next_weekly(weekday, parts[1], timezone_name, now)
            await self.bot.db.execute(
                "UPDATE scheduled_messages SET weekday = ?, local_time = ?, next_run_at = ?, enabled = 1, failure_count = 0 WHERE id = ?",
                (weekday, parts[1].strip(), to_iso(next_run), schedule_id),
            )
        else:
            next_run = parse_local_datetime(value, timezone_name).astimezone(now.tzinfo)
            if next_run <= now:
                raise ValueError("현재보다 미래 시각을 입력하세요.")
            await self.bot.db.execute(
                "UPDATE scheduled_messages SET next_run_at = ?, enabled = 1, failure_count = 0 WHERE id = ?",
                (to_iso(next_run), schedule_id),
            )

        await interaction.response.send_message(
            f"예약 `#{schedule_id}`의 다음 실행을 <t:{int(next_run.timestamp())}:F>로 변경했습니다.",
            ephemeral=True,
        )

    @app_commands.command(name="delete", description="예약을 완전히 삭제합니다.")
    async def delete(self, interaction: discord.Interaction, schedule_id: int) -> None:
        await self._owned_row(interaction, schedule_id)
        await self.bot.db.execute("DELETE FROM scheduled_messages WHERE id = ?", (schedule_id,))
        await interaction.response.send_message(f"예약 `#{schedule_id}`을 삭제했습니다.", ephemeral=True)

    @app_commands.command(name="run", description="예약 메시지를 지금 즉시 시험 전송합니다.")
    async def run_now(self, interaction: discord.Interaction, schedule_id: int) -> None:
        row = await self._owned_row(interaction, schedule_id)
        await interaction.response.defer(ephemeral=True)
        await self._send_row(row)
        await interaction.followup.send(f"예약 `#{schedule_id}`을 시험 전송했습니다.", ephemeral=True)

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

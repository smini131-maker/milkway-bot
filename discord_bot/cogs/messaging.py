from __future__ import annotations

import re

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.utils.mentions import (
    ensure_mention_permissions,
    render_message,
    resolve_mention,
)
from discord_bot.utils.permissions import (
    ensure_bot_channel_permissions,
    ensure_user_can_send,
)

POLL_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
_HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")


def parse_color(value: str | None) -> discord.Color:
    if not value:
        return discord.Color.blurple()
    match = _HEX_RE.fullmatch(value.strip())
    if not match:
        raise ValueError("색상은 #5865F2 같은 6자리 HEX 형식으로 입력하세요.")
    return discord.Color(int(match.group(1), 16))


class MessagingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="메시지", description="봇이 지정한 채널에 메시지를 보냅니다.")
    @app_commands.rename(channel="채널", message="내용", role="역할", user="사용자", ping_everyone="전체멘션", ping_here="현재멘션")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(channel="메시지를 보낼 채널", message="보낼 내용")
    async def send_message(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str,
        role: discord.Role | None = None,
        user: discord.Member | None = None,
        ping_everyone: bool = False,
        ping_here: bool = False,
    ) -> None:
        cleaned = message.strip()
        if not cleaned:
            raise ValueError("메시지를 입력하세요.")
        if len(cleaned) > 1850:
            raise ValueError("메시지는 1850자 이하로 입력하세요.")
        ensure_user_can_send(interaction, channel)
        ensure_bot_channel_permissions(interaction, channel)
        ensure_mention_permissions(
            interaction,
            channel,
            role=role,
            ping_everyone=ping_everyone,
            ping_here=ping_here,
        )
        spec = resolve_mention(role, user, ping_everyone, ping_here)
        content, allowed_mentions = render_message(cleaned, spec)
        sent = await channel.send(content, allowed_mentions=allowed_mentions)
        await interaction.response.send_message(
            f"전송 완료: {sent.jump_url}", ephemeral=True
        )

    @app_commands.command(name="공지", description="깔끔한 임베드 공지를 전송합니다.")
    @app_commands.rename(channel="채널", title="제목", body="본문", color="색상", image_url="이미지", footer="하단문구", role="역할", ping_everyone="전체멘션", ping_here="현재멘션")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.describe(
        channel="공지를 보낼 채널",
        title="공지 제목",
        body="공지 본문",
        color="HEX 색상, 예: #5865F2",
        image_url="공지 이미지 URL",
        footer="하단 문구",
    )
    async def announce(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        body: str,
        color: str | None = None,
        image_url: str | None = None,
        footer: str | None = None,
        role: discord.Role | None = None,
        ping_everyone: bool = False,
        ping_here: bool = False,
    ) -> None:
        if not title.strip() or not body.strip():
            raise ValueError("제목과 본문을 모두 입력하세요.")
        if len(title) > 256 or len(body) > 4000:
            raise ValueError("제목은 256자, 본문은 4000자 이하여야 합니다.")

        ensure_user_can_send(interaction, channel)
        ensure_bot_channel_permissions(interaction, channel, embed_links=True)
        ensure_mention_permissions(
            interaction,
            channel,
            role=role,
            ping_everyone=ping_everyone,
            ping_here=ping_here,
        )
        spec = resolve_mention(role=role, ping_everyone=ping_everyone, ping_here=ping_here)
        content, allowed_mentions = render_message("", spec)
        embed = discord.Embed(
            title=title.strip(),
            description=body.strip(),
            color=parse_color(color),
            timestamp=discord.utils.utcnow(),
        )
        if image_url:
            if not image_url.startswith(("https://", "http://")):
                raise ValueError("이미지 URL은 http:// 또는 https://로 시작해야 합니다.")
            embed.set_image(url=image_url)
        if footer:
            embed.set_footer(text=footer[:2048])
        if interaction.user.display_avatar:
            embed.set_author(
                name=str(interaction.user),
                icon_url=interaction.user.display_avatar.url,
            )

        sent = await channel.send(
            content=content.strip() or None,
            embed=embed,
            allowed_mentions=allowed_mentions,
        )
        await interaction.response.send_message(
            f"공지 전송 완료: {sent.jump_url}", ephemeral=True
        )

    @app_commands.command(name="투표", description="반응 이모지로 투표를 만듭니다.")
    @app_commands.rename(question="질문", options="선택지", channel="채널")
    @app_commands.guild_only()
    @app_commands.checks.cooldown(2, 30.0)
    @app_commands.describe(
        question="투표 질문",
        options="선택지를 | 로 구분하세요. 예: 치킨 | 피자 | 햄버거",
        channel="투표를 보낼 채널. 비우면 현재 채널",
    )
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        options: str,
        channel: discord.TextChannel | None = None,
    ) -> None:
        target = channel or interaction.channel
        if not isinstance(target, (discord.TextChannel, discord.Thread)):
            raise ValueError("텍스트 채널에서만 투표를 만들 수 있습니다.")
        ensure_user_can_send(interaction, target)
        ensure_bot_channel_permissions(
            interaction,
            target,
            embed_links=True,
            add_reactions=True,
            read_message_history=True,
        )
        parsed = [option.strip() for option in options.split("|") if option.strip()]
        if not 2 <= len(parsed) <= 10:
            raise ValueError("선택지는 2개 이상 10개 이하로 입력하세요.")
        if len(question.strip()) > 256 or any(len(option) > 100 for option in parsed):
            raise ValueError("질문은 256자, 각 선택지는 100자 이하여야 합니다.")

        description = "\n".join(
            f"{POLL_EMOJIS[index]} {option}" for index, option in enumerate(parsed)
        )
        embed = discord.Embed(
            title=f"📊 {question.strip()}",
            description=description,
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text=f"투표 생성자: {interaction.user}")
        message = await target.send(embed=embed)
        for emoji in POLL_EMOJIS[: len(parsed)]:
            await message.add_reaction(emoji)
        await interaction.response.send_message(
            f"투표 생성 완료: {message.jump_url}", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MessagingCog(bot))

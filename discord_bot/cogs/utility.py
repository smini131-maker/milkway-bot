from __future__ import annotations

import random
import re
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from discord_bot.utils.timeparse import parse_local_datetime

INVITE_PERMISSIONS = 1374658194518
_DICE_RE = re.compile(r"^(?P<count>\d{1,2})d(?P<sides>\d{1,4})$", re.IGNORECASE)


class UtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="도움말", description="봇의 간단한 명령어 목록을 확인합니다.")
    async def help_command(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="🌌 Milkway Bot 간단 사용법",
            description="모든 주요 명령어를 한글로 정리했습니다.",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="🎓 대학생활",
            value=(
                "`/과제 추가|보기|완료|삭제`\n"
                "`/시험 추가|보기|삭제`\n"
                "`/시간표 추가|오늘|보기|삭제`\n"
                "`/대학생 한눈에|학점|집중`"
            ),
            inline=False,
        )
        embed.add_field(
            name="🤖 Gemini",
            value="`/인공지능 질문|검색|요약|퀴즈|사용량`",
            inline=False,
        )
        embed.add_field(
            name="⏰ 알림과 자동전송",
            value=(
                "`/알림 후에|날짜|보기|삭제`\n"
                "`/예약 간격|매일|매주|한번|보기|삭제`"
            ),
            inline=False,
        )
        embed.add_field(
            name="📢 서버 기능",
            value=(
                "`/메시지` `/공지` `/투표`\n"
                "`/설정 시간대|환영|퇴장|자동역할|로그|끄기|보기`\n"
                "`/관리 삭제|타임아웃|타임아웃해제|추방|차단|차단해제|슬로우|경고|경고보기|경고삭제`"
            ),
            inline=False,
        )
        embed.add_field(
            name="🧰 기타",
            value="`/핑` `/초대` `/서버정보` `/사용자정보` `/아바타` `/선택` `/주사위` `/동전` `/시간`",
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="초대", description="Milkway Bot의 정식 서버 초대 링크를 확인합니다.")
    async def invite(self, interaction: discord.Interaction) -> None:
        application_id = self.bot.user.id if self.bot.user else 1533024340155699290
        url = (
            "https://discord.com/oauth2/authorize"
            f"?client_id={application_id}"
            f"&permissions={INVITE_PERMISSIONS}"
            "&integration_type=0"
            "&scope=bot%20applications.commands"
        )
        embed = discord.Embed(
            title="🔗 Milkway Bot 초대",
            description=f"[여기를 눌러 서버에 초대하세요]({url})",
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="서버 관리 권한이 있는 계정으로 열어야 서버를 선택할 수 있습니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="핑", description="봇의 응답 지연 시간을 확인합니다.")
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"🏓 Pong! `{round(self.bot.latency * 1000)}ms`", ephemeral=True
        )

    @app_commands.command(name="서버정보", description="현재 서버의 정보를 확인합니다.")
    @app_commands.guild_only()
    async def server_info(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        owner = guild.owner or await guild.fetch_member(guild.owner_id)
        embed = discord.Embed(
            title=guild.name,
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="서버 ID", value=f"`{guild.id}`")
        embed.add_field(name="소유자", value=owner.mention)
        embed.add_field(name="멤버", value=str(guild.member_count or 0))
        embed.add_field(name="채널", value=str(len(guild.channels)))
        embed.add_field(name="역할", value=str(len(guild.roles)))
        embed.add_field(
            name="부스트",
            value=f"레벨 {guild.premium_tier} · {guild.premium_subscription_count}개",
        )
        embed.add_field(
            name="생성일",
            value=f"<t:{int(guild.created_at.timestamp())}:F>",
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="사용자정보", description="사용자의 서버 정보를 확인합니다.")
    @app_commands.guild_only()
    @app_commands.rename(member="사용자")
    async def user_info(
        self,
        interaction: discord.Interaction,
        member: discord.Member | None = None,
    ) -> None:
        target = member or interaction.user
        if not isinstance(target, discord.Member):
            raise ValueError("서버 멤버를 선택하세요.")
        roles = [role.mention for role in target.roles[1:][-10:]]
        embed = discord.Embed(
            title=str(target),
            color=target.color if target.color.value else discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="사용자 ID", value=f"`{target.id}`", inline=False)
        embed.add_field(
            name="계정 생성",
            value=f"<t:{int(target.created_at.timestamp())}:F>",
            inline=False,
        )
        embed.add_field(
            name="서버 참가",
            value=f"<t:{int(target.joined_at.timestamp())}:F>" if target.joined_at else "확인 불가",
            inline=False,
        )
        embed.add_field(
            name=f"역할 ({len(target.roles) - 1})",
            value=" ".join(roles) if roles else "없음",
            inline=False,
        )
        await interaction.response.send_message(
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @app_commands.command(name="아바타", description="사용자의 아바타 원본을 확인합니다.")
    @app_commands.rename(user="사용자")
    async def avatar(
        self,
        interaction: discord.Interaction,
        user: discord.User | None = None,
    ) -> None:
        target = user or interaction.user
        embed = discord.Embed(title=f"{target} 아바타", color=discord.Color.blurple())
        embed.set_image(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="선택", description="여러 선택지 중 하나를 무작위로 고릅니다.")
    @app_commands.rename(options="선택지")
    @app_commands.describe(options="선택지를 | 로 구분하세요.")
    async def choose(self, interaction: discord.Interaction, options: str) -> None:
        parsed = [item.strip() for item in options.split("|") if item.strip()]
        if len(parsed) < 2:
            raise ValueError("선택지를 | 로 구분해 2개 이상 입력하세요.")
        if len(parsed) > 30:
            raise ValueError("선택지는 최대 30개입니다.")
        await interaction.response.send_message(f"👉 **{random.choice(parsed)}**")

    @app_commands.command(name="주사위", description="NdM 형식의 주사위를 굴립니다.")
    @app_commands.rename(notation="표기")
    async def dice(self, interaction: discord.Interaction, notation: str = "1d6") -> None:
        match = _DICE_RE.fullmatch(notation.strip())
        if not match:
            raise ValueError("주사위는 2d6 같은 NdM 형식으로 입력하세요.")
        count = int(match.group("count"))
        sides = int(match.group("sides"))
        if not 1 <= count <= 20 or not 2 <= sides <= 1000:
            raise ValueError("주사위 개수는 1~20개, 면 수는 2~1000으로 입력하세요.")
        rolls = [random.randint(1, sides) for _ in range(count)]
        await interaction.response.send_message(
            f"🎲 `{count}d{sides}` → {', '.join(map(str, rolls))}\n합계: **{sum(rolls)}**"
        )

    @app_commands.command(name="동전", description="동전을 던집니다.")
    async def coin(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"🪙 **{random.choice(['앞면', '뒷면'])}**")

    @app_commands.command(name="시간", description="Discord에서 자동 변환되는 시간 태그를 만듭니다.")
    @app_commands.guild_only()
    @app_commands.rename(when="일시", style="형식")
    @app_commands.describe(when="예: 2026-08-15 18:00", style="표시 형식")
    async def timestamp(
        self,
        interaction: discord.Interaction,
        when: str,
        style: Literal["F", "f", "D", "d", "T", "t", "R"] = "F",
    ) -> None:
        timezone_name = await self.bot.db.guild_timezone(interaction.guild_id)
        parsed = parse_local_datetime(when, timezone_name)
        unix = int(parsed.timestamp())
        tag = f"<t:{unix}:{style}>"
        await interaction.response.send_message(
            f"시간대: `{timezone_name}`\n표시: {tag}\n복사용: `{tag}`",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(UtilityCog(bot))
